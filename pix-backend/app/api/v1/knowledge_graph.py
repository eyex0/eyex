"""πX Knowledge Graph API."""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from app.dependencies import get_current_org_id, get_current_user
from app.models.user import User

logger = logging.getLogger("pix.api.knowledge")

knowledge_router = APIRouter(prefix="/knowledge", tags=["Knowledge Graph"])


class NodeCreate(BaseModel):
    label: str
    type: str
    properties: dict = {}


class RelationCreate(BaseModel):
    source_id: str
    target_id: str
    relation_type: str
    properties: dict = {}
    weight: float = 1.0


class ExtractRequest(BaseModel):
    text: str


class BuildRequest(BaseModel):
    document_id: str
    text: str


@knowledge_router.get("/nodes")
async def list_nodes(
    node_type: str | None = None,
    search: str | None = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    user: User = Depends(get_current_user),
    org_id: str = Depends(get_current_org_id),
):
    from sqlalchemy import text
    from app.database import async_session_factory
    conditions = ["org_id = :org_id"]
    params = {"org_id": org_id, "limit": limit, "offset": offset}
    if node_type:
        conditions.append("type = :ntype")
        params["ntype"] = node_type
    if search:
        conditions.append("label ILIKE :search")
        params["search"] = f"%{search}%"
    where = " AND ".join(conditions)
    async with async_session_factory() as db:
        result = await db.execute(
            text(f"SELECT id, label, type, properties FROM knowledge_nodes WHERE {where} LIMIT :limit OFFSET :offset"),
            params,
        )
        nodes = [{"id": r[0], "label": r[1], "type": r[2], "properties": r[3]} for r in result.fetchall()]
    return {"nodes": nodes, "total": len(nodes)}


@knowledge_router.post("/nodes")
async def create_node(
    body: NodeCreate,
    user: User = Depends(get_current_user),
    org_id: str = Depends(get_current_org_id),
):
    import uuid
    from sqlalchemy import text
    from app.database import async_session_factory
    node_id = str(uuid.uuid4())
    async with async_session_factory() as db:
        await db.execute(
            text("INSERT INTO knowledge_nodes (id, org_id, label, type, properties) VALUES (:id, :org_id, :label, :type, :props)"),
            {"id": node_id, "org_id": org_id, "label": body.label, "type": body.type, "props": str(body.properties).replace("'", '"')},
        )
        await db.commit()
    return {"id": node_id, "label": body.label, "type": body.type}


@knowledge_router.get("/nodes/{node_id}")
async def get_node(node_id: str, user: User = Depends(get_current_user), org_id: str = Depends(get_current_org_id)):
    from sqlalchemy import text
    from app.database import async_session_factory
    async with async_session_factory() as db:
        result = await db.execute(
            text("SELECT id, label, type, properties FROM knowledge_nodes WHERE id = :id AND org_id = :org_id"),
            {"id": node_id, "org_id": org_id},
        )
        row = result.fetchone()
        if not row:
            return {"error": "Node not found"}, 404
        edges = await db.execute(
            text("SELECT id, source_id, target_id, relation_type, weight FROM knowledge_edges WHERE (source_id = :id OR target_id = :id) AND org_id = :org_id"),
            {"id": node_id, "org_id": org_id},
        )
        neighbors = [{"id": str(e[0]), "source": e[1], "target": e[2], "relation_type": e[3], "weight": e[4]} for e in edges.fetchall()]
    return {"id": row[0], "label": row[1], "type": row[2], "properties": row[3], "neighbors": neighbors}


@knowledge_router.delete("/nodes/{node_id}")
async def delete_node(node_id: str, user: User = Depends(get_current_user), org_id: str = Depends(get_current_org_id)):
    from sqlalchemy import text
    from app.database import async_session_factory
    async with async_session_factory() as db:
        await db.execute(text("DELETE FROM knowledge_edges WHERE (source_id = :id OR target_id = :id) AND org_id = :org_id"), {"id": node_id, "org_id": org_id})
        result = await db.execute(text("DELETE FROM knowledge_nodes WHERE id = :id AND org_id = :org_id"), {"id": node_id, "org_id": org_id})
        await db.commit()
    return {"deleted": result.rowcount > 0}


@knowledge_router.post("/relations")
async def create_relation(
    body: RelationCreate,
    user: User = Depends(get_current_user),
    org_id: str = Depends(get_current_org_id),
):
    import uuid
    from sqlalchemy import text
    from app.database import async_session_factory
    rel_id = str(uuid.uuid4())
    async with async_session_factory() as db:
        await db.execute(
            text("INSERT INTO knowledge_edges (id, org_id, source_id, target_id, relation_type, properties, weight) VALUES (:id, :org_id, :src, :tgt, :rel, :props, :weight)"),
            {"id": rel_id, "org_id": org_id, "src": body.source_id, "tgt": body.target_id, "rel": body.relation_type, "props": str(body.properties).replace("'", '"'), "weight": body.weight},
        )
        await db.commit()
    return {"id": rel_id}


@knowledge_router.get("/graph")
async def get_graph(
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    user: User = Depends(get_current_user),
    org_id: str = Depends(get_current_org_id),
):
    from sqlalchemy import text
    from app.database import async_session_factory
    async with async_session_factory() as db:
        nodes_result = await db.execute(
            text("SELECT id, label, type FROM knowledge_nodes WHERE org_id = :org_id LIMIT :limit OFFSET :offset"),
            {"org_id": org_id, "limit": limit, "offset": offset},
        )
        nodes = [{"id": r[0], "label": r[1], "type": r[2]} for r in nodes_result.fetchall()]
        edges_result = await db.execute(
            text("SELECT source_id, target_id, relation_type FROM knowledge_edges WHERE org_id = :org_id LIMIT :limit"),
            {"org_id": org_id, "limit": limit * 2},
        )
        edges = [{"source": r[0], "target": r[1], "relation_type": r[2]} for r in edges_result.fetchall()]
    return {"nodes": nodes, "edges": edges}


@knowledge_router.post("/extract")
async def extract_entities(
    body: ExtractRequest,
    user: User = Depends(get_current_user),
    org_id: str = Depends(get_current_org_id),
):
    from packages.cognitive_kernel.knowledge_graph.entity_extractor import EntityExtractor
    extractor = EntityExtractor()
    entities = await extractor.extract_entities(body.text, org_id)
    relationships = await extractor.extract_relationships(body.text, entities)
    return {"entities": entities, "relationships": relationships}


@knowledge_router.post("/build")
async def build_graph(
    body: BuildRequest,
    user: User = Depends(get_current_user),
    org_id: str = Depends(get_current_org_id),
):
    from packages.cognitive_kernel.knowledge_graph.graph_builder import GraphBuilder
    builder = GraphBuilder()
    result = await builder.build_from_document(body.document_id, body.text, org_id)
    return result


@knowledge_router.get("/stats")
async def graph_stats(user: User = Depends(get_current_user), org_id: str = Depends(get_current_org_id)):
    from sqlalchemy import text
    from app.database import async_session_factory
    async with async_session_factory() as db:
        node_count = await db.execute(text("SELECT COUNT(*) FROM knowledge_nodes WHERE org_id = :oid"), {"oid": org_id})
        edge_count = await db.execute(text("SELECT COUNT(*) FROM knowledge_edges WHERE org_id = :oid"), {"oid": org_id})
        type_dist = await db.execute(text("SELECT type, COUNT(*) FROM knowledge_nodes WHERE org_id = :oid GROUP BY type"), {"oid": org_id})
    return {
        "node_count": node_count.scalar() or 0,
        "edge_count": edge_count.scalar() or 0,
        "type_distribution": {r[0]: r[1] for r in type_dist.fetchall()},
    }
