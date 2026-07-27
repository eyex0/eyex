from __future__ import annotations

from app.cognitive_data_layer.canonical.model import EntityType
from app.cognitive_data_layer.semantic import SemanticUnderstandingEngine


class TestSemanticUnderstandingEngine:
    def test_customer_aliases(self):
        engine = SemanticUnderstandingEngine()
        mapping = engine.infer_entity("Customer Name")
        assert mapping.entity_type == EntityType.CUSTOMER
        assert mapping.confidence >= 0.8

    def test_revenue_aliases(self):
        engine = SemanticUnderstandingEngine()
        mapping = engine.infer_entity("Total Sales")
        assert mapping.entity_type == EntityType.REVENUE

    def test_business_date_aliases(self):
        engine = SemanticUnderstandingEngine()
        mapping = engine.infer_entity("Invoice Date")
        assert mapping.entity_type == EntityType.BUSINESS_DATE

    def test_unknown_column(self):
        engine = SemanticUnderstandingEngine()
        mapping = engine.infer_entity("XYZ_FOO_BAR")
        assert mapping.entity_type == EntityType.UNKNOWN

    def test_batch_infer(self):
        engine = SemanticUnderstandingEngine()
        mappings = engine.batch_infer(["Client", "Income", "Purchase Date"])
        assert mappings[0].entity_type == EntityType.CUSTOMER
        assert mappings[1].entity_type == EntityType.REVENUE
        assert mappings[2].entity_type == EntityType.BUSINESS_DATE

    def test_explanation_present(self):
        engine = SemanticUnderstandingEngine()
        mapping = engine.infer_entity("Employee")
        assert "Employee" in mapping.explanation or "employee" in mapping.explanation
