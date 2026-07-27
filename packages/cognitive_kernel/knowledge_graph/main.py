from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

logger = logging.getLogger("pix.db.knowledge_graph")


@dataclass
class KnowledgeNode:
    """A node in the company knowledge graph."""

    id: str
    label: str
    type: str
    properties: dict[str, Any] = field(default_factory=dict)
    org_id: str = "default"
    created_at: str | None = None
    updated_at: str | None = None


@dataclass
class KnowledgeRelation:
    """A directed relationship between two knowledge nodes."""

    source_id: str
    target_id: str
    relation_type: str
    properties: dict[str, Any] = field(default_factory=dict)
    weight: float = 1.0


RELATION_TYPES = {
    "impacts": "directly affects or influences",
    "depends_on": "requires or depends on",
    "part_of": "is a component or subset of",
    "drives": "is a driver or cause of",
    "mitigates": "reduces risk or impact of",
    "competes_with": "competes with or is an alternative to",
    "measured_by": "is measured or tracked by",
    "reports_to": "reports to or is accountable to",
    "generates": "produces or creates",
    "requires": "needs as a prerequisite",
    "aligns_with": "supports or is consistent with",
    "threatens": "poses a risk or threat to",
}


class KnowledgeGraph:
    """Lightweight in-memory knowledge graph for company business context.

    Stores typed nodes and labeled, weighted relationships. Supports
    traversal, query by type, and context extraction for AI agents.
    """

    def __init__(self) -> None:
        self._nodes: dict[str, KnowledgeNode] = {}
        self._relations: list[KnowledgeRelation] = []
        self._org_nodes: dict[str, set[str]] = {}

    def add_node(
        self,
        node_id: str,
        label: str,
        node_type: str,
        properties: dict[str, Any] | None = None,
        org_id: str = "default",
    ) -> KnowledgeNode:
        now = datetime.now(UTC).isoformat()
        properties = properties or {}
        if node_id in self._nodes:
            existing = self._nodes[node_id]
            existing.label = label
            existing.type = node_type
            existing.properties.update(properties)
            existing.updated_at = now
            return existing

        node = KnowledgeNode(
            id=node_id,
            label=label,
            type=node_type,
            properties=properties,
            org_id=org_id,
            created_at=now,
            updated_at=now,
        )
        self._nodes[node_id] = node
        if org_id not in self._org_nodes:
            self._org_nodes[org_id] = set()
        self._org_nodes[org_id].add(node_id)
        logger.debug("Added KG node %s (%s)", node_id, node_type)
        return node

    def add_relation(
        self,
        source_id: str,
        target_id: str,
        relation_type: str,
        properties: dict[str, Any] | None = None,
        weight: float = 1.0,
    ) -> KnowledgeRelation | None:
        if source_id not in self._nodes or target_id not in self._nodes:
            logger.warning("Cannot add relation: one or both nodes missing (%s -> %s)", source_id, target_id)
            return None
        if relation_type not in RELATION_TYPES:
            logger.warning("Unknown relation type: %s", relation_type)
            return None

        rel = KnowledgeRelation(
            source_id=source_id,
            target_id=target_id,
            relation_type=relation_type,
            properties=properties or {},
            weight=weight,
        )
        self._relations.append(rel)
        return rel

    def get_node(self, node_id: str) -> KnowledgeNode | None:
        return self._nodes.get(node_id)

    def get_nodes_by_type(self, node_type: str, org_id: str = "default") -> list[KnowledgeNode]:
        return [
            n for n in self._nodes.values()
            if n.type == node_type and n.org_id == org_id
        ]

    def get_relations(self, node_id: str) -> list[dict[str, Any]]:
        outgoing: list[dict[str, Any]] = []
        incoming: list[dict[str, Any]] = []

        for rel in self._relations:
            if rel.source_id == node_id:
                target = self._nodes.get(rel.target_id)
                outgoing.append({
                    "direction": "outgoing",
                    "relation": rel.relation_type,
                    "target_id": rel.target_id,
                    "target_label": target.label if target else "unknown",
                    "target_type": target.type if target else "unknown",
                    "weight": rel.weight,
                    "properties": rel.properties,
                })
            if rel.target_id == node_id:
                source = self._nodes.get(rel.source_id)
                incoming.append({
                    "direction": "incoming",
                    "relation": rel.relation_type,
                    "source_id": rel.source_id,
                    "source_label": source.label if source else "unknown",
                    "source_type": source.type if source else "unknown",
                    "weight": rel.weight,
                    "properties": rel.properties,
                })

        return outgoing + incoming

    def get_context_for_org(self, org_id: str = "default") -> str:
        node_ids = self._org_nodes.get(org_id, set())
        if not node_ids:
            return ""

        lines = ["=== Company Knowledge Graph ==="]
        for nid in node_ids:
            node = self._nodes.get(nid)
            if not node:
                continue
            lines.append(f"\n## {node.label} ({node.type})")
            for key, val in node.properties.items():
                lines.append(f"  {key}: {val}")
            rels = self.get_relations(nid)
            if rels:
                for r in rels:
                    if r["direction"] == "outgoing":
                        lines.append(f"  → {r['relation']} → {r['target_label']}")
                    else:
                        lines.append(f"  ← {r['relation']} ← {r['source_label']}")

        return "\n".join(lines)

    def get_company_profile(self, org_id: str = "default") -> dict[str, Any]:
        nodes = [n for n in self._nodes.values() if n.org_id == org_id]
        profile = {
            "name": "",
            "industry": "",
            "metrics": {},
            "key_people": [],
            "products": [],
            "competitors": [],
            "risks": [],
        }

        for n in nodes:
            if n.type == "company":
                profile["name"] = n.properties.get("name", "")
                profile["industry"] = n.properties.get("industry", "")
            elif n.type == "metric":
                profile["metrics"][n.label] = n.properties.get("value", "")
            elif n.type == "person":
                profile["key_people"].append({
                    "name": n.label,
                    "role": n.properties.get("role", ""),
                })
            elif n.type == "product":
                profile["products"].append(n.label)
            elif n.type == "competitor":
                profile["competitors"].append(n.label)
            elif n.type == "risk":
                profile["risks"].append({
                    "description": n.label,
                    "severity": n.properties.get("severity", "medium"),
                })

        return profile

    def delete_node(self, node_id: str) -> bool:
        if node_id not in self._nodes:
            return False
        node = self._nodes.pop(node_id)
        self._relations = [
            r for r in self._relations
            if r.source_id != node_id and r.target_id != node_id
        ]
        org_set = self._org_nodes.get(node.org_id, set())
        org_set.discard(node_id)
        return True

    def clear_org(self, org_id: str) -> int:
        ids = self._org_nodes.pop(org_id, set())
        for nid in ids:
            self._nodes.pop(nid, None)
        self._relations = [
            r for r in self._relations
            if r.source_id not in ids and r.target_id not in ids
        ]
        return len(ids)


_kg: KnowledgeGraph | None = None


def get_knowledge_graph() -> KnowledgeGraph:
    global _kg
    if _kg is None:
        _kg = KnowledgeGraph()
    return _kg
