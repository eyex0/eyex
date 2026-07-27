"""
πX AI Audit Trail — Every AI action must record: who, when, which data,
which model, which agent, why.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any
import uuid


@dataclass
class AuditEntry:
    id: str
    org_id: str
    who: str        # user_id or agent_id
    when: str       # ISO timestamp
    which_data: str  # data accessed
    which_model: str  # LLM model used
    which_agent: str   # agent name
    why: str         # reason for the action
    action: str      # what was done
    result: str      # outcome
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "id": self.id, "org_id": self.org_id,
            "who": self.who, "when": self.when,
            "which_data": self.which_data, "which_model": self.which_model,
            "which_agent": self.which_agent, "why": self.why,
            "action": self.action, "result": self.result,
            "metadata": self.metadata,
        }


class AuditTrail:
    """Immutable audit trail for every AI action."""

    def __init__(self) -> None:
        self._entries: list[AuditEntry] = []

    def record(
        self,
        org_id: str,
        who: str,
        which_data: str,
        which_model: str,
        which_agent: str,
        why: str,
        action: str,
        result: str,
        metadata: dict | None = None,
    ) -> AuditEntry:
        entry = AuditEntry(
            id=f"audit_{uuid.uuid4().hex[:12]}",
            org_id=org_id,
            who=who,
            when=datetime.now(UTC).isoformat(),
            which_data=which_data,
            which_model=which_model,
            which_agent=which_agent,
            why=why,
            action=action,
            result=result,
            metadata=metadata or {},
        )
        self._entries.append(entry)
        return entry

    def get_entries(
        self,
        org_id: str | None = None,
        agent_id: str | None = None,
        limit: int = 100,
    ) -> list[dict]:
        results = self._entries
        if org_id:
            results = [e for e in results if e.org_id == org_id]
        if agent_id:
            results = [e for e in results if e.who == agent_id]
        return [e.to_dict() for e in results[-limit:]]

    def get_count(self, org_id: str | None = None) -> int:
        if org_id:
            return sum(1 for e in self._entries if e.org_id == org_id)
        return len(self._entries)
