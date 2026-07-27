"""πX Entity Extractor — LLM-based entity and relationship extraction."""
from __future__ import annotations

import json
import logging
from typing import Any

from packages.cognitive_kernel.ai_gateway import AI_GATEWAY

logger = logging.getLogger("pix.knowledge.extractor")

ENTITY_TYPES = ["Company", "Customer", "Product", "Employee", "Project",
                 "Decision", "Document", "Metric", "Vendor", "Market", "Technology"]
RELATION_TYPES = ["owns", "uses", "depends_on", "impacts", "causes",
                  "related_to", "part_of", "drives", "generates", "requires"]


class EntityExtractor:
    """Extract entities and relationships from text using LLM."""

    def __init__(self, gateway=None):
        self.gateway = gateway or AI_GATEWAY

    async def extract_entities(self, text: str, org_id: str = "default") -> list[dict]:
        prompt = f"""Extract entities from the following text. Return a JSON array of objects.
Each object: {{"name": "...", "entity_type": "...", "properties": {{}}, "confidence": 0.0-1.0}}
Entity types: {", ".join(ENTITY_TYPES)}

Text:
{text[:8000]}

Return ONLY the JSON array, no other text."""

        try:
            response = await self.gateway.generate(
                __import__("packages.cognitive_kernel.ai_gateway.providers.base", fromlist=["GenerateRequest"]).GenerateRequest(
                    prompt=prompt, temperature=0.3, max_tokens=2000
                )
            )
            content = response.content.strip()
            if content.startswith("```"):
                content = content.split("\n", 1)[1].rsplit("```", 1)[0]
            entities = json.loads(content)
            return [e for e in entities if e.get("name") and e.get("entity_type")]
        except Exception as exc:
            logger.error("Entity extraction failed: %s", exc)
            return []

    async def extract_relationships(self, text: str, entities: list[dict]) -> list[dict]:
        entity_names = [e["name"] for e in entities]
        prompt = f"""Extract relationships between entities from the text. Return a JSON array.
Each object: {{"source": "entity_name", "target": "entity_name", "relation_type": "...", "confidence": 0.0-1.0}}
Relation types: {", ".join(RELATION_TYPES)}
Entities found: {entity_names}

Text:
{text[:8000]}

Return ONLY the JSON array."""

        try:
            response = await self.gateway.generate(
                __import__("packages.cognitive_kernel.ai_gateway.providers.base", fromlist=["GenerateRequest"]).GenerateRequest(
                    prompt=prompt, temperature=0.3, max_tokens=1500
                )
            )
            content = response.content.strip()
            if content.startswith("```"):
                content = content.split("\n", 1)[1].rsplit("```", 1)[0]
            rels = json.loads(content)
            return [r for r in rels if r.get("source") and r.get("target") and r.get("relation_type")]
        except Exception as exc:
            logger.error("Relationship extraction failed: %s", exc)
            return []

    async def resolve_entity(self, entity: dict, existing_entities: list[dict]) -> str:
        """Match entity to existing one by name (fuzzy), or return 'new'."""
        name = entity.get("name", "").lower().strip()
        for existing in existing_entities:
            if existing.get("label", "").lower().strip() == name:
                return existing["id"]
        return "new"
