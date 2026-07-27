from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db_session
from app.dependencies import get_current_user
from app.models.enterprise_trust import ActionRiskLevel, ApprovalStatus
from app.models.user import User
from app.services.governance import (
    ActionRequestCreate,
    DecisionCreate,
    ExplainabilityCreate,
    HumanReviewCreate,
    PolicyCreate,
    WorkflowCreate,
    get_governance_service,
)

logger = logging.getLogger("pix.api.trust")

trust_router = APIRouter(prefix="/trust", tags=["Trust & Intelligence"])


class PolicyRequest(BaseModel):
    name: str
    policy_type: str
    risk_level: ActionRiskLevel = ActionRiskLevel.MEDIUM
    action_types: list[str] = Field(default_factory=list)
    auto_approve: bool = False
    require_explanation: bool = True
    require_human_review: bool = False
    approver_roles: list[str] = Field(default_factory=list)
    max_auto_approve_value: float | None = None
    rules: dict = Field(default_factory=dict)


class ActionRequestBody(BaseModel):
    agent_id: str
    action_type: str
    description: str
    workspace_id: str | None = None
    input_data: dict = Field(default_factory=dict)
    proposed_action: dict = Field(default_factory=dict)
    estimated_impact: dict = Field(default_factory=dict)


class DecisionRequest(BaseModel):
    decision: str
    step_number: int = 1
    comments: str | None = None


class WorkflowRequest(BaseModel):
    name: str
    trigger_action_types: list[str] = Field(default_factory=list)
    trigger_risk_levels: list[str] = Field(default_factory=list)
    steps: list[dict] = Field(default_factory=list)
    description: str | None = None


class HumanReviewRequest(BaseModel):
    task_type: str
    title: str
    description: str
    request_id: str | None = None
    assigned_to: str | None = None
    priority: str = "medium"
    context: dict = Field(default_factory=dict)


class HumanReviewResolution(BaseModel):
    resolution: str


class ExplainabilityRequest(BaseModel):
    agent_id: str
    report_type: str
    summary: str
    request_id: str | None = None
    reasoning_steps: list[dict] = Field(default_factory=list)
    evidence: list[dict] = Field(default_factory=list)
    confidence_score: float = 0.0
    input_features: dict = Field(default_factory=dict)
    output_explanation: str | None = None
    limitations: list[str] = Field(default_factory=list)


class ExecutionResult(BaseModel):
    result: dict = Field(default_factory=dict)


def _to_policy_create(org_id: str, payload: PolicyRequest) -> PolicyCreate:
    return PolicyCreate(
        org_id=org_id,
        name=payload.name,
        policy_type=payload.policy_type,
        risk_level=payload.risk_level,
        action_types=payload.action_types,
        auto_approve=payload.auto_approve,
        require_explanation=payload.require_explanation,
        require_human_review=payload.require_human_review,
        approver_roles=payload.approver_roles,
        max_auto_approve_value=payload.max_auto_approve_value,
        rules=payload.rules,
    )


def _to_action_request_create(
    org_id: str, user_id: str, payload: ActionRequestBody
) -> ActionRequestCreate:
    return ActionRequestCreate(
        org_id=org_id,
        agent_id=payload.agent_id,
        action_type=payload.action_type,
        description=payload.description,
        requested_by=user_id,
        workspace_id=payload.workspace_id,
        input_data=payload.input_data,
        proposed_action=payload.proposed_action,
        estimated_impact=payload.estimated_impact,
    )


@trust_router.post("/policies")
async def create_policy(
    payload: PolicyRequest,
    db: AsyncSession = Depends(get_db_session),
    user: User = Depends(get_current_user),
) -> dict[str, Any]:
    service = get_governance_service(db)
    policy = await service.create_policy(_to_policy_create(str(user.organization_id), payload))
    return {"id": str(policy.id), "name": policy.name, "risk_level": policy.risk_level.value}


@trust_router.get("/policies")
async def list_policies(
    active_only: bool = Query(False),
    db: AsyncSession = Depends(get_db_session),
    user: User = Depends(get_current_user),
) -> dict[str, Any]:
    service = get_governance_service(db)
    policies = await service.list_policies(str(user.organization_id), active_only=active_only)
    return {
        "items": [
            {
                "id": str(p.id),
                "name": p.name,
                "policy_type": p.policy_type,
                "risk_level": p.risk_level.value,
                "action_types": p.action_types,
                "auto_approve": p.auto_approve,
                "is_active": p.is_active,
            }
            for p in policies
        ]
    }


@trust_router.post("/action-requests")
async def create_action_request(
    payload: ActionRequestBody,
    db: AsyncSession = Depends(get_db_session),
    user: User = Depends(get_current_user),
) -> dict[str, Any]:
    service = get_governance_service(db)
    request = await service.create_action_request(
        _to_action_request_create(str(user.organization_id), str(user.id), payload)
    )
    return {
        "id": str(request.id),
        "status": request.status.value,
        "risk_level": request.risk_level.value,
        "agent_id": request.agent_id,
        "action_type": request.action_type,
    }


@trust_router.get("/action-requests")
async def list_action_requests(
    status: ApprovalStatus | None = Query(None),
    agent_id: str | None = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db_session),
    user: User = Depends(get_current_user),
) -> dict[str, Any]:
    service = get_governance_service(db)
    result = await service.list_action_requests(
        str(user.organization_id), status=status, agent_id=agent_id, page=page, per_page=per_page
    )
    return {
        "items": [
            {
                "id": str(r.id),
                "agent_id": r.agent_id,
                "action_type": r.action_type,
                "status": r.status.value,
                "risk_level": r.risk_level.value,
                "requested_by": str(r.requested_by),
                "requested_at": r.requested_at.isoformat() if r.requested_at else None,
            }
            for r in result["items"]
        ],
        "total": result["total"],
        "page": result["page"],
        "per_page": result["per_page"],
        "total_pages": result["total_pages"],
    }


@trust_router.get("/action-requests/{request_id}")
async def get_action_request(
    request_id: str,
    db: AsyncSession = Depends(get_db_session),
    user: User = Depends(get_current_user),
) -> dict[str, Any]:
    service = get_governance_service(db)
    request = await service.get_action_request(request_id)
    if not request or str(request.org_id) != str(user.organization_id):
        raise HTTPException(status_code=404, detail="Action request not found")
    return {
        "id": str(request.id),
        "agent_id": request.agent_id,
        "action_type": request.action_type,
        "status": request.status.value,
        "risk_level": request.risk_level.value,
        "description": request.description,
        "requested_by": str(request.requested_by),
        "requested_at": request.requested_at.isoformat() if request.requested_at else None,
        "approved_by": str(request.approved_by) if request.approved_by else None,
        "approved_at": request.approved_at.isoformat() if request.approved_at else None,
    }


@trust_router.post("/action-requests/{request_id}/decisions")
async def submit_decision(
    request_id: str,
    payload: DecisionRequest,
    db: AsyncSession = Depends(get_db_session),
    user: User = Depends(get_current_user),
) -> dict[str, Any]:
    service = get_governance_service(db)
    request = await service.get_action_request(request_id)
    if not request or str(request.org_id) != str(user.organization_id):
        raise HTTPException(status_code=404, detail="Action request not found")
    decision = await service.submit_decision(
        DecisionCreate(
            request_id=request_id,
            decision=payload.decision,
            decided_by=str(user.id),
            step_number=payload.step_number,
            comments=payload.comments,
        )
    )
    if not decision:
        raise HTTPException(status_code=400, detail="Unable to record decision")
    return {
        "id": str(decision.id),
        "decision": decision.decision,
        "decided_by": str(decision.decided_by),
    }


@trust_router.post("/action-requests/{request_id}/execute")
async def record_execution(
    request_id: str,
    payload: ExecutionResult,
    db: AsyncSession = Depends(get_db_session),
    user: User = Depends(get_current_user),
) -> dict[str, Any]:
    service = get_governance_service(db)
    request = await service.get_action_request(request_id)
    if not request or str(request.org_id) != str(user.organization_id):
        raise HTTPException(status_code=404, detail="Action request not found")
    updated = await service.record_execution(request_id, payload.result)
    return {
        "id": str(updated.id),
        "executed_at": updated.executed_at.isoformat() if updated.executed_at else None,
    }


@trust_router.post("/workflows")
async def create_workflow(
    payload: WorkflowRequest,
    db: AsyncSession = Depends(get_db_session),
    user: User = Depends(get_current_user),
) -> dict[str, Any]:
    service = get_governance_service(db)
    workflow = await service.create_workflow(
        WorkflowCreate(
            org_id=str(user.organization_id),
            name=payload.name,
            trigger_action_types=payload.trigger_action_types,
            trigger_risk_levels=payload.trigger_risk_levels,
            steps=payload.steps,
            description=payload.description,
        )
    )
    return {"id": str(workflow.id), "name": workflow.name, "is_active": workflow.is_active}


@trust_router.get("/workflows")
async def list_workflows(
    db: AsyncSession = Depends(get_db_session),
    user: User = Depends(get_current_user),
) -> dict[str, Any]:
    service = get_governance_service(db)
    workflows = await service.list_workflows(str(user.organization_id))
    return {
        "items": [
            {
                "id": str(w.id),
                "name": w.name,
                "trigger_action_types": w.trigger_action_types,
                "trigger_risk_levels": w.trigger_risk_levels,
                "is_active": w.is_active,
            }
            for w in workflows
        ]
    }


@trust_router.post("/human-reviews")
async def create_human_review(
    payload: HumanReviewRequest,
    db: AsyncSession = Depends(get_db_session),
    user: User = Depends(get_current_user),
) -> dict[str, Any]:
    service = get_governance_service(db)
    task = await service.create_human_review(
        HumanReviewCreate(
            org_id=str(user.organization_id),
            task_type=payload.task_type,
            title=payload.title,
            description=payload.description,
            request_id=payload.request_id,
            assigned_to=payload.assigned_to,
            priority=payload.priority,
            context=payload.context,
        )
    )
    return {"id": str(task.id), "status": task.status, "title": task.title}


@trust_router.get("/human-reviews")
async def list_human_reviews(
    status: str | None = Query(None),
    assigned_to: str | None = Query(None),
    db: AsyncSession = Depends(get_db_session),
    user: User = Depends(get_current_user),
) -> dict[str, Any]:
    service = get_governance_service(db)
    tasks = await service.list_human_reviews(
        str(user.organization_id), status=status, assigned_to=assigned_to
    )
    return {
        "items": [
            {
                "id": str(t.id),
                "task_type": t.task_type,
                "title": t.title,
                "status": t.status,
                "priority": t.priority,
                "assigned_to": str(t.assigned_to) if t.assigned_to else None,
            }
            for t in tasks
        ]
    }


@trust_router.post("/human-reviews/{task_id}/complete")
async def complete_human_review(
    task_id: str,
    payload: HumanReviewResolution,
    db: AsyncSession = Depends(get_db_session),
    user: User = Depends(get_current_user),
) -> dict[str, Any]:
    service = get_governance_service(db)
    task = await service.complete_human_review(task_id, payload.resolution, str(user.id))
    if not task:
        raise HTTPException(status_code=404, detail="Human review task not found")
    return {
        "id": str(task.id),
        "status": task.status,
        "completed_at": task.completed_at.isoformat() if task.completed_at else None,
    }


@trust_router.post("/explainability")
async def create_explainability_report(
    payload: ExplainabilityRequest,
    db: AsyncSession = Depends(get_db_session),
    user: User = Depends(get_current_user),
) -> dict[str, Any]:
    service = get_governance_service(db)
    report = await service.generate_explainability_report(
        ExplainabilityCreate(
            org_id=str(user.organization_id),
            agent_id=payload.agent_id,
            report_type=payload.report_type,
            summary=payload.summary,
            request_id=payload.request_id,
            reasoning_steps=payload.reasoning_steps,
            evidence=payload.evidence,
            confidence_score=payload.confidence_score,
            input_features=payload.input_features,
            output_explanation=payload.output_explanation,
            limitations=payload.limitations,
        )
    )
    return {
        "id": str(report.id),
        "agent_id": report.agent_id,
        "report_type": report.report_type,
        "confidence_score": report.confidence_score,
        "generated_at": report.generated_at.isoformat() if report.generated_at else None,
    }


@trust_router.get("/explainability")
async def list_explainability_reports(
    agent_id: str | None = Query(None),
    db: AsyncSession = Depends(get_db_session),
    user: User = Depends(get_current_user),
) -> dict[str, Any]:
    service = get_governance_service(db)
    reports = await service.list_explainability_reports(
        str(user.organization_id), agent_id=agent_id
    )
    return {
        "items": [
            {
                "id": str(r.id),
                "agent_id": r.agent_id,
                "report_type": r.report_type,
                "summary": r.summary,
                "confidence_score": r.confidence_score,
                "generated_at": r.generated_at.isoformat() if r.generated_at else None,
            }
            for r in reports
        ]
    }


@trust_router.get("/summary")
async def governance_summary(
    db: AsyncSession = Depends(get_db_session),
    user: User = Depends(get_current_user),
) -> dict[str, Any]:
    service = get_governance_service(db)
    summary = await service.get_governance_summary(str(user.organization_id))
    return summary
