"""πX Graph Builder — Build knowledge graph from documents."""
from __future__ import annotations

import logging
import uuid

from .graph_store import GraphStore
from .entity_extractor import EntityExtractor

logger = logging.getLogger("pix.knowledge.graph_builder")


class GraphBuilder:
    """Orchestrates entity extraction → resolution → graph storage."""

    def __init__(self, graph_store: GraphStore | None = None, entity_extractor: EntityExtractor | None = None):
        self.graph_store = graph_store
        self.extractor = entity_extractor or EntityExtractor()

    async def build_from_document(
        self, document_id: str, text: str, org_id: str = "default",
    ) -> dict:
        """Extract entities and relationships from a document and add to graph."""
        # Step 1: Extract entities
        entities = await self.extractor.extract_entities(text, org_id)
        # Step 2: Extract relationships
        relationships = await self.extractor.extract_relationships(text, entities)
        # Step 3: Resolve and store nodes
        existing = []
        if self.graph_store:
            for entity in entities:
                existing_match = await self.extractor.resolve_entity(
                    {"name": entity["name"]}, existing
                )
                if existing_match != "new":
                    continue
                node_id = str(uuid.uuid4())
                if self.graph_store:
                    await self.graph_store.add_node(
                        node_id=node_id,
                        label=entity["name"],
                        node_type=entity["entity_type"],
                        properties=entity.get("properties", {}),
                        org_id=org_id,
                    )
                existing.append({"id": node_id, "label": entity["name"]})

        # Step 4: Store edges
        relations_created = 0
        for rel in relationships:
            source = next((e for e in existing if e["label"] == rel["source"]), None)
            target = next((e for e in existing if e["label"] == rel["target"]), None)
            if source and target and self.graph_store:
                await self.graph_store.add_relation(
                    source_id=source["id"],
                    target_id=target["id"],
                    relation_type=rel["relation_type"],
                    weight=rel.get("confidence", 0.5),
                    org_id=org_id,
                )
                relations_created += 1

        logger.info("Built graph from doc %s: %d nodes, %d edges", document_id, len(existing), relations_created)
        return {
            "document_id": document_id,
            "nodes_created": len(existing),
            "relations_created": relations_created,
            "entities": [e["label"] for e in existing],
        }

    @staticmethod
    def _fuzzy_match(name1: str, name2: str) -> bool:
        n1, n2 = name1.lower().strip(), name2.lower().strip()
        return n1 == n2 or n1 in n2 or n2 in n1
