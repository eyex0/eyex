"""
πX Semantic Mapping Engine V2 — Multi-layer column understanding.

Mapping flow for each column:
  1. Company Glossary → exact term/alias match (highest priority, learned)
  2. Company Ontology → entity alias match
  3. Historical Learning → previously corrected mappings for this org
  4. Industry Template → default aliases for the detected industry
  5. LLM Reasoning → AI-based inference fallback (lowest priority)

Combines all signals with confidence weighting.
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger("pix.data_intelligence.semantic_mapping_v2")


@dataclass
class SemanticMapping:
    source_column: str
    meaning: str | None = None
    entity: str | None = None
    confidence: float = 0.0
    method: str = "unknown"  # glossary, ontology, history, template, llm, heuristic
    explanation: str = ""
    sample_values: list = field(default_factory=list)
    semantic_type: str = "unknown"
    aliases_matched: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "source_column": self.source_column,
            "meaning": self.meaning,
            "entity": self.entity,
            "confidence": self.confidence,
            "method": self.method,
            "explanation": self.explanation,
            "semantic_type": self.semantic_type,
            "aliases_matched": self.aliases_matched,
        }


class SemanticMappingEngineV2:
    """Multi-layer semantic mapping with profile, ontology, glossary, and learning."""

    def __init__(
        self,
        context_provider=None,
        semantic_history_manager=None,
        gateway=None,
        industry_templates=None,
    ):
        self.context_provider = context_provider
        self.semantic_history = semantic_history_manager
        self.gateway = gateway
        self.industry_templates = industry_templates

    def map_column(
        self,
        column_name: str,
        sample_values: list | None = None,
        organization_id: str | None = None,
        profile_context: dict | None = None,
    ) -> dict:
        """
        Map a column to its business meaning using the multi-layer flow.
        Returns dict with: source_column, meaning, entity, confidence, method, explanation
        """
        sample_values = sample_values or []
        normalized = column_name.lower().strip().replace("_", " ").replace("-", " ").replace(".", " ")

        # Use provided profile context or load it
        ctx = profile_context
        if ctx is None and self.context_provider and organization_id:
            # In async context this would be: ctx = await self.context_provider.get_context(organization_id)
            # For sync usage, caller should pass profile_context
            ctx = {}

        ctx = ctx or {}
        glossary = ctx.get("glossary", [])
        ontology = ctx.get("ontology", [])
        industry = ctx.get("company_identity", {}).get("industry")

        # Layer 1: Company Glossary (highest priority — company-confirmed terminology)
        result = self._match_glossary(column_name, normalized, glossary)
        if result and result["confidence"] >= 0.7:
            return result

        # Layer 2: Company Ontology (entity aliases defined in the profile)
        ontology_result = self._match_ontology(column_name, normalized, ontology)
        if ontology_result and ontology_result["confidence"] >= 0.7:
            # If glossary also matched, merge and boost confidence
            if result:
                ontology_result["confidence"] = min(1.0, ontology_result["confidence"] + 0.1)
                ontology_result["method"] = "ontology+glossary"
            return ontology_result

        # Layer 3: Historical Learning (previously corrected mappings)
        # This would be async in production — for sync use, caller passes history
        # history_result = await self._match_history(column_name, organization_id)

        # Layer 4: Industry Template defaults
        template_result = self._match_template(column_name, normalized, industry)
        if template_result and template_result["confidence"] >= 0.6:
            return template_result

        # Layer 5: Heuristic matching (built-in aliases)
        heuristic_result = self._match_heuristic(column_name, normalized, sample_values)
        if heuristic_result and heuristic_result["confidence"] >= 0.5:
            return heuristic_result

        # If we got partial results from any layer, return the best one
        best = max(
            [r for r in [result, ontology_result, template_result, heuristic_result] if r],
            key=lambda r: r.get("confidence", 0),
            default=None,
        )
        if best:
            return best

        # Layer 6: LLM fallback (would be async in production)
        # For now, return low-confidence unknown
        return {
            "source_column": column_name,
            "meaning": None,
            "entity": None,
            "confidence": 0.1,
            "method": "unknown",
            "explanation": f"No mapping found for '{column_name}'",
            "semantic_type": self._infer_semantic_type(column_name, sample_values),
            "aliases_matched": [],
        }

    def map_columns_batch(
        self,
        columns: list[dict],
        organization_id: str | None = None,
        profile_context: dict | None = None,
    ) -> list[dict]:
        """Map multiple columns at once."""
        return [
            self.map_column(
                c["name"], c.get("sample_values", []),
                organization_id, profile_context,
            )
            for c in columns
        ]

    def _match_glossary(self, column_name: str, normalized: str, glossary: list[dict]) -> dict | None:
        """Layer 1: Match against company glossary terms and aliases."""
        for term in glossary:
            # Check canonical term
            if term.get("term", "").lower() == normalized:
                return self._build_result(
                    column_name, term.get("term"), term.get("maps_to_entity"),
                    0.95, "glossary",
                    f"Exact glossary match: '{column_name}' = '{term['term']}'",
                    [term.get("term", "")],
                )
            # Check aliases
            for alias in term.get("aliases", []):
                alias_norm = alias.lower().strip()
                if alias_norm == normalized:
                    return self._build_result(
                        column_name, term.get("term"), term.get("maps_to_entity"),
                        0.90, "glossary",
                        f"Glossary alias match: '{alias}' → '{term['term']}'",
                        [alias],
                    )
                if alias_norm in normalized or normalized in alias_norm:
                    return self._build_result(
                        column_name, term.get("term"), term.get("maps_to_entity"),
                        0.75, "glossary",
                        f"Partial glossary match: '{alias}' ~ '{column_name}'",
                        [alias],
                    )
            # Check synonyms
            for synonym in term.get("synonyms", []):
                if synonym.lower().strip() == normalized:
                    return self._build_result(
                        column_name, term.get("term"), term.get("maps_to_entity"),
                        0.85, "glossary",
                        f"Glossary synonym match: '{synonym}' → '{term['term']}'",
                        [synonym],
                    )
        return None

    def _match_ontology(self, column_name: str, normalized: str, ontology: list[dict]) -> dict | None:
        """Layer 2: Match against company ontology entity aliases."""
        for entity in ontology:
            entity_type = entity.get("entity_type", "")
            # Check entity type directly
            if entity_type.lower() == normalized:
                return self._build_result(
                    column_name, entity.get("label") or entity_type, entity_type,
                    entity.get("confidence", 0.8), "ontology",
                    f"Ontology type match: '{column_name}' = '{entity_type}'",
                    [entity_type],
                )
            # Check aliases
            for alias in entity.get("aliases", []):
                alias_norm = alias.lower().strip()
                if alias_norm == normalized:
                    return self._build_result(
                        column_name, entity.get("label") or entity_type, entity_type,
                        0.85, "ontology",
                        f"Ontology alias match: '{alias}' → '{entity_type}'",
                        [alias],
                    )
                if alias_norm in normalized or normalized in alias_norm:
                    return self._build_result(
                        column_name, entity.get("label") or entity_type, entity_type,
                        0.65, "ontology",
                        f"Partial ontology match: '{alias}' ~ '{column_name}'",
                        [alias],
                    )
        return None

    def _match_template(self, column_name: str, normalized: str, industry: str | None) -> dict | None:
        """Layer 4: Match against industry template defaults."""
        if not industry or not self.industry_templates:
            return None

        from packages.cognitive_kernel.intelligence_profile.industry_templates import IndustryTemplateRegistry
        registry = self.industry_templates if isinstance(self.industry_templates, IndustryTemplateRegistry) else IndustryTemplateRegistry()
        template = registry.get_template(industry)
        if not template:
            return None

        # Check template entities
        for entity in template.entities:
            for alias in entity.get("aliases", []):
                alias_norm = alias.lower().strip()
                if alias_norm == normalized or alias_norm in normalized or normalized in alias_norm:
                    return self._build_result(
                        column_name, entity.get("label") or entity["entity_type"], entity["entity_type"],
                        0.70, "template",
                        f"Industry template match ({industry}): '{alias}' → '{entity['entity_type']}'",
                        [alias],
                    )

        # Check template terminology
        for term in template.terminology:
            for alias in [term["term"]] + term.get("aliases", []):
                alias_norm = alias.lower().strip()
                if alias_norm == normalized or alias_norm in normalized:
                    return self._build_result(
                        column_name, term["term"], None,
                        0.65, "template",
                        f"Template terminology match: '{alias}' → '{term['term']}'",
                        [alias],
                    )
        return None

    def _match_heuristic(self, column_name: str, normalized: str, sample_values: list) -> dict | None:
        """Layer 5: Built-in heuristic matching with common business aliases."""
        heuristic_aliases = {
            "customer": ["customer", "cust", "client", "buyer", "account name", "cust name", "customer name", "shopper", "consumer"],
            "revenue": ["revenue", "rev", "net rev", "net_rev", "net revenue", "sales", "sales amount", "turnover", "income", "gross sales"],
            "cost": ["cost", "expense", "cogs", "expenditure", "spend", "operating cost", "overhead"],
            "product": ["product", "item", "sku", "merchandise", "goods"],
            "employee": ["employee", "staff", "worker", "personnel", "operator", "associate"],
            "date": ["date", "timestamp", "created at", "updated at", "business date", "transaction date"],
            "store": ["store", "shop", "branch", "outlet", "location"],
            "machine": ["machine", "equipment", "asset", "line", "station"],
            "supplier": ["supplier", "vendor", "provider", "distributor"],
            "quantity": ["quantity", "qty", "units", "volume", "count"],
            "price": ["price", "unit price", "rate", "tariff"],
            "margin": ["margin", "profit", "gross margin", "net margin", "ebitda"],
            "defect": ["defect", "defect count", "error count", "reject", "scrap"],
            "cycle_time": ["cycle time", "production time", "lead time", "takt time", "cycle_time"],
            "oee": ["oee", "overall equipment effectiveness"],
            "account": ["account", "account no", "account number", "account_no", "iban"],
            "transaction": ["transaction", "txn", "trx", "transfer", "payment"],
            "risk_score": ["risk score", "risk", "risk_rating", "credit score"],
            "patient": ["patient", "patient id", "patient_name", "beneficiary"],
            "treatment": ["treatment", "procedure", "procedure code", "treatment code", "icd"],
        }

        for entity, aliases in heuristic_aliases.items():
            for alias in aliases:
                if alias == normalized:
                    meaning = alias.replace("_", " ").title()
                    return self._build_result(
                        column_name, meaning, entity,
                        0.60, "heuristic",
                        f"Heuristic match: '{column_name}' → '{entity}'",
                        [alias],
                    )
                if alias in normalized or normalized in alias:
                    return self._build_result(
                        column_name, alias.replace("_", " ").title(), entity,
                        0.45, "heuristic",
                        f"Partial heuristic match: '{alias}' ~ '{column_name}'",
                        [alias],
                    )
        return None

    def _infer_semantic_type(self, name: str, sample_values: list) -> str:
        """Quick semantic type inference."""
        name_lower = name.lower()
        if any(kw in name_lower for kw in ["date", "time", "_at", "timestamp"]):
            return "date"
        if any(kw in name_lower for kw in ["email", "mail"]):
            return "email"
        if any(kw in name_lower for kw in ["phone", "tel"]):
            return "phone"
        if any(kw in name_lower for kw in ["rev", "amount", "price", "cost", "value", "balance"]):
            return "currency"
        if any(kw in name_lower for kw in ["id", "code", "ref", "key"]):
            return "identifier"
        if sample_values and all(isinstance(v, (int, float)) for v in sample_values[:5]):
            return "numeric"
        return "text"

    @staticmethod
    def _build_result(
        column_name: str, meaning: str | None, entity: str | None,
        confidence: float, method: str, explanation: str, aliases: list[str],
    ) -> dict:
        return {
            "source_column": column_name,
            "meaning": meaning,
            "entity": entity,
            "confidence": confidence,
            "method": method,
            "explanation": explanation,
            "semantic_type": "unknown",
            "aliases_matched": aliases,
        }
