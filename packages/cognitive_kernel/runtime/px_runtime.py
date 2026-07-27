"""
πX Runtime — Background agent execution, scheduled tasks, event-driven processing.

The runtime is the engine that makes πX run continuously without human triggering.
It manages:
  - Background agent execution queues
  - Scheduled intelligence tasks (cron-like)
  - Event-driven processing (reacts to KPI changes, data updates, anomalies)
  - Retry handling with circuit breaker
  - Failure recovery and health monitoring
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from typing import Any, Callable
import asyncio
import uuid

from .retry_handler import RetryHandler, RetryConfig


class TaskPriority(StrEnum):
    CRITICAL = "critical"  # Anomaly investigations
    HIGH = "high"          # KPI threshold breaches
    NORMAL = "normal"      # Scheduled tasks
    LOW = "low"            # Background maintenance


class RuntimeTaskType(StrEnum):
    AGENT_EXECUTE = "agent_execute"
    SCHEDULED_CHECK = "scheduled_check"
    ANOMALY_INVESTIGATION = "anomaly_investigation"
    KPI_MONITOR = "kpi_monitor"
    DATA_UPDATE = "data_update"
    MEMORY_CLEANUP = "memory_cleanup"
    HEALTH_CHECK = "health_check"


@dataclass
class RuntimeTask:
    id: str
    task_type: RuntimeTaskType
    org_id: str
    agent_id: str
    payload: dict[str, Any] = field(default_factory=dict)
    priority: TaskPriority = TaskPriority.NORMAL
    state: str = "pending"
    attempts: list[dict] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    started_at: str = ""
    completed_at: str = ""
    error: str = ""
    result: Any = None

    def to_dict(self) -> dict:
        return {
            "id": self.id, "task_type": self.task_type.value, "org_id": self.org_id,
            "agent_id": self.agent_id, "priority": self.priority.value,
            "state": self.state, "attempts": self.attempts,
            "created_at": self.created_at, "started_at": self.started_at,
            "completed_at": self.completed_at, "error": self.error,
            "result": self.result,
        }


@dataclass
class ScheduledTask:
    id: str
    org_id: str
    agent_id: str
    task_type: RuntimeTaskType
    interval_seconds: int
    payload: dict[str, Any] = field(default_factory=dict)
    active: bool = True
    last_run: str = ""
    next_run: str = ""
    run_count: int = 0


class PXRuntime:
    """The continuous execution engine for πX."""

    def __init__(self, retry_config: RetryConfig | None = None) -> None:
        self._task_queue: list[RuntimeTask] = []
        self._schedules: dict[str, ScheduledTask] = {}
        self._completed: list[RuntimeTask] = []
        self._handlers: dict[RuntimeTaskType, Callable] = {}
        self._retry = RetryHandler(retry_config or RetryConfig())
        self._running = False
        self._health_status: dict[str, Any] = {
            "total_tasks": 0, "succeeded": 0, "failed": 0,
            "avg_duration_ms": 0, "uptime_seconds": 0,
        }
        self._started_at = datetime.now(UTC)

    def register_handler(self, task_type: RuntimeTaskType, handler: Callable) -> None:
        self._handlers[task_type] = handler

    def enqueue(
        self,
        task_type: RuntimeTaskType,
        org_id: str,
        agent_id: str,
        payload: dict | None = None,
        priority: TaskPriority = TaskPriority.NORMAL,
    ) -> RuntimeTask:
        """Enqueue a background task."""
        task = RuntimeTask(
            id=f"task_{uuid.uuid4().hex[:12]}",
            task_type=task_type,
            org_id=org_id,
            agent_id=agent_id,
            payload=payload or {},
            priority=priority,
        )
        # Insert by priority (critical first)
        priority_order = {
            TaskPriority.CRITICAL: 0, TaskPriority.HIGH: 1,
            TaskPriority.NORMAL: 2, TaskPriority.LOW: 3,
        }
        inserted = False
        for i, existing in enumerate(self._task_queue):
            if priority_order[task.priority] < priority_order[existing.priority]:
                self._task_queue.insert(i, task)
                inserted = True
                break
        if not inserted:
            self._task_queue.append(task)
        self._health_status["total_tasks"] += 1
        return task

    def schedule(
        self,
        org_id: str,
        agent_id: str,
        task_type: RuntimeTaskType,
        interval_seconds: int,
        payload: dict | None = None,
    ) -> ScheduledTask:
        """Schedule a recurring task."""
        next_run = datetime.now(UTC) + timedelta(seconds=interval_seconds)
        sched = ScheduledTask(
            id=f"sched_{uuid.uuid4().hex[:12]}",
            org_id=org_id,
            agent_id=agent_id,
            task_type=task_type,
            interval_seconds=interval_seconds,
            payload=payload or {},
            next_run=next_run.isoformat(),
        )
        self._schedules[sched.id] = sched
        return sched

    def pause_schedule(self, schedule_id: str) -> bool:
        sched = self._schedules.get(schedule_id)
        if sched:
            sched.active = False
            return True
        return False

    def resume_schedule(self, schedule_id: str) -> bool:
        sched = self._schedules.get(schedule_id)
        if sched:
            sched.active = True
            return True
        return False

    def remove_schedule(self, schedule_id: str) -> bool:
        return self._schedules.pop(schedule_id, None) is not None

    async def tick(self) -> list[RuntimeTask]:
        """Process one tick: check schedules, execute queued tasks."""
        # Check schedules and enqueue due tasks
        now = datetime.now(UTC)
        for sched in self._schedules.values():
            if not sched.active:
                continue
            if sched.next_run and now >= datetime.fromisoformat(sched.next_run):
                task = self.enqueue(
                    task_type=sched.task_type,
                    org_id=sched.org_id,
                    agent_id=sched.agent_id,
                    payload=sched.payload,
                    priority=TaskPriority.NORMAL,
                )
                sched.last_run = now.isoformat()
                sched.run_count += 1
                sched.next_run = (now + timedelta(seconds=sched.interval_seconds)).isoformat()

        # Execute queued tasks
        executed: list[RuntimeTask] = []
        while self._task_queue:
            task = self._task_queue.pop(0)
            result = await self._execute_task(task)
            executed.append(task)
        return executed

    async def _execute_task(self, task: RuntimeTask) -> Any:
        """Execute a single task with retry handling."""
        task.state = "running"
        task.started_at = datetime.now(UTC).isoformat()
        start = datetime.now(UTC)

        handler = self._handlers.get(task.task_type)
        if not handler:
            task.state = "failed"
            task.error = f"No handler for task type: {task.task_type.value}"
            self._completed.append(task)
            self._health_status["failed"] += 1
            return None

        try:
            result = await self._retry.execute_with_retry(
                f"{task.task_type.value}:{task.id}",
                handler,
                task=task,
            )
            task.state = "succeeded"
            task.result = result
            task.completed_at = datetime.now(UTC).isoformat()
            self._health_status["succeeded"] += 1
        except Exception as e:
            task.state = "failed"
            task.error = str(e)
            task.completed_at = datetime.now(UTC).isoformat()
            self._health_status["failed"] += 1
        finally:
            elapsed = (datetime.now(UTC) - start).total_seconds() * 1000
            task.attempts.append({
                "started_at": task.started_at,
                "finished_at": task.completed_at,
                "success": task.state == "succeeded",
                "duration_ms": int(elapsed),
            })
            self._completed.append(task)

        # Update avg duration
        total = self._health_status["succeeded"] + self._health_status["failed"]
        if total > 0:
            durations = [a["duration_ms"] for t in self._completed for a in t.attempts]
            if durations:
                self._health_status["avg_duration_ms"] = int(sum(durations) / len(durations))

        return task.result

    def get_queue(self) -> list[dict]:
        return [t.to_dict() for t in self._task_queue]

    def get_completed(self, limit: int = 50) -> list[dict]:
        return [t.to_dict() for t in self._completed[-limit:]]

    def get_schedules(self, org_id: str | None = None) -> list[dict]:
        schedules = list(self._schedules.values())
        if org_id:
            schedules = [s for s in schedules if s.org_id == org_id]
        return [
            {
                "id": s.id, "org_id": s.org_id, "agent_id": s.agent_id,
                "task_type": s.task_type.value, "interval_seconds": s.interval_seconds,
                "active": s.active, "last_run": s.last_run, "next_run": s.next_run,
                "run_count": s.run_count,
            }
            for s in schedules
        ]

    def get_health(self) -> dict[str, Any]:
        uptime = (datetime.now(UTC) - self._started_at).total_seconds()
        self._health_status["uptime_seconds"] = int(uptime)
        self._health_status["queue_length"] = len(self._task_queue)
        self._health_status["active_schedules"] = sum(1 for s in self._schedules.values() if s.active)
        self._health_status["completed_count"] = len(self._completed)
        return dict(self._health_status)

    def get_retry_state(self, task_name: str) -> dict[str, Any]:
        return self._retry.get_state(task_name)
