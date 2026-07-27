from __future__ import annotations

import logging
import time
from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

logger = logging.getLogger("pix.services.learning")


@dataclass
class FeedbackEntry:
    session_id: str
    agent_name: str
    rating: int  # 1-5
    feedback_text: str = ""
    recommendation_id: str = ""
    org_id: str = "default"
    timestamp: str = ""


@dataclass
class RecommendationOutcome:
    recommendation_id: str
    recommendation_text: str
    agent_name: str
    action_taken: bool = False
    outcome_successful: bool | None = None
    business_impact: str = ""
    org_id: str = "default"
    created_at: str = ""
    resolved_at: str = ""


class LearningSystem:
    """Continuous learning system that improves agent performance over time.

    Tracks recommendations, collects feedback, measures outcomes,
    and uses this data to improve future agent responses.
    """

    def __init__(self) -> None:
        self._feedback: list[FeedbackEntry] = []
        self._outcomes: list[RecommendationOutcome] = []
        self._agent_performance: dict[str, dict[str, float]] = defaultdict(lambda: {
            "total_recommendations": 0, "successful_outcomes": 0,
            "failed_outcomes": 0, "avg_rating": 0.0, "rating_count": 0,
            "total_response_time_ms": 0, "response_count": 0,
        })
        self._successful_patterns: dict[str, int] = defaultdict(int)
        self._failed_patterns: dict[str, int] = defaultdict(int)

    def record_feedback(
        self, session_id: str, agent_name: str, rating: int,
        feedback_text: str = "", recommendation_id: str = "",
        org_id: str = "default",
    ) -> FeedbackEntry:
        rating = max(1, min(5, rating))
        entry = FeedbackEntry(
            session_id=session_id, agent_name=agent_name,
            rating=rating, feedback_text=feedback_text,
            recommendation_id=recommendation_id, org_id=org_id,
            timestamp=datetime.now(UTC).isoformat(),
        )
        self._feedback.append(entry)
        perf = self._agent_performance[agent_name]
        perf["rating_count"] += 1
        perf["avg_rating"] = (
            (perf["avg_rating"] * (perf["rating_count"] - 1) + rating)
            / perf["rating_count"]
        )
        logger.info("Feedback recorded: agent=%s rating=%d/5 org=%s", agent_name, rating, org_id)
        return entry

    def record_recommendation_outcome(
        self, recommendation_text: str, agent_name: str,
        action_taken: bool = False, outcome_successful: bool | None = None,
        business_impact: str = "", org_id: str = "default",
    ) -> RecommendationOutcome:
        outcome = RecommendationOutcome(
            recommendation_id=f"rec_{int(time.time())}_{len(self._outcomes)}",
            recommendation_text=recommendation_text,
            agent_name=agent_name,
            action_taken=action_taken,
            outcome_successful=outcome_successful,
            business_impact=business_impact,
            org_id=org_id,
            created_at=datetime.now(UTC).isoformat(),
            resolved_at=datetime.now(UTC).isoformat() if outcome_successful is not None else "",
        )
        self._outcomes.append(outcome)
        perf = self._agent_performance[agent_name]
        perf["total_recommendations"] += 1
        if outcome_successful is True:
            perf["successful_outcomes"] += 1
        elif outcome_successful is False:
            perf["failed_outcomes"] += 1
        logger.info(
            "Outcome recorded: agent=%s action=%s success=%s",
            agent_name, action_taken, outcome_successful,
        )
        return outcome

    def record_agent_response_time(self, agent_name: str, duration_ms: float) -> None:
        perf = self._agent_performance[agent_name]
        perf["response_count"] += 1
        perf["total_response_time_ms"] += duration_ms

    def track_pattern_success(self, pattern_name: str, success: bool) -> None:
        if success:
            self._successful_patterns[pattern_name] += 1
        else:
            self._failed_patterns[pattern_name] += 1

    def get_agent_learning_summary(self, agent_name: str) -> dict[str, Any]:
        perf = self._agent_performance.get(agent_name, {})
        return {
            "agent": agent_name,
            "total_recommendations": perf.get("total_recommendations", 0),
            "successful_outcomes": perf.get("successful_outcomes", 0),
            "failed_outcomes": perf.get("failed_outcomes", 0),
            "success_rate": round(
                perf.get("successful_outcomes", 0) / max(perf.get("total_recommendations", 0), 1) * 100, 1
            ),
            "avg_rating": round(perf.get("avg_rating", 0.0), 2),
            "rating_count": perf.get("rating_count", 0),
            "avg_response_time_ms": round(
                perf.get("total_response_time_ms", 0) / max(perf.get("response_count", 0), 1), 2
            ),
            "improvement_since_last_week": self._calculate_improvement(agent_name),
        }

    def get_org_learning_summary(self, org_id: str) -> dict[str, Any]:
        org_feedback = [f for f in self._feedback if f.org_id == org_id]
        org_outcomes = [o for o in self._outcomes if o.org_id == org_id]
        agent_summaries = {}
        for entry in org_feedback:
            if entry.agent_name not in agent_summaries:
                agent_summaries[entry.agent_name] = self.get_agent_learning_summary(entry.agent_name)
        return {
            "org_id": org_id,
            "total_feedback": len(org_feedback),
            "avg_rating": round(
                sum(f.rating for f in org_feedback) / max(len(org_feedback), 1), 2
            ),
            "total_recommendations": len(org_outcomes),
            "success_rate": round(
                sum(1 for o in org_outcomes if o.outcome_successful is True) / max(len(org_outcomes), 1) * 100, 1
            ),
            "agents": list(agent_summaries.values()),
            "top_patterns": dict(sorted(
                self._successful_patterns.items(), key=lambda x: x[1], reverse=True
            )[:10]),
        }

    def get_improvement_signals(self, agent_name: str) -> list[str]:
        signals: list[str] = []
        perf = self._agent_performance.get(agent_name, {})
        if perf.get("failed_outcomes", 0) > perf.get("successful_outcomes", 0):
            signals.append(f"{agent_name} has more failures than successes — review output quality")
        if perf.get("avg_rating", 5.0) < 3.0:
            signals.append(f"{agent_name} average rating ({perf['avg_rating']:.1f}) below threshold — needs prompt improvement")
        if perf.get("total_recommendations", 0) > 10 and perf.get("success_rate", 1.0) < 0.5:
            signals.append(f"{agent_name} success rate below 50% — consider revising decision framework")
        return signals

    def _calculate_improvement(self, agent_name: str) -> str:
        recent_outcomes = [
            o for o in self._outcomes
            if o.agent_name == agent_name
        ]
        if len(recent_outcomes) < 5:
            return "insufficient_data"
        recent_successes = sum(1 for o in recent_outcomes[-5:] if o.outcome_successful is True)
        if recent_successes >= 4:
            return "improving"
        elif recent_successes >= 3:
            return "stable"
        return "declining"


_learning: LearningSystem | None = None


def get_learning_system() -> LearningSystem:
    global _learning
    if _learning is None:
        _learning = LearningSystem()
    return _learning
