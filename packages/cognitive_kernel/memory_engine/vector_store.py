"""πX Vector Store — pgvector-backed vector storage and search."""
from __future__ import annotations

import logging
import uuid
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

logger = logging.getLogger("pix.memory.vector_store")


class VectorStore:
    """PostgreSQL + pgvector vector store for semantic search."""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession] | None = None):
        self.session_factory = session_factory

    async def store(
        self,
        chunk_id: str | None,
        text: str,
        embedding: list[float],
        metadata: dict[str, Any],
        org_id: str,
        document_id: str | None = None,
    ) -> str:
        """Store a text chunk with its embedding."""
        chunk_id = chunk_id or str(uuid.uuid4())
        async with self.session_factory() as db:
            await db.execute(
                text(
                    "INSERT INTO memory_chunks (id, org_id, document_id, text, embedding, metadata) "
                    "VALUES (:id, :org_id, :doc_id, :text, CAST(:embedding AS vector), :metadata)"
                ),
                {
                    "id": chunk_id,
                    "org_id": org_id,
                    "doc_id": document_id,
                    "text": text,
                    "embedding": str(embedding),
                    "metadata": str(metadata).replace("'", '"'),
                },
            )
            await db.commit()
        logger.debug("Stored chunk %s for org %s", chunk_id, org_id)
        return chunk_id

    async def search(
        self,
        query_embedding: list[float],
        limit: int = 10,
        filter_metadata: dict[str, Any] | None = None,
        org_id: str | None = None,
    ) -> list[dict[str, Any]]:
        """Semantic search using cosine similarity."""
        conditions = []
        params: dict[str, Any] = {"embedding": str(query_embedding), "limit": limit}

        if org_id:
            conditions.append("org_id = :org_id")
            params["org_id"] = org_id

        if filter_metadata:
            for key, value in filter_metadata.items():
                conditions.append(f"metadata->>'{key}' = :meta_{key}")
                params[f"meta_{key}"] = str(value)

        where = " AND ".join(conditions) if conditions else "true"
        query = text(
            f"SELECT id, text, metadata, "
            f"1 - (embedding <=> CAST(:embedding AS vector)) AS score "
            f"FROM memory_chunks WHERE {where} "
            f"ORDER BY embedding <=> CAST(:embedding AS vector) "
            f"LIMIT :limit"
        )
        async with self.session_factory() as db:
            result = await db.execute(query, params)
            rows = result.fetchall()
            return [
                {"id": str(r[0]), "text": r[1], "metadata": r[2], "score": float(r[3])}
                for r in rows
            ]

    async def hybrid_search(
        self,
        query_text: str,
        query_embedding: list[float],
        limit: int = 10,
        org_id: str | None = None,
    ) -> list[dict[str, Any]]:
        """Hybrid search: combine keyword (tsvector) + vector similarity."""
        conditions = ["text ILIKE :query"]
        params: dict[str, Any] = {
            "embedding": str(query_embedding),
            "query": f"%{query_text}%",
            "limit": limit,
        }
        if org_id:
            conditions.append("org_id = :org_id")
            params["org_id"] = org_id

        where = " AND ".join(conditions)
        query = text(
            f"SELECT id, text, metadata, "
            f"1 - (embedding <=> CAST(:embedding AS vector)) AS vector_score, "
            f"CASE WHEN text ILIKE :query THEN 1.0 ELSE 0.0 END AS keyword_score "
            f"FROM memory_chunks WHERE {where} "
            f"ORDER BY (vector_score * 0.7 + keyword_score * 0.3) DESC "
            f"LIMIT :limit"
        )
        async with self.session_factory() as db:
            result = await db.execute(query, params)
            rows = result.fetchall()
            return [
                {
                    "id": str(r[0]),
                    "text": r[1],
                    "metadata": r[2],
                    "score": float(r[3]) * 0.7 + float(r[4]) * 0.3,
                }
                for r in rows
            ]

    async def delete(self, chunk_id: str) -> bool:
        async with self.session_factory() as db:
            result = await db.execute(
                text("DELETE FROM memory_chunks WHERE id = :id"), {"id": chunk_id}
            )
            await db.commit()
            return result.rowcount > 0

    async def update(
        self, chunk_id: str, text: str | None = None, metadata: dict | None = None
    ) -> bool:
        sets = []
        params: dict[str, Any] = {"id": chunk_id}
        if text is not None:
            sets.append("text = :text")
            params["text"] = text
        if metadata is not None:
            sets.append("metadata = :metadata")
            params["metadata"] = str(metadata).replace("'", '"')
        if not sets:
            return False
        async with self.session_factory() as db:
            await db.execute(
                text(f"UPDATE memory_chunks SET {', '.join(sets)} WHERE id = :id"), params
            )
            await db.commit()
            return True
