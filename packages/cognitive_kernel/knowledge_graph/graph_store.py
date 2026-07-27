from __future__ import annotations
import logging
import uuid
from typing import Any, Dict, List, Optional
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker

logger = logging.getLogger("pix.db.knowledge_graph")

def _to_uuid(val: Any) -> str:
    if not val:
        return "00000000-0000-0000-0000-000000000000"
    if isinstance(val, uuid.UUID):
        return str(val)
    val_str = str(val).strip()
    if val_str == "default":
        return "00000000-0000-0000-0000-000000000000"
    try:
        return str(uuid.UUID(val_str))
    except ValueError:
        return str(uuid.uuid5(uuid.NAMESPACE_DNS, val_str))

class GraphStore:
    def __init__(self, session_factory: async_sessionmaker) -> None:
        self.session_factory = session_factory

    async def add_node(
        self,
        node_id: str,
        label: str,
        node_type: str,
        properties: dict | None = None,
        org_id: str = "default"
    ) -> str:
        uuid_id = _to_uuid(node_id)
        uuid_org = _to_uuid(org_id)
        properties = properties or {}
        
        async with self.session_factory() as session:
            await session.execute(
                text("""
                    INSERT INTO knowledge_nodes (id, org_id, label, type, properties, created_at, updated_at)
                    VALUES (:id, :org_id, :label, :type, :properties, NOW(), NOW())
                    ON CONFLICT (id) DO UPDATE SET
                        label = EXCLUDED.label,
                        type = EXCLUDED.type,
                        properties = EXCLUDED.properties,
                        updated_at = NOW()
                """),
                {
                    "id": uuid_id,
                    "org_id": uuid_org,
                    "label": label,
                    "type": node_type,
                    "properties": properties,
                }
            )
            await session.commit()
            return uuid_id

    async def add_relation(
        self,
        source_id: str,
        target_id: str,
        relation_type: str,
        properties: dict | None = None,
        weight: float = 1.0,
        org_id: str = "default"
    ) -> str:
        uuid_source = _to_uuid(source_id)
        uuid_target = _to_uuid(target_id)
        uuid_org = _to_uuid(org_id)
        properties = properties or {}
        
        async with self.session_factory() as session:
            result = await session.execute(
                text("""
                    INSERT INTO knowledge_edges (org_id, source_id, target_id, relation_type, properties, weight, created_at)
                    VALUES (:org_id, :source_id, :target_id, :relation_type, :properties, :weight, NOW())
                    RETURNING id
                """),
                {
                    "org_id": uuid_org,
                    "source_id": uuid_source,
                    "target_id": uuid_target,
                    "relation_type": relation_type,
                    "properties": properties,
                    "weight": weight,
                }
            )
            row = result.fetchone()
            await session.commit()
            if row:
                return str(row.id)
            raise RuntimeError("Failed to insert relationship")

    async def get_node(self, node_id: str) -> dict | None:
        uuid_id = _to_uuid(node_id)
        async with self.session_factory() as session:
            result = await session.execute(
                text("""
                    SELECT id, org_id, label, type, properties, created_at, updated_at
                    FROM knowledge_nodes
                    WHERE id = :id
                """),
                {"id": uuid_id}
            )
            row = result.fetchone()
            if not row:
                return None
            return {
                "id": str(row.id),
                "org_id": str(row.org_id),
                "label": row.label,
                "type": row.type,
                "properties": row.properties if isinstance(row.properties, dict) else {},
                "created_at": row.created_at.isoformat() if row.created_at else None,
                "updated_at": row.updated_at.isoformat() if row.updated_at else None,
            }

    async def get_neighbors(
        self,
        node_id: str,
        relation_type: str | None = None,
        direction: str = "both"
    ) -> list[dict]:
        uuid_id = _to_uuid(node_id)
        
        params: dict[str, Any] = {"id": uuid_id}
        rel_filter = ""
        if relation_type:
            rel_filter = "AND e.relation_type = :relation_type"
            params["relation_type"] = relation_type
            
        queries = []
        if direction in ("outgoing", "both"):
            queries.append(f"""
                SELECT n.id, n.org_id, n.label, n.type, n.properties, n.created_at, n.updated_at,
                       e.relation_type, e.weight, e.properties as edge_properties,
                       'outgoing' as direction
                FROM knowledge_edges e
                JOIN knowledge_nodes n ON e.target_id = n.id
                WHERE e.source_id = :id {rel_filter}
            """)
        if direction in ("incoming", "both"):
            queries.append(f"""
                SELECT n.id, n.org_id, n.label, n.type, n.properties, n.created_at, n.updated_at,
                       e.relation_type, e.weight, e.properties as edge_properties,
                       'incoming' as direction
                FROM knowledge_edges e
                JOIN knowledge_nodes n ON e.source_id = n.id
                WHERE e.target_id = :id {rel_filter}
            """)
            
        if not queries:
            return []
            
        full_query = " UNION ALL ".join(queries)
        
        async with self.session_factory() as session:
            result = await session.execute(text(full_query), params)
            rows = result.fetchall()
            
            neighbors = []
            for row in rows:
                neighbors.append({
                    "id": str(row.id),
                    "org_id": str(row.org_id),
                    "label": row.label,
                    "type": row.type,
                    "properties": row.properties if isinstance(row.properties, dict) else {},
                    "created_at": row.created_at.isoformat() if row.created_at else None,
                    "updated_at": row.updated_at.isoformat() if row.updated_at else None,
                    "relation_type": row.relation_type,
                    "weight": row.weight,
                    "edge_properties": row.edge_properties if isinstance(row.edge_properties, dict) else {},
                    "direction": row.direction,
                })
            return neighbors

    async def get_relations(self, node_id: str) -> list[dict]:
        uuid_id = _to_uuid(node_id)
        async with self.session_factory() as session:
            result = await session.execute(
                text("""
                    SELECT e.id as edge_id, e.relation_type, e.weight, e.properties as edge_properties,
                           e.source_id, e.target_id,
                           s.label as source_label, s.type as source_type,
                           t.label as target_label, t.type as target_type
                    FROM knowledge_edges e
                    LEFT JOIN knowledge_nodes s ON e.source_id = s.id
                    LEFT JOIN knowledge_nodes t ON e.target_id = t.id
                    WHERE e.source_id = :id OR e.target_id = :id
                """),
                {"id": uuid_id}
            )
            rows = result.fetchall()
            relations = []
            for row in rows:
                is_source = str(row.source_id) == str(uuid_id)
                direction = "outgoing" if is_source else "incoming"
                relations.append({
                    "id": str(row.edge_id),
                    "direction": direction,
                    "relation": row.relation_type,
                    "relation_type": row.relation_type,
                    "source_id": str(row.source_id),
                    "target_id": str(row.target_id),
                    "source_label": row.source_label or "unknown",
                    "source_type": row.source_type or "unknown",
                    "target_label": row.target_label or "unknown",
                    "target_type": row.target_type or "unknown",
                    "weight": row.weight,
                    "properties": row.edge_properties if isinstance(row.edge_properties, dict) else {},
                })
            return relations

    async def search_nodes(
        self,
        query: str,
        node_type: str | None = None,
        org_id: str | None = None,
        limit: int = 20
    ) -> list[dict]:
        uuid_org = _to_uuid(org_id) if org_id else None
        
        sql = """
            SELECT id, org_id, label, type, properties, created_at, updated_at
            FROM knowledge_nodes
            WHERE (label ILIKE :query OR type ILIKE :query)
        """
        params: dict[str, Any] = {"query": f"%{query}%", "limit": limit}
        
        if node_type:
            sql += " AND type = :node_type"
            params["node_type"] = node_type
            
        if uuid_org:
            sql += " AND org_id = :org_id"
            params["org_id"] = uuid_org
            
        sql += " LIMIT :limit"
        
        async with self.session_factory() as session:
            result = await session.execute(text(sql), params)
            rows = result.fetchall()
            return [
                {
                    "id": str(row.id),
                    "org_id": str(row.org_id),
                    "label": row.label,
                    "type": row.type,
                    "properties": row.properties if isinstance(row.properties, dict) else {},
                    "created_at": row.created_at.isoformat() if row.created_at else None,
                    "updated_at": row.updated_at.isoformat() if row.updated_at else None,
                }
                for row in rows
            ]

    async def traverse(
        self,
        start_id: str,
        max_depth: int = 3,
        relation_types: list[str] | None = None
    ) -> dict:
        uuid_start = _to_uuid(start_id)
        
        visited: dict[str, dict] = {}
        queue: list[tuple[str, int]] = [(str(uuid_start), 0)]
        
        while queue:
            current_id, depth = queue.pop(0)
            if current_id in visited:
                continue
                
            node = await self.get_node(current_id)
            if not node:
                continue
                
            neighbors = []
            if relation_types:
                for rt in relation_types:
                    nb = await self.get_neighbors(current_id, relation_type=rt, direction="both")
                    neighbors.extend(nb)
            else:
                neighbors = await self.get_neighbors(current_id, direction="both")
                
            visited[current_id] = {
                "node": node,
                "neighbors": neighbors
            }
            
            if depth < max_depth:
                for n in neighbors:
                    n_id = n["id"]
                    if n_id not in visited:
                        queue.append((n_id, depth + 1))
                        
        return visited

    async def shortest_path(self, source_id: str, target_id: str) -> list[str] | None:
        str_source = str(_to_uuid(source_id))
        str_target = str(_to_uuid(target_id))
        
        if str_source == str_target:
            return [str_source]
            
        queue: list[list[str]] = [[str_source]]
        visited = {str_source}
        
        while queue:
            path = queue.pop(0)
            current_node_id = path[-1]
            
            neighbors = await self.get_neighbors(current_node_id, direction="both")
            for neighbor in neighbors:
                neighbor_id = neighbor["id"]
                if neighbor_id == str_target:
                    return path + [neighbor_id]
                if neighbor_id not in visited:
                    visited.add(neighbor_id)
                    queue.append(path + [neighbor_id])
                    
        return None

    async def centrality(self, node_id: str) -> float:
        uuid_id = _to_uuid(node_id)
        async with self.session_factory() as session:
            res_total = await session.execute(text("SELECT COUNT(*) FROM knowledge_nodes"))
            total_nodes = res_total.scalar() or 0
            if total_nodes <= 1:
                return 0.0
                
            res_deg = await session.execute(
                text("""
                    SELECT COUNT(DISTINCT id) FROM (
                        SELECT id FROM knowledge_edges WHERE source_id = :id
                        UNION
                        SELECT id FROM knowledge_edges WHERE target_id = :id
                    ) as combined
                """),
                {"id": uuid_id}
            )
            degree = res_deg.scalar() or 0
            return float(degree) / (total_nodes - 1)

    async def delete_node(self, node_id: str) -> bool:
        uuid_id = _to_uuid(node_id)
        async with self.session_factory() as session:
            result = await session.execute(
                text("DELETE FROM knowledge_nodes WHERE id = :id"),
                {"id": uuid_id}
            )
            await session.commit()
            return (result.rowcount or 0) > 0

    async def delete_relation(self, relation_id: str) -> bool:
        uuid_id = _to_uuid(relation_id)
        async with self.session_factory() as session:
            result = await session.execute(
                text("DELETE FROM knowledge_edges WHERE id = :id"),
                {"id": uuid_id}
            )
            await session.commit()
            return (result.rowcount or 0) > 0

    async def get_graph_stats(self, org_id: str) -> dict:
        uuid_org = _to_uuid(org_id)
        async with self.session_factory() as session:
            res_nodes = await session.execute(
                text("SELECT COUNT(*) FROM knowledge_nodes WHERE org_id = :org_id"),
                {"org_id": uuid_org}
            )
            node_count = res_nodes.scalar() or 0
            
            res_edges = await session.execute(
                text("SELECT COUNT(*) FROM knowledge_edges WHERE org_id = :org_id"),
                {"org_id": uuid_org}
            )
            edge_count = res_edges.scalar() or 0
            
            res_dist = await session.execute(
                text("""
                    SELECT type, COUNT(*) as cnt 
                    FROM knowledge_nodes 
                    WHERE org_id = :org_id 
                    GROUP BY type
                """),
                {"org_id": uuid_org}
            )
            type_dist = {row.type: row.cnt for row in res_dist.fetchall()}
            
            return {
                "node_count": node_count,
                "edge_count": edge_count,
                "type_distribution": type_dist
            }
