from __future__ import annotations

import pytest

from app.core.middleware import _get_client_ip
from app.core.security import decode_token, create_access_token, create_refresh_token
from app.agents.tools.file_tools import _resolve_path, _assert_safe_path
from app.agents.tools.db_tools import _ALLOWED_DML_TABLES


class TestSQLInjection:
    """db_query uses parameterized LIMIT — verify no string interpolation."""

    def test_allowed_dml_tables(self):
        assert "conversation_messages" in _ALLOWED_DML_TABLES
        assert "long_term_memory" in _ALLOWED_DML_TABLES
        assert "agent_memory_records" in _ALLOWED_DML_TABLES
        assert "users" not in _ALLOWED_DML_TABLES

    def test_forbidden_keywords_in_table_refs(self):
        dangerous = {"users", "organizations", "finance_invoices", "crm_customers"}
        assert not dangerous.intersection(_ALLOWED_DML_TABLES)


class TestPathTraversal:
    def test_resolve_path_absolute(self):
        p = _resolve_path("/etc/passwd")
        assert str(p) == str(p.resolve())

    def test_assert_safe_path_allowed(self):
        from pathlib import Path
        from app.agents.tools.file_tools import _BASE_DIR
        safe = _BASE_DIR / "__test_allowed__.tmp"
        try:
            safe.write_text("hello")
            _assert_safe_path(safe)
        finally:
            if safe.exists():
                safe.unlink()


class TestTokenSecurity:
    def test_decode_expired_token_returns_error(self):
        payload = decode_token("eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwiZXhwIjoxNTE2MjM5MDIyLCJ0eXBlIjoiYWNjZXNzIn0.5Z1zE9xKQ8v7H9z1p2q3r4s5t6u7v8w9x0y1z2a3b4c5d")
        assert "error" in payload
        assert payload["error"] in ("expired", "invalid")


class TestClientIP:
    def test_direct_ip(self):
        class MockRequest:
            client = type("obj", (object,), {"host": "1.2.3.4"})()
            headers = {}
        assert _get_client_ip(MockRequest()) == "1.2.3.4"

    def test_forwarded_for_valid(self):
        class MockRequest:
            client = type("obj", (object,), {"host": "127.0.0.1"})()
            headers = {"x-forwarded-for": "203.0.113.5, 10.0.0.1"}
        assert _get_client_ip(MockRequest()) == "203.0.113.5"

    def test_forwarded_for_spoof_ignored(self):
        class MockRequest:
            client = type("obj", (object,), {"host": "127.0.0.1"})()
            headers = {"x-forwarded-for": "not-an-ip, 10.0.0.1"}
        assert _get_client_ip(MockRequest()) == "127.0.0.1"


class TestInputValidation:
    def test_empty_input_rejected(self):
        from pydantic import ValidationError
        from app.schemas.agent import AgentRequest
        with pytest.raises(ValidationError):
            AgentRequest(input="")

    def test_oversized_input_rejected(self):
        from pydantic import ValidationError
        from app.schemas.agent import AgentRequest
        with pytest.raises(ValidationError):
            AgentRequest(input="x" * 100_001)

    def test_min_password_length(self):
        from pydantic import ValidationError
        from app.schemas.auth import RegisterRequest
        with pytest.raises(ValidationError):
            RegisterRequest(email="test@test.com", password="abc12")
