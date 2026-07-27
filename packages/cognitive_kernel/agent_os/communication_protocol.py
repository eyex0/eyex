"""
πX Agent Communication Protocol — Agent-to-agent messaging and shared reasoning.

Supports: agent→agent messages, shared reasoning context, conflict resolution, consensus decisions.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any
import uuid


class MessageType(StrEnum):
    QUERY = "query"
    RESPONSE = "response"
    EVIDENCE = "evidence"
    DISAGREEMENT = "disagreement"
    CONSENSUS = "consensus"
    BROADCAST = "broadcast"


@dataclass
class AgentMessage:
    id: str
    from_agent_id: str
    to_agent_id: str  # "supervisor" for broadcast
    org_id: str
    message_type: MessageType
    content: str
    metadata: dict[str, Any] = field(default_factory=dict)
    confidence: float = 0.5
    timestamp: str = field(default_factory=lambda: datetime.now(UTC).isoformat())

    def to_dict(self) -> dict:
        return {
            "id": self.id, "from_agent_id": self.from_agent_id, "to_agent_id": self.to_agent_id,
            "org_id": self.org_id, "message_type": self.message_type.value,
            "content": self.content, "metadata": self.metadata,
            "confidence": self.confidence, "timestamp": self.timestamp,
        }


@dataclass
class SharedReasoningContext:
    """Shared context that all agents in an orchestration can read/write."""
    org_id: str
    query: str
    evidence: list[dict[str, Any]] = field(default_factory=list)
    analyses: dict[str, str] = field(default_factory=dict)  # agent_id → analysis
    disagreements: list[dict[str, Any]] = field(default_factory=list)
    consensus: str = ""
    final_decision: str = ""


class AgentCommunicationProtocol:
    """Manages agent-to-agent communication and shared reasoning."""

    def __init__(self) -> None:
        self._messages: list[AgentMessage] = []
        self._contexts: dict[str, SharedReasoningContext] = {}  # session_id → context

    def create_session(self, org_id: str, query: str) -> str:
        session_id = f"session_{uuid.uuid4().hex[:12]}"
        self._contexts[session_id] = SharedReasoningContext(org_id=org_id, query=query)
        return session_id

    def send(
        self,
        from_agent_id: str,
        to_agent_id: str,
        org_id: str,
        message_type: MessageType,
        content: str,
        confidence: float = 0.5,
        metadata: dict | None = None,
    ) -> AgentMessage:
        msg = AgentMessage(
            id=f"msg_{uuid.uuid4().hex[:12]}",
            from_agent_id=from_agent_id,
            to_agent_id=to_agent_id,
            org_id=org_id,
            message_type=message_type,
            content=content,
            confidence=confidence,
            metadata=metadata or {},
        )
        self._messages.append(msg)
        return msg

    def broadcast(
        self,
        from_agent_id: str,
        org_id: str,
        content: str,
        confidence: float = 0.5,
    ) -> AgentMessage:
        return self.send(from_agent_id, "supervisor", org_id, MessageType.BROADCAST, content, confidence)

    def get_messages(
        self,
        agent_id: str | None = None,
        org_id: str | None = None,
        limit: int = 50,
    ) -> list[AgentMessage]:
        msgs = self._messages
        if agent_id:
            msgs = [m for m in msgs if m.from_agent_id == agent_id or m.to_agent_id == agent_id]
        if org_id:
            msgs = [m for m in msgs if m.org_id == org_id]
        return msgs[-limit:]

    def add_evidence(self, session_id: str, agent_id: str, evidence: str, confidence: float = 0.7) -> None:
        ctx = self._contexts.get(session_id)
        if ctx:
            ctx.evidence.append({"agent_id": agent_id, "evidence": evidence, "confidence": confidence})

    def add_analysis(self, session_id: str, agent_id: str, analysis: str) -> None:
        ctx = self._contexts.get(session_id)
        if ctx:
            ctx.analyses[agent_id] = analysis

    def register_disagreement(self, session_id: str, agent_id: str, disagreement: str, position: str = "") -> None:
        ctx = self._contexts.get(session_id)
        if ctx:
            ctx.disagreements.append({"agent_id": agent_id, "disagreement": disagreement, "position": position})

    def resolve_conflicts(self, session_id: str) -> str:
        """Resolve disagreements by majority consensus."""
        ctx = self._contexts.get(session_id)
        if not ctx or not ctx.disagreements:
            return "No conflicts to resolve"
        
        # Simple majority: if >50% of analyses agree, that's consensus
        if len(ctx.analyses) > len(ctx.disagreements):
            ctx.consensus = "Majority consensus reached"
        else:
            ctx.consensus = "Conflict unresolved — escalated to human review"
        return ctx.consensus

    def get_context(self, session_id: str) -> SharedReasoningContext | None:
        return self._contexts.get(session_id)

    def finalize_decision(self, session_id: str, decision: str) -> None:
        ctx = self._contexts.get(session_id)
        if ctx:
            ctx.final_decision = decision
            ctx.consensus = self.resolve_conflicts(session_id)
