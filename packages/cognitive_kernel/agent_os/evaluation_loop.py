"""
πX Agent Evaluation Loop — Every action must be evaluated.

Flow: Agent Action → Outcome → Score → Learning Memory

Tracks: accuracy, confidence, business impact, human approval
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from .agent_memory import AgentMemory, MemoryType


@dataclass
class EvaluationRecord:
    agent_id: str
    action: str
    outcome: str
    accuracy: float = 0.0
    confidence: float = 0.0
    business_impact: float = 0.0
    human_approved: bool | None = None
    score: float = 0.0
    feedback: str = ""
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())

    def to_dict(self) -> dict:
        return {
            "agent_id": self.agent_id,
            "action": self.action,
            "outcome": self.outcome,
            "accuracy": self.accuracy,
            "confidence": self.confidence,
            "business_impact": self.business_impact,
            "human_approved": self.human_approved,
            "score": self.score,
            "feedback": self.feedback,
            "created_at": self.created_at,
        }


class AgentEvaluationLoop:
    """Evaluates agent actions and feeds back into learning memory."""

    def __init__(self, memory: AgentMemory | None = None) -> None:
        self.memory = memory or AgentMemory()
        self._records: list[EvaluationRecord] = []

    def evaluate(
        self,
        agent_id: str,
        org_id: str,
        action: str,
        outcome: str,
        accuracy: float = 0.0,
        confidence: float = 0.0,
        business_impact: float = 0.0,
        human_approved: bool | None = None,
        feedback: str = "",
    ) -> EvaluationRecord:
        """Evaluate an agent action and record it."""
        # Weighted score: accuracy (30%), confidence (20%), impact (30%), approval (20%)
        approval_score = 1.0 if human_approved is True else (0.5 if human_approved is None else 0.0)
        score = (
            accuracy * 0.30 +
            confidence * 0.20 +
            business_impact * 0.30 +
            approval_score * 0.20
        )

        record = EvaluationRecord(
            agent_id=agent_id,
            action=action,
            outcome=outcome,
            accuracy=accuracy,
            confidence=confidence,
            business_impact=business_impact,
            human_approved=human_approved,
            score=round(score, 4),
            feedback=feedback,
        )
        self._records.append(record)

        # Feed into experience memory
        self.memory.record_outcome(agent_id, org_id, action, outcome, score)

        return record

    def get_performance_trend(self, agent_id: str, limit: int = 50) -> dict[str, Any]:
        """Get performance metrics for an agent."""
        agent_records = [r for r in self._records if r.agent_id == agent_id][-limit:]
        if not agent_records:
            return {"agent_id": agent_id, "total_actions": 0, "avg_score": 0.0}

        scores = [r.score for r in agent_records]
        accuracies = [r.accuracy for r in agent_records]
        impacts = [r.business_impact for r in agent_records]
        approved = sum(1 for r in agent_records if r.human_approved is True)

        return {
            "agent_id": agent_id,
            "total_actions": len(agent_records),
            "avg_score": round(sum(scores) / len(scores), 4),
            "avg_accuracy": round(sum(accuracies) / len(accuracies), 4),
            "avg_impact": round(sum(impacts) / len(impacts), 4),
            "approval_rate": round(approved / len(agent_records), 4) if agent_records else 0.0,
            "trend": "improving" if scores[-1] > scores[0] else "stable" if scores[-1] == scores[0] else "declining",
        }

    def get_all_records(self, agent_id: str | None = None, limit: int = 100) -> list[dict]:
        records = self._records if agent_id is None else [r for r in self._records if r.agent_id == agent_id]
        return [r.to_dict() for r in records[-limit:]]
