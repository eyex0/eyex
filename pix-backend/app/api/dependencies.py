from __future__ import annotations

from fastapi import Request

from packages.cognitive_kernel.agent_runtime import set_global_persistent_memory
from packages.cognitive_kernel.memory_engine import PersistentMemory


async def get_memory_service(request: Request) -> PersistentMemory:
    memory = getattr(request.app.state, "memory", None)
    if memory is None:
        memory = PersistentMemory()
        set_global_persistent_memory(memory)
        request.app.state.memory = memory
    return memory
