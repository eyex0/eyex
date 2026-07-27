"""
πX Profile-Aware Entity Extractor — Knowledge Graph integration.

Instead of using hardcoded entity types (Company, Customer, Product, etc.),
this extractor reads the organization's Intelligence Profile ontology and
dynamically builds extraction prompts from the company's custom entity types.

Retail company → extracts Store, Product, Customer, Promotion
Manufacturing company → extracts Machine, WorkOrder, Supplier, Material
"""
from __future__ import annotations

import json
import logging
from typing import Any

from packages.cognitive_kernel.ai_gateway import AI_GATEWAY
from packages.cognitive_kernel.ai_gateway.providers.base import GenerateRequest
from packages.cognitive_kernel.intelligence_profile.context_provider import ProfileContextProvider

logger = logging.getLogger("pix.knowledge_graph.profile_aware_extractor")


class ProfileAwareEntityExtractor:
    """Extracts entities using the organization's custom ontology — not hardcoded types."""

    def __init__(
        self,
        session_factory=None,
        gateway=None,
        context_provider: ProfileContextProvider | None = None,
    ):
        self.gateway = gateway or AI_GATEWAY
        self.context_provider = context_provider

    async def extract(
        self,
        organization_id: str,
        text: str,
        context_provider: ProfileContextProvider | None = None,
    ) -> dict:
        """
        Extract entities and relationships from text using the org's ontology.

        Returns:
            {
                "entities": [{"name": "...", "entity_type": "...", "confidence": 0.x}],
                "relationships": [{"source": "...", "target": "...", "type": "...", "confidence": 0.x}]
            }
        """
        provider = context_provider or self.context_provider
        if not provider:
            raise ValueError("ProfileContextProvider is required for profile-aware extraction")

        # Load ontology from profile
        profile_ctx = await provider.get_context(organization_id)
        ontology = profile_ctx.get("ontology", [])

        if not ontology:
            # Fallback to generic extraction if no profile exists
            logger.info("No ontology in profile for org %s — using generic extraction", organization_id)
            return await self._generic_extract(text)

        # Build entity type list for prompt
        entity_types_desc = self._build_ontology_prompt(ontology)

        # Build glossary context
        glossary = profile_ctx.get("glossary", [])
        glossary_str = "\n".join(
            f"- {t['term']}: {t.get('definition', '')} (aliases: {', '.join(t.get('aliases', [])[:3])})"
            for t in glossary[:15]
        ) if glossary else "No company-specific terminology defined."

        # Build KPI context (entities may relate to KPIs)
        kpis = profile_ctx.get("kpis", [])
        kpi_str = "\n".join(f"- {k['name']}: {k.get('definition', '')}" for k in kpis[:10]) if kpis else ""

        prompt = f"""Extract entities and relationships from the following text.

Company industry: {profile_ctx.get('company_identity', {}).get('industry', 'unknown')}

Entity types (from the company's intelligence profile):
{entity_types_desc}

Company terminology:
{glossary_str}

{"Company KPIs (for context):": ''}
{kpi_str}

Text to analyze:
{text[:4000]}

Return a JSON object:
{{
    "entities": [{{"name": "...", "entity_type": "one of the types above", "confidence": 0.0-1.0}}],
    "relationships": [{{"source": "entity_name", "target": "entity_name", "type": "relationship_type", "confidence": 0.0-1.0}}]
}}

Return ONLY the JSON."""

        try:
            response = await self.gateway.generate(
                GenerateRequest(prompt=prompt, temperature=0.3, max_tokens=2000)
            )
            content = response.content.strip()
            if content.startswith("```"):
                content = content.split("\n", 1)[1].rsplit("```", 1)[0]
            result = json.loads(content)

            # Validate entity types against ontology
            valid_types = {e["entity_type"].lower() for e in ontology}
            entities = []
            for entity in result.get("entities", []):
                et = entity.get("entity_type", "").lower()
                if et in valid_types:
                    entities.append(entity)
                else:
                    # Try to match via aliases
                    for ont_entity in ontology:
                        if et in [a.lower() for a in ont_entity.get("aliases", [])]:
                            entity["entity_type"] = ont_entity["entity_type"]
                            entities.append(entity)
                            break

            return {
                "entities": entities,
                "relationships": result.get("relationships", []),
                "ontology_used": [e["entity_type"] for e in ontology],
                "profile_id": profile_ctx.get("profile_id"),
            }
        except Exception as exc:
            logger.error("Profile-aware extraction failed: %s", exc)
            return await self._generic_extract(text)

    def _build_ontology_prompt(self, ontology: list[dict]) -> str:
        """Build entity type descriptions from the org's ontology."""
        lines = []
        for entity in ontology:
            aliases = ", ".join(entity.get("aliases", []))
            label = entity.get("label") or entity["entity_type"]
            desc = f"- {entity['entity_type']} (label: {label}"
            if aliases:
                desc += f", also known as: {aliases}"
            desc += ")"
            # Add properties if available
            props = entity.get("properties_schema", {})
            if props and isinstance(props, dict) and props.get("fields"):
                field_names = [f["name"] for f in props["fields"][:5]]
                desc += f" — fields: {', '.join(field_names)}"
            lines.append(desc)
        return "\n".join(lines) if lines else "No entity types defined"

    async def _generic_extract(self, text: str) -> dict:
        """Fallback extraction when no profile exists."""
        prompt = f"""Extract key entities and relationships from this text.
Return JSON: {{"entities": [{{"name": "...", "entity_type": "...", "confidence": 0.0-1.0}}], "relationships": []}}
Text: {text[:3000]}
Return ONLY the JSON."""
        try:
            response = await self.gateway.generate(
                GenerateRequest(prompt=prompt, temperature=0.3, max_tokens=1500)
            )
            content = response.content.strip()
            if content.startswith("```"):
                content = content.split("\n", 1)[1].rsplit("```", 1)[0]
            return json.loads(content)
        except Exception as exc:
            logger.error("Generic extraction failed: %s", exc)
            return {"entities": [], "relationships": []}
