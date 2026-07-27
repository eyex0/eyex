from __future__ import annotations

import asyncio
import json
import logging

from fastapi import APIRouter, Depends, Query, Request, WebSocket, WebSocketDisconnect
from starlette.responses import StreamingResponse

from app.api.dependencies import get_memory_service
from app.core.context import org_id_ctx
from app.core.security import decode_token
from app.core.supabase_auth import decode_supabase_token, extract_user_id, is_supabase_token
from app.database import async_session_factory
from packages.cognitive-kernel.memory-engine import PersistentMemory
from app.dependencies import get_current_org_id, get_current_user, require_chat_quota
from app.models.user import User
from app.schemas.agent import AgentRequest, WorkflowResult
from app.schemas.chat import ChatRequest, ChatResponse, ConversationHistory
from app.services.agent_service import AgentOrchestratorService

logger = logging.getLogger("pix.api.chat")

chat_router = APIRouter(prefix="/chat", tags=["Chat"])


@chat_router.post("", response_model=ChatResponse)
async def send_message(
    body: ChatRequest,
    request: Request,
    memory: PersistentMemory = Depends(get_memory_service),
    user: User = Depends(get_current_user),
    org_id: str = Depends(get_current_org_id),
    _quota: None = require_chat_quota(),
) -> ChatResponse:
    service = AgentOrchestratorService(memory_service=memory, org_id=org_id)
    result: WorkflowResult = await service.execute(
        AgentRequest(input=body.message, thread_id=body.session_id)
    )
    return ChatResponse(
        success=result.success,
        output=result.output,
        steps=[s.model_dump() for s in result.steps],
        session_id=result.thread_id,
        error=result.error,
    )


@chat_router.get("/{session_id}", response_model=ConversationHistory)
async def get_conversation(
    session_id: str,
    request: Request,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    memory: PersistentMemory = Depends(get_memory_service),
    user: User = Depends(get_current_user),
    org_id: str = Depends(get_current_org_id),
) -> ConversationHistory:
    messages = await memory.get_conversation(session_id, limit=limit, offset=offset, org_id=org_id)
    return ConversationHistory(
        session_id=session_id,
        messages=[
            {
                "id": m["id"],
                "role": m["role"],
                "content": m["content"],
                "agent_name": m.get("agent_name"),
                "created_at": m.get("created_at"),
            }
            for m in messages
        ],
    )


@chat_router.delete("/{session_id}")
async def delete_conversation(
    session_id: str,
    request: Request,
    memory: PersistentMemory = Depends(get_memory_service),
    user: User = Depends(get_current_user),
    org_id: str = Depends(get_current_org_id),
) -> dict:
    count = await memory.delete_conversation(session_id, org_id=org_id)
    return {"deleted": count, "session_id": session_id}


@chat_router.post("/stream")
async def stream_chat(
    body: ChatRequest,
    request: Request,
    memory: PersistentMemory = Depends(get_memory_service),
    user: User = Depends(get_current_user),
    org_id: str = Depends(get_current_org_id),
    _quota: None = require_chat_quota(),
) -> StreamingResponse:
    service = AgentOrchestratorService(memory_service=memory, org_id=org_id)

    async def event_generator():
        try:
            result: WorkflowResult = await service.execute(
                AgentRequest(input=body.message, thread_id=body.session_id)
            )

            for step in result.steps:
                event_data = json.dumps({"agent": step.node, "content": step.output})
                yield f"event: agent\ndata: {event_data}\n\n"

            output = result.output or ""
            words = output.split()
            for word in words:
                yield f"event: token\ndata: {json.dumps({'token': word + ' '})}\n\n"
                await asyncio.sleep(0.02)

            yield f"event: done\ndata: {json.dumps({'success': result.success, 'session_id': result.thread_id, 'output': result.output})}\n\n"
        except Exception as exc:
            logger.exception("Stream chat failed")
            yield f"event: error\ndata: {json.dumps({'error': str(exc)})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


async def _resolve_org_id_for_user(user: User | None) -> str | None:
    if user is None:
        return None
    user_org_ids = {str(m.organization_id) for m in user.organizations}
    return next(iter(user_org_ids), None) or "default"


@chat_router.websocket("/ws")
async def websocket_chat(websocket: WebSocket, token: str = Query(...)) -> None:
    if is_supabase_token(token):
        payload = decode_supabase_token(token)
    else:
        payload = decode_token(token)
    user_id = extract_user_id(payload)
    if not user_id:
        await websocket.close(code=4001, reason="Unauthorized")
        return

    user: User | None = None
    try:
        async with async_session_factory() as session:
            from uuid import UUID
            user = await session.get(User, UUID(user_id))
    except Exception:
        logger.warning("Failed to resolve websocket user %s", user_id)

    org_id = await _resolve_org_id_for_user(user)
    org_token = org_id_ctx.set(org_id)
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_json()
            if data.get("type") == "message":
                content = data.get("content", "")
                session_id = data.get("session_id")

                memory: PersistentMemory = getattr(websocket.app.state, "memory", None)
                if memory is None:
                    memory = PersistentMemory()

                service = AgentOrchestratorService(memory_service=memory, org_id=org_id)
                result: WorkflowResult = await service.execute(
                    AgentRequest(input=content, thread_id=session_id)
                )

                for step in result.steps:
                    await websocket.send_json({
                        "type": "agent",
                        "agent": step.node,
                        "content": step.output,
                    })

                await websocket.send_json({
                    "type": "result",
                    "success": result.success,
                    "output": result.output,
                    "session_id": result.thread_id,
                })
            elif data.get("type") == "ping":
                await websocket.send_json({"type": "pong"})
    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected")
    except Exception as exc:
        logger.exception("WebSocket error")
        try:
            await websocket.send_json({"type": "error", "error": str(exc)})
        except Exception:
            pass
    finally:
        org_id_ctx.reset(org_token)
