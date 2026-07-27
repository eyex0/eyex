"""Benchmark schema validation for all Pydantic model types."""
from __future__ import annotations

import time
from datetime import datetime, timezone

import pytest

from app.schemas.agent import AgentRequest, AgentResponse, AgentStep, WorkflowResult
from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse
from app.schemas.chat import ChatMessage, ChatRequest, ChatResponse, ConversationHistory
from app.schemas.memory import (
    LongTermMemoryEntry,
    MemoryDeleteResult,
    MemoryOperationResult,
    MemoryStoreRequest,
    MemorySummary,
)
from app.schemas.status import SessionInfo, SessionList, SystemStatus, WorkflowStatusResponse
from app.schemas.user import UserCreate, UserRead, UserUpdate


class TestAgentSchemaBenchmark:
    def test_agent_request_creation(self):
        times = []
        for _ in range(1000):
            start = time.perf_counter()
            m = AgentRequest(input="Write a Python function to calculate fibonacci numbers.")
            elapsed = (time.perf_counter() - start) * 1000
            times.append(elapsed)
        avg = sum(times) / len(times)
        assert avg < 1, f"AgentRequest avg {avg:.4f}ms exceeded 1ms"

    def test_workflow_result_creation(self):
        times = []
        for _ in range(1000):
            start = time.perf_counter()
            m = WorkflowResult(success=True, output="Done", thread_id="t1")
            elapsed = (time.perf_counter() - start) * 1000
            times.append(elapsed)
        avg = sum(times) / len(times)
        assert avg < 1, f"WorkflowResult avg {avg:.4f}ms exceeded 1ms"

    def test_agent_step_creation(self):
        times = []
        for _ in range(1000):
            start = time.perf_counter()
            m = AgentStep(node="coder", output="completed", duration_ms=100)
            elapsed = (time.perf_counter() - start) * 1000
            times.append(elapsed)
        avg = sum(times) / len(times)
        assert avg < 1, f"AgentStep avg {avg:.4f}ms exceeded 1ms"

    def test_agent_response_creation(self):
        from app.schemas.agent import AgentResponse

        wr = WorkflowResult(success=True, output="Done", thread_id="t1")
        times = []
        for _ in range(1000):
            start = time.perf_counter()
            m = AgentResponse(result=wr)
            elapsed = (time.perf_counter() - start) * 1000
            times.append(elapsed)
        avg = sum(times) / len(times)
        assert avg < 1, f"AgentResponse avg {avg:.4f}ms exceeded 1ms"


class TestAuthSchemaBenchmark:
    def test_login_request_creation(self):
        times = []
        for _ in range(1000):
            start = time.perf_counter()
            m = LoginRequest(email="user@example.com", password="securepass123")
            elapsed = (time.perf_counter() - start) * 1000
            times.append(elapsed)
        avg = sum(times) / len(times)
        assert avg < 1, f"LoginRequest avg {avg:.4f}ms exceeded 1ms"

    def test_register_request_creation(self):
        times = []
        for _ in range(1000):
            start = time.perf_counter()
            m = RegisterRequest(email="user@example.com", password="securepass123", full_name="Test User")
            elapsed = (time.perf_counter() - start) * 1000
            times.append(elapsed)
        avg = sum(times) / len(times)
        assert avg < 1, f"RegisterRequest avg {avg:.4f}ms exceeded 1ms"

    def test_token_response_creation(self):
        times = []
        for _ in range(1000):
            start = time.perf_counter()
            m = TokenResponse(access_token="abc", refresh_token="def", expires_in=3600)
            elapsed = (time.perf_counter() - start) * 1000
            times.append(elapsed)
        avg = sum(times) / len(times)
        assert avg < 1, f"TokenResponse avg {avg:.4f}ms exceeded 1ms"


class TestChatSchemaBenchmark:
    def test_chat_request_creation(self):
        times = []
        for _ in range(1000):
            start = time.perf_counter()
            m = ChatRequest(message="Hello, how are you?", session_id="s1")
            elapsed = (time.perf_counter() - start) * 1000
            times.append(elapsed)
        avg = sum(times) / len(times)
        assert avg < 1, f"ChatRequest avg {avg:.4f}ms exceeded 1ms"

    def test_chat_message_creation(self):
        times = []
        for _ in range(1000):
            start = time.perf_counter()
            m = ChatMessage(id="msg-1", role="user", content="Hello")
            elapsed = (time.perf_counter() - start) * 1000
            times.append(elapsed)
        avg = sum(times) / len(times)
        assert avg < 1, f"ChatMessage avg {avg:.4f}ms exceeded 1ms"

    def test_conversation_history_creation(self):
        msg = ChatMessage(id="msg-1", role="user", content="Hello")
        times = []
        for _ in range(1000):
            start = time.perf_counter()
            m = ConversationHistory(session_id="s1", messages=[msg])
            elapsed = (time.perf_counter() - start) * 1000
            times.append(elapsed)
        avg = sum(times) / len(times)
        assert avg < 1, f"ConversationHistory avg {avg:.4f}ms exceeded 1ms"

    def test_chat_response_creation(self):
        times = []
        for _ in range(1000):
            start = time.perf_counter()
            m = ChatResponse(success=True, output="Hello!", session_id="s1")
            elapsed = (time.perf_counter() - start) * 1000
            times.append(elapsed)
        avg = sum(times) / len(times)
        assert avg < 1, f"ChatResponse avg {avg:.4f}ms exceeded 1ms"


class TestMemorySchemaBenchmark:
    def test_memory_store_request_creation(self):
        times = []
        for _ in range(1000):
            start = time.perf_counter()
            m = MemoryStoreRequest(key="user_pref", value="dark_mode", memory_type="fact")
            elapsed = (time.perf_counter() - start) * 1000
            times.append(elapsed)
        avg = sum(times) / len(times)
        assert avg < 1, f"MemoryStoreRequest avg {avg:.4f}ms exceeded 1ms"

    def test_long_term_memory_entry_creation(self):
        times = []
        for _ in range(1000):
            start = time.perf_counter()
            m = LongTermMemoryEntry(key="pref", value="dark", importance=0.8)
            elapsed = (time.perf_counter() - start) * 1000
            times.append(elapsed)
        avg = sum(times) / len(times)
        assert avg < 1, f"LongTermMemoryEntry avg {avg:.4f}ms exceeded 1ms"

    def test_memory_summary_creation(self):
        times = []
        for _ in range(1000):
            start = time.perf_counter()
            m = MemorySummary(session_id="s1", message_count=10, long_term={}, agent_memories={})
            elapsed = (time.perf_counter() - start) * 1000
            times.append(elapsed)
        avg = sum(times) / len(times)
        assert avg < 1, f"MemorySummary avg {avg:.4f}ms exceeded 1ms"

    def test_memory_delete_result_creation(self):
        times = []
        for _ in range(1000):
            start = time.perf_counter()
            m = MemoryDeleteResult(deleted={"conversation": 5, "long_term": 2})
            elapsed = (time.perf_counter() - start) * 1000
            times.append(elapsed)
        avg = sum(times) / len(times)
        assert avg < 1, f"MemoryDeleteResult avg {avg:.4f}ms exceeded 1ms"

    def test_memory_operation_result_creation(self):
        times = []
        for _ in range(1000):
            start = time.perf_counter()
            m = MemoryOperationResult(success=True)
            elapsed = (time.perf_counter() - start) * 1000
            times.append(elapsed)
        avg = sum(times) / len(times)
        assert avg < 1, f"MemoryOperationResult avg {avg:.4f}ms exceeded 1ms"


class TestStatusSchemaBenchmark:
    def test_system_status_creation(self):
        times = []
        for _ in range(1000):
            start = time.perf_counter()
            m = SystemStatus(
                status="ok",
                uptime_seconds=3600.0,
                sessions_active=5,
                workflows_completed=100,
                workflows_failed=2,
                tools_count=25,
            )
            elapsed = (time.perf_counter() - start) * 1000
            times.append(elapsed)
        avg = sum(times) / len(times)
        assert avg < 1, f"SystemStatus avg {avg:.4f}ms exceeded 1ms"

    def test_session_info_creation(self):
        times = []
        for _ in range(1000):
            start = time.perf_counter()
            m = SessionInfo(session_id="s1", message_count=10)
            elapsed = (time.perf_counter() - start) * 1000
            times.append(elapsed)
        avg = sum(times) / len(times)
        assert avg < 1, f"SessionInfo avg {avg:.4f}ms exceeded 1ms"

    def test_session_list_creation(self):
        info = SessionInfo(session_id="s1", message_count=10)
        times = []
        for _ in range(1000):
            start = time.perf_counter()
            m = SessionList(sessions=[info])
            elapsed = (time.perf_counter() - start) * 1000
            times.append(elapsed)
        avg = sum(times) / len(times)
        assert avg < 1, f"SessionList avg {avg:.4f}ms exceeded 1ms"

    def test_workflow_status_response_creation(self):
        times = []
        for _ in range(1000):
            start = time.perf_counter()
            m = WorkflowStatusResponse(thread_id="t1", status="completed")
            elapsed = (time.perf_counter() - start) * 1000
            times.append(elapsed)
        avg = sum(times) / len(times)
        assert avg < 1, f"WorkflowStatusResponse avg {avg:.4f}ms exceeded 1ms"


class TestUserSchemaBenchmark:
    def test_user_create_creation(self):
        times = []
        for _ in range(1000):
            start = time.perf_counter()
            m = UserCreate(email="user@example.com", password="securepass123")
            elapsed = (time.perf_counter() - start) * 1000
            times.append(elapsed)
        avg = sum(times) / len(times)
        assert avg < 1, f"UserCreate avg {avg:.4f}ms exceeded 1ms"

    def test_user_update_creation(self):
        times = []
        for _ in range(1000):
            start = time.perf_counter()
            m = UserUpdate(full_name="Updated Name")
            elapsed = (time.perf_counter() - start) * 1000
            times.append(elapsed)
        avg = sum(times) / len(times)
        assert avg < 1, f"UserUpdate avg {avg:.4f}ms exceeded 1ms"

    def test_user_read_creation(self):
        from datetime import datetime, timezone

        now = datetime.now(timezone.utc)
        times = []
        for _ in range(1000):
            start = time.perf_counter()
            m = UserRead(
                id="user-1",
                email="user@example.com",
                full_name="Test User",
                is_active=True,
                is_superuser=False,
                created_at=now,
                last_login_at=now,
                avatar_url=None,
            )
            elapsed = (time.perf_counter() - start) * 1000
            times.append(elapsed)
        avg = sum(times) / len(times)
        assert avg < 1, f"UserRead avg {avg:.4f}ms exceeded 1ms"
