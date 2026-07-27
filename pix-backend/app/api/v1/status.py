from __future__ import annotations

import logging
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, Request

from app.api.dependencies import get_memory_service
from packages.cognitive_kernel.memory_engine import PersistentMemory

logger = logging.getLogger("pix.api.status")

status_router = APIRouter(prefix="/status", tags=["Status"])

_start_time = datetime.now(UTC)


@status_router.get("")
async def system_status(
    request: Request,
    memory: PersistentMemory = Depends(get_memory_service),
):
    global _start_time
    uptime = (datetime.now(UTC) - _start_time).total_seconds()

    memory_health = None
    try:
        memory_health = await memory.health()
    except Exception as exc:
        memory_health = {"error": str(exc)}

    from app.agents.tools.registry import get_registry
    registry = get_registry()

    return {
        "status": "running",
        "uptime_seconds": uptime,
        "sessions_active": 0,
        "workflows_completed": 0,
        "workflows_failed": 0,
        "memory_health": memory_health,
        "tools_count": len(registry.list_all_tools()),
        "agents_available": len(registry.list_roles()),
        "started_at": _start_time.isoformat(),
    }


@status_router.get("/sessions")
async def list_sessions(
    request: Request,
    memory: PersistentMemory = Depends(get_memory_service),
):
    return {"sessions": [], "total": 0}


@status_router.get("/workflow/{thread_id}")
async def workflow_status(
    thread_id: str,
    request: Request,
    memory: PersistentMemory = Depends(get_memory_service),
):
    state = None
    try:
        state = await memory.get_working_state(thread_id)
    except Exception:
        pass

    if state:
        return {
            "thread_id": thread_id,
            "status": state.get("status", "unknown"),
            "steps": state.get("nodes_executed", []),
            "output": state.get("final_response"),
            "error": state.get("error"),
        }

    return {
        "thread_id": thread_id,
        "status": "not_found",
        "steps": [],
        "output": None,
        "error": None,
    }
