"""
πX Intelligence Observatory — Enterprise observability for all AI operations.

Tracks: AI cost, token usage, latency, model performance, agent performance,
decision accuracy, errors, security events.

Dashboards: CEO View, CTO View, CFO View, CISO View.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any
import uuid


class MetricType(StrEnum):
    AI_COST = "ai_cost"
    TOKEN_USAGE = "token_usage"
    LATENCY = "latency"
    MODEL_PERFORMANCE = "model_performance"
    AGENT_PERFORMANCE = "agent_performance"
    DECISION_ACCURACY = "decision_accuracy"
    ERRORS = "errors"
    SECURITY_EVENTS = "security_events"


@dataclass
class ObservabilityMetric:
    id: str
    org_id: str
    metric_type: MetricType
    value: float
    unit: str = ""
    agent_id: str = ""
    model: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now(UTC).isoformat())


@dataclass
class SecurityEvent:
    id: str
    org_id: str
    event_type: str  # "access_denied", "permission_violation", "data_breach_attempt"
    agent_id: str
    description: str
    severity: str = "low"  # low, medium, high, critical
    timestamp: str = field(default_factory=lambda: datetime.now(UTC).isoformat())


class IntelligenceObservatory:
    """Enterprise observability for all AI operations."""

    def __init__(self) -> None:
        self._metrics: list[ObservabilityMetric] = []
        self._security_events: list[SecurityEvent] = []

    def record_metric(
        self,
        org_id: str,
        metric_type: MetricType,
        value: float,
        unit: str = "",
        agent_id: str = "",
        model: str = "",
        metadata: dict | None = None,
    ) -> ObservabilityMetric:
        metric = ObservabilityMetric(
            id=f"metric_{uuid.uuid4().hex[:12]}",
            org_id=org_id,
            metric_type=metric_type,
            value=value,
            unit=unit,
            agent_id=agent_id,
            model=model,
            metadata=metadata or {},
        )
        self._metrics.append(metric)
        return metric

    def record_security_event(
        self,
        org_id: str,
        event_type: str,
        agent_id: str,
        description: str,
        severity: str = "low",
    ) -> SecurityEvent:
        event = SecurityEvent(
            id=f"sec_{uuid.uuid4().hex[:12]}",
            org_id=org_id,
            event_type=event_type,
            agent_id=agent_id,
            description=description,
            severity=severity,
        )
        self._security_events.append(event)
        return event

    def get_dashboard(self, org_id: str, view: str = "ceo") -> dict[str, Any]:
        """Get observability dashboard for a specific role view."""
        org_metrics = [m for m in self._metrics if m.org_id == org_id]
        org_security = [s for s in self._security_events if s.org_id == org_id]

        if view == "ceo":
            return self._ceo_view(org_id, org_metrics, org_security)
        elif view == "cto":
            return self._cto_view(org_id, org_metrics, org_security)
        elif view == "cfo":
            return self._cfo_view(org_id, org_metrics, org_security)
        elif view == "ciso":
            return self._ciso_view(org_id, org_metrics, org_security)
        return {}

    def _ceo_view(self, org_id: str, metrics: list, security: list) -> dict:
        ai_costs = [m for m in metrics if m.metric_type == MetricType.AI_COST]
        agent_perfs = [m for m in metrics if m.metric_type == MetricType.AGENT_PERFORMANCE]
        decision_accs = [m for m in metrics if m.metric_type == MetricType.DECISION_ACCURACY]
        return {
            "view": "ceo",
            "org_id": org_id,
            "total_ai_cost": sum(m.value for m in ai_costs),
            "agent_count": len(set(m.agent_id for m in agent_perfs if m.agent_id)),
            "avg_agent_performance": sum(m.value for m in agent_perfs) / len(agent_perfs) if agent_perfs else 0,
            "decision_accuracy": sum(m.value for m in decision_accs) / len(decision_accs) if decision_accs else 0,
            "security_incidents": len([s for s in security if s.severity in ("high", "critical")]),
        }

    def _cto_view(self, org_id: str, metrics: list, security: list) -> dict:
        latencies = [m for m in metrics if m.metric_type == MetricType.LATENCY]
        model_perfs = [m for m in metrics if m.metric_type == MetricType.MODEL_PERFORMANCE]
        errors = [m for m in metrics if m.metric_type == MetricType.ERRORS]
        return {
            "view": "cto",
            "org_id": org_id,
            "avg_latency_ms": sum(m.value for m in latencies) / len(latencies) if latencies else 0,
            "total_errors": len(errors),
            "model_performance": {m.model: m.value for m in model_perfs},
            "total_calls": len([m for m in metrics if m.metric_type in (MetricType.TOKEN_USAGE,)]),
            "security_alerts": len(security),
        }

    def _cfo_view(self, org_id: str, metrics: list, security: list) -> dict:
        ai_costs = [m for m in metrics if m.metric_type == MetricType.AI_COST]
        token_usage = [m for m in metrics if m.metric_type == MetricType.TOKEN_USAGE]
        by_model: dict[str, float] = {}
        for m in ai_costs:
            by_model[m.model] = by_model.get(m.model, 0) + m.value
        return {
            "view": "cfo",
            "org_id": org_id,
            "total_ai_cost": sum(m.value for m in ai_costs),
            "total_tokens": sum(m.value for m in token_usage),
            "cost_by_model": by_model,
            "cost_per_call": sum(m.value for m in ai_costs) / len(ai_costs) if ai_costs else 0,
            "projected_monthly_cost": sum(m.value for m in ai_costs) * 30,  # rough projection
        }

    def _ciso_view(self, org_id: str, metrics: list, security: list) -> dict:
        return {
            "view": "ciso",
            "org_id": org_id,
            "total_security_events": len(security),
            "critical_events": len([s for s in security if s.severity == "critical"]),
            "high_events": len([s for s in security if s.severity == "high"]),
            "recent_events": [
                {"type": s.event_type, "agent_id": s.agent_id, "severity": s.severity, "description": s.description}
                for s in security[-10:]
            ],
        }

    def get_metrics(self, org_id: str | None = None, metric_type: str | None = None, limit: int = 100) -> list[dict]:
        results = self._metrics
        if org_id:
            results = [m for m in results if m.org_id == org_id]
        if metric_type:
            results = [m for m in results if m.metric_type.value == metric_type]
        return [
            {
                "id": m.id, "metric_type": m.metric_type.value, "value": m.value,
                "unit": m.unit, "agent_id": m.agent_id, "model": m.model,
                "timestamp": m.timestamp,
            }
            for m in results[-limit:]
        ]

    def get_security_events(self, org_id: str | None = None, limit: int = 50) -> list[dict]:
        results = self._security_events
        if org_id:
            results = [s for s in results if s.org_id == org_id]
        return [
            {
                "id": s.id, "event_type": s.event_type, "agent_id": s.agent_id,
                "description": s.description, "severity": s.severity, "timestamp": s.timestamp,
            }
            for s in results[-limit:]
        ]
