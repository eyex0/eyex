from __future__ import annotations

import logging
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

logger = logging.getLogger("pix.services.analytics")


@dataclass
class AnalyticsEvent:
    event_type: str
    org_id: str
    agent_name: str | None = None
    value: float | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    timestamp: str = ""


class CustomerAnalyticsService:
    """Tracks customer usage, problems, recommendations, actions, and business impact.

    All metrics are scoped per organization for data isolation.
    """

    def __init__(self) -> None:
        self._events: list[AnalyticsEvent] = []
        self._problems_detected: dict[str, int] = defaultdict(int)
        self._recommendations_generated: dict[str, int] = defaultdict(int)
        self._actions_taken: dict[str, int] = defaultdict(int)
        self._agent_usage: dict[str, dict[str, Any]] = defaultdict(lambda: {
            "runs": 0, "total_duration_ms": 0, "errors": 0, "tokens_used": 0,
        })
        self._daily_metrics: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))

    def _day_key(self) -> str:
        return datetime.now(UTC).strftime("%Y-%m-%d")

    def record_problem_detected(self, org_id: str, problem_type: str, severity: str = "medium") -> None:
        key = f"{org_id}:{problem_type}"
        self._problems_detected[key] += 1
        event = AnalyticsEvent(
            event_type="problem_detected",
            org_id=org_id,
            metadata={"problem_type": problem_type, "severity": severity},
            timestamp=datetime.now(UTC).isoformat(),
        )
        self._events.append(event)
        self._daily_metrics[self._day_key()]["problems_detected"] += 1
        logger.info("[Analytics] Problem detected: org=%s type=%s severity=%s", org_id, problem_type, severity)

    def record_recommendation(self, org_id: str, agent_name: str, recommendation_type: str) -> None:
        key = f"{org_id}:{recommendation_type}"
        self._recommendations_generated[key] += 1
        event = AnalyticsEvent(
            event_type="recommendation_generated",
            org_id=org_id,
            agent_name=agent_name,
            metadata={"recommendation_type": recommendation_type},
            timestamp=datetime.now(UTC).isoformat(),
        )
        self._events.append(event)
        self._daily_metrics[self._day_key()]["recommendations"] += 1

    def record_action_taken(self, org_id: str, action_type: str, estimated_impact: str = "low") -> None:
        key = f"{org_id}:{action_type}"
        self._actions_taken[key] += 1
        event = AnalyticsEvent(
            event_type="action_taken",
            org_id=org_id,
            metadata={"action_type": action_type, "estimated_impact": estimated_impact},
            timestamp=datetime.now(UTC).isoformat(),
        )
        self._events.append(event)
        self._daily_metrics[self._day_key()]["actions_taken"] += 1

    def record_agent_execution(
        self, org_id: str, agent_name: str, duration_ms: float,
        success: bool, tokens_used: int = 0,
    ) -> None:
        agent_data = self._agent_usage[agent_name]
        agent_data["runs"] += 1
        agent_data["total_duration_ms"] += duration_ms
        agent_data["tokens_used"] += tokens_used
        if not success:
            agent_data["errors"] += 1
        self._daily_metrics[self._day_key()]["agent_runs"] += 1
        self._daily_metrics[self._day_key()]["total_duration_ms"] += duration_ms

    def get_org_summary(self, org_id: str) -> dict[str, Any]:
        org_problems = {k.split(":", 1)[1]: v for k, v in self._problems_detected.items() if k.startswith(f"{org_id}:")}
        org_recommendations = {k.split(":", 1)[1]: v for k, v in self._recommendations_generated.items() if k.startswith(f"{org_id}:")}
        org_actions = {k.split(":", 1)[1]: v for k, v in self._actions_taken.items() if k.startswith(f"{org_id}:")}

        total_problems = sum(org_problems.values())
        total_recommendations = sum(org_recommendations.values())
        total_actions = sum(org_actions.values())

        estimated_time_saved_minutes = total_recommendations * 45
        estimated_impact_score = min(100, (total_actions / max(total_recommendations, 1)) * 100)

        return {
            "org_id": org_id,
            "period": "all_time",
            "problems_detected": {
                "total": total_problems,
                "by_type": org_problems,
            },
            "recommendations_generated": {
                "total": total_recommendations,
                "by_type": org_recommendations,
            },
            "actions_taken": {
                "total": total_actions,
                "by_type": org_actions,
            },
            "estimated_time_saved_minutes": estimated_time_saved_minutes,
            "estimated_time_saved_hours": round(estimated_time_saved_minutes / 60, 1),
            "business_impact_score": estimated_impact_score,
            "recommendation_to_action_rate": round(
                total_actions / max(total_recommendations, 1) * 100, 1
            ),
        }

    def get_agent_analytics(self) -> list[dict[str, Any]]:
        return [
            {
                "agent": name,
                "runs": data["runs"],
                "avg_duration_ms": round(data["total_duration_ms"] / max(data["runs"], 1), 2),
                "total_duration_ms": round(data["total_duration_ms"], 2),
                "errors": data["errors"],
                "error_rate": round(data["errors"] / max(data["runs"], 1) * 100, 2),
                "tokens_used": data["tokens_used"],
            }
            for name, data in sorted(self._agent_usage.items())
        ]

    def get_daily_trend(self, days: int = 30) -> list[dict[str, Any]]:
        from datetime import timedelta
        today = datetime.now(UTC).date()
        trends = []
        for i in range(days):
            day = (today - timedelta(days=days - 1 - i)).isoformat()
            metrics = self._daily_metrics.get(day, {})
            trends.append({
                "date": day,
                "problems_detected": int(metrics.get("problems_detected", 0)),
                "recommendations": int(metrics.get("recommendations", 0)),
                "actions_taken": int(metrics.get("actions_taken", 0)),
                "agent_runs": int(metrics.get("agent_runs", 0)),
                "avg_duration_ms": round(
                    metrics.get("total_duration_ms", 0) / max(metrics.get("agent_runs", 0), 1), 2
                ),
            })
        return trends

    def get_dashboard(self, org_id: str) -> dict[str, Any]:
        summary = self.get_org_summary(org_id)
        return {
            **summary,
            "agents": self.get_agent_analytics(),
            "daily_trend": self.get_daily_trend(14),
            "recent_events": [
                {"type": e.event_type, "agent": e.agent_name, "org_id": e.org_id, "time": e.timestamp}
                for e in self._events[-20:]
            ],
        }


_analytics: CustomerAnalyticsService | None = None


def get_analytics_service() -> CustomerAnalyticsService:
    global _analytics
    if _analytics is None:
        _analytics = CustomerAnalyticsService()
    return _analytics
