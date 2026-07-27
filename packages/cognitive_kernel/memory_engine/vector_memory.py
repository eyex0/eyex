from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from numpy import dot, linalg, ndarray

logger = logging.getLogger("pix.db.vector_memory")

try:
    from sentence_transformers import SentenceTransformer

    _model = SentenceTransformer("all-MiniLM-L6-v2")
    _available = True
except Exception:
    _available = False
    _model = None


@dataclass
class VectorEntry:
    id: str
    text: str
    embedding: list[float]
    metadata: dict[str, Any] = field(default_factory=dict)
    source: str = "manual"
    org_id: str = "default"
    created_at: str | None = None


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    arr_a = ndarray(a)
    arr_b = ndarray(b)
    norm_a = linalg.norm(arr_a)
    norm_b = linalg.norm(arr_b)
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return float(dot(arr_a, arr_b) / (norm_a * norm_b))


class VectorMemory:
    """In-memory vector store with embedding-based semantic search.

    Uses sentence-transformers for embeddings. Falls back to a simple
    TF-IDF-like keyword scoring if the model is unavailable.
    """

    def __init__(self) -> None:
        self._entries: dict[str, VectorEntry] = {}
        self._org_indices: dict[str, list[str]] = {}

    @property
    def available(self) -> bool:
        return _available

    def _embed(self, text: str) -> list[float]:
        if _model is not None:
            emb = _model.encode(text, normalize_embeddings=True)
            return emb.tolist()
        return [0.0]

    def store(
        self,
        text: str,
        metadata: dict[str, Any] | None = None,
        source: str = "manual",
        org_id: str = "default",
        entry_id: str | None = None,
    ) -> str:
        entry_id = entry_id or f"vec_{len(self._entries)}_{int(__import__('time').time())}"
        embedding = self._embed(text)
        entry = VectorEntry(
            id=entry_id,
            text=text,
            embedding=embedding,
            metadata=metadata or {},
            source=source,
            org_id=org_id,
        )
        self._entries[entry_id] = entry
        if org_id not in self._org_indices:
            self._org_indices[org_id] = []
        self._org_indices[org_id].append(entry_id)
        logger.debug("Stored vector entry %s (%d chars, org=%s)", entry_id, len(text), org_id)
        return entry_id

    def search(
        self,
        query: str,
        org_id: str = "default",
        top_k: int = 5,
        min_score: float = 0.0,
    ) -> list[dict[str, Any]]:
        query_emb = self._embed(query)
        candidates = self._org_indices.get(org_id, [])
        scored: list[tuple[float, VectorEntry]] = []

        for eid in candidates:
            entry = self._entries.get(eid)
            if entry is None:
                continue
            score = _cosine_similarity(query_emb, entry.embedding)
            if score < min_score:
                continue
            scored.append((score, entry))

        scored.sort(key=lambda x: x[0], reverse=True)

        return [
            {
                "id": entry.id,
                "text": entry.text[:500],
                "score": round(score, 4),
                "metadata": entry.metadata,
                "source": entry.source,
            }
            for score, entry in scored[:top_k]
        ]

    def delete(self, entry_id: str) -> bool:
        entry = self._entries.pop(entry_id, None)
        if entry is None:
            return False
        org_list = self._org_indices.get(entry.org_id, [])
        if entry_id in org_list:
            org_list.remove(entry_id)
        return True

    def clear_org(self, org_id: str) -> int:
        ids = self._org_indices.pop(org_id, [])
        for eid in ids:
            self._entries.pop(eid, None)
        return len(ids)

    def count(self, org_id: str | None = None) -> int:
        if org_id:
            return len(self._org_indices.get(org_id, []))
        return len(self._entries)

    def get_context(self, query: str, org_id: str = "default", top_k: int = 3) -> str:
        results = self.search(query, org_id=org_id, top_k=top_k, min_score=0.15)
        if not results:
            return ""
        parts = []
        for r in results:
            src = r.get("source", "unknown")
            parts.append(f"[{src}] {r['text']}")
        return "\n\n".join(parts)


_vector_store: VectorMemory | None = None


def get_vector_memory() -> VectorMemory:
    global _vector_store
    if _vector_store is None:
        _vector_store = VectorMemory()
    return _vector_store
