"""
πX Profile Intelligence Agent — AI-powered profile creation and refinement.

This is the upgraded ProfileBuilder. Instead of just building a profile from data,
the ProfileIntelligenceAgent:

1. Analyzes uploaded data (columns, values, patterns)
2. Infers industry, entities, KPIs, departments, terminology
3. Suggests a complete intelligence profile with confidence scores
4. Learns from user corrections to improve future suggestions
5. Continuously refines the profile as new data is ingested

Integration with existing systems:
  - Uses app.cognitive_data_layer.semantic.SemanticUnderstandingEngine for column mapping
  - Uses app.cognitive_data_layer.canonical.CanonicalBuilder for dataset analysis
  - Uses packages.cognitive_kernel.ai_gateway.AIGateway for LLM-based inference
  - Uses packages.cognitive_kernel.intelligence_profile.industry_templates for templates
"""
from __future__ import annotations

import json
import logging
import uuid
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from packages.cognitive_kernel.ai_gateway import AI_GATEWAY
from packages.cognitive_kernel.ai_gateway.providers.base import GenerateRequest

from .profile_core import ProfileManager, IntelligenceProfile
from .profile_ontology import OntologyManager
from .profile_kpis import KPIManager
from .profile_glossary import GlossaryManager
from .profile_data_sources import DataSourceManager
from .profile_events import EventManager, ProfileEventType
from .semantic_history import SemanticHistoryManager
from .confidence_scorer import ProfileConfidenceScorer
from .industry_templates import IndustryTemplateRegistry
from .tenant_security import ProfileTenantGuard

logger = logging.getLogger("pix.intelligence_profile.agent")


class ProfileIntelligenceAgent:
    """
    The AI agent that creates, refines, and manages intelligence profiles.

    Flow:
        1. Company uploads first dataset
        2. Agent analyzes columns, values, patterns
        3. Agent infers industry, entities, KPIs, terminology
        4. Agent suggests a complete profile with confidence scores
        5. User confirms or edits
        6. Profile is created and activated
        7. As new data arrives, agent refines the profile
    """

    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        gateway=None,
    ):
        self.session_factory = session_factory
        self.gateway = gateway or AI_GATEWAY
        self.templates = IndustryTemplateRegistry()
        self.confidence_scorer = ProfileConfidenceScorer()

        # Sub-managers
        self.profile_manager = ProfileManager(session_factory)
        self.ontology_manager = OntologyManager(session_factory)
        self.kpi_manager = KPIManager(session_factory)
        self.glossary_manager = GlossaryManager(session_factory)
        self.datasource_manager = DataSourceManager(session_factory)
        self.event_manager = EventManager(session_factory)
        self.semantic_history = SemanticHistoryManager(session_factory)
        self.tenant_guard = ProfileTenantGuard(session_factory)

    async def analyze_dataset(
        self,
        organization_id: str,
        file_name: str,
        file_type: str,
        columns: list[dict[str, Any]],
    ) -> dict:
        """
        Step 2-3: Analyze uploaded data and generate profile suggestions.

        Args:
            organization_id: The org uploading the data
            file_name: Name of the uploaded file
            file_type: File extension (xlsx, csv, pdf, etc.)
            columns: List of column metadata:
                [{"name": "Cust Name", "sample_values": ["Acme Corp", ...],
                  "dtype": "object", "null_count": 0, "unique_count": 154}, ...]

        Returns:
            {
                "suggested_industry": "retail",
                "suggested_entities": [...],
                "suggested_kpis": [...],
                "suggested_glossary": [...],
                "suggested_departments": [...],
                "suggested_agents": [...],
                "confidence_scores": {...},
                "template_match": "retail",
            }
        """
        organization_id = self.tenant_guard.validate_org_id(organization_id)

        # Step 1: Use existing semantic understanding engine for column mapping
        column_mappings = await self._map_columns(columns)

        # Step 2: Infer industry using LLM
        industry_guess = await self._infer_industry(columns, column_mappings)

        # Step 3: Match to industry template
        template = self.templates.get_template(industry_guess)
        template_data = template.to_dict() if template else None

        # Step 4: Merge template with data-driven suggestions
        suggested_entities = await self._suggest_entities(columns, column_mappings, template_data)
        suggested_kpis = await self._suggest_kpis(columns, column_mappings, template_data)
        suggested_glossary = await self._suggest_glossary(columns, column_mappings, template_data)
        suggested_departments = template_data["departments"] if template_data else []
        suggested_agents = template_data["recommended_agents"] if template_data else []

        # Step 5: Calculate confidence scores
        confidence_scores = {
            "industry": industry_guess.get("confidence", 0.5) if isinstance(industry_guess, dict) else 0.5,
            "entities": sum(e.get("confidence", 0.5) for e in suggested_entities) / max(len(suggested_entities), 1),
            "kpis": sum(k.get("confidence", 0.5) for k in suggested_kpis) / max(len(suggested_kpis), 1),
            "glossary": sum(g.get("confidence", 0.5) for g in suggested_glossary) / max(len(suggested_glossary), 1),
            "overall": 0.0,
        }
        confidence_scores["overall"] = sum(confidence_scores.values()) / 5

        # Record semantic mappings in history
        for mapping in column_mappings:
            await self.semantic_history.record_mapping(
                organization_id=organization_id,
                column_name=mapping.get("column_name", ""),
                inferred_entity=mapping.get("entity_type"),
                inferred_confidence=mapping.get("confidence", 0.0),
                source_name=file_name,
                sample_values=mapping.get("sample_values", []),
                semantic_type=mapping.get("semantic_type"),
            )

        return {
            "suggested_industry": industry_guess if isinstance(industry_guess, dict) else {"industry": industry_guess, "confidence": 0.5},
            "suggested_entities": suggested_entities,
            "suggested_kpis": suggested_kpis,
            "suggested_glossary": suggested_glossary,
            "suggested_departments": suggested_departments,
            "suggested_agents": suggested_agents,
            "confidence_scores": confidence_scores,
            "template_match": industry_guess if isinstance(industry_guess, str) else None,
            "column_mappings": column_mappings,
        }

    async def create_profile_from_suggestions(
        self,
        organization_id: str,
        suggestions: dict,
        user_confirmed: bool = False,
        user_id: str | None = None,
    ) -> IntelligenceProfile:
        """
        Step 5: Create the intelligence profile from confirmed suggestions.
        """
        organization_id = self.tenant_guard.validate_org_id(organization_id)

        # Determine source for all items
        source = "user_confirmed" if user_confirmed else "inferred"

        # Create the profile
        industry = suggestions.get("suggested_industry", {})
        if isinstance(industry, dict):
            industry_name = industry.get("industry", "unknown")
        else:
            industry_name = str(industry)

        profile = await self.profile_manager.create(
            organization_id=organization_id,
            industry=industry_name,
            business_model=suggestions.get("business_model"),
            company_size=suggestions.get("company_size"),
            region=suggestions.get("region"),
            profile_config={
                "departments": suggestions.get("suggested_departments", []),
                "recommended_agents": suggestions.get("suggested_agents", []),
                "policies": {},
                "preferred_models": {},
            },
        )

        # Add ontology entities
        for entity in suggestions.get("suggested_entities", []):
            await self.ontology_manager.add_entity(
                organization_id=organization_id,
                profile_id=profile.id,
                entity_type=entity["entity_type"],
                entity_label=entity.get("label"),
                properties_schema=entity.get("properties_schema", {}),
                relationships=entity.get("relationships", []),
                aliases=entity.get("aliases", []),
                confidence=entity.get("confidence", 0.5),
                source=source if user_confirmed else entity.get("source", "inferred"),
            )

        # Add KPIs
        for kpi in suggestions.get("suggested_kpis", []):
            await self.kpi_manager.add_kpi(
                organization_id=organization_id,
                profile_id=profile.id,
                name=kpi["name"],
                label=kpi.get("label"),
                category=kpi.get("category"),
                definition=kpi.get("definition"),
                formula=kpi.get("formula", {}),
                target=kpi.get("target", {}),
                unit=kpi.get("unit"),
                aliases=kpi.get("aliases", []),
                confidence=kpi.get("confidence", 0.5),
                source=source if user_confirmed else kpi.get("source", "inferred"),
            )

        # Add glossary terms
        for term in suggestions.get("suggested_glossary", []):
            await self.glossary_manager.add_term(
                organization_id=organization_id,
                profile_id=profile.id,
                term=term["term"],
                definition=term.get("definition"),
                aliases=term.get("aliases", []),
                synonyms=term.get("synonyms", []),
                category=term.get("category"),
                maps_to_entity=term.get("maps_to_entity"),
                confidence=term.get("confidence", 0.5),
                source=source if user_confirmed else term.get("source", "inferred"),
            )

        # Emit events
        await self.event_manager.emit(
            organization_id=organization_id,
            event_type=ProfileEventType.PROFILE_CREATED,
            profile_id=profile.id,
            event_data={"industry": industry_name, "source": source},
            triggered_by="user" if user_confirmed else "system",
            user_id=user_id,
        )
        await self.event_manager.emit(
            organization_id=organization_id,
            event_type=ProfileEventType.TEMPLATE_APPLIED,
            profile_id=profile.id,
            event_data={"template": industry_name},
        )

        # Calculate and update confidence
        confidence = suggestions.get("confidence_scores", {}).get("overall", 0.5)
        profile = await self.profile_manager.update(
            organization_id, profile.id,
            {"confidence_score": confidence},
            changed_by=user_id,
            change_reason="Initial profile creation",
        )

        logger.info("Created intelligence profile %s for org %s (industry: %s, confidence: %.2f)",
                     profile.id, organization_id, industry_name, confidence)
        return profile

    async def refine_profile(
        self,
        organization_id: str,
        profile_id: str,
        new_data_columns: list[dict],
        file_name: str,
        file_type: str,
    ) -> dict:
        """
        Continuously refine the profile as new data is ingested.
        """
        organization_id = self.tenant_guard.validate_org_id(organization_id)

        # Verify access
        if not await self.tenant_guard.verify_access(organization_id, profile_id):
            raise PermissionError("Access denied: profile not found for this organization")

        # Analyze new data
        analysis = await self.analyze_dataset(organization_id, file_name, file_type, new_data_columns)

        # Register the data source
        await self.datasource_manager.add_source(
            organization_id=organization_id,
            profile_id=profile_id,
            name=file_name,
            source_type=file_type,
            schema_metadata={"columns": new_data_columns},
            semantic_mappings=analysis.get("column_mappings", []),
            confidence=analysis.get("confidence_scores", {}).get("overall", 0.5),
            status="connected",
        )

        # Emit event
        await self.event_manager.emit(
            organization_id=organization_id,
            event_type=ProfileEventType.DATASOURCE_CONNECTED,
            profile_id=profile_id,
            event_data={"source": file_name, "type": file_type},
        )

        # Check for new entities not yet in the profile
        existing_entities = await self.ontology_manager.get_entities(organization_id, profile_id)
        existing_types = {e["entity_type"].lower() for e in existing_entities}

        new_entities_added = 0
        for entity in analysis.get("suggested_entities", []):
            if entity["entity_type"].lower() not in existing_types:
                await self.ontology_manager.add_entity(
                    organization_id=organization_id,
                    profile_id=profile_id,
                    entity_type=entity["entity_type"],
                    entity_label=entity.get("label"),
                    aliases=entity.get("aliases", []),
                    confidence=entity.get("confidence", 0.5),
                    source="inferred",
                )
                new_entities_added += 1

        # Recalculate confidence
        confidence_explanation = await self._recalculate_confidence(organization_id, profile_id)

        await self.event_manager.emit(
            organization_id=organization_id,
            event_type=ProfileEventType.CONFIDENCE_RECALCULATED,
            profile_id=profile_id,
            event_data=confidence_explanation,
        )

        return {
            "new_entities_added": new_entities_added,
            "data_source_registered": file_name,
            "confidence": confidence_explanation,
            "suggestions": analysis,
        }

    async def _map_columns(self, columns: list[dict]) -> list[dict]:
        """Map columns to canonical entities using existing semantic engine."""
        try:
            from app.cognitive_data_layer.semantic import SemanticUnderstandingEngine
            engine = SemanticUnderstandingEngine()
            mappings = []
            for col in columns:
                result = engine.infer_entity(col["name"], col.get("sample_values", []))
                mappings.append({
                    "column_name": col["name"],
                    "entity_type": result.entity_type.value if result.entity_type.value != "unknown" else None,
                    "confidence": result.confidence,
                    "explanation": result.explanation,
                    "semantic_type": self._infer_semantic_type(col),
                    "sample_values": col.get("sample_values", []),
                })
            return mappings
        except ImportError:
            logger.warning("SemanticUnderstandingEngine not available, using basic mapping")
            return [
                {"column_name": c["name"], "entity_type": None, "confidence": 0.0,
                 "explanation": "Semantic engine unavailable", "sample_values": c.get("sample_values", [])}
                for c in columns
            ]

    async def _infer_industry(self, columns: list[dict], mappings: list[dict]) -> dict:
        """Infer industry from column patterns using LLM."""
        column_names = [c["name"] for c in columns]
        entity_types = [m["entity_type"] for m in mappings if m["entity_type"]]

        # Quick heuristic check first
        col_str = " ".join(column_names).lower()
        heuristic_guess = None
        if any(w in col_str for w in ["sku", "sell_out", "sell-out", "merchandise", "store"]):
            heuristic_guess = "retail"
        elif any(w in col_str for w in ["patient", "procedure", "diagnosis", "icd"]):
            heuristic_guess = "healthcare"
        elif any(w in col_str for w in ["shipment", "vehicle", "route", "freight"]):
            heuristic_guess = "logistics"
        elif any(w in col_str for w in ["mrr", "churn", "subscription", "saas"]):
            heuristic_guess = "saas"
        elif any(w in col_str for w in ["work_order", "bom", "oee", "cycle_time"]):
            heuristic_guess = "manufacturing"
        elif any(w in col_str for w in ["account", "transaction", "isin", "npl", "loan"]):
            heuristic_guess = "finance"
        elif any(w in col_str for w in ["project", "contractor", "site", "building"]):
            heuristic_guess = "construction"

        if heuristic_guess:
            return {"industry": heuristic_guess, "confidence": 0.85, "method": "heuristic"}

        # Use LLM for inference
        prompt = f"""Analyze these business data columns and infer the industry.
Columns: {column_names}
Inferred entities: {entity_types}

Return JSON: {{"industry": "retail|manufacturing|finance|healthcare|logistics|saas|construction|other", "confidence": 0.0-1.0}}

Return ONLY the JSON."""

        try:
            response = await self.gateway.generate(
                GenerateRequest(prompt=prompt, temperature=0.2, max_tokens=200)
            )
            content = response.content.strip()
            if content.startswith("```"):
                content = content.split("\n", 1)[1].rsplit("```", 1)[0]
            result = json.loads(content)
            return {**result, "method": "llm"}
        except Exception as exc:
            logger.error("Industry inference failed: %s", exc)
            return {"industry": "unknown", "confidence": 0.3, "method": "fallback"}

    async def _suggest_entities(
        self, columns: list[dict], mappings: list[dict], template: dict | None
    ) -> list[dict]:
        """Suggest entities from column mappings and template."""
        entities = []
        seen_types = set()

        # From template
        if template:
            for entity in template.get("entities", []):
                entities.append({**entity, "confidence": 0.7, "source": "template"})
                seen_types.add(entity["entity_type"])

        # From column mappings
        for mapping in mappings:
            if mapping["entity_type"] and mapping["entity_type"] not in seen_types:
                entities.append({
                    "entity_type": mapping["entity_type"],
                    "label": mapping["entity_type"].replace("_", " ").title(),
                    "aliases": [mapping["column_name"].lower()],
                    "confidence": mapping["confidence"],
                    "source": "inferred",
                    "properties_schema": {"fields": [{"name": mapping["column_name"], "type": mapping.get("semantic_type", "text")}]},
                })
                seen_types.add(mapping["entity_type"])

        return entities

    async def _suggest_kpis(
        self, columns: list[dict], mappings: list[dict], template: dict | None
    ) -> list[dict]:
        """Suggest KPIs from template and data patterns."""
        kpis = []

        if template:
            for kpi in template.get("kpis", []):
                kpis.append({**kpi, "confidence": 0.7, "source": "template"})

        # Try to detect KPIs from column names
        kpi_keywords = {
            "revenue": ["rev", "revenue", "sales_amount", "net_sales", "income", "turnover"],
            "cost": ["cost", "expense", "cogs", "spend", "expenditure"],
            "margin": ["margin", "profit", "ebitda"],
            "quantity": ["qty", "quantity", "units", "volume", "count"],
        }
        for col in columns:
            col_lower = col["name"].lower()
            for kpi_name, keywords in kpi_keywords.items():
                if any(kw in col_lower for kw in keywords):
                    if not any(k["name"] == kpi_name for k in kpis):
                        kpis.append({
                            "name": kpi_name,
                            "label": kpi_name.title(),
                            "category": "revenue" if kpi_name in ("revenue", "margin") else "operations",
                            "definition": f"Sum of {col['name']}",
                            "formula": {"type": "sum", "field": col["name"]},
                            "target": {},
                            "aliases": [col_lower],
                            "confidence": 0.6,
                            "source": "inferred",
                        })

        return kpis

    async def _suggest_glossary(
        self, columns: list[dict], mappings: list[dict], template: dict | None
    ) -> list[dict]:
        """Suggest glossary terms from template and column names."""
        terms = []

        if template:
            for term in template.get("terminology", []):
                terms.append({**term, "confidence": 0.7, "source": "template"})

        # Add column names as potential glossary terms
        for col in columns:
            # Check if this column maps to an entity
            mapping = next((m for m in mappings if m["column_name"] == col["name"]), None)
            if mapping and mapping["entity_type"]:
                terms.append({
                    "term": col["name"],
                    "definition": f"Maps to {mapping['entity_type']}",
                    "aliases": [],
                    "category": "data_column",
                    "maps_to_entity": mapping["entity_type"],
                    "confidence": mapping["confidence"],
                    "source": "inferred",
                })

        return terms

    def _infer_semantic_type(self, col: dict) -> str:
        """Infer the semantic type of a column."""
        dtype = col.get("dtype", "object")
        if dtype in ("int64", "float64", "int32", "float32"):
            name = col.get("name", "").lower()
            if any(kw in name for kw in ["price", "cost", "rev", "amount", "value"]):
                return "currency"
            return "numeric"
        if dtype in ("datetime64", "datetime64[ns]"):
            return "date"
        if dtype == "bool":
            return "boolean"
        name = col.get("name", "").lower()
        if any(kw in name for kw in ["email", "mail"]):
            return "email"
        if any(kw in name for kw in ["phone", "tel", "mobile"]):
            return "phone"
        if any(kw in name for kw in ["date", "time", "timestamp"]):
            return "date"
        if col.get("unique_count", 0) == col.get("total_count", 1):
            return "identifier"
        return "text"

    async def _recalculate_confidence(self, organization_id: str, profile_id: str) -> dict:
        """Recalculate the overall confidence score for a profile."""
        entities = await self.ontology_manager.get_entities(organization_id, profile_id)
        kpis = await self.kpi_manager.get_kpis(organization_id, profile_id)
        glossary = await self.glossary_manager.get_terms(organization_id, profile_id)
        data_sources = await self.datasource_manager.get_sources(organization_id, profile_id)
        semantic_stats = await self.semantic_history.get_learning_stats(organization_id)

        avg_ds_conf = sum(ds["confidence"] for ds in data_sources) / max(len(data_sources), 1)
        user_confirmed = sum(1 for e in entities + kpis + glossary if e.get("source") == "user_confirmed")
        total_items = len(entities) + len(kpis) + len(glossary)

        explanation = self.confidence_scorer.explain(
            ontology_count=len(entities),
            kpi_count=len(kpis),
            glossary_count=len(glossary),
            data_source_count=len(data_sources),
            avg_data_source_confidence=avg_ds_conf,
            total_semantic_mappings=semantic_stats["total_mappings"],
            user_corrections=semantic_stats["user_corrections"],
            user_confirmed_count=user_confirmed,
            total_items=total_items,
        )

        # Update profile confidence
        await self.profile_manager.update(
            organization_id, profile_id,
            {"confidence_score": explanation["overall"]},
            change_reason="Confidence recalculation",
        )

        return explanation
