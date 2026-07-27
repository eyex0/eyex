"""
πX Workflow Engine — Temporal-style orchestration for long-running agents.

Supports: long-running workflows, retries, recovery, scheduling, background intelligence.
Each workflow is a sequence of steps that can run, retry, recover, and persist state.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any, Callable
import uuid


class StepStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    RETRYING = "retrying"
    SKIPPED = "skipped"
    COMPENSATING = "compensating"  # rollback step


class WorkflowStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    PAUSED = "paused"
    COMPENSATING = "compensating"


@dataclass
class WorkflowStep:
    id: str
    name: str
    step_type: str = "activity"  # activity, wait, decision, timer
    handler: str = ""  # handler name to execute
    config: dict[str, Any] = field(default_factory=dict)
    timeout_seconds: int = 300
    max_retries: int = 3
    status: StepStatus = StepStatus.PENDING
    attempts: int = 0
    result: Any = None
    error: str = ""
    started_at: str = ""
    completed_at: str = ""
    compensation_handler: str = ""  # rollback handler name


@dataclass
class Workflow:
    id: str
    name: str
    org_id: str
    agent_id: str
    steps: list[WorkflowStep] = field(default_factory=list)
    status: WorkflowStatus = WorkflowStatus.PENDING
    current_step: int = 0
    input_data: dict[str, Any] = field(default_factory=dict)
    output_data: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    updated_at: str = ""
    completed_at: str = ""
    error: str = ""

    def to_dict(self) -> dict:
        return {
            "id": self.id, "name": self.name, "org_id": self.org_id,
            "agent_id": self.agent_id, "status": self.status.value,
            "current_step": self.current_step,
            "steps": [{"id": s.id, "name": s.name, "status": s.status.value,
                        "attempts": s.attempts, "error": s.error} for s in self.steps],
            "input_data": self.input_data, "output_data": self.output_data,
            "created_at": self.created_at, "updated_at": self.updated_at,
            "completed_at": self.completed_at, "error": self.error,
        }


class WorkflowEngine:
    """Temporal-style workflow engine for long-running agent workflows.

    Production: Temporal.io worker with activity definitions.
    Here: in-process execution with retry, compensation, and recovery.
    """

    def __init__(self) -> None:
        self._workflows: dict[str, Workflow] = {}
        self._handlers: dict[str, Callable] = {}
        self._compensation_handlers: dict[str, Callable] = {}
        self._schedules: dict[str, dict] = {}  # workflow_name → cron config

    def register_handler(self, name: str, handler: Callable) -> None:
        self._handlers[name] = handler

    def register_compensation(self, name: str, handler: Callable) -> None:
        self._compensation_handlers[name] = handler

    def create_workflow(
        self,
        name: str,
        org_id: str,
        agent_id: str,
        steps: list[dict[str, Any]],
        input_data: dict | None = None,
    ) -> Workflow:
        """Create a workflow from step definitions."""
        wf_steps = [
            WorkflowStep(
                id=s.get("id", f"step_{i}"),
                name=s["name"],
                step_type=s.get("type", "activity"),
                handler=s.get("handler", ""),
                config=s.get("config", {}),
                timeout_seconds=s.get("timeout", 300),
                max_retries=s.get("max_retries", 3),
                compensation_handler=s.get("compensation", ""),
            )
            for i, s in enumerate(steps)
        ]
        wf = Workflow(
            id=f"wf_{uuid.uuid4().hex[:12]}",
            name=name,
            org_id=org_id,
            agent_id=agent_id,
            steps=wf_steps,
            input_data=input_data or {},
        )
        self._workflows[wf.id] = wf
        return wf

    async def execute(self, workflow_id: str) -> Workflow:
        """Execute a workflow to completion."""
        wf = self._workflows.get(workflow_id)
        if not wf:
            raise ValueError(f"Workflow {workflow_id} not found")

        wf.status = WorkflowStatus.RUNNING
        wf.updated_at = datetime.now(UTC).isoformat()

        for i, step in enumerate(wf.steps):
            wf.current_step = i
            step.status = StepStatus.RUNNING
            step.started_at = datetime.now(UTC).isoformat()

            handler = self._handlers.get(step.handler)
            if not handler:
                step.status = StepStatus.FAILED
                step.error = f"Handler '{step.handler}' not registered"
                wf.status = WorkflowStatus.FAILED
                wf.error = step.error
                await self._compensate(wf, i)
                return wf

            for attempt in range(1, step.max_retries + 1):
                step.attempts = attempt
                try:
                    import asyncio
                    result = handler(wf, step) if not asyncio.iscoroutinefunction(handler) else await handler(wf, step)
                    step.result = result
                    step.status = StepStatus.SUCCEEDED
                    step.completed_at = datetime.now(UTC).isoformat()
                    wf.output_data[step.name] = result
                    break
                except Exception as e:
                    step.error = str(e)
                    if attempt < step.max_retries:
                        step.status = StepStatus.RETRYING
                    else:
                        step.status = StepStatus.FAILED
                        step.completed_at = datetime.now(UTC).isoformat()
                        wf.status = WorkflowStatus.FAILED
                        wf.error = f"Step '{step.name}' failed after {attempt} attempts: {e}"
                        await self._compensate(wf, i)
                        return wf

        wf.status = WorkflowStatus.SUCCEEDED
        wf.completed_at = datetime.now(UTC).isoformat()
        wf.updated_at = datetime.now(UTC).isoformat()
        return wf

    async def _compensate(self, wf: Workflow, failed_step: int) -> None:
        """Run compensation handlers for completed steps (rollback)."""
        wf.status = WorkflowStatus.COMPENSATING
        had_compensation = False
        for i in range(failed_step - 1, -1, -1):
            step = wf.steps[i]
            if step.status == StepStatus.SUCCEEDED and step.compensation_handler:
                comp_handler = self._compensation_handlers.get(step.compensation_handler)
                if comp_handler:
                    step.status = StepStatus.COMPENSATING
                    had_compensation = True
                    try:
                        comp_handler(wf, step)
                        step.status = StepStatus.SUCCEEDED
                    except Exception:
                        step.status = StepStatus.FAILED
        # Restore FAILED status after compensation
        wf.status = WorkflowStatus.FAILED

    def pause(self, workflow_id: str) -> bool:
        wf = self._workflows.get(workflow_id)
        if wf and wf.status == WorkflowStatus.RUNNING:
            wf.status = WorkflowStatus.PAUSED
            return True
        return False

    def resume(self, workflow_id: str) -> bool:
        wf = self._workflows.get(workflow_id)
        if wf and wf.status == WorkflowStatus.PAUSED:
            wf.status = WorkflowStatus.RUNNING
            return True
        return False

    def get_workflow(self, workflow_id: str) -> Workflow | None:
        return self._workflows.get(workflow_id)

    def list_workflows(self, org_id: str | None = None, limit: int = 50) -> list[dict]:
        wfs = list(self._workflows.values())
        if org_id:
            wfs = [w for w in wfs if w.org_id == org_id]
        return [w.to_dict() for w in wfs[-limit:]]

    def schedule_workflow(self, workflow_name: str, cron: str, org_id: str, agent_id: str, steps: list[dict]) -> str:
        """Schedule a recurring workflow (production: Temporal schedule)."""
        sched_id = f"sched_{uuid.uuid4().hex[:12]}"
        self._schedules[sched_id] = {
            "workflow_name": workflow_name,
            "cron": cron,
            "org_id": org_id,
            "agent_id": agent_id,
            "steps": steps,
            "active": True,
        }
        return sched_id

    def get_schedules(self) -> list[dict]:
        return list(self._schedules.values())

    def get_stats(self) -> dict[str, Any]:
        wfs = list(self._workflows.values())
        return {
            "total": len(wfs),
            "running": sum(1 for w in wfs if w.status == WorkflowStatus.RUNNING),
            "succeeded": sum(1 for w in wfs if w.status == WorkflowStatus.SUCCEEDED),
            "failed": sum(1 for w in wfs if w.status == WorkflowStatus.FAILED),
            "paused": sum(1 for w in wfs if w.status == WorkflowStatus.PAUSED),
        }
