"""
πX Production Security — RLS, encryption, API rate limits, audit compliance.

Row-Level Security (RLS) policies for PostgreSQL, field-level encryption,
API rate limiting per org, and audit compliance reporting.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any
import hashlib
import time
import uuid


@dataclass
class RateLimitConfig:
    """Per-org API rate limits."""
    org_id: str
    requests_per_minute: int = 100
    requests_per_hour: int = 5000
    ai_calls_per_hour: int = 200
    concurrent_agents: int = 5


@dataclass
class RateLimitState:
    org_id: str
    requests_this_minute: int = 0
    requests_this_hour: int = 0
    ai_calls_this_hour: int = 0
    active_agents: int = 0
    minute_window_start: float = field(default_factory=time.time)
    hour_window_start: float = field(default_factory=time.time)


@dataclass
class SecurityAuditReport:
    """Compliance-ready audit report."""
    org_id: str
    report_id: str
    total_events: int = 0
    access_violations: int = 0
    rate_limit_hits: int = 0
    security_events: list[dict] = field(default_factory=list)
    generated_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())


class ProductionSecurity:
    """Production security: RLS, encryption, rate limits, audit compliance."""

    # RLS policies as SQL (executed via migration in production)
    RLS_POLICIES: list[str] = [
        """ALTER TABLE agent_instances ENABLE ROW LEVEL SECURITY;""",
        """CREATE POLICY tenant_isolation_agents ON agent_instances
           USING (org_id = current_setting('app.current_org_id')::uuid);""",
        """ALTER TABLE agent_memory ENABLE ROW LEVEL SECURITY;""",
        """CREATE POLICY tenant_isolation_memory ON agent_memory
           USING (org_id = current_setting('app.current_org_id')::uuid);""",
        """ALTER TABLE ai_quality_assessments ENABLE ROW LEVEL SECURITY;""",
        """CREATE POLICY tenant_isolation_qa ON ai_quality_assessments
           USING (org_id = current_setting('app.current_org_id')::uuid);""",
        """ALTER TABLE agent_execution_history ENABLE ROW LEVEL SECURITY;""",
        """CREATE POLICY tenant_isolation_exec ON agent_execution_history
           USING (org_id = current_setting('app.current_org_id')::uuid);""",
        """ALTER TABLE ai_audit_trail ENABLE ROW LEVEL SECURITY;""",
        """CREATE POLICY tenant_isolation_audit ON ai_audit_trail
           USING (org_id = current_setting('app.current_org_id')::uuid);""",
        """ALTER TABLE persistent_agent_memory ENABLE ROW LEVEL SECURITY;""",
        """CREATE POLICY tenant_isolation_pmem ON persistent_agent_memory
           USING (org_id = current_setting('app.current_org_id')::uuid);""",
    ]

    # Fields that must be encrypted at rest
    ENCRYPTED_FIELDS: dict[str, list[str]] = {
        "agent_memory": ["content"],
        "persistent_agent_memory": ["context", "reasoning", "result", "feedback"],
        "ai_audit_trail": ["which_data", "why"],
    }

    def __init__(self) -> None:
        self._rate_limits: dict[str, RateLimitConfig] = {}
        self._rate_states: dict[str, RateLimitState] = {}
        self._security_events: list[dict] = []
        self._encryption_key = b"pix-production-key-32bytes!!!!!!!"[:32]  # In prod: from secrets manager

    def set_rate_limit(self, config: RateLimitConfig) -> None:
        self._rate_limits[config.org_id] = config
        if config.org_id not in self._rate_states:
            self._rate_states[config.org_id] = RateLimitState(org_id=config.org_id)

    def check_rate_limit(self, org_id: str, is_ai_call: bool = False) -> dict[str, Any]:
        """Check if request is within rate limits. Returns {allowed, reason}."""
        config = self._rate_limits.get(org_id)
        if not config:
            return {"allowed": True, "reason": "No limit configured"}

        state = self._rate_states.get(org_id, RateLimitState(org_id=org_id))
        now = time.time()

        # Reset windows
        if now - state.minute_window_start >= 60:
            state.requests_this_minute = 0
            state.minute_window_start = now
        if now - state.hour_window_start >= 3600:
            state.requests_this_hour = 0
            state.ai_calls_this_hour = 0
            state.hour_window_start = now

        state.requests_this_minute += 1
        state.requests_this_hour += 1
        if is_ai_call:
            state.ai_calls_this_hour += 1

        if state.requests_this_minute > config.requests_per_minute:
            self._record_security_event(org_id, "rate_limit_exceeded", "minute", "medium")
            return {"allowed": False, "reason": f"Rate limit: {config.requests_per_minute}/min exceeded"}

        if state.requests_this_hour > config.requests_per_hour:
            self._record_security_event(org_id, "rate_limit_exceeded", "hourly", "high")
            return {"allowed": False, "reason": f"Rate limit: {config.requests_per_hour}/hr exceeded"}

        if is_ai_call and state.ai_calls_this_hour > config.ai_calls_per_hour:
            self._record_security_event(org_id, "ai_call_limit_exceeded", "ai_hourly", "high")
            return {"allowed": False, "reason": f"AI call limit: {config.ai_calls_per_hour}/hr exceeded"}

        return {"allowed": True, "reason": "OK"}

    def encrypt_field(self, table: str, field_name: str, value: str) -> str:
        """Encrypt a sensitive field at rest (simulated with hash-based masking)."""
        if field_name not in self.ENCRYPTED_FIELDS.get(table, []):
            return value
        # In production: from cryptography.fernet import Fernet; f = Fernet(key); return f.encrypt(value.encode()).decode()
        masked = hashlib.sha256(self._encryption_key + value.encode()).hexdigest()[:len(value)]
        return f"ENC:{masked}"

    def decrypt_field(self, table: str, field_name: str, value: str) -> str:
        """Decrypt a sensitive field (simulated)."""
        if not value.startswith("ENC:"):
            return value
        # In production: return Fernet(key).decrypt(value[4:].encode()).decode()
        return value  # Simulation: return as-is (can't reverse a hash)

    def verify_rls(self, table_name: str, org_id: str, rows: list[dict]) -> dict[str, Any]:
        """Verify RLS is enforced: all rows must belong to the specified org."""
        violations = [r for r in rows if r.get("org_id") and r["org_id"] != org_id]
        return {
            "table": table_name,
            "org_id": org_id,
            "rows_checked": len(rows),
            "violations": len(violations),
            "rls_enforced": len(violations) == 0,
        }

    def _record_security_event(self, org_id: str, event_type: str, detail: str, severity: str) -> None:
        self._security_events.append({
            "id": f"sec_{uuid.uuid4().hex[:12]}",
            "org_id": org_id,
            "event_type": event_type,
            "detail": detail,
            "severity": severity,
            "timestamp": datetime.now(UTC).isoformat(),
        })

    def get_security_events(self, org_id: str | None = None, limit: int = 50) -> list[dict]:
        events = self._security_events
        if org_id:
            events = [e for e in events if e["org_id"] == org_id]
        return events[-limit:]

    def generate_audit_report(self, org_id: str, security_events: list[dict] | None = None) -> SecurityAuditReport:
        """Generate a compliance-ready audit report."""
        events = security_events or self.get_security_events(org_id)
        violations = [e for e in events if e.get("severity") in ("high", "critical")]
        rate_hits = [e for e in events if "rate_limit" in e.get("event_type", "")]
        return SecurityAuditReport(
            org_id=org_id,
            report_id=f"audit_{uuid.uuid4().hex[:12]}",
            total_events=len(events),
            access_violations=len(violations),
            rate_limit_hits=len(rate_hits),
            security_events=events[-20:],
        )

    def get_rls_sql(self) -> list[str]:
        """Return all RLS SQL statements for migration execution."""
        return self.RLS_POLICIES
