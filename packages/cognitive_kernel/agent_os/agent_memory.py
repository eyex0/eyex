"""
πX Agent Memory — Each agent has 4 memory types:

1. Short-term memory: Current conversation context
2. Long-term memory: Persistent knowledge across sessions
3. Experience memory: Past actions and their outcomes
4. Decision history: Track of decisions made and their results
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any
import uuid


class MemoryType(StrEnum):
    SHORT_TERM = "short_term"
    LONG_TERM = "long_term"
    EXPERIENCE = "experience"
    DECISION_HISTORY = "decision_history"


@dataclass
class MemoryEntry:
    id: str
    agent_id: str
    org_id: str
    memory_type: MemoryType
    content: str
    metadata: dict[str, Any] = field(default_factory=dict)
    importance: float = 0.5  # 0.0–1.0
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    accessed_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    access_count: int = 0

    def to_dict(self) -> dict:
        return {
            "id": self.id, "agent_id": self.agent_id, "org_id": self.org_id,
            "memory_type": self.memory_type.value, "content": self.content,
            "metadata": self.metadata, "importance": self.importance,
            "created_at": self.created_at, "accessed_at": self.accessed_at,
            "access_count": self.access_count,
        }


class AgentMemory:
    """4-layer memory system for each agent."""

    def __init__(self) -> None:
        # agent_id → list of MemoryEntry
        self._memories: dict[str, list[MemoryEntry]] = {}

    def store(
        self,
        agent_id: str,
        org_id: str,
        memory_type: MemoryType,
        content: str,
        metadata: dict | None = None,
        importance: float = 0.5,
    ) -> MemoryEntry:
        entry = MemoryEntry(
            id=f"mem_{uuid.uuid4().hex[:12]}",
            agent_id=agent_id,
            org_id=org_id,
            memory_type=memory_type,
            content=content,
            metadata=metadata or {},
            importance=importance,
        )
        if agent_id not in self._memories:
            self._memories[agent_id] = []
        self._memories[agent_id].append(entry)
        # Short-term memory keeps only last 20 entries
        if memory_type == MemoryType.SHORT_TERM:
            short_term = [m for m in self._memories[agent_id] if m.memory_type == MemoryType.SHORT_TERM]
            if len(short_term) > 20:
                # Remove oldest short-term memories
                for m in short_term[:-20]:
                    self._memories[agent_id].remove(m)
        return entry

    def retrieve(
        self,
        agent_id: str,
        memory_type: MemoryType | None = None,
        limit: int = 10,
        min_importance: float = 0.0,
    ) -> list[MemoryEntry]:
        entries = self._memories.get(agent_id, [])
        if memory_type:
            entries = [e for e in entries if e.memory_type == memory_type]
        entries = [e for e in entries if e.importance >= min_importance]
        entries = sorted(entries, key=lambda e: (e.importance, e.created_at), reverse=True)
        # Update access
        for e in entries[:limit]:
            e.access_count += 1
            e.accessed_at = datetime.now(UTC).isoformat()
        return entries[:limit]

    def search(self, agent_id: str, query: str, limit: int = 5) -> list[MemoryEntry]:
        """Simple text search across all memory types."""
        query_lower = query.lower()
        entries = self._memories.get(agent_id, [])
        results = [e for e in entries if query_lower in e.content.lower()]
        results.sort(key=lambda e: e.importance, reverse=True)
        return results[:limit]

    def get_context(self, agent_id: str) -> str:
        """Build a context string from short-term + relevant long-term memory."""
        short_term = self.retrieve(agent_id, MemoryType.SHORT_TERM, limit=10)
        long_term = self.retrieve(agent_id, MemoryType.LONG_TERM, limit=5, min_importance=0.7)
        experience = self.retrieve(agent_id, MemoryType.EXPERIENCE, limit=3, min_importance=0.6)

        parts = []
        if short_term:
            parts.append("=== Recent Context ===")
            for m in short_term:
                parts.append(m.content)
        if long_term:
            parts.append("\n=== Long-term Knowledge ===")
            for m in long_term:
                parts.append(m.content)
        if experience:
            parts.append("\n=== Past Experience ===")
            for m in experience:
                parts.append(m.content)
        return "\n".join(parts) if parts else ""

    def get_decision_history(self, agent_id: str, limit: int = 20) -> list[MemoryEntry]:
        return self.retrieve(agent_id, MemoryType.DECISION_HISTORY, limit=limit)

    def record_outcome(self, agent_id: str, org_id: str, action: str, outcome: str, score: float) -> None:
        """Record an experience for the evaluation loop."""
        self.store(
            agent_id=agent_id,
            org_id=org_id,
            memory_type=MemoryType.EXPERIENCE,
            content=f"Action: {action} → Outcome: {outcome} (Score: {score:.2f})",
            metadata={"action": action, "outcome": outcome, "score": score},
            importance=min(score, 1.0),
        )

    def get_stats(self, agent_id: str) -> dict[str, Any]:
        entries = self._memories.get(agent_id, [])
        return {
            "total": len(entries),
            "short_term": sum(1 for e in entries if e.memory_type == MemoryType.SHORT_TERM),
            "long_term": sum(1 for e in entries if e.memory_type == MemoryType.LONG_TERM),
            "experience": sum(1 for e in entries if e.memory_type == MemoryType.EXPERIENCE),
            "decisions": sum(1 for e in entries if e.memory_type == MemoryType.DECISION_HISTORY),
        }
