from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient

from app.api.dependencies import get_memory_service
from app.dependencies import get_current_user
from app.main import app


@pytest.fixture
def mock_user():
    from app.models.user import User
    return User(
        id="00000000-0000-0000-0000-000000000002",
        email="user@test.com",
        hashed_password="x",
        is_active=True,
        is_superuser=False,
    )


@pytest.fixture
def mock_memory(mock_user):
    app.dependency_overrides[get_current_user] = lambda: mock_user
    m = AsyncMock()
    m.health.return_value = {"postgresql": True, "redis": True, "healthy": True}
    m.count_conversation_messages.return_value = 3
    m.get_conversation.return_value = [
        {"id": "1", "role": "user", "content": "hello", "agent_name": None, "created_at": "2024-01-01T00:00:00", "metadata": {}},
        {"id": "2", "role": "assistant", "content": "hi", "agent_name": "coder", "created_at": "2024-01-01T00:00:01", "metadata": {}},
    ]
    m.recall_all.return_value = {"user_name": "Alice", "project": "πX"}
    m.get_all_agent_memory.return_value = {"last_output": "some code"}
    m.delete_conversation.return_value = 2
    m.clear_long_term.return_value = 2
    m.clear_agent_memory.return_value = 1
    m.forget.return_value = True
    m.remember = AsyncMock()
    m.set_working_state = AsyncMock()
    m.clear_short_term = AsyncMock()
    m.clear_working_state = AsyncMock()
    return m


@pytest.fixture(autouse=True)
def clear_overrides():
    app.dependency_overrides.clear()
    yield
    app.dependency_overrides.clear()


# ------------------------------------------------------------------ #
#  /health
# ------------------------------------------------------------------ #

@pytest.mark.asyncio
async def test_health_degraded(client: AsyncClient):
    """Without lifespan — memory not configured — should report degraded."""
    resp = await client.get("/api/v1/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "degraded"
    assert data["dependencies"]["postgresql"] is False
    assert data["dependencies"]["redis"] is False
    assert data["dependencies"]["tools"] > 0
    assert "uptime_seconds" in data


@pytest.mark.asyncio
async def test_health_with_memory(client: AsyncClient, mock_memory):
    app.state.memory = mock_memory
    resp = await client.get("/api/v1/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["dependencies"]["postgresql"] is True
    assert data["dependencies"]["redis"] is True
    app.state.memory = None


# ------------------------------------------------------------------ #
#  /chat
# ------------------------------------------------------------------ #

@pytest.mark.asyncio
async def test_chat_get_conversation(client: AsyncClient, mock_memory):
    app.dependency_overrides[get_memory_service] = lambda: mock_memory
    resp = await client.get("/api/v1/chat/test-session")
    assert resp.status_code == 200
    data = resp.json()
    assert data["session_id"] == "test-session"
    assert len(data["messages"]) == 2
    assert data["messages"][0]["role"] == "user"


@pytest.mark.asyncio
async def test_chat_get_conversation_empty(client: AsyncClient, mock_memory):
    mock_memory.get_conversation.return_value = []
    app.dependency_overrides[get_memory_service] = lambda: mock_memory
    resp = await client.get("/api/v1/chat/empty-session")
    assert resp.status_code == 200
    data = resp.json()
    assert data["session_id"] == "empty-session"
    assert data["messages"] == []


@pytest.mark.asyncio
async def test_chat_delete_conversation(client: AsyncClient, mock_memory):
    app.dependency_overrides[get_memory_service] = lambda: mock_memory
    resp = await client.delete("/api/v1/chat/test-session")
    assert resp.status_code == 200
    data = resp.json()
    assert data["deleted"] == 2
    assert data["session_id"] == "test-session"


@pytest.mark.asyncio
async def test_chat_post_send_message(client: AsyncClient, mock_memory):
    app.dependency_overrides[get_memory_service] = lambda: mock_memory
    from app.services.agent_service import AgentOrchestratorService
    from app.schemas.agent import AgentStep, WorkflowResult

    with patch.object(AgentOrchestratorService, "execute") as mock_exec:
        mock_exec.return_value = WorkflowResult(
            success=True,
            output="Test agent response",
            steps=[AgentStep(node="planner", output="plan created", duration_ms=100)],
            thread_id="session-1",
        )
        resp = await client.post("/api/v1/chat", json={
            "message": "build a todo app",
            "session_id": "session-1",
        })

    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert data["output"] == "Test agent response"
    assert data["session_id"] == "session-1"
    assert len(data["steps"]) == 1


@pytest.mark.asyncio
async def test_chat_post_without_session(client: AsyncClient, mock_memory):
    app.dependency_overrides[get_memory_service] = lambda: mock_memory
    from app.services.agent_service import AgentOrchestratorService
    from app.schemas.agent import WorkflowResult

    with patch.object(AgentOrchestratorService, "execute") as mock_exec:
        mock_exec.return_value = WorkflowResult(
            success=True, output="hello back", steps=[], thread_id="auto-gen-id",
        )
        resp = await client.post("/api/v1/chat", json={
            "message": "hello",
        })

    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True


# ------------------------------------------------------------------ #
#  /agents  (v2)
# ------------------------------------------------------------------ #

@pytest.mark.asyncio
async def test_list_agents(client: AsyncClient):
    resp = await client.get("/api/v1/agents")
    assert resp.status_code == 200
    data = resp.json()
    assert "agents" in data
    roles = {a["role"] for a in data["agents"]}
    assert "planner" in roles
    assert "coder" in roles
    assert "devops" in roles
    for agent in data["agents"]:
        assert "name" in agent
        assert "description" in agent
        assert "tools" in agent
        assert isinstance(agent["tools"], list)


@pytest.mark.asyncio
async def test_get_agent_detail(client: AsyncClient):
    resp = await client.get("/api/v1/agents/coder")
    assert resp.status_code == 200
    data = resp.json()
    assert data["role"] == "coder"
    assert data["name"]
    assert data["description"]
    assert len(data["tools"]) > 0


@pytest.mark.asyncio
async def test_get_agent_detail_not_found(client: AsyncClient):
    resp = await client.get("/api/v1/agents/nonexistent")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_execute_agent_by_role(client: AsyncClient, mock_memory):
    app.dependency_overrides[get_memory_service] = lambda: mock_memory
    from pydantic import BaseModel

    class FakeOutput(BaseModel):
        summary: str = "done"
        plan: str = "step 1"

    from app.agents.base import NodeAgent
    with patch.object(NodeAgent, "execute") as mock_exec:
        mock_exec.return_value = FakeOutput()
        resp = await client.post("/api/v1/agents/planner/execute", json={
            "input": "plan a project",
            "session_id": "sess-1",
        })

    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert data["agent_name"] == "planner"


@pytest.mark.asyncio
async def test_execute_agent_role_not_found(client: AsyncClient, mock_memory):
    app.dependency_overrides[get_memory_service] = lambda: mock_memory
    resp = await client.post("/api/v1/agents/nonexistent/execute", json={
        "input": "test",
    })
    assert resp.status_code == 404


# ------------------------------------------------------------------ #
#  /status
# ------------------------------------------------------------------ #

@pytest.mark.asyncio
async def test_system_status(client: AsyncClient, mock_memory):
    app.dependency_overrides[get_memory_service] = lambda: mock_memory
    resp = await client.get("/api/v1/status")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "running"
    assert data["tools_count"] > 0
    assert data["agents_available"] > 0
    assert data["memory_health"]["postgresql"] is True
    assert "uptime_seconds" in data


@pytest.mark.asyncio
async def test_status_list_sessions(client: AsyncClient, mock_memory):
    app.dependency_overrides[get_memory_service] = lambda: mock_memory
    resp = await client.get("/api/v1/status/sessions")
    assert resp.status_code == 200
    data = resp.json()
    assert "sessions" in data
    assert data["total"] == 0


@pytest.mark.asyncio
async def test_status_workflow_not_found(client: AsyncClient, mock_memory):
    mock_memory.get_working_state.return_value = None
    app.dependency_overrides[get_memory_service] = lambda: mock_memory
    resp = await client.get("/api/v1/status/workflow/unknown-thread")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "not_found"


@pytest.mark.asyncio
async def test_status_workflow_found(client: AsyncClient, mock_memory):
    mock_memory.get_working_state.return_value = {
        "status": "completed", "nodes_executed": [{"node": "planner"}],
        "final_response": "plan ready",
    }
    app.dependency_overrides[get_memory_service] = lambda: mock_memory
    resp = await client.get("/api/v1/status/workflow/thread-1")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "completed"
    assert data["output"] == "plan ready"
    assert len(data["steps"]) == 1


# ------------------------------------------------------------------ #
#  /memory
# ------------------------------------------------------------------ #

@pytest.mark.asyncio
async def test_memory_summary(client: AsyncClient, mock_memory):
    app.dependency_overrides[get_memory_service] = lambda: mock_memory
    resp = await client.get("/api/v1/memory/session-1")
    assert resp.status_code == 200
    data = resp.json()
    assert data["session_id"] == "session-1"
    assert data["message_count"] == 3
    assert "user_name" in data["long_term"]


@pytest.mark.asyncio
async def test_memory_get_conversation(client: AsyncClient, mock_memory):
    app.dependency_overrides[get_memory_service] = lambda: mock_memory
    resp = await client.get("/api/v1/memory/session-1/conversation")
    assert resp.status_code == 200
    data = resp.json()
    assert data["session_id"] == "session-1"
    assert len(data["messages"]) == 2


@pytest.mark.asyncio
async def test_memory_get_long_term(client: AsyncClient, mock_memory):
    app.dependency_overrides[get_memory_service] = lambda: mock_memory
    resp = await client.get("/api/v1/memory/session-1/long-term")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    keys = {e["key"] for e in data}
    assert "user_name" in keys


@pytest.mark.asyncio
async def test_memory_store_long_term(client: AsyncClient, mock_memory):
    app.dependency_overrides[get_memory_service] = lambda: mock_memory
    resp = await client.post("/api/v1/memory/session-1/long-term", json={
        "key": "preference",
        "value": "dark mode",
        "memory_type": "preference",
        "importance": 0.8,
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    mock_memory.remember.assert_awaited_once_with(
        session_id="session-1", key="preference", value="dark mode",
        memory_type="preference", importance=0.8, org_id="default",
    )


@pytest.mark.asyncio
async def test_memory_forget_long_term(client: AsyncClient, mock_memory):
    app.dependency_overrides[get_memory_service] = lambda: mock_memory
    resp = await client.delete("/api/v1/memory/session-1/long-term/user_name")
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    mock_memory.forget.assert_awaited_once_with("session-1", "user_name", org_id="default")


@pytest.mark.asyncio
async def test_memory_clear_all(client: AsyncClient, mock_memory):
    app.dependency_overrides[get_memory_service] = lambda: mock_memory
    resp = await client.delete("/api/v1/memory/session-1")
    assert resp.status_code == 200
    data = resp.json()
    assert data["deleted"]["conversation"] == 2
    assert data["deleted"]["long_term"] == 2
    assert data["deleted"]["agent_memory"] == 1
    mock_memory.clear_short_term.assert_awaited_once_with("session-1")
    mock_memory.clear_working_state.assert_awaited_once_with("session-1")


@pytest.mark.asyncio
async def test_memory_forget_not_found(client: AsyncClient, mock_memory):
    mock_memory.forget.return_value = False
    app.dependency_overrides[get_memory_service] = lambda: mock_memory
    resp = await client.delete("/api/v1/memory/session-1/long-term/missing_key")
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is False


@pytest.mark.asyncio
async def test_chat_message_too_long(client: AsyncClient, mock_memory):
    app.dependency_overrides[get_memory_service] = lambda: mock_memory
    resp = await client.post("/api/v1/chat", json={
        "message": "x" * 13_000,
        "session_id": "test-session",
    })
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_chat_daily_quota_enforced(client: AsyncClient, mock_memory, monkeypatch):
    from app import dependencies as deps_module
    from app.config import Settings, get_settings
    from app.core.quota import reset_quota_service
    from app.services.agent_service import AgentOrchestratorService

    app.dependency_overrides[get_memory_service] = lambda: mock_memory
    get_settings.cache_clear()
    reset_quota_service()

    base_settings = get_settings()
    limited_settings = Settings(
        **{
            **base_settings.model_dump(),
            "chat_daily_message_limit": 2,
        }
    )
    monkeypatch.setattr(deps_module, "get_settings", lambda: limited_settings)

    with patch.object(AgentOrchestratorService, "execute") as mock_exec:
        mock_exec.return_value = AsyncMock(
            success=True, output="hi", steps=[], thread_id="test-session", error=None
        )
        for _ in range(2):
            resp = await client.post("/api/v1/chat", json={
                "message": "hello",
                "session_id": "test-session",
            })
            assert resp.status_code == 200

        resp = await client.post("/api/v1/chat", json={
            "message": "hello",
            "session_id": "test-session",
        })
        assert resp.status_code == 429
        assert "Daily chat limit reached" in resp.json()["detail"]
