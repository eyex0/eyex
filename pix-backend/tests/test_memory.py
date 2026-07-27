"""Tests for PersistentMemory integration with NodeAgent and AgentGraph."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from langchain_core.language_models import BaseChatModel
from pydantic import BaseModel

from app.agents.base import NodeAgent, set_global_persistent_memory
from app.agents.graph import _get_graph_memory


class DummyOutput(BaseModel):
    summary: str
    details: str


class DummyAgent(NodeAgent):
    @property
    def name(self) -> str:
        return "dummy"

    @property
    def description(self) -> str:
        return "Dummy agent for testing"

    @property
    def system_prompt(self) -> str:
        return "You are a dummy agent."

    @property
    def output_schema(self) -> type[BaseModel]:
        return DummyOutput

    def _fallback_output(self, input_text: str, error: str) -> DummyOutput:
        return DummyOutput(summary=f"Fallback: {error}", details=input_text)


@pytest.fixture
def mock_llm():
    return MagicMock(spec=BaseChatModel)


@pytest.fixture
def mock_memory_service():
    svc = AsyncMock()
    svc.session_factory = MagicMock()
    svc.add_conversation_message = AsyncMock(return_value="msg-id")
    svc.get_conversation = AsyncMock(return_value=[])
    svc.store_interaction = AsyncMock()
    svc.set_agent_memory = AsyncMock()
    return svc


@pytest.fixture
def dummy_agent(mock_llm, mock_memory_service):
    return DummyAgent(llm=mock_llm, memory_service=mock_memory_service)


class TestNodeAgentMemory:
    @pytest.fixture(autouse=True)
    def _clean_memory(self):
        from app.agents.base import _MEMORY

        _MEMORY.clear("test-session")
        _MEMORY.clear("s1")
        yield

    async def test_store_interaction_persistent(self, dummy_agent, mock_memory_service):
        output = DummyOutput(summary="test", details="test details")
        await dummy_agent._store_interaction("test-session", "hello", output)

        mock_memory_service.store_interaction.assert_awaited_once()
        call_kwargs = mock_memory_service.store_interaction.call_args.kwargs
        assert call_kwargs["session_id"] == "test-session"
        assert call_kwargs["agent_name"] == "dummy"
        assert "test" in call_kwargs["assistant_message"]

    async def test_store_interaction_skipped_without_session(self, dummy_agent, mock_memory_service):
        output = DummyOutput(summary="test", details="test details")
        await dummy_agent._store_interaction(None, "hello", output)
        mock_memory_service.store_interaction.assert_not_called()

    async def test_store_interaction_fallback_in_memory(self, mock_llm, mock_memory_service):
        mock_memory_service.store_interaction.side_effect = Exception("DB error")
        agent = DummyAgent(llm=mock_llm, memory_service=mock_memory_service)
        output = DummyOutput(summary="test", details="test details")

        await agent._store_interaction("test-session", "hello", output)

        msgs = agent.memory.get("test-session")
        assert len(msgs) == 2
        assert msgs[0]["role"] == "user"
        assert msgs[0]["content"] == "hello"

    async def test_extract_facts_with_summary(self, dummy_agent):
        output = DummyOutput(summary="test summary", details="test details")
        facts = dummy_agent._extract_facts(output)
        assert any(k == "dummy_last_summary" and v == "test summary" for k, v, _ in facts)

    async def test_extract_facts_no_explanation_field(self, dummy_agent):
        output = DummyOutput(summary="", details="only details")
        facts = dummy_agent._extract_facts(output)
        assert len(facts) == 0

    async def test_load_history_from_memory_service(self, dummy_agent, mock_memory_service):
        mock_memory_service.get_conversation.return_value = [
            {"role": "user", "content": "hi"},
            {"role": "assistant", "content": "hello there"},
        ]

        history = await dummy_agent._load_history("test-session")

        assert len(history) == 2
        assert history[0].content == "hi"
        assert history[1].content == "hello there"
        mock_memory_service.get_conversation.assert_awaited_once_with("test-session", limit=50)

    async def test_load_history_fallback_to_in_memory(self, dummy_agent, mock_memory_service):
        mock_memory_service.get_conversation.side_effect = Exception("DB down")
        dummy_agent.memory.add("test-session", "user", "fallback msg")

        history = await dummy_agent._load_history("test-session")

        assert len(history) == 1
        assert history[0].content == "fallback msg"

    async def test_load_history_returns_empty_without_session(self, dummy_agent):
        history = await dummy_agent._load_history(None)
        assert history == []

    async def test_create_node_returns_callable(self, dummy_agent):
        node_fn = dummy_agent.create_node()
        assert callable(node_fn)
        assert node_fn.__name__ == "dummy_node"

    async def test_create_node_with_mocked_execute(self, dummy_agent):
        node_fn = dummy_agent.create_node()

        with patch.object(dummy_agent, "execute", new=AsyncMock(return_value=DummyOutput(summary="ok", details="test"))):
            result = await node_fn({"request": "test", "session_id": "s1"})
            assert result["dummy_result"]["summary"] == "ok"
            assert result["status"] == "running"

    async def test_create_node_error_handling(self, dummy_agent):
        node_fn = dummy_agent.create_node()

        with patch.object(dummy_agent, "execute", new=AsyncMock(side_effect=ValueError("bad"))):
            result = await node_fn({"request": "test", "session_id": "s1"})
            assert result["status"] == "failed"
            assert "bad" in result["error"]


class TestGlobalMemory:
    def test_set_and_get_global_persistent_memory(self, mock_memory_service):
        set_global_persistent_memory(mock_memory_service)
        from app.agents.base import _get_global_persistent_memory

        assert _get_global_persistent_memory() is mock_memory_service

    def test_graph_memory_getter_setter(self, mock_memory_service):
        assert _get_graph_memory() is None
        from app.agents.graph import _set_graph_memory

        _set_graph_memory(mock_memory_service)
        assert _get_graph_memory() is mock_memory_service
        _set_graph_memory(None)
        assert _get_graph_memory() is None
