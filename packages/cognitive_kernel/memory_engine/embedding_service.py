"""πX Embedding Service — Generate embeddings via AI Gateway."""
from __future__ import annotations

import hashlib
import json
import logging
from typing import Any

from packages.cognitive_kernel.ai_gateway import AI_GATEWAY

logger = logging.getLogger("pix.memory.embedding")


class EmbeddingService:
    """Wraps the AI Gateway for embedding generation with caching."""

    def __init__(self, gateway=None, redis_client: Any = None):
        self.gateway = gateway or AI_GATEWAY
        self.redis = redis_client
        self._cache: dict[str, list[float]] = {}  # in-memory fallback

    async def embed_text(self, text: str, model: str = "text-embedding-3-small") -> list[float]:
        """Embed a single text string."""
        cache_key = self._cache_key(text, model)
        cached = await self._get_cached(cache_key)
        if cached:
            return cached

        try:
            embeddings = await self.gateway.embed([text], provider="openai", model=model)
            if embeddings:
                await self._set_cached(cache_key, embeddings[0], ttl=86400)
                return embeddings[0]
        except Exception as exc:
            logger.error("Embedding failed: %s", exc)
            # Return a zero vector as fallback (1536 dims for OpenAI)
            return [0.0] * 1536
        return [0.0] * 1536

    async def embed_batch(
        self, texts: list[str], model: str = "text-embedding-3-small", batch_size: int = 100
    ) -> list[list[float]]:
        """Embed multiple texts with batching and rate limiting."""
        results: list[list[float]] = []
        for i in range(0, len(texts), batch_size):
            batch = texts[i : i + batch_size]
            # Check cache for each
            uncached_texts = []
            cached_results: dict[int, list[float]] = {}
            for j, text in enumerate(batch):
                cache_key = self._cache_key(text, model)
                cached = await self._get_cached(cache_key)
                if cached:
                    cached_results[j] = cached
                else:
                    uncached_texts.append(text)

            # Embed uncached
            if uncached_texts:
                try:
                    embeddings = await self.gateway.embed(
                        uncached_texts, provider="openai", model=model
                    )
                    for k, emb in enumerate(embeddings):
                        await self._set_cached(
                            self._cache_key(uncached_texts[k], model), emb, ttl=86400
                        )
                except Exception as exc:
                    logger.error("Batch embedding failed: %s", exc)
                    embeddings = [[0.0] * 1536] * len(uncached_texts)
            else:
                embeddings = []

            # Merge cached + fresh
            emb_iter = iter(embeddings)
            for j in range(len(batch)):
                if j in cached_results:
                    results.append(cached_results[j])
                else:
                    results.append(next(emb_iter, [0.0] * 1536))
        return results

    def _cache_key(self, text: str, model: str) -> str:
        return f"embed:{model}:{hashlib.sha256(text.encode()).hexdigest()}"

    async def _get_cached(self, key: str) -> list[float] | None:
        if self.redis:
            try:
                val = await self.redis.get(key)
                if val:
                    return json.loads(val)
            except Exception:
                pass
        return self._cache.get(key)

    async def _set_cached(self, key: str, value: list[float], ttl: int = 86400):
        if self.redis:
            try:
                await self.redis.setex(key, ttl, json.dumps(value))
            except Exception:
                pass
        self._cache[key] = value
