from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import and_, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enterprise_trust import (
    ActionRiskLevel,
    AIActionRequest,
    AIApprovalDecision,
    AIApprovalWorkflow,
    AIGovernancePolicy,
    ApprovalStatus,
    ExplainableAIReport,
    HumanReviewTask,
)

logger = logging.getLogger("pix.services.governance")


@dataclass
class ActionRequestCreate:
    org_id: str
    agent_id: str
    action_type: str
    description: str
    requested_by: str
    workspace_id: str | None = None
    input_data: dict = field(default_factory=dict)
    proposed_action: dict = field(default_factory=dict)
    estimated_impact: dict = field(default_factory=dict)


@dataclass
class PolicyCreate:
    org_id: str
    name: str
    policy_type: str
    risk_level: ActionRiskLevel = ActionRiskLevel.MEDIUM
    action_types: list[str] = field(default_factory=list)
    auto_approve: bool = False
    require_explanation: bool = True
    require_human_review: bool = False
    approver_roles: list[str] = field(default_factory=list)
    max_auto_approve_value: float | None = None
    rules: dict = field(default_factory=dict)


@dataclass
class WorkflowCreate:
    org_id: str
    name: str
    trigger_action_types: list[str] = field(default_factory=list)
    trigger_risk_levels: list[str] = field(default_factory=list)
    steps: list[dict] = field(default_factory=list)
    description: str | None = None


@dataclass
class DecisionCreate:
    request_id: str
    decision: str
    decided_by: str
    step_number: int = 1
    comments: str | None = None


@dataclass
class HumanReviewCreate:
    org_id: str
    task_type: str
    title: str
    description: str
    request_id: str | None = None
    assigned_to: str | None = None
    priority: str = "medium"
    due_date: datetime | None = None
    context: dict = field(default_factory=dict)


@dataclass
class ExplainabilityCreate:
    org_id: str
    agent_id: str
    report_type: str
    summary: str
    request_id: str | None = None
    reasoning_steps: list[dict] = field(default_factory=list)
    evidence: list[dict] = field(default_factory=list)
    confidence_score: float = 0.0
    input_features: dict = field(default_factory=dict)
    output_explanation: str | None = None
    limitations: list[str] = field(default_factory=list)


class RiskAssessmentEngine:
    """Determines risk level for AI action requests based on policy rules."""

    def assess_risk(
        self,
        action_type: str,
        proposed_action: dict,
        estimated_impact: dict,
        org_policies: list[AIGovernancePolicy],
    ) -> ActionRiskLevel:
        # Start with explicit policy matches
        for policy in org_policies:
            if policy.is_active and action_type in (policy.action_types or []):
                return policy.risk_level

        # Fallback heuristics based on estimated impact
        financial_impact = float(estimated_impact.get("financial_value", 0) or 0)
        affected_users = int(estimated_impact.get("affected_users", 0) or 0)
        data_sensitivity = str(estimated_impact.get("data_sensitivity", "low")).lower()

        if (
            financial_impact >= 100_000
            or data_sensitivity == "critical"
            or affected_users >= 10_000
        ):
            return ActionRiskLevel.CRITICAL
        if financial_impact >= 10_000 or data_sensitivity == "high" or affected_users >= 1_000:
            return ActionRiskLevel.HIGH
        if financial_impact >= 1_000 or data_sensitivity == "medium" or affected_users >= 100:
            return ActionRiskLevel.MEDIUM
        return ActionRiskLevel.LOW

    def should_auto_approve(
        self,
        request: AIActionRequest,
        policies: list[AIGovernancePolicy],
    ) -> bool:
        for policy in policies:
            if not policy.is_active:
                continue
            if request.action_type not in (policy.action_types or []):
                continue
            if not policy.auto_approve:
                continue
            if policy.require_human_review:
                return False
            if policy.max_auto_approve_value is not None:
                impact = request.estimated_impact or {}
                value = float(impact.get("financial_value", 0) or 0)
                if value > policy.max_auto_approve_value:
                    return False
            return True
        return False

    def required_approvers(
        self,
        request: AIActionRequest,
        policies: list[AIGovernancePolicy],
    ) -> list[str]:
        roles = set()
        for policy in policies:
            if not policy.is_active:
                continue
            if request.action_type not in (policy.action_types or []):
                continue
            if request.risk_level.value not in (
                policy.risk_level.value,
                ActionRiskLevel.CRITICAL.value,
            ):
                # Only apply if the policy matches the action or policy is higher/equal risk
                if policy.risk_level.value != request.risk_level.value:
                    continue
            roles.update(policy.approver_roles or [])
        return list(roles)


class AIGovernanceService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.risk_engine = RiskAssessmentEngine()

    async def create_policy(self, data: PolicyCreate) -> AIGovernancePolicy:
        policy = AIGovernancePolicy(
            org_id=uuid.UUID(data.org_id),
            name=data.name,
            description=None,
            policy_type=data.policy_type,
            risk_level=data.risk_level,
            action_types=data.action_types,
            auto_approve=data.auto_approve,
            require_explanation=data.require_explanation,
            require_human_review=data.require_human_review,
            approver_roles=data.approver_roles,
            max_auto_approve_value=data.max_auto_approve_value,
            rules=data.rules,
        )
        self.db.add(policy)
        await self.db.commit()
        await self.db.refresh(policy)
        logger.info("Created AI governance policy %s for org %s", policy.id, data.org_id)
        return policy

    async def list_policies(
        self, org_id: str, active_only: bool = False
    ) -> list[AIGovernancePolicy]:
        query = select(AIGovernancePolicy).where(AIGovernancePolicy.org_id == uuid.UUID(org_id))
        if active_only:
            query = query.where(AIGovernancePolicy.is_active.is_(True))
        result = await self.db.execute(query.order_by(AIGovernancePolicy.created_at))
        return list(result.scalars().all())

    async def get_policy(self, policy_id: str) -> AIGovernancePolicy | None:
        result = await self.db.execute(
            select(AIGovernancePolicy).where(AIGovernancePolicy.id == uuid.UUID(policy_id))
        )
        return result.scalar_one_or_none()

    async def create_action_request(self, data: ActionRequestCreate) -> AIActionRequest:
        policies = await self.list_policies(data.org_id, active_only=True)
        risk_level = self.risk_engine.assess_risk(
            data.action_type,
            data.proposed_action,
            data.estimated_impact,
            policies,
        )
        request = AIActionRequest(
            org_id=uuid.UUID(data.org_id),
            workspace_id=uuid.UUID(data.workspace_id) if data.workspace_id else None,
            agent_id=data.agent_id,
            action_type=data.action_type,
            status=ApprovalStatus.PENDING,
            risk_level=risk_level,
            requested_by=uuid.UUID(data.requested_by),
            description=data.description,
            input_data=data.input_data,
            proposed_action=data.proposed_action,
            estimated_impact=data.estimated_impact,
        )

        if self.risk_engine.should_auto_approve(request, policies):
            request.status = ApprovalStatus.APPROVED
            request.approved_by = None
            request.approved_at = datetime.now(UTC)
            logger.info("Auto-approved request %s under org policy", request.id)
        else:
            # Auto-escalate critical actions
            if risk_level == ActionRiskLevel.CRITICAL:
                request.status = ApprovalStatus.ESCALATED
                logger.info("Escalated critical action request %s", request.id)

        self.db.add(request)
        await self.db.commit()
        await self.db.refresh(request)

        # Auto-generate explainability if required
        for policy in policies:
            if (
                policy.is_active
                and data.action_type in (policy.action_types or [])
                and policy.require_explanation
            ):
                await self.generate_explainability_report(
                    ExplainabilityCreate(
                        org_id=data.org_id,
                        agent_id=data.agent_id,
                        request_id=str(request.id),
                        report_type="action_approval",
                        summary=(
                            f"Explainability report for {data.action_type} "
                            f"requested by {data.requested_by}"
                        ),
                        reasoning_steps=[
                            {
                                "step": 1,
                                "description": "Policy match",
                                "detail": f"Matched policy risk level {risk_level.value}",
                            },
                            {
                                "step": 2,
                                "description": "Impact assessment",
                                "detail": str(data.estimated_impact),
                            },
                        ],
                        confidence_score=0.85,
                        input_features=data.input_data,
                    )
                )
                break

        return request

    async def get_action_request(self, request_id: str) -> AIActionRequest | None:
        result = await self.db.execute(
            select(AIActionRequest).where(AIActionRequest.id == uuid.UUID(request_id))
        )
        return result.scalar_one_or_none()

    async def list_action_requests(
        self,
        org_id: str,
        status: ApprovalStatus | None = None,
        agent_id: str | None = None,
        page: int = 1,
        per_page: int = 20,
    ) -> dict[str, Any]:
        query = select(AIActionRequest).where(AIActionRequest.org_id == uuid.UUID(org_id))
        if status:
            query = query.where(AIActionRequest.status == status)
        if agent_id:
            query = query.where(AIActionRequest.agent_id == agent_id)
        query = query.order_by(desc(AIActionRequest.created_at))

        total_result = await self.db.execute(select(func.count()).select_from(query.subquery()))
        total = total_result.scalar() or 0

        offset = (page - 1) * per_page
        items = list((await self.db.execute(query.offset(offset).limit(per_page))).scalars().all())
        return {
            "items": items,
            "total": total,
            "page": page,
            "per_page": per_page,
            "total_pages": (total + per_page - 1) // per_page,
        }

    async def submit_decision(self, data: DecisionCreate) -> AIApprovalDecision | None:
        request = await self.get_action_request(data.request_id)
        if not request:
            return None

        decision = AIApprovalDecision(
            request_id=request.id,
            step_number=data.step_number,
            decision=data.decision,
            decided_by=uuid.UUID(data.decided_by),
            comments=data.comments,
        )
        self.db.add(decision)

        if data.decision.lower() == "approved":
            request.status = ApprovalStatus.APPROVED
            request.approved_by = uuid.UUID(data.decided_by)
            request.approved_at = datetime.now(UTC)
        elif data.decision.lower() == "rejected":
            request.status = ApprovalStatus.REJECTED
            request.rejection_reason = data.comments or "No reason provided"
        elif data.decision.lower() == "escalated":
            request.status = ApprovalStatus.ESCALATED

        await self.db.commit()
        await self.db.refresh(decision)
        await self.db.refresh(request)
        logger.info("Decision %s recorded for request %s", data.decision, request.id)
        return decision

    async def record_execution(self, request_id: str, result: dict) -> AIActionRequest | None:
        request = await self.get_action_request(request_id)
        if not request:
            return None
        request.executed_at = datetime.now(UTC)
        request.execution_result = result
        await self.db.commit()
        await self.db.refresh(request)
        return request

    async def create_workflow(self, data: WorkflowCreate) -> AIApprovalWorkflow:
        workflow = AIApprovalWorkflow(
            org_id=uuid.UUID(data.org_id),
            name=data.name,
            description=data.description,
            trigger_action_types=data.trigger_action_types,
            trigger_risk_levels=data.trigger_risk_levels,
            steps=data.steps,
        )
        self.db.add(workflow)
        await self.db.commit()
        await self.db.refresh(workflow)
        return workflow

    async def get_workflow(self, workflow_id: str) -> AIApprovalWorkflow | None:
        result = await self.db.execute(
            select(AIApprovalWorkflow).where(AIApprovalWorkflow.id == uuid.UUID(workflow_id))
        )
        return result.scalar_one_or_none()

    async def list_workflows(self, org_id: str) -> list[AIApprovalWorkflow]:
        result = await self.db.execute(
            select(AIApprovalWorkflow)
            .where(AIApprovalWorkflow.org_id == uuid.UUID(org_id))
            .order_by(AIApprovalWorkflow.created_at)
        )
        return list(result.scalars().all())

    async def create_human_review(self, data: HumanReviewCreate) -> HumanReviewTask:
        task = HumanReviewTask(
            org_id=uuid.UUID(data.org_id),
            request_id=uuid.UUID(data.request_id) if data.request_id else None,
            task_type=data.task_type,
            title=data.title,
            description=data.description,
            assigned_to=uuid.UUID(data.assigned_to) if data.assigned_to else None,
            priority=data.priority,
            due_date=data.due_date,
            context=data.context,
        )
        self.db.add(task)
        await self.db.commit()
        await self.db.refresh(task)
        return task

    async def get_human_review(self, task_id: str) -> HumanReviewTask | None:
        result = await self.db.execute(
            select(HumanReviewTask).where(HumanReviewTask.id == uuid.UUID(task_id))
        )
        return result.scalar_one_or_none()

    async def list_human_reviews(
        self,
        org_id: str,
        status: str | None = None,
        assigned_to: str | None = None,
    ) -> list[HumanReviewTask]:
        query = select(HumanReviewTask).where(HumanReviewTask.org_id == uuid.UUID(org_id))
        if status:
            query = query.where(HumanReviewTask.status == status)
        if assigned_to:
            query = query.where(HumanReviewTask.assigned_to == uuid.UUID(assigned_to))
        result = await self.db.execute(query.order_by(desc(HumanReviewTask.created_at)))
        return list(result.scalars().all())

    async def complete_human_review(
        self, task_id: str, resolution: str, user_id: str
    ) -> HumanReviewTask | None:
        task = await self.get_human_review(task_id)
        if not task:
            return None
        task.status = "completed"
        task.resolution = resolution
        task.completed_at = datetime.now(UTC)
        await self.db.commit()
        await self.db.refresh(task)

        # If linked to a pending action request, auto-approve it
        if task.request_id:
            request = await self.get_action_request(str(task.request_id))
            if request and request.status == ApprovalStatus.PENDING:
                await self.submit_decision(
                    DecisionCreate(
                        request_id=str(request.id),
                        decision="approved",
                        decided_by=user_id,
                        comments=f"Approved via human review task {task_id}: {resolution}",
                    )
                )
        return task

    async def generate_explainability_report(
        self, data: ExplainabilityCreate
    ) -> ExplainableAIReport:
        report = ExplainableAIReport(
            org_id=uuid.UUID(data.org_id),
            agent_id=data.agent_id,
            request_id=uuid.UUID(data.request_id) if data.request_id else None,
            report_type=data.report_type,
            summary=data.summary,
            reasoning_steps=data.reasoning_steps,
            evidence=data.evidence,
            confidence_score=data.confidence_score,
            input_features=data.input_features,
            output_explanation=data.output_explanation,
            limitations=data.limitations,
        )
        self.db.add(report)
        await self.db.commit()
        await self.db.refresh(report)
        return report

    async def get_explainability_report(self, report_id: str) -> ExplainableAIReport | None:
        result = await self.db.execute(
            select(ExplainableAIReport).where(ExplainableAIReport.id == uuid.UUID(report_id))
        )
        return result.scalar_one_or_none()

    async def list_explainability_reports(
        self,
        org_id: str,
        agent_id: str | None = None,
    ) -> list[ExplainableAIReport]:
        query = select(ExplainableAIReport).where(ExplainableAIReport.org_id == uuid.UUID(org_id))
        if agent_id:
            query = query.where(ExplainableAIReport.agent_id == agent_id)
        result = await self.db.execute(query.order_by(desc(ExplainableAIReport.generated_at)))
        return list(result.scalars().all())

    async def get_governance_summary(self, org_id: str) -> dict[str, Any]:
        org_uuid = uuid.UUID(org_id)
        total = await self.db.execute(
            select(func.count()).where(AIActionRequest.org_id == org_uuid)
        )
        pending = await self.db.execute(
            select(func.count()).where(
                and_(
                    AIActionRequest.org_id == org_uuid,
                    AIActionRequest.status == ApprovalStatus.PENDING,
                )
            )
        )
        approved = await self.db.execute(
            select(func.count()).where(
                and_(
                    AIActionRequest.org_id == org_uuid,
                    AIActionRequest.status == ApprovalStatus.APPROVED,
                )
            )
        )
        rejected = await self.db.execute(
            select(func.count()).where(
                and_(
                    AIActionRequest.org_id == org_uuid,
                    AIActionRequest.status == ApprovalStatus.REJECTED,
                )
            )
        )
        escalated = await self.db.execute(
            select(func.count()).where(
                and_(
                    AIActionRequest.org_id == org_uuid,
                    AIActionRequest.status == ApprovalStatus.ESCALATED,
                )
            )
        )
        all_requests = await self.db.execute(
            select(AIActionRequest).where(AIActionRequest.org_id == org_uuid)
        )
        by_risk: dict[str, int] = {}
        for req in all_requests.scalars().all():
            by_risk[req.risk_level.value] = by_risk.get(req.risk_level.value, 0) + 1

        return {
            "total_requests": total.scalar() or 0,
            "pending": pending.scalar() or 0,
            "approved": approved.scalar() or 0,
            "rejected": rejected.scalar() or 0,
            "escalated": escalated.scalar() or 0,
            "by_risk_level": by_risk,
        }


_governance_service: AIGovernanceService | None = None


def get_governance_service(db: AsyncSession) -> AIGovernanceService:
    global _governance_service
    if _governance_service is None:
        _governance_service = AIGovernanceService(db)
    return _governance_service
