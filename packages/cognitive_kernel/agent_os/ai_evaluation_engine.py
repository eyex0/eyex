"""
πX AI Evaluation Engine — Enterprise AI quality layer.

Evaluates: accuracy, confidence, hallucination risk, source quality,
user feedback, business outcome → AI Quality Score (0–100).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any
import uuid


class QualityFactor(StrEnum):
    ACCURACY = "accuracy"
    CONFIDENCE = "confidence"
    HALLUCINATION_RISK = "hallucination_risk"
    SOURCE_QUALITY = "source_quality"
    USER_FEEDBACK = "user_feedback"
    BUSINESS_OUTCOME = "business_outcome"


@dataclass
class QualityAssessment:
    id: str
    agent_id: str
    org_id: str
    query: str
    response: str
    factors: dict[str, float] = field(default_factory=dict)  # factor → 0.0-1.0
    quality_score: int = 0  # 0-100
    hallucination_flags: list[str] = field(default_factory=list)
    sources_cited: list[str] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    feedback: str = ""
    approved: bool | None = None

    def to_dict(self) -> dict:
        return {
            "id": self.id, "agent_id": self.agent_id, "org_id": self.org_id,
            "query": self.query, "response": self.response[:200],
            "factors": self.factors, "quality_score": self.quality_score,
            "hallucination_flags": self.hallucination_flags,
            "sources_cited": self.sources_cited,
            "created_at": self.created_at, "feedback": self.feedback,
            "approved": self.approved,
        }


class AIEvaluationEngine:
    """Evaluates every AI response with a 0-100 quality score."""

    # Factor weights (sum to 1.0)
    WEIGHTS: dict[QualityFactor, float] = {
        QualityFactor.ACCURACY: 0.25,
        QualityFactor.CONFIDENCE: 0.15,
        QualityFactor.HALLUCINATION_RISK: 0.20,
        QualityFactor.SOURCE_QUALITY: 0.15,
        QualityFactor.USER_FEEDBACK: 0.10,
        QualityFactor.BUSINESS_OUTCOME: 0.15,
    }

    def __init__(self) -> None:
        self._assessments: list[QualityAssessment] = []

    def evaluate(
        self,
        agent_id: str,
        org_id: str,
        query: str,
        response: str,
        accuracy: float = 0.5,
        confidence: float = 0.5,
        source_quality: float = 0.5,
        user_feedback: float = 0.5,
        business_outcome: float = 0.5,
        sources_cited: list[str] | None = None,
    ) -> QualityAssessment:
        """Evaluate an AI response and produce a 0-100 quality score."""
        # Detect hallucination risk
        hallucination_risk = self._assess_hallucination_risk(response, sources_cited or [])
        hallucination_flags = self._detect_hallucination_flags(response)

        factors = {
            QualityFactor.ACCURACY.value: accuracy,
            QualityFactor.CONFIDENCE.value: confidence,
            QualityFactor.HALLUCINATION_RISK.value: 1.0 - hallucination_risk,  # Inverted: lower risk = higher score
            QualityFactor.SOURCE_QUALITY.value: source_quality,
            QualityFactor.USER_FEEDBACK.value: user_feedback,
            QualityFactor.BUSINESS_OUTCOME.value: business_outcome,
        }

        # Weighted quality score (0-100)
        score = 0.0
        for factor, weight in self.WEIGHTS.items():
            score += factors[factor.value] * weight
        quality_score = int(score * 100)

        assessment = QualityAssessment(
            id=f"qa_{uuid.uuid4().hex[:12]}",
            agent_id=agent_id,
            org_id=org_id,
            query=query,
            response=response,
            factors=factors,
            quality_score=quality_score,
            hallucination_flags=hallucination_flags,
            sources_cited=sources_cited or [],
        )
        self._assessments.append(assessment)
        return assessment

    def _assess_hallucination_risk(self, response: str, sources: list[str]) -> float:
        """Assess hallucination risk (0.0 = no risk, 1.0 = high risk)."""
        risk = 0.0
        # No sources cited → higher risk
        if not sources:
            risk += 0.3
        # Very long responses without sources → higher risk
        if len(response) > 500 and not sources:
            risk += 0.2
        # Vague language → higher risk
        vague_terms = ["might be", "could possibly", "it seems", "perhaps", "likely"]
        vague_count = sum(1 for t in vague_terms if t in response.lower())
        risk += min(vague_count * 0.1, 0.3)
        # Specific numbers without sources → higher risk
        import re
        numbers = re.findall(r'\d+\.?\d*%?', response)
        if len(numbers) > 5 and not sources:
            risk += 0.2
        return min(risk, 1.0)

    def _detect_hallucination_flags(self, response: str) -> list[str]:
        """Detect specific hallucination indicators."""
        flags = []
        if "I believe" in response and "data" not in response.lower():
            flags.append("unsubstantiated_belief")
        if "definitely" in response.lower() or "certainly" in response.lower():
            if "data shows" not in response.lower():
                flags.append("overconfident_without_data")
        if len(response) > 1000:
            flags.append("excessive_length")
        return flags

    def add_feedback(self, assessment_id: str, feedback: str, approved: bool) -> bool:
        for a in self._assessments:
            if a.id == assessment_id:
                a.feedback = feedback
                a.approved = approved
                # Recalculate user_feedback factor
                a.factors[QualityFactor.USER_FEEDBACK.value] = 1.0 if approved else 0.0
                self._recalculate_score(a)
                return True
        return False

    def _recalculate_score(self, assessment: QualityAssessment) -> None:
        score = 0.0
        for factor, weight in self.WEIGHTS.items():
            score += assessment.factors[factor.value] * weight
        assessment.quality_score = int(score * 100)

    def get_assessments(self, agent_id: str | None = None, org_id: str | None = None, limit: int = 50) -> list[dict]:
        results = self._assessments
        if agent_id:
            results = [a for a in results if a.agent_id == agent_id]
        if org_id:
            results = [a for a in results if a.org_id == org_id]
        return [a.to_dict() for a in results[-limit:]]

    def get_quality_stats(self, agent_id: str | None = None) -> dict[str, Any]:
        results = [a for a in self._assessments if not agent_id or a.agent_id == agent_id]
        if not results:
            return {"total": 0, "avg_score": 0}
        scores = [a.quality_score for a in results]
        return {
            "total": len(results),
            "avg_score": sum(scores) // len(scores),
            "min_score": min(scores),
            "max_score": max(scores),
            "hallucination_rate": sum(1 for a in results if a.hallucination_flags) / len(results),
            "approval_rate": sum(1 for a in results if a.approved is True) / len(results),
        }
