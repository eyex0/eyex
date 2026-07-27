"""Benchmark memory operations for PersistentMemory mock and health checks."""
from __future__ import annotations

import time
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.agents.base import NodeAgent, set_global_persistent_memory
from packages.cognitive-kernel.memory-engine import PersistentMemory


class TestPersistentMemoryMockBenchmark:
    @pytest.fixture
    def mock_memory(self):
        svc = AsyncMock(spec=PersistentMemory)
        svc.session_factory = MagicMock()
        svc.add_conversation_message = AsyncMock(return_value="msg-id")
        svc.get_conversation = AsyncMock(return_value=[])
        svc.store_interaction = AsyncMock()
        svc.set_agent_memory = AsyncMock()
        svc.health = AsyncMock(return_value={"healthy": True, "postgresql": True, "redis": True})
        return svc

    async def test_mock_method_call_overhead(self, mock_memory):
        times = []
        for _ in range(100):
            start = time.perf_counter()
            await mock_memory.add_conversation_message("session-1", "user", "hello")
            elapsed = (time.perf_counter() - start) * 1000
            times.append(elapsed)
        avg = sum(times) / len(times)
        assert avg < 1, f"Mock method call avg {avg:.4f}ms exceeded 1ms"

    async def test_mock_store_interaction_overhead(self, mock_memory):
        times = []
        for _ in range(50):
            start = time.perf_counter()
            await mock_memory.store_interaction(
                session_id="session-1",
                user_message="hello",
                assistant_message='{"summary": "test"}',
                agent_name="dummy",
                facts=[("key", "value", 0.5)],
            )
            elapsed = (time.perf_counter() - start) * 1000
            times.append(elapsed)
        avg = sum(times) / len(times)
        assert avg < 10, f"Mock store_interaction avg {avg:.4f}ms exceeded 10ms"

    async def test_health_returns_under_load(self, mock_memory):
        times = []
        for _ in range(20):
            start = time.perf_counter()
            result = await mock_memory.health()
            elapsed = (time.perf_counter() - start) * 1000
            times.append(elapsed)
        avg = sum(times) / len(times)
        assert avg < 100, f"health() avg {avg:.2f}ms exceeded 100ms"
        assert result["healthy"] is True
