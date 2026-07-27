from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, Query, Request

from app.api.dependencies import get_memory_service
from packages.cognitive_kernel.memory_engine import PersistentMemory
from app.dependencies import get_current_org_id, get_current_user
from app.models.user import User
from app.schemas.chat import ConversationHistory
from app.schemas.memory import (
    LongTermMemoryEntry,
    MemoryDeleteResult,
    MemoryOperationResult,
    MemoryStoreRequest,
    MemorySummary,
)

logger = logging.getLogger("pix.api.memory")

memory_router = APIRouter(prefix="/memory", tags=["Memory"])


@memory_router.get("/{session_id}", response_model=MemorySummary)
async def get_memory_summary(
    session_id: str,
    request: Request,
    memory: PersistentMemory = Depends(get_memory_service),
    user: User = Depends(get_current_user),
    org_id: str = Depends(get_current_org_id),
) -> MemorySummary:
    msg_count = await memory.count_conversation_messages(session_id, org_id=org_id)
    long_term = await memory.recall_all(session_id, org_id=org_id)

    agent_memories: dict[str, dict[str, str]] = {}
    for agent_name in ("planner", "researcher", "coder", "reviewer", "tester", "documenter", "devops"):
        am = await memory.get_all_agent_memory(session_id, agent_name, org_id=org_id)
        if am:
            agent_memories[agent_name] = am

    return MemorySummary(
        session_id=session_id,
        message_count=msg_count,
        long_term=long_term,
        agent_memories=agent_memories,
    )


@memory_router.get("/{session_id}/conversation", response_model=ConversationHistory)
async def get_session_conversation(
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


@memory_router.get("/{session_id}/long-term", response_model=list[LongTermMemoryEntry])
async def get_long_term_memory(
    session_id: str,
    request: Request,
    memory: PersistentMemory = Depends(get_memory_service),
    user: User = Depends(get_current_user),
    org_id: str = Depends(get_current_org_id),
) -> list[LongTermMemoryEntry]:
    all_mem = await memory.recall_all(session_id, org_id=org_id)
    return [
        LongTermMemoryEntry(key=k, value=v, importance=0.5)
        for k, v in all_mem.items()
    ]


@memory_router.post("/{session_id}/long-term", response_model=MemoryOperationResult)
async def store_long_term_memory(
    session_id: str,
    body: MemoryStoreRequest,
    request: Request,
    memory: PersistentMemory = Depends(get_memory_service),
    user: User = Depends(get_current_user),
    org_id: str = Depends(get_current_org_id),
) -> MemoryOperationResult:
    await memory.remember(
        session_id=session_id,
        key=body.key,
        value=body.value,
        memory_type=body.memory_type,
        importance=body.importance,
        org_id=org_id,
    )
    return MemoryOperationResult(success=True)


@memory_router.delete("/{session_id}/long-term/{key}", response_model=MemoryOperationResult)
async def forget_long_term_memory(
    session_id: str,
    key: str,
    request: Request,
    memory: PersistentMemory = Depends(get_memory_service),
    user: User = Depends(get_current_user),
    org_id: str = Depends(get_current_org_id),
) -> MemoryOperationResult:
    forgotten = await memory.forget(session_id, key, org_id=org_id)
    return MemoryOperationResult(success=forgotten)


@memory_router.delete("/{session_id}", response_model=MemoryDeleteResult)
async def clear_all_memory(
    session_id: str,
    request: Request,
    memory: PersistentMemory = Depends(get_memory_service),
    user: User = Depends(get_current_user),
    org_id: str = Depends(get_current_org_id),
) -> MemoryDeleteResult:
    conv_deleted = await memory.delete_conversation(session_id, org_id=org_id)
    lt_deleted = await memory.clear_long_term(session_id, org_id=org_id)
    am_deleted = await memory.clear_agent_memory(session_id, org_id=org_id)
    await memory.clear_short_term(session_id)
    await memory.clear_working_state(session_id)
    return MemoryDeleteResult(deleted={
        "conversation": conv_deleted,
        "long_term": lt_deleted,
        "agent_memory": am_deleted,
    })
