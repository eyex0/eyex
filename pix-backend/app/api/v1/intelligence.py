from __future__ import annotations

import json
import logging
from typing import Any

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile

from app.api.dependencies import get_memory_service
from packages.cognitive_kernel.memory_engine import PersistentMemory
from app.dependencies import (
    get_current_org_id,
    get_current_user,
    require_intelligence_quota,
)
from app.models.user import User
from app.models.workspace import TaskExecution
from app.services.agent_service import AgentOrchestratorService

logger = logging.getLogger("pix.api.intelligence")

intelligence_router = APIRouter(prefix="/intelligence", tags=["Intelligence"])


@intelligence_router.post("/analyze")
async def analyze_business(
    query: str = Form(...),
    context: str | None = Form(None),
    session_id: str | None = Form(None),
    memory: PersistentMemory = Depends(get_memory_service),
    user: User = Depends(get_current_user),
    org_id: str = Depends(get_current_org_id),
    _quota: None = require_intelligence_quota(),
):
    enriched = query
    if context:
        enriched = f"{query}\n\n[Company Context]\n{context}"

    service = AgentOrchestratorService(memory_service=memory, org_id=org_id)
    result = await service.execute(
        type("AgentRequest", (), {"input": enriched, "thread_id": session_id})(),
    )

    if result.success and session_id:
        try:
            steps_json = [s.model_dump() for s in result.steps]
            await _record_analysis(session_id, query, result.output, steps_json, memory)
        except Exception as exc:
            logger.warning("Failed to record analysis: %s", exc)

    return {
        "success": result.success,
        "output": result.output,
        "steps": [s.model_dump() for s in result.steps],
        "session_id": result.thread_id,
        "error": result.error,
    }


@intelligence_router.post("/analyze-stream")
async def analyze_business_stream(
    query: str = Form(...),
    context: str | None = Form(None),
    session_id: str | None = Form(None),
    memory: PersistentMemory = Depends(get_memory_service),
    user: User = Depends(get_current_user),
    org_id: str = Depends(get_current_org_id),
    _quota: None = require_intelligence_quota(),
):
    from starlette.responses import StreamingResponse

    enriched = query
    if context:
        enriched = f"{query}\n\n[Company Context]\n{context}"

    async def event_generator():
        service = AgentOrchestratorService(memory_service=memory, org_id=org_id)
        result = await service.execute(
            type("AgentRequest", (), {"input": enriched, "thread_id": session_id})(),
        )

        for step in result.steps:
            yield f"event: agent\ndata: {json.dumps({'agent': step.node, 'content': step.output[:500]})}\n\n"

        output = result.output or ""
        words = output.split()
        for word in words:
            yield f"event: token\ndata: {json.dumps({'token': word + ' '})}\n\n"

        yield f"event: done\ndata: {json.dumps({'success': result.success, 'session_id': result.thread_id, 'output': result.output})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive", "X-Accel-Buffering": "no"},
    )


@intelligence_router.post("/knowledge")
async def store_knowledge(
    key: str = Form(...),
    value: str = Form(...),
    category: str = Form("fact"),
    memory: PersistentMemory = Depends(get_memory_service),
    session_id: str = Form("default"),
    user: User = Depends(get_current_user),
    org_id: str = Depends(get_current_org_id),
):
    await memory.remember(
        session_id=session_id,
        key=f"knowledge:{key}",
        value=value,
        memory_type=category,
        importance=0.8,
        org_id=org_id,
    )
    return {"stored": True, "key": key, "category": category}


@intelligence_router.get("/knowledge")
async def get_knowledge(
    category: str | None = Query(None),
    memory: PersistentMemory = Depends(get_memory_service),
    session_id: str = Query("default"),
    user: User = Depends(get_current_user),
    org_id: str = Depends(get_current_org_id),
):
    if category:
        records = await memory.recall_by_type(session_id, category, org_id=org_id)
    else:
        raw = await memory.recall_all(session_id, min_importance=0.0, org_id=org_id)
        records = [{"key": k, "value": v, "category": "fact"} for k, v in raw.items() if k.startswith("knowledge:")]
    return {"records": records, "count": len(records)}


@intelligence_router.post("/documents/upload")
async def upload_document(
    file: UploadFile = File(...),
    session_id: str = Form("default"),
    memory: PersistentMemory = Depends(get_memory_service),
    user: User = Depends(get_current_user),
    org_id: str = Depends(get_current_org_id),
):
    content = await file.read()
    text = content.decode("utf-8", errors="replace")
    chunks = _chunk_text(text)

    stored = []
    for i, chunk in enumerate(chunks):
        key = f"document:{file.filename}:chunk:{i}"
        await memory.remember(
            session_id=session_id,
            key=key,
            value=chunk,
            memory_type="document",
            importance=0.7,
            org_id=org_id,
        )
        stored.append({"chunk": i, "key": key, "size": len(chunk)})

    await memory.remember(
        session_id=session_id,
        key=f"document:{file.filename}:meta",
        value=json.dumps({"filename": file.filename, "chunks": len(chunks), "total_size": len(text)}),
        memory_type="document_meta",
        importance=0.9,
        org_id=org_id,
    )

    return {
        "filename": file.filename,
        "chunks": len(chunks),
        "total_chars": len(text),
        "stored": stored,
    }


@intelligence_router.get("/documents")
async def list_documents(
    memory: PersistentMemory = Depends(get_memory_service),
    session_id: str = Query("default"),
    user: User = Depends(get_current_user),
    org_id: str = Depends(get_current_org_id),
):
    raw = await memory.recall_all(session_id, min_importance=0.0, org_id=org_id)
    docs = {}
    for k, v in raw.items():
        if k.startswith("document:") and k.endswith(":meta"):
            docs[k.replace(":meta", "").replace("document:", "")] = json.loads(v)
    return {"documents": list(docs.values())}


@intelligence_router.get("/documents/{filename}")
async def get_document(
    filename: str,
    memory: PersistentMemory = Depends(get_memory_service),
    session_id: str = Query("default"),
    user: User = Depends(get_current_user),
    org_id: str = Depends(get_current_org_id),
):
    raw = await memory.recall_all(session_id, min_importance=0.0, org_id=org_id)
    chunks = []
    for k, v in raw.items():
        if k.startswith(f"document:{filename}:chunk:"):
            chunks.append({"index": int(k.split(":")[-1]), "content": v})
    chunks.sort(key=lambda c: c["index"])
    return {"filename": filename, "chunks": len(chunks), "content": "\n".join(c["content"] for c in chunks)}


@intelligence_router.get("/report/{session_id}")
async def get_report(
    session_id: str,
    memory: PersistentMemory = Depends(get_memory_service),
    user: User = Depends(get_current_user),
    org_id: str = Depends(get_current_org_id),
):
    try:
        conversation = await memory.get_conversation(session_id, limit=100, org_id=org_id)
        knowledge = await memory.recall_all(session_id, min_importance=0.5, org_id=org_id)
        return {
            "session_id": session_id,
            "messages": conversation,
            "knowledge": knowledge,
            "message_count": len(conversation),
        }
    except Exception as exc:
        return {"error": str(exc), "session_id": session_id}


async def _record_analysis(
    session_id: str,
    query: str,
    output: str,
    steps: list[dict[str, Any]],
    memory: PersistentMemory,
) -> None:
    try:
        async with memory.session_factory() as db:
            task = TaskExecution(
                session_id=session_id,
                input_text=query[:5000],
                output_text=output[:5000] if output else None,
                status="completed" if output else "failed",
                steps=steps,
                agent_role="intelligence",
            )
            db.add(task)
    except Exception:
        pass


def _chunk_text(text: str, max_chars: int = 2000) -> list[str]:
    if len(text) <= max_chars:
        return [text]
    chunks = []
    for i in range(0, len(text), max_chars):
        chunks.append(text[i:i + max_chars])
    return chunks
