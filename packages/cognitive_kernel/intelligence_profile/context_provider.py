"""
πX Profile Context Provider — Unified context layer for all intelligence engines.

Every engine calls ProfileContextProvider.get_context(org_id) instead of using
hardcoded entity types, KPIs, or terminology. This is the single integration point
between the Intelligence Profile and the rest of the cognitive architecture.
"""
from __future__ import annotations

import json
import logging
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

logger = logging.getLogger("pix.intelligence_profile.context_provider")


class ProfileContextProvider:
    """
    Loads and caches the full organization intelligence profile as a context object.
    All engines use this instead of hardcoded assumptions.
    """

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]):
        self.session_factory = session_factory
        self._cache: dict[str, dict] = {}
        self._cache_ttl_seconds = 300  # 5-minute cache

    async def get_context(self, organization_id: str) -> dict:
        """
        Return the full intelligence context for an organization:
        {
            company_identity: {industry, business_model, size, region, locations},
            ontology: [entity definitions],
            glossary: [terms],
            kpis: [KPI definitions],
            data_sources: [connected systems],
            agents: [recommended agent configs],
            ai_preferences: {models, budget, privacy}
        }
        """
        # Check cache
        cached = self._cache.get(organization_id)
        if cached:
            return cached

        context = await self._load_full_context(organization_id)
        self._cache[organization_id] = context
        return context

    async def _load_full_context(self, organization_id: str) -> dict:
        """Load all profile components from the database."""
        async with self.session_factory() as db:
            # Load profile
            profile_result = await db.execute(
                text(
                    "SELECT id, industry, business_model, company_size, region, locations, "
                    "profile_config, confidence_score, status "
                    "FROM intelligence_profiles WHERE organization_id = :org_id "
                    "AND status != 'archived' ORDER BY updated_at DESC LIMIT 1"
                ),
                {"org_id": organization_id},
            )
            profile_row = profile_result.fetchone()

            if not profile_row:
                logger.info("No profile found for org %s — returning empty context", organization_id)
                return self._empty_context(organization_id)

            profile_id = str(profile_row[0])

            # Load ontology
            ontology_result = await db.execute(
                text("SELECT entity_type, entity_label, properties_schema, relationships, aliases, confidence, source FROM profile_ontology WHERE organization_id = :org_id AND profile_id = :pid"),
                {"org_id": organization_id, "pid": profile_id},
            )
            ontology = [
                {
                    "entity_type": r[0],
                    "label": r[1],
                    "properties_schema": r[2] if isinstance(r[2], dict) else json.loads(r[2] or "{}"),
                    "relationships": r[3] if isinstance(r[3], list) else json.loads(r[3] or "[]"),
                    "aliases": r[4] if isinstance(r[4], list) else json.loads(r[4] or "[]"),
                    "confidence": float(r[5] or 0.5),
                    "source": r[6],
                }
                for r in ontology_result.fetchall()
            ]

            # Load KPIs
            kpi_result = await db.execute(
                text("SELECT name, label, category, definition, formula, target, unit, aliases, confidence FROM profile_kpis WHERE organization_id = :org_id AND profile_id = :pid"),
                {"org_id": organization_id, "pid": profile_id},
            )
            kpis = [
                {
                    "name": r[0], "label": r[1], "category": r[2], "definition": r[3],
                    "formula": r[4] if isinstance(r[4], dict) else json.loads(r[4] or "{}"),
                    "target": r[5] if isinstance(r[5], dict) else json.loads(r[5] or "{}"),
                    "unit": r[6],
                    "aliases": r[7] if isinstance(r[7], list) else json.loads(r[7] or "[]"),
                    "confidence": float(r[8] or 0.5),
                }
                for r in kpi_result.fetchall()
            ]

            # Load glossary
            glossary_result = await db.execute(
                text("SELECT term, definition, aliases, synonyms, category, maps_to_entity, confidence FROM profile_glossary WHERE organization_id = :org_id AND profile_id = :pid"),
                {"org_id": organization_id, "pid": profile_id},
            )
            glossary = [
                {
                    "term": r[0], "definition": r[1],
                    "aliases": r[2] if isinstance(r[2], list) else json.loads(r[2] or "[]"),
                    "synonyms": r[3] if isinstance(r[3], list) else json.loads(r[3] or "[]"),
                    "category": r[4], "maps_to_entity": r[5],
                    "confidence": float(r[6] or 0.5),
                }
                for r in glossary_result.fetchall()
            ]

            # Load data sources
            ds_result = await db.execute(
                text("SELECT name, source_type, schema_metadata, semantic_mappings, confidence, status FROM profile_data_sources WHERE organization_id = :org_id AND profile_id = :pid"),
                {"org_id": organization_id, "pid": profile_id},
            )
            data_sources = [
                {
                    "name": r[0], "source_type": r[1],
                    "schema_metadata": r[2] if isinstance(r[2], dict) else json.loads(r[2] or "{}"),
                    "semantic_mappings": r[3] if isinstance(r[3], list) else json.loads(r[3] or "[]"),
                    "confidence": float(r[4] or 0.5),
                    "status": r[5],
                }
                for r in ds_result.fetchall()
            ]

            # Parse profile config for agents and AI preferences
            config = profile_row[6] if isinstance(profile_row[6], dict) else json.loads(profile_row[6] or "{}")
            agents = config.get("recommended_agents", [])
            ai_preferences = config.get("ai_preferences", {
                "preferred_models": config.get("preferred_models", {}),
                "budget_limit": config.get("budget_limit", None),
                "privacy_level": config.get("privacy_level", "standard"),
                "data_sensitivity": config.get("data_sensitivity", "normal"),
            })
            policies = config.get("policies", {})

        context = {
            "profile_id": profile_id,
            "company_identity": {
                "industry": profile_row[1],
                "business_model": profile_row[2],
                "company_size": profile_row[3],
                "region": profile_row[4],
                "locations": profile_row[5] if isinstance(profile_row[5], list) else json.loads(profile_row[5] or "[]"),
            },
            "ontology": ontology,
            "glossary": glossary,
            "kpis": kpis,
            "data_sources": data_sources,
            "agents": agents,
            "ai_preferences": ai_preferences,
            "policies": policies,
            "confidence_score": float(profile_row[7] or 0.0),
        }

        logger.debug("Loaded context for org %s: %d entities, %d KPIs, %d glossary terms",
                     organization_id, len(ontology), len(kpis), len(glossary))
        return context

    async def get_entity_types(self, organization_id: str) -> list[str]:
        """Return just the entity types for an org — used by knowledge graph extractor."""
        ctx = await self.get_context(organization_id)
        return [e["entity_type"] for e in ctx["ontology"]]

    async def get_ontology_for_prompt(self, organization_id: str) -> str:
        """Return ontology formatted for LLM prompts — used by entity extractor."""
        ctx = await self.get_context(organization_id)
        lines = []
        for entity in ctx["ontology"]:
            aliases = ", ".join(entity.get("aliases", []))
            lines.append(f"- {entity['entity_type']} (aliases: {aliases})")
        return "\n".join(lines) if lines else "No entities defined"

    async def get_kpi_context(self, organization_id: str) -> str:
        """Return KPIs formatted for decision reasoning context."""
        ctx = await self.get_context(organization_id)
        lines = []
        for kpi in ctx["kpis"]:
            target = kpi.get("target", {})
            target_str = f" target={target.get('value', 'N/A')}{target.get('unit', '')}" if target else ""
            lines.append(f"- {kpi['name']}: {kpi.get('definition', 'N/A')}{target_str}")
        return "\n".join(lines) if lines else "No KPIs defined"

    async def get_glossary_for_resolution(self, organization_id: str) -> dict:
        """Return glossary as a term→canonical mapping — used by memory engine."""
        ctx = await self.get_context(organization_id)
        mapping = {}
        for term in ctx["glossary"]:
            canonical = term["term"].lower()
            mapping[canonical] = term
            for alias in term.get("aliases", []):
                mapping[alias.lower()] = term
            for synonym in term.get("synonyms", []):
                mapping[synonym.lower()] = term
        return mapping

    async def get_ai_policy(self, organization_id: str) -> dict:
        """Return AI preferences — used by AI Gateway for model routing."""
        ctx = await self.get_context(organization_id)
        return ctx.get("ai_preferences", {})

    async def get_agent_configs(self, organization_id: str) -> list[dict]:
        """Return agent configurations — used by AgentFactory."""
        ctx = await self.get_context(organization_id)
        return ctx.get("agents", [])

    def invalidate_cache(self, organization_id: str | None = None):
        """Clear cache for a specific org or all orgs."""
        if organization_id:
            self._cache.pop(organization_id, None)
        else:
            self._cache.clear()

    @staticmethod
    def _empty_context(organization_id: str) -> dict:
        return {
            "profile_id": None,
            "company_identity": {},
            "ontology": [],
            "glossary": [],
            "kpis": [],
            "data_sources": [],
            "agents": [],
            "ai_preferences": {},
            "policies": {},
            "confidence_score": 0.0,
        }
