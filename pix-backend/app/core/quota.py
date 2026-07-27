from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from typing import Any

from redis.asyncio import Redis

from app.database import get_redis_pool

logger = logging.getLogger("pix.core.quota")


def _today() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%d")


class UserQuotaService:
    """Per-user daily quota enforcement with Redis and an in-memory fallback.

    Production deployments should provide Redis so the limit is shared across
    workers. The in-memory fallback is acceptable for single-process tests and
    local development without Redis.
    """

    def __init__(self, redis_client: Redis | None = None) -> None:
        self._redis: Redis | None = redis_client
        self._memory: dict[str, dict[str, Any]] = {}
        self._use_redis = redis_client is not None

    def _redis_key(self, user_id: str, metric: str, date: str | None = None) -> str:
        date = date or _today()
        return f"quota:{user_id}:{metric}:{date}"

    async def _increment_redis(self, key: str, ttl_seconds: int) -> int:
        if self._redis is None:
            raise RuntimeError("Redis not available")
        pipe = self._redis.pipeline()
        pipe.incr(key)
        pipe.expire(key, ttl_seconds)
        results = await pipe.execute()
        return int(results[0])

    def _increment_memory(self, key: str, ttl_seconds: int) -> int:
        now = datetime.now(UTC)
        entry = self._memory.get(key)
        if entry is None or datetime.fromisoformat(entry["expires_at"]) < now:
            self._memory[key] = {"count": 0, "expires_at": (now + timedelta(seconds=ttl_seconds)).isoformat()}
        self._memory[key]["count"] += 1
        return self._memory[key]["count"]

    async def check_and_increment(
        self,
        user_id: str,
        metric: str,
        limit: int,
        window_seconds: int = 86_400,
    ) -> tuple[bool, int]:
        """Return (allowed, current_count)."""
        if limit <= 0:
            return True, 0

        key = self._redis_key(user_id, metric)
        try:
            if self._use_redis:
                count = await self._increment_redis(key, window_seconds)
            else:
                count = self._increment_memory(key, window_seconds)
        except Exception as exc:
            logger.warning("Quota check failed for %s/%s: %s", user_id, metric, exc)
            if self._use_redis:
                # Redis became unavailable; fall back to in-memory for this process.
                self._use_redis = False
                try:
                    count = self._increment_memory(key, window_seconds)
                except Exception:
                    # Fail open if even the fallback fails.
                    return True, 0
            else:
                # Fail open if quota backend is unavailable.
                return True, 0

        return count <= limit, count

    async def current_usage(self, user_id: str, metric: str, date: str | None = None) -> int:
        key = self._redis_key(user_id, metric, date)
        try:
            if self._use_redis:
                value = await self._redis.get(key)
                return int(value) if value else 0
            entry = self._memory.get(key)
            if entry is None or datetime.fromisoformat(entry["expires_at"]) < datetime.now(UTC):
                return 0
            return entry["count"]
        except Exception as exc:
            logger.warning("Failed to read quota for %s/%s: %s", user_id, metric, exc)
            return 0


# Global singleton; safe because Redis is async-safe and memory fallback is per-process.
_quota_service: UserQuotaService | None = None


def get_quota_service() -> UserQuotaService:
    global _quota_service
    if _quota_service is None:
        try:
            redis = Redis(connection_pool=get_redis_pool())
            _quota_service = UserQuotaService(redis_client=redis)
        except Exception:
            logger.info("Redis unavailable for quota service; using in-memory fallback")
            _quota_service = UserQuotaService()
    return _quota_service


def reset_quota_service() -> None:
    global _quota_service
    _quota_service = None
