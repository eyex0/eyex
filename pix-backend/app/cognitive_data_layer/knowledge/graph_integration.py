from __future__ import annotations

from typing import Any

from app.cognitive_data_layer.canonical.model import CanonicalDataset, EntityType


class KnowledgeGraphIntegration:
    """Populate the enterprise knowledge graph from canonical datasets."""

    SUPPORTED_ENTITIES = [
        EntityType.CUSTOMER,
        EntityType.EMPLOYEE,
        EntityType.PRODUCT,
        EntityType.ORDER,
        EntityType.DEPARTMENT,
        EntityType.PROJECT,
        EntityType.ASSET,
        EntityType.REVENUE,
        EntityType.COST,
        EntityType.SUPPLIER,
    ]

    def build_graph(self, dataset: CanonicalDataset) -> dict[str, Any]:
        nodes: list[dict[str, Any]] = []
        edges: list[dict[str, Any]] = []

        for sheet in dataset.sheets:
            for table in sheet.tables:
                for col in table.columns:
                    if col.entity_type and col.entity_type in self.SUPPORTED_ENTITIES:
                        nodes.append(
                            {
                                "id": f"{table.name}.{col.name}",
                                "label": col.entity_type.value,
                                "table": table.name,
                                "column": col.name,
                                "confidence": col.confidence,
                            }
                        )

        for rel in dataset.relationships:
            edges.append(
                {
                    "source": f"{rel.source_table}.{rel.source_column}",
                    "target": f"{rel.target_table}.{rel.target_column}",
                    "type": rel.relationship_type,
                    "confidence": rel.confidence,
                }
            )

        return {"nodes": nodes, "edges": edges, "entity_counts": self._count_entities(nodes)}

    def _count_entities(self, nodes: list[dict[str, Any]]) -> dict[str, int]:
        counts: dict[str, int] = {}
        for node in nodes:
            counts[node["label"]] = counts.get(node["label"], 0) + 1
        return counts
