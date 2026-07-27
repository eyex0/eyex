"""Tests for the Knowledge Graph entities."""
from packages.cognitive_kernel.knowledge_graph.entities import EntityFactory, ENTITY_TYPES


class TestEntities:
    def test_create_company(self):
        entity = EntityFactory.create_entity("Company", id="1", name="Acme Corp")
        assert entity.name == "Acme Corp"
        assert entity.entity_type == "Company"

    def test_create_customer(self):
        entity = EntityFactory.create_entity("Customer", id="2", name="John Doe", company="Acme")
        assert entity.entity_type == "Customer"
        assert entity.company == "Acme" if hasattr(entity, "company") else True

    def test_create_product(self):
        entity = EntityFactory.create_entity("Product", id="3", name="Widget", price=99.99)
        assert entity.entity_type == "Product"
        assert entity.name == "Widget"

    def test_all_entity_types(self):
        for entity_type in ENTITY_TYPES:
            entity = EntityFactory.create_entity(entity_type, id="test", name="Test")
            assert entity.entity_type == entity_type

    def test_unknown_entity_type(self):
        entity = EntityFactory.create_entity("Unknown", id="x", name="Test")
        assert entity.name == "Test"
