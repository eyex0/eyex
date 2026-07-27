"""
πX Agent Scheduler — Proactive autonomous agents.

Agents don't just answer — they monitor. Scheduled tasks, event triggers,
KPI monitoring, anomaly detection, automatic investigations.

Example: Revenue drops 15% → Sales Agent investigates → Finance Agent validates
         → CEO Agent receives explanation.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any, Callable
import uuid


class TriggerType(StrEnum):
    SCHEDULED = "scheduled"          # cron-like interval
    KPI_THRESHOLD = "kpi_threshold"   # KPI crosses a threshold
    ANOMALY = "anomaly"              # data anomaly detected
    EVENT = "event"                  # external event
    DATA_UPDATED = "data_updated"    # new data ingested


class ScheduleStatus(StrEnum):
    ACTIVE = "active"
    PAUSED = "paused"
    TRIGGERED = "triggered"
    COMPLETED = "completed"


@dataclass
class AgentSchedule:
    id: str
    org_id: str
    agent_id: str
    trigger_type: TriggerType
    condition: dict[str, Any]  # e.g. {"kpi": "revenue", "threshold": -0.15, "comparison": "percent_change"}
    interval_seconds: int = 3600  # for scheduled type
    action: str = ""  # what the agent should do when triggered
    status: ScheduleStatus = ScheduleStatus.ACTIVE
    last_triggered: str = ""
    trigger_count: int = 0
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())


@dataclass
class InvestigationResult:
    agent_id: str
    trigger_reason: str
    findings: str
    confidence: float = 0.0
    recommendations: list[str] = field(default_factory=list)
    escalated_to: list[str] = field(default_factory=list)  # agent_ids for escalation
    timestamp: str = field(default_factory=lambda: datetime.now(UTC).isoformat())


class AgentScheduler:
    """Manages proactive agent monitoring and automatic investigations."""

    def __init__(self) -> None:
        self._schedules: dict[str, AgentSchedule] = {}
        self._investigations: list[InvestigationResult] = []
        self._kpi_values: dict[str, dict[str, float]] = {}  # org_id → {kpi_name → value}
        self._previous_kpi_values: dict[str, dict[str, float]] = {}

    def create_schedule(
        self,
        org_id: str,
        agent_id: str,
        trigger_type: TriggerType,
        condition: dict[str, Any],
        action: str = "",
        interval_seconds: int = 3600,
    ) -> AgentSchedule:
        schedule = AgentSchedule(
            id=f"sched_{uuid.uuid4().hex[:12]}",
            org_id=org_id,
            agent_id=agent_id,
            trigger_type=trigger_type,
            condition=condition,
            action=action,
            interval_seconds=interval_seconds,
        )
        self._schedules[schedule.id] = schedule
        return schedule

    def update_kpi(self, org_id: str, kpi_name: str, value: float) -> list[AgentSchedule]:
        """Update a KPI value and check for triggers."""
        if org_id not in self._kpi_values:
            self._kpi_values[org_id] = {}
            self._previous_kpi_values[org_id] = {}
        
        self._previous_kpi_values[org_id][kpi_name] = self._kpi_values[org_id].get(kpi_name, value)
        self._kpi_values[org_id][kpi_name] = value

        # Check KPI threshold triggers
        triggered: list[AgentSchedule] = []
        for sched in self._schedules.values():
            if sched.org_id != org_id or sched.status != ScheduleStatus.ACTIVE:
                continue
            if sched.trigger_type == TriggerType.KPI_THRESHOLD:
                if self._check_kpi_trigger(sched, org_id, kpi_name, value):
                    triggered.append(sched)
                    sched.last_triggered = datetime.now(UTC).isoformat()
                    sched.trigger_count += 1
                    sched.status = ScheduleStatus.TRIGGERED
        return triggered

    def _check_kpi_trigger(self, schedule: AgentSchedule, org_id: str, kpi_name: str, value: float) -> bool:
        cond = schedule.condition
        target_kpi = cond.get("kpi", "")
        if target_kpi.lower() != kpi_name.lower():
            return False

        threshold = cond.get("threshold", 0)
        comparison = cond.get("comparison", "absolute")

        if comparison == "percent_change":
            prev = self._previous_kpi_values.get(org_id, {}).get(kpi_name, value)
            if prev == 0:
                return False
            pct_change = (value - prev) / prev
            return pct_change <= threshold if threshold < 0 else pct_change >= threshold
        elif comparison == "absolute":
            return value <= threshold if threshold < 0 else value >= threshold
        elif comparison == "below":
            return value < threshold
        elif comparison == "above":
            return value > threshold
        return False

    def detect_anomaly(self, org_id: str, kpi_name: str, value: float, history: list[float] | None = None) -> bool:
        """Simple anomaly detection using z-score."""
        if not history or len(history) < 3:
            return False
        mean = sum(history) / len(history)
        variance = sum((x - mean) ** 2 for x in history) / len(history)
        std = variance ** 0.5
        if std == 0:
            return False
        z_score = abs(value - mean) / std
        return z_score > 2.0  # 2 standard deviations

    def trigger_investigation(
        self,
        org_id: str,
        agent_id: str,
        reason: str,
        escalation_agents: list[str] | None = None,
    ) -> InvestigationResult:
        """Trigger an automatic investigation by an agent."""
        result = InvestigationResult(
            agent_id=agent_id,
            trigger_reason=reason,
            findings=f"Automatic investigation triggered: {reason}",
            confidence=0.6,
            recommendations=[f"Investigate: {reason}", "Check related KPIs", "Review recent data changes"],
            escalated_to=escalation_agents or [],
        )
        self._investigations.append(result)
        return result

    def get_schedules(self, org_id: str | None = None, agent_id: str | None = None) -> list[AgentSchedule]:
        schedules = list(self._schedules.values())
        if org_id:
            schedules = [s for s in schedules if s.org_id == org_id]
        if agent_id:
            schedules = [s for s in schedules if s.agent_id == agent_id]
        return schedules

    def pause_schedule(self, schedule_id: str) -> bool:
        sched = self._schedules.get(schedule_id)
        if sched:
            sched.status = ScheduleStatus.PAUSED
            return True
        return False

    def resume_schedule(self, schedule_id: str) -> bool:
        sched = self._schedules.get(schedule_id)
        if sched:
            sched.status = ScheduleStatus.ACTIVE
            return True
        return False

    def get_investigations(self, org_id: str | None = None, limit: int = 50) -> list[dict]:
        invs = self._investigations
        return [
            {
                "agent_id": i.agent_id,
                "trigger_reason": i.trigger_reason,
                "findings": i.findings,
                "confidence": i.confidence,
                "recommendations": i.recommendations,
                "escalated_to": i.escalated_to,
                "timestamp": i.timestamp,
            }
            for i in invs[-limit:]
        ]

    def get_kpi_values(self, org_id: str) -> dict[str, float]:
        return self._kpi_values.get(org_id, {})
