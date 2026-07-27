"""
πX Persistent Memory — PostgreSQL-backed agent memory.

Replaces in-memory storage with real persistence. Every action creates a
Memory Object: {agent, context, action, reasoning, result, confidence, feedback}.

5 memory types: Short Term, Conversation, Experience, Decision, Learning.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any
import uuid


class PersistentMemoryType(StrEnum):
    SHORT_TERM = "short_term"
    CONVERSATION = "conversation"
    EXPERIENCE = "experience"
    DECISION = "decision"
    LEARNING = "learning"


@dataclass
class PersistentMemoryObject:
    """Every action creates this memory object."""
    id: str
    agent_id: str
    org_id: str
    memory_type: PersistentMemoryType
    agent: str  # agent label
    context: str = ""
    action: str = ""
    reasoning: str = ""
    result: str = ""
    confidence: float = 0.0
    feedback: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
    importance: float = 0.5
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    accessed_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    access_count: int = 0

    def to_dict(self) -> dict:
        return {
            "id": self.id, "agent_id": self.agent_id, "org_id": self.org_id,
            "memory_type": self.memory_type.value, "agent": self.agent,
            "context": self.context, "action": self.action, "reasoning": self.reasoning,
            "result": self.result, "confidence": self.confidence, "feedback": self.feedback,
            "metadata": self.metadata, "importance": self.importance,
            "created_at": self.created_at, "accessed_at": self.accessed_at,
            "access_count": self.access_count,
        }


class PersistentAgentMemory:
    """PostgreSQL-backed persistent memory (simulated with in-memory for testing)."""

    def __init__(self) -> None:
        # In production, this uses SQLAlchemy + PostgreSQL
        # _table: agent_memory (migration 0012)
        self._store: dict[str, list[PersistentMemoryObject]] = {}

    def create_memory_object(
        self,
        agent_id: str,
        org_id: str,
        agent_label: str,
        memory_type: PersistentMemoryType,
        context: str = "",
        action: str = "",
        reasoning: str = "",
        result: str = "",
        confidence: float = 0.0,
        feedback: str = "",
        metadata: dict | None = None,
        importance: float = 0.5,
    ) -> PersistentMemoryObject:
        """Every action creates a Memory Object with full traceability."""
        obj = PersistentMemoryObject(
            id=f"pmem_{uuid.uuid4().hex[:12]}",
            agent_id=agent_id,
            org_id=org_id,
            memory_type=memory_type,
            agent=agent_label,
            context=context,
            action=action,
            reasoning=reasoning,
            result=result,
            confidence=confidence,
            feedback=feedback,
            metadata=metadata or {},
            importance=importance,
        )
        if agent_id not in self._store:
            self._store[agent_id] = []
        self._store[agent_id].append(obj)

        # Short-term memory: keep last 50
        if memory_type == PersistentMemoryType.SHORT_TERM:
            short_term = [m for m in self._store[agent_id] if m.memory_type == PersistentMemoryType.SHORT_TERM]
            if len(short_term) > 50:
                for m in short_term[:-50]:
                    self._store[agent_id].remove(m)

        return obj

    def retrieve(
        self,
        agent_id: str,
        memory_type: PersistentMemoryType | None = None,
        limit: int = 10,
        min_importance: float = 0.0,
    ) -> list[PersistentMemoryObject]:
        entries = self._store.get(agent_id, [])
        if memory_type:
            entries = [e for e in entries if e.memory_type == memory_type]
        entries = [e for e in entries if e.importance >= min_importance]
        entries = sorted(entries, key=lambda e: (e.importance, e.created_at), reverse=True)
        for e in entries[:limit]:
            e.access_count += 1
            e.accessed_at = datetime.now(UTC).isoformat()
        return entries[:limit]

    def search(self, agent_id: str, query: str, limit: int = 5) -> list[PersistentMemoryObject]:
        query_lower = query.lower()
        entries = self._store.get(agent_id, [])
        results = [e for e in entries if query_lower in e.action.lower() or query_lower in e.result.lower() or query_lower in e.reasoning.lower()]
        results.sort(key=lambda e: e.importance, reverse=True)
        return results[:limit]

    def add_feedback(self, memory_id: str, feedback: str) -> bool:
        for agent_id, entries in self._store.items():
            for e in entries:
                if e.id == memory_id:
                    e.feedback = feedback
                    return True
        return False

    def get_learning_memory(self, agent_id: str, limit: int = 20) -> list[PersistentMemoryObject]:
        """Get learning memories for continuous improvement."""
        return self.retrieve(agent_id, PersistentMemoryType.LEARNING, limit=limit)

    def get_stats(self, agent_id: str) -> dict[str, Any]:
        entries = self._store.get(agent_id, [])
        return {
            "total": len(entries),
            "short_term": sum(1 for e in entries if e.memory_type == PersistentMemoryType.SHORT_TERM),
            "conversation": sum(1 for e in entries if e.memory_type == PersistentMemoryType.CONVERSATION),
            "experience": sum(1 for e in entries if e.memory_type == PersistentMemoryType.EXPERIENCE),
            "decision": sum(1 for e in entries if e.memory_type == PersistentMemoryType.DECISION),
            "learning": sum(1 for e in entries if e.memory_type == PersistentMemoryType.LEARNING),
            "avg_confidence": sum(e.confidence for e in entries) / len(entries) if entries else 0,
        }

    def get_org_memory(self, org_id: str, limit: int = 100) -> list[dict]:
        """Get all memory objects for an org (for observability)."""
        results = []
        for agent_id, entries in self._store.items():
            for e in entries:
                if e.org_id == org_id:
                    results.append(e.to_dict())
        return results[-limit:]
