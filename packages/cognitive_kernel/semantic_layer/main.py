from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.cognitive_data_layer.canonical.model import EntityType

# Canonical business vocabulary with aliases
CANONICAL_ALIASES: dict[EntityType, list[str]] = {
    EntityType.CUSTOMER: [
        "customer",
        "client",
        "buyer",
        "account",
        "customer name",
        "cust",
        "client name",
        "account name",
        "buyer name",
        "purchaser",
        "consumer",
        "end customer",
        "ship to",
        "bill to",
    ],
    EntityType.EMPLOYEE: [
        "employee",
        "staff",
        "worker",
        "personnel",
        "team member",
        "associate",
        "colleague",
        "employee name",
        "staff name",
        "worker name",
    ],
    EntityType.PRODUCT: [
        "product",
        "item",
        "sku",
        "goods",
        "merchandise",
        "product name",
        "item name",
        "product code",
        "material",
        "service",
    ],
    EntityType.ORDER: [
        "order",
        "purchase order",
        "sales order",
        "order id",
        "order number",
        "po number",
        "so number",
        "order ref",
    ],
    EntityType.INVOICE: [
        "invoice",
        "invoice id",
        "invoice number",
        "bill",
        "billing",
        "receipt",
    ],
    EntityType.DEPARTMENT: [
        "department",
        "division",
        "unit",
        "team",
        "business unit",
        "dept",
        "section",
        "group",
    ],
    EntityType.PROJECT: [
        "project",
        "initiative",
        "program",
        "project name",
        "project id",
        "engagement",
        "campaign",
    ],
    EntityType.ASSET: [
        "asset",
        "equipment",
        "machine",
        "vehicle",
        "property",
        "asset id",
        "asset tag",
        "fixed asset",
    ],
    EntityType.REVENUE: [
        "revenue",
        "sales",
        "income",
        "amount",
        "total sales",
        "net revenue",
        "gross revenue",
        "turnover",
        "proceeds",
        "total amount",
        "sales amount",
    ],
    EntityType.COST: [
        "cost",
        "expense",
        "expenditure",
        "spend",
        "total cost",
        "cost amount",
        "operating cost",
        "cogs",
        "overhead",
    ],
    EntityType.SUPPLIER: [
        "supplier",
        "vendor",
        "provider",
        "seller",
        "supplier name",
        "vendor name",
        "provider name",
        "distributor",
    ],
    EntityType.INVENTORY: [
        "inventory",
        "stock",
        "quantity on hand",
        "inventory level",
        "stock level",
        "units",
    ],
    EntityType.TRANSACTION: [
        "transaction",
        "transaction id",
        "transaction date",
        "payment",
        "transfer",
        "txn",
        "trx",
    ],
    EntityType.BUSINESS_DATE: [
        "date",
        "invoice date",
        "order date",
        "purchase date",
        "transaction date",
        "payment date",
        "due date",
        "delivery date",
        "shipment date",
        "booking date",
        "business date",
        "created at",
        "updated at",
        "timestamp",
    ],
}


@dataclass
class SemanticMapping:
    column: str
    entity_type: EntityType
    confidence: float
    explanation: str
    aliases_matched: list[str]


class SemanticUnderstandingEngine:
    """Map business columns to canonical entities using deterministic + LLM reasoning."""

    def __init__(self, llm_client: Any | None = None) -> None:
        self.llm_client = llm_client

    def infer_entity(
        self, column_name: str, sample_values: list[Any] | None = None
    ) -> SemanticMapping:
        normalized = column_name.lower().strip().replace("_", " ").replace("-", " ")
        best_entity = EntityType.UNKNOWN
        best_score = 0.0
        matched_aliases: list[str] = []

        # First pass: exact matches across all entities take precedence.
        for entity, aliases in CANONICAL_ALIASES.items():
            for alias in aliases:
                alias_norm = alias.lower().strip()
                if alias_norm == normalized:
                    return SemanticMapping(
                        column=column_name,
                        entity_type=entity,
                        confidence=1.0,
                        explanation=f"Exact match for alias '{alias}'",
                        aliases_matched=[alias],
                    )

        # Second pass: partial matches.
        for entity, aliases in CANONICAL_ALIASES.items():
            for alias in aliases:
                alias_norm = alias.lower().strip()
                if alias_norm in normalized:
                    score = 0.8
                elif normalized in alias_norm:
                    score = 0.5
                else:
                    continue

                if score > best_score:
                    best_score = score
                    best_entity = entity
                    matched_aliases = [alias]

        # Validate with sample values for ambiguous cases
        if sample_values and best_score < 1.0:
            best_score = self._validate_with_samples(best_entity, sample_values, best_score)

        explanation = (
            f"Column '{column_name}' matched canonical entity '{best_entity.value}' "
            f"via aliases: {matched_aliases}"
            if matched_aliases
            else f"No strong alias match for '{column_name}'"
        )

        return SemanticMapping(
            column=column_name,
            entity_type=best_entity,
            confidence=round(best_score, 2),
            explanation=explanation,
            aliases_matched=matched_aliases,
        )

    def _validate_with_samples(
        self, entity: EntityType, samples: list[Any], base_score: float
    ) -> float:
        if entity == EntityType.BUSINESS_DATE:
            date_like = sum(1 for v in samples if isinstance(v, str) and len(v.split("/")) == 3)
            if date_like > len(samples) / 2:
                return max(base_score, 0.85)
        if entity == EntityType.REVENUE:
            numeric_like = sum(1 for v in samples if isinstance(v, (int, float)))
            if numeric_like > len(samples) / 2:
                return max(base_score, 0.85)
        return base_score

    async def infer_with_llm(self, column_name: str, sample_values: list[Any]) -> SemanticMapping:
        """Optional LLM-based inference for ambiguous columns."""
        if not self.llm_client:
            return self.infer_entity(column_name, sample_values)

        prompt = (
            f"Map this business column to one of: {', '.join(e.value for e in EntityType)}.\n"
            f"Column: {column_name}\n"
            f"Sample values: {sample_values[:5]}\n"
            "Return only the entity name."
        )
        try:
            response = await self.llm_client.complete(prompt)
            entity = EntityType(response.strip().lower())
            return SemanticMapping(
                column=column_name,
                entity_type=entity,
                confidence=0.75,
                explanation="Inferred by LLM",
                aliases_matched=[],
            )
        except Exception:  # noqa: BLE001
            return self.infer_entity(column_name, sample_values)

    def batch_infer(
        self, column_names: list[str], sample_map: dict[str, list[Any]] | None = None
    ) -> list[SemanticMapping]:
        sample_map = sample_map or {}
        return [self.infer_entity(c, sample_map.get(c, [])) for c in column_names]
