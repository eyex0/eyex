import os
import json
from datetime import datetime, UTC
from typing import Any, Dict, List, Optional
from redis.asyncio import Redis, ConnectionPool

_redis_pool: Optional[ConnectionPool] = None

def get_redis_client() -> Redis:
    global _redis_pool
    if _redis_pool is None:
        redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
        _redis_pool = ConnectionPool.from_url(redis_url, max_connections=50, decode_responses=True)
    return Redis(connection_pool=_redis_pool)

class CostTracker:
    def __init__(self, redis_client: Optional[Redis] = None):
        self.redis = redis_client or get_redis_client()

    def _get_date_str(self) -> str:
        return datetime.now(UTC).strftime("%Y-%m-%d")

    async def record_usage(
        self,
        org_id: str,
        provider: str,
        model: str,
        input_tokens: int,
        output_tokens: int,
        cost: float
    ) -> None:
        """Records AI model usage and costs in Redis."""
        if not org_id:
            org_id = "default_org"

        date_str = self._get_date_str()
        
        # Track all unique orgs and dates
        await self.redis.sadd("cost_tracker:orgs", org_id)
        await self.redis.sadd(f"cost_tracker:org:{org_id}:dates", date_str)

        # Hash key for the specific org and date
        hash_key = f"cost_tracker:org:{org_id}:{date_str}"
        
        # Pipeline to increment usage fields
        async with self.redis.pipeline(transaction=True) as pipe:
            pipe.hincrbyfloat(hash_key, f"{provider}:{model}:cost", cost)
            pipe.hincrby(hash_key, f"{provider}:{model}:input_tokens", input_tokens)
            pipe.hincrby(hash_key, f"{provider}:{model}:output_tokens", output_tokens)
            pipe.hincrby(hash_key, f"{provider}:{model}:requests", 1)
            await pipe.execute()

    async def get_cost_summary(self, org_id: str) -> Dict[str, Any]:
        """Returns summarized usage info for a given org (aggregated across all time)."""
        if not org_id:
            org_id = "default_org"

        dates = await self.redis.smembers(f"cost_tracker:org:{org_id}:dates")
        
        total_cost = 0.0
        total_input_tokens = 0
        total_output_tokens = 0
        total_requests = 0
        by_provider: Dict[str, Dict[str, Any]] = {}

        for date_str in dates:
            hash_key = f"cost_tracker:org:{org_id}:{date_str}"
            data = await self.redis.hgetall(hash_key)
            if not data:
                continue

            for key, val in data.items():
                parts = key.split(":")
                if len(parts) != 3:
                    continue
                provider, model, field = parts
                
                if provider not in by_provider:
                    by_provider[provider] = {
                        "cost": 0.0,
                        "input_tokens": 0,
                        "output_tokens": 0,
                        "requests": 0,
                        "models": {}
                    }
                
                if model not in by_provider[provider]["models"]:
                    by_provider[provider]["models"][model] = {
                        "cost": 0.0,
                        "input_tokens": 0,
                        "output_tokens": 0,
                        "requests": 0
                    }

                if field == "cost":
                    f_val = float(val)
                    total_cost += f_val
                    by_provider[provider]["cost"] += f_val
                    by_provider[provider]["models"][model]["cost"] += f_val
                elif field == "input_tokens":
                    i_val = int(val)
                    total_input_tokens += i_val
                    by_provider[provider]["input_tokens"] += i_val
                    by_provider[provider]["models"][model]["input_tokens"] += i_val
                elif field == "output_tokens":
                    i_val = int(val)
                    total_output_tokens += i_val
                    by_provider[provider]["output_tokens"] += i_val
                    by_provider[provider]["models"][model]["output_tokens"] += i_val
                elif field == "requests":
                    i_val = int(val)
                    total_requests += i_val
                    by_provider[provider]["requests"] += i_val
                    by_provider[provider]["models"][model]["requests"] += i_val

        return {
            "org_id": org_id,
            "total_cost": total_cost,
            "total_input_tokens": total_input_tokens,
            "total_output_tokens": total_output_tokens,
            "total_tokens": total_input_tokens + total_output_tokens,
            "total_requests": total_requests,
            "by_provider": by_provider
        }

    async def get_usage_report(
        self,
        org_id: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Returns daily usage report within the start and end dates (inclusive)."""
        if not org_id:
            org_id = "default_org"

        dates = await self.redis.smembers(f"cost_tracker:org:{org_id}:dates")
        sorted_dates = sorted(list(dates))

        report = []
        for date_str in sorted_dates:
            if start_date and date_str < start_date:
                continue
            if end_date and date_str > end_date:
                continue

            hash_key = f"cost_tracker:org:{org_id}:{date_str}"
            data = await self.redis.hgetall(hash_key)
            if not data:
                continue

            day_cost = 0.0
            day_input_tokens = 0
            day_output_tokens = 0
            day_requests = 0
            breakdown: Dict[str, Dict[str, Any]] = {}

            for key, val in data.items():
                parts = key.split(":")
                if len(parts) != 3:
                    continue
                provider, model, field = parts
                
                model_key = f"{provider}:{model}"
                if model_key not in breakdown:
                    breakdown[model_key] = {
                        "provider": provider,
                        "model": model,
                        "cost": 0.0,
                        "input_tokens": 0,
                        "output_tokens": 0,
                        "requests": 0
                    }

                if field == "cost":
                    f_val = float(val)
                    day_cost += f_val
                    breakdown[model_key]["cost"] += f_val
                elif field == "input_tokens":
                    i_val = int(val)
                    day_input_tokens += i_val
                    breakdown[model_key]["input_tokens"] += i_val
                elif field == "output_tokens":
                    i_val = int(val)
                    day_output_tokens += i_val
                    breakdown[model_key]["output_tokens"] += i_val
                elif field == "requests":
                    i_val = int(val)
                    day_requests += i_val
                    breakdown[model_key]["requests"] += i_val

            report.append({
                "date": date_str,
                "total_cost": day_cost,
                "total_input_tokens": day_input_tokens,
                "total_output_tokens": day_output_tokens,
                "total_requests": day_requests,
                "breakdown": list(breakdown.values())
            })

        return report

COST_TRACKER = CostTracker()
