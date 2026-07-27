from __future__ import annotations

from fastapi import Request

from packages.cognitive-kernel.agent-runtime import set_global_persistent_memory
from packages.cognitive-kernel.memory-engine import PersistentMemory


async def get_memory_service(request: Request) -> PersistentMemory:
    memory = getattr(request.app.state, "memory", None)
    if memory is None:
        memory = PersistentMemory()
        set_global_persistent_memory(memory)
        request.app.state.memory = memory
    return memory
