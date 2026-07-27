import os
import json
import math
from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel
from redis.asyncio import Redis, ConnectionPool

_redis_pool: Optional[ConnectionPool] = None

def get_redis_client() -> Redis:
    global _redis_pool
    if _redis_pool is None:
        redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
        _redis_pool = ConnectionPool.from_url(redis_url, max_connections=50, decode_responses=True)
    return Redis(connection_pool=_redis_pool)

def cosine_similarity(v1: List[float], v2: List[float]) -> float:
    if not v1 or not v2 or len(v1) != len(v2):
        return 0.0
    dot_product = sum(a * b for a, b in zip(v1, v2))
    mag_v1 = math.sqrt(sum(a * a for a in v1))
    mag_v2 = math.sqrt(sum(b * b for b in v2))
    if mag_v1 == 0 or mag_v2 == 0:
        return 0.0
    return dot_product / (mag_v1 * mag_v2)

class SemanticCache:
    def __init__(self, redis_client: Optional[Redis] = None, similarity_threshold: float = 0.95):
        self.redis = redis_client or get_redis_client()
        self.similarity_threshold = similarity_threshold

    async def get(
        self,
        prompt_hash: str,
        prompt: Optional[str] = None,
        embedding: Optional[List[float]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Retrieves cached response. Supports direct lookup by hash and semantic similarity lookup if embedding is provided.
        """
        # 1. Direct match (O(1) lookup)
        direct_key = f"semantic_cache:hash:{prompt_hash}"
        cached_data = await self.redis.get(direct_key)
        if cached_data:
            try:
                return json.loads(cached_data)
            except json.JSONDecodeError:
                pass

        # 2. Semantic match (O(N) search over active keys)
        if embedding:
            active_hashes = await self.redis.smembers("semantic_cache:keys")
            best_match: Optional[Dict[str, Any]] = None
            highest_sim = 0.0

            for h in active_hashes:
                # Direct check if this key is still alive in redis
                data_key = f"semantic_cache:data:{h}"
                raw_data = await self.redis.get(data_key)
                if not raw_data:
                    # Key expired in Redis; clean up our tracking set
                    await self.redis.srem("semantic_cache:keys", h)
                    continue

                try:
                    data = json.loads(raw_data)
                    cached_embedding = data.get("embedding")
                    if cached_embedding:
                        sim = cosine_similarity(embedding, cached_embedding)
                        if sim > highest_sim:
                            highest_sim = sim
                            best_match = data.get("response")
                except Exception:
                    continue

            if highest_sim > self.similarity_threshold and best_match:
                return best_match

        return None

    async def set(
        self,
        prompt_hash: str,
        response: Union[Dict[str, Any], str, BaseModel],
        prompt: str = "",
        embedding: Optional[List[float]] = None,
        ttl: int = 3600
    ) -> None:
        """
        Caches the response. Optionally records embedding and raw prompt for semantic matching.
        """
        # Serialize response
        if isinstance(response, BaseModel):
            resp_dict = response.model_dump()
        elif isinstance(response, dict):
            resp_dict = response
        else:
            resp_dict = {"content": str(response)}

        serialized_resp = json.dumps(resp_dict)

        # 1. Store direct lookup key
        direct_key = f"semantic_cache:hash:{prompt_hash}"
        await self.redis.setex(direct_key, ttl, serialized_resp)

        # 2. Store semantic data key if embedding and prompt are provided
        if embedding and prompt:
            data_key = f"semantic_cache:data:{prompt_hash}"
            semantic_data = {
                "prompt": prompt,
                "embedding": embedding,
                "response": resp_dict
            }
            await self.redis.setex(data_key, ttl, json.dumps(semantic_data))
            await self.redis.sadd("semantic_cache:keys", prompt_hash)

    async def invalidate(self, prompt_hash: Optional[str] = None) -> None:
        """
        Invalidates a specific cached prompt hash, or clears all cached queries if prompt_hash is None.
        """
        if prompt_hash:
            await self.redis.delete(f"semantic_cache:hash:{prompt_hash}")
            await self.redis.delete(f"semantic_cache:data:{prompt_hash}")
            await self.redis.srem("semantic_cache:keys", prompt_hash)
        else:
            # Clear all semantic cache keys
            active_hashes = await self.redis.smembers("semantic_cache:keys")
            keys_to_delete = [f"semantic_cache:hash:{h}" for h in active_hashes]
            keys_to_delete += [f"semantic_cache:data:{h}" for h in active_hashes]
            keys_to_delete.append("semantic_cache:keys")
            
            # Find direct cache keys using scan just in case
            cursor = 0
            while True:
                cursor, keys = await self.redis.scan(cursor, match="semantic_cache:*", count=100)
                if keys:
                    keys_to_delete.extend(keys)
                if cursor == 0:
                    break
                    
            unique_keys = list(set(keys_to_delete))
            if unique_keys:
                await self.redis.delete(*unique_keys)

SEMANTIC_CACHE = SemanticCache()
