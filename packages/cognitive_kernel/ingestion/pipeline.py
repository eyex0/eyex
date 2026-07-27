"""πX Ingestion Pipeline — Full document ingestion: parse → normalize → chunk → embed → store."""
from __future__ import annotations

import logging
import time
import uuid
from typing import Any

from .parser import PARSER_REGISTRY
from packages.cognitive_kernel.memory_engine.normalizer import TextNormalizer
from packages.cognitive_kernel.memory_engine.chunker import TextChunker, ChunkingStrategy
from packages.cognitive_kernel.memory_engine.embedding_service import EmbeddingService
from packages.cognitive_kernel.memory_engine.vector_store import VectorStore

logger = logging.getLogger("pix.ingestion")


class IngestionResult:
    def __init__(self, document_id: str, chunks_created: int, embeddings_generated: int,
                 processing_time_ms: float, errors: list[str] = None):
        self.document_id = document_id
        self.chunks_created = chunks_created
        self.embeddings_generated = embeddings_generated
        self.processing_time_ms = processing_time_ms
        self.errors = errors or []

    def to_dict(self) -> dict:
        return {
            "document_id": self.document_id,
            "chunks_created": self.chunks_created,
            "embeddings_generated": self.embeddings_generated,
            "processing_time_ms": self.processing_time_ms,
            "errors": self.errors,
        }


class IngestionPipeline:
    """Full ingestion pipeline: parse → normalize → chunk → embed → store → metadata."""

    def __init__(
        self,
        vector_store: VectorStore | None = None,
        embedding_service: EmbeddingService | None = None,
        chunker: TextChunker | None = None,
        normalizer: TextNormalizer | None = None,
    ):
        self.normalizer = normalizer or TextNormalizer()
        self.chunker = chunker or TextChunker()
        self.embedding_service = embedding_service or EmbeddingService()
        self.vector_store = vector_store  # Set later with session factory

    async def ingest_file(
        self,
        file_path: str,
        file_content: bytes,
        org_id: str,
        metadata: dict[str, Any] | None = None,
    ) -> dict:
        """Ingest a file through the full pipeline."""
        start = time.monotonic()
        document_id = str(uuid.uuid4())
        errors = []

        # Step 1: Parse
        file_ext = "." + file_path.split(".")[-1].lower()
        parser = PARSER_REGISTRY.get_parser(file_ext)
        if not parser:
            errors.append(f"No parser for {file_ext}")
            return IngestionResult(document_id, 0, 0, 0, errors).to_dict()

        try:
            parsed = parser.parse(file_content)
            content = parser.extract_content(parsed)
        except Exception as exc:
            errors.append(f"Parse error: {exc}")
            return IngestionResult(document_id, 0, 0, 0, errors).to_dict()

        return await self._process_text(
            content, org_id, document_id, metadata, start, errors
        )

    async def ingest_text(
        self,
        text: str,
        org_id: str,
        metadata: dict[str, Any] | None = None,
    ) -> dict:
        """Ingest raw text through the pipeline."""
        start = time.monotonic()
        document_id = str(uuid.uuid4())
        return await self._process_text(text, org_id, document_id, metadata, start, [])

    async def _process_text(
        self,
        content: str,
        org_id: str,
        document_id: str,
        metadata: dict | None,
        start_time: float,
        errors: list[str],
    ) -> dict:
        # Step 2: Normalize
        content = self.normalizer.normalize(content)
        content = self.normalizer.clean(content)

        # Step 3: Chunk (semantic strategy for better quality)
        chunks = self.chunker.chunk_semantic(content)
        if not chunks:
            chunks = self.chunker.chunk_fixed_size(content)

        # Step 4: Embed
        chunk_texts = [c["text"] for c in chunks]
        try:
            embeddings = await self.embedding_service.embed_batch(chunk_texts)
        except Exception as exc:
            errors.append(f"Embedding error: {exc}")
            embeddings = [[0.0] * 1536] * len(chunk_texts)

        # Step 5: Store
        chunks_created = 0
        for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
            chunk_meta = {
                **(metadata or {}),
                "chunk_index": i,
                "token_count": chunk["token_count"],
                "source": "ingestion_pipeline",
            }
            try:
                if self.vector_store:
                    await self.vector_store.store(
                        chunk_id=chunk["id"],
                        text=chunk["text"],
                        embedding=embedding,
                        metadata=chunk_meta,
                        org_id=org_id,
                        document_id=document_id,
                    )
                chunks_created += 1
            except Exception as exc:
                errors.append(f"Store error chunk {i}: {exc}")

        elapsed = (time.monotonic() - start_time) * 1000
        logger.info("Ingested doc %s: %d chunks, %d embeddings, %.0fms",
                    document_id, chunks_created, len(embeddings), elapsed)

        return IngestionResult(
            document_id=document_id,
            chunks_created=chunks_created,
            embeddings_generated=len(embeddings),
            processing_time_ms=elapsed,
            errors=errors,
        ).to_dict()
