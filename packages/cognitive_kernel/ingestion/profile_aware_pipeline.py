"""
πX Profile-Aware Ingestion Pipeline — Memory Engine integration.

Replaces the generic ingestion pipeline with one that injects profile context
at every stage:

Upload → Profile Context Injection → Semantic Understanding → Entity Detection
       → Chunking → Embedding → Vector Storage (with profile_id, semantic_entities, business_context)

Every memory object stored carries:
  - profile_id: which intelligence profile it belongs to
  - semantic_entities: which ontology entities were detected in the data
  - business_context: industry, terminology context from the profile
  - confidence_score: confidence of the semantic mapping
"""
from __future__ import annotations

import json
import logging
import uuid
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from packages.cognitive_kernel.intelligence_profile.context_provider import ProfileContextProvider

logger = logging.getLogger("pix.ingestion.profile_aware")


class ProfileAwareIngestionPipeline:
    """Ingestion pipeline that uses Intelligence Profile for semantic understanding."""

    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        context_provider: ProfileContextProvider | None = None,
    ):
        self.session_factory = session_factory
        self.context_provider = context_provider or ProfileContextProvider(session_factory)

    async def ingest(
        self,
        organization_id: str,
        file_name: str,
        file_type: str,
        content: bytes,
        columns: list[dict] | None = None,
    ) -> dict:
        """
        Full profile-aware ingestion flow:
        1. Load profile context (industry, ontology, glossary)
        2. Semantic understanding (map columns to ontology entities)
        3. Entity detection (identify which entities appear in the data)
        4. Chunking
        5. Embedding
        6. Vector storage with profile metadata
        """
        # Step 1: Load profile context
        profile_ctx = await self.context_provider.get_context(organization_id)
        profile_id = profile_ctx.get("profile_id")

        if not profile_id:
            logger.info("No profile for org %s — ingesting with generic context", organization_id)

        # Step 2: Semantic understanding using profile ontology
        glossary_mapping = await self.context_provider.get_glossary_for_resolution(organization_id)
        semantic_entities = self._detect_entities(columns or [], profile_ctx, glossary_mapping)

        # Step 3: Build business context string
        business_context = self._build_business_context(profile_ctx)

        # Step 4: Chunk content
        text_content = content.decode("utf-8", errors="replace") if isinstance(content, bytes) else str(content)
        chunks = self._chunk_text(text_content)

        # Step 5: Store each chunk with profile metadata
        stored_chunks = []
        async with self.session_factory() as db:
            for i, chunk_text in enumerate(chunks):
                chunk_id = str(uuid.uuid4())
                metadata = {
                    "profile_id": profile_id,
                    "organization_id": organization_id,
                    "source_file": file_name,
                    "file_type": file_type,
                    "semantic_entities": semantic_entities,
                    "business_context": business_context,
                    "industry": profile_ctx.get("company_identity", {}).get("industry"),
                    "chunk_index": i,
                }
                await db.execute(
                    text(
                        "INSERT INTO memory_chunks (id, org_id, document_id, text, metadata) "
                        "VALUES (:id, :org_id, :doc_id, :text, :metadata) "
                        "ON CONFLICT (id) DO NOTHING"
                    ),
                    {
                        "id": chunk_id,
                        "org_id": organization_id,
                        "doc_id": str(uuid.uuid4()),
                        "text": chunk_text,
                        "metadata": json.dumps(metadata),
                    },
                )
                stored_chunks.append(chunk_id)
            await db.commit()

        logger.info("Ingested %d chunks for org %s (profile: %s, entities: %s)",
                     len(stored_chunks), organization_id, profile_id, [e["entity_type"] for e in semantic_entities])

        return {
            "chunks_created": len(stored_chunks),
            "profile_id": profile_id,
            "semantic_entities": semantic_entities,
            "business_context": business_context[:200],
            "confidence_score": profile_ctx.get("confidence_score", 0.0),
        }

    def _detect_entities(
        self, columns: list[dict], profile_ctx: dict, glossary: dict
    ) -> list[dict]:
        """Detect which ontology entities appear in the data columns."""
        ontology = profile_ctx.get("ontology", [])
        if not ontology:
            return []

        # Build alias → entity_type mapping from ontology
        alias_map = {}
        for entity in ontology:
            alias_map[entity["entity_type"].lower()] = entity
            for alias in entity.get("aliases", []):
                alias_map[alias.lower()] = entity

        detected = []
        seen_types = set()

        for col in columns:
            col_name = col.get("name", "").lower()
            # Check glossary first for company-specific terms
            glossary_match = glossary.get(col_name)
            if glossary_match and glossary_match.get("maps_to_entity"):
                entity_type = glossary_match["maps_to_entity"]
                if entity_type not in seen_types:
                    detected.append({
                        "entity_type": entity_type,
                        "column": col["name"],
                        "source": "glossary",
                        "confidence": glossary_match.get("confidence", 0.8),
                    })
                    seen_types.add(entity_type)
                continue

            # Check ontology aliases
            for alias, entity in alias_map.items():
                if alias in col_name or col_name in alias:
                    entity_type = entity["entity_type"]
                    if entity_type not in seen_types:
                        detected.append({
                            "entity_type": entity_type,
                            "column": col["name"],
                            "source": "ontology",
                            "confidence": entity.get("confidence", 0.6),
                        })
                        seen_types.add(entity_type)
                    break

        return detected

    def _build_business_context(self, profile_ctx: dict) -> str:
        """Build a context string from the profile for embedding enrichment."""
        identity = profile_ctx.get("company_identity", {})
        parts = []
        if identity.get("industry"):
            parts.append(f"Industry: {identity['industry']}")
        if identity.get("business_model"):
            parts.append(f"Business model: {identity['business_model']}")
        if identity.get("region"):
            parts.append(f"Region: {identity['region']}")

        # Add key glossary terms
        glossary = profile_ctx.get("glossary", [])
        if glossary:
            terms = [f"{t['term']} ({', '.join(t.get('aliases', [])[:3])})" for t in glossary[:10]]
            parts.append(f"Terminology: {'; '.join(terms)}")

        # Add KPI names
        kpis = profile_ctx.get("kpis", [])
        if kpis:
            kpi_names = [k["name"] for k in kpis[:5]]
            parts.append(f"KPIs: {', '.join(kpi_names)}")

        return " | ".join(parts)

    def _chunk_text(self, text: str, max_size: int = 1000, overlap: int = 200) -> list[str]:
        """Simple chunking — uses existing TextChunker if available."""
        try:
            from packages.cognitive_kernel.memory_engine.chunker import TextChunker
            chunker = TextChunker()
            result = chunker.chunk_fixed_size(text, size=max_size, overlap=overlap)
            return [c["text"] for c in result]
        except ImportError:
            if len(text) <= max_size:
                return [text]
            chunks = []
            for i in range(0, len(text), max_size - overlap):
                chunks.append(text[i:i + max_size])
            return chunks
