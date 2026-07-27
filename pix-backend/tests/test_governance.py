from __future__ import annotations

import uuid
from typing import Any

import pytest
from sqlalchemy import BinaryExpression, BooleanClauseList
from sqlalchemy.sql.elements import False_, True_

from app.api.v1.trust import trust_router
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
from app.services.governance import (
    ActionRequestCreate,
    AIGovernanceService,
    DecisionCreate,
    ExplainabilityCreate,
    HumanReviewCreate,
    PolicyCreate,
    RiskAssessmentEngine,
    WorkflowCreate,
)


class _FakeResult:
    def __init__(self, data: list[Any] | Any) -> None:
        self._data = data

    def scalar_one_or_none(self) -> Any:
        if isinstance(self._data, list):
            return self._data[0] if self._data else None
        return self._data

    def scalar(self) -> Any:
        if isinstance(self._data, list):
            return self._data[0] if self._data else 0
        return self._data if self._data is not None else 0

    def scalars(self) -> _FakeResult:
        return self

    def all(self) -> list[Any]:
        if isinstance(self._data, list):
            return self._data
        return [self._data] if self._data is not None else []


def _get_filter_value(right: Any) -> Any:
    if isinstance(right, True_):
        return True
    if isinstance(right, False_):
        return False
    if hasattr(right, "value"):
        return right.value
    if hasattr(right, "effective_value"):
        return right.effective_value
    return right


def _eval_clause(obj: Any, clause: Any) -> bool:
    if isinstance(clause, BinaryExpression):
        left = clause.left
        right = clause.right
        attr = getattr(left, "key", None)
        if attr is None:
            return True
        expected = _get_filter_value(right)
        actual = getattr(obj, attr, None)
        op = getattr(clause, "operator", None)
        if op is None:
            return actual == expected
        op_name = getattr(op, "__name__", str(op))
        if op_name == "eq":
            return actual == expected
        if op_name == "ne":
            return actual != expected
        if op_name in ("is_", "is_true"):
            return bool(actual) is bool(expected)
        if op_name in ("is_not", "is_false"):
            return bool(actual) is not bool(expected)
        return True
    if isinstance(clause, BooleanClauseList):
        results = [_eval_clause(obj, c) for c in clause.clauses]
        op_name = getattr(clause.operator, "__name__", "and_")
        if "or" in op_name:
            return any(results)
        return all(results)
    return True


def _is_count_query(query: Any) -> bool:
    if not hasattr(query, "selected_columns") or not query.selected_columns:
        return False
    col = query.selected_columns[0]
    name = type(col).__name__
    return "count" in name.lower() or (
        hasattr(col, "name") and col.name and "count" in col.name.lower()
    )


def _apply_defaults(obj: Any) -> None:
    """Apply Python-side column defaults (SQLAlchemy defers this until flush)."""
    mapper = type(obj).__mapper__
    for col in mapper.columns:
        attr = mapper.get_property_by_column(col).key
        if getattr(obj, attr) is None and col.default is not None:
            if col.default.is_scalar:
                setattr(obj, attr, col.default.arg)
            elif callable(col.default.arg):
                setattr(obj, attr, col.default.arg())


class _FakeAsyncSession:
    def __init__(self) -> None:
        self._store: dict[type, list[Any]] = {}
        self._counters: dict[str, int] = {}

    def add(self, obj: Any) -> None:
        self._store.setdefault(type(obj), []).append(obj)
        if not hasattr(obj, "id") or obj.id is None:
            obj.id = uuid.uuid4()
        _apply_defaults(obj)

    async def commit(self) -> None:
        pass

    async def flush(self) -> None:
        pass

    async def refresh(self, obj: Any) -> None:
        pass

    def _entity_type(self, query: Any) -> type | None:
        text = str(query)
        if "ai_governance_policies" in text:
            return AIGovernancePolicy
        if "ai_action_requests" in text:
            return AIActionRequest
        if "ai_approval_decisions" in text:
            return AIApprovalDecision
        if "ai_approval_workflows" in text:
            return AIApprovalWorkflow
        if "human_review_tasks" in text:
            return HumanReviewTask
        if "explainable_ai_reports" in text:
            return ExplainableAIReport
        return None

    async def execute(self, query: Any) -> _FakeResult:
        entity = self._entity_type(query)
        if entity is None:
            return _FakeResult([])
        items = list(self._store.get(entity, []))
        if hasattr(query, "whereclause") and query.whereclause is not None:
            items = [item for item in items if _eval_clause(item, query.whereclause)]
        if _is_count_query(query):
            return _FakeResult(len(items))
        return _FakeResult(items)


ORG_ID = "12345678-1234-5678-1234-567812345678"
USER_ID = "11111111-1111-1111-1111-111111111111"
AGENT_ID = "agent-001"


class TestRiskAssessmentEngine:
    def test_assess_critical_high_financial_impact(self):
        engine = RiskAssessmentEngine()
        level = engine.assess_risk(
            "transaction",
            {},
            {"financial_value": 250_000},
            [],
        )
        assert level == ActionRiskLevel.CRITICAL

    def test_assess_high_medium_impact(self):
        engine = RiskAssessmentEngine()
        level = engine.assess_risk(
            "report",
            {},
            {"financial_value": 25_000, "affected_users": 1500},
            [],
        )
        assert level == ActionRiskLevel.HIGH

    def test_assess_medium(self):
        engine = RiskAssessmentEngine()
        level = engine.assess_risk(
            "recommend",
            {},
            {"financial_value": 2_000, "affected_users": 150},
            [],
        )
        assert level == ActionRiskLevel.MEDIUM

    def test_assess_low(self):
        engine = RiskAssessmentEngine()
        level = engine.assess_risk(
            "query",
            {},
            {"financial_value": 100, "affected_users": 10},
            [],
        )
        assert level == ActionRiskLevel.LOW

    def test_policy_override(self):
        engine = RiskAssessmentEngine()
        policy = AIGovernancePolicy(
            org_id=uuid.UUID(ORG_ID),
            name="High Risk Data",
            policy_type="data_access",
            risk_level=ActionRiskLevel.HIGH,
            action_types=["query"],
            is_active=True,
        )
        level = engine.assess_risk("query", {}, {"financial_value": 100}, [policy])
        assert level == ActionRiskLevel.HIGH

    def test_should_auto_approve(self):
        engine = RiskAssessmentEngine()
        policy = AIGovernancePolicy(
            org_id=uuid.UUID(ORG_ID),
            name="Auto Approve",
            policy_type="auto",
            risk_level=ActionRiskLevel.LOW,
            action_types=["query"],
            auto_approve=True,
            is_active=True,
            max_auto_approve_value=1000,
        )
        request = AIActionRequest(
            org_id=uuid.UUID(ORG_ID),
            agent_id=AGENT_ID,
            action_type="query",
            status=ApprovalStatus.PENDING,
            risk_level=ActionRiskLevel.LOW,
            requested_by=uuid.UUID(USER_ID),
            description="Test",
            estimated_impact={"financial_value": 500},
        )
        assert engine.should_auto_approve(request, [policy]) is True

    def test_should_not_auto_approve_over_limit(self):
        engine = RiskAssessmentEngine()
        policy = AIGovernancePolicy(
            org_id=uuid.UUID(ORG_ID),
            name="Auto Approve",
            policy_type="auto",
            risk_level=ActionRiskLevel.LOW,
            action_types=["query"],
            auto_approve=True,
            is_active=True,
            max_auto_approve_value=1000,
        )
        request = AIActionRequest(
            org_id=uuid.UUID(ORG_ID),
            agent_id=AGENT_ID,
            action_type="query",
            status=ApprovalStatus.PENDING,
            risk_level=ActionRiskLevel.LOW,
            requested_by=uuid.UUID(USER_ID),
            description="Test",
            estimated_impact={"financial_value": 5000},
        )
        assert engine.should_auto_approve(request, [policy]) is False


class TestAIGovernanceService:
    @pytest.fixture
    def db(self):
        return _FakeAsyncSession()

    @pytest.fixture
    def service(self, db):
        return AIGovernanceService(db)

    @pytest.mark.asyncio
    async def test_create_policy(self, service):
        policy = await service.create_policy(
            PolicyCreate(
                org_id=ORG_ID,
                name="Test Policy",
                policy_type="test",
                risk_level=ActionRiskLevel.HIGH,
                action_types=["transfer"],
                approver_roles=["admin"],
            )
        )
        assert policy.name == "Test Policy"
        assert policy.risk_level == ActionRiskLevel.HIGH
        assert policy.org_id == uuid.UUID(ORG_ID)

    @pytest.mark.asyncio
    async def test_create_action_request_no_policy(self, service):
        request = await service.create_action_request(
            ActionRequestCreate(
                org_id=ORG_ID,
                agent_id=AGENT_ID,
                action_type="transfer",
                description="Transfer funds",
                requested_by=USER_ID,
                estimated_impact={"financial_value": 500},
            )
        )
        assert request.status == ApprovalStatus.PENDING
        assert request.risk_level == ActionRiskLevel.LOW

    @pytest.mark.asyncio
    async def test_create_action_request_auto_approve(self, service, db):
        await service.create_policy(
            PolicyCreate(
                org_id=ORG_ID,
                name="Auto Approve",
                policy_type="auto",
                risk_level=ActionRiskLevel.LOW,
                action_types=["query"],
                auto_approve=True,
                max_auto_approve_value=1000,
                require_explanation=False,
            )
        )
        request = await service.create_action_request(
            ActionRequestCreate(
                org_id=ORG_ID,
                agent_id=AGENT_ID,
                action_type="query",
                description="Simple query",
                requested_by=USER_ID,
                estimated_impact={"financial_value": 500},
            )
        )
        assert request.status == ApprovalStatus.APPROVED
        assert request.approved_at is not None

    @pytest.mark.asyncio
    async def test_create_action_request_escalates_critical(self, service):
        request = await service.create_action_request(
            ActionRequestCreate(
                org_id=ORG_ID,
                agent_id=AGENT_ID,
                action_type="transaction",
                description="Large transaction",
                requested_by=USER_ID,
                estimated_impact={"financial_value": 500_000},
            )
        )
        assert request.status == ApprovalStatus.ESCALATED
        assert request.risk_level == ActionRiskLevel.CRITICAL

    @pytest.mark.asyncio
    async def test_submit_decision_approve(self, service, db):
        request = await service.create_action_request(
            ActionRequestCreate(
                org_id=ORG_ID,
                agent_id=AGENT_ID,
                action_type="transfer",
                description="Transfer funds",
                requested_by=USER_ID,
                estimated_impact={"financial_value": 500},
            )
        )
        decision = await service.submit_decision(
            DecisionCreate(
                request_id=str(request.id),
                decision="approved",
                decided_by=USER_ID,
                comments="Looks good",
            )
        )
        assert decision is not None
        assert decision.decision == "approved"
        refreshed = await service.get_action_request(str(request.id))
        assert refreshed.status == ApprovalStatus.APPROVED

    @pytest.mark.asyncio
    async def test_submit_decision_reject(self, service, db):
        request = await service.create_action_request(
            ActionRequestCreate(
                org_id=ORG_ID,
                agent_id=AGENT_ID,
                action_type="transfer",
                description="Transfer funds",
                requested_by=USER_ID,
                estimated_impact={"financial_value": 500},
            )
        )
        await service.submit_decision(
            DecisionCreate(
                request_id=str(request.id),
                decision="rejected",
                decided_by=USER_ID,
                comments="Too risky",
            )
        )
        refreshed = await service.get_action_request(str(request.id))
        assert refreshed.status == ApprovalStatus.REJECTED

    @pytest.mark.asyncio
    async def test_create_and_complete_human_review(self, service, db):
        request = await service.create_action_request(
            ActionRequestCreate(
                org_id=ORG_ID,
                agent_id=AGENT_ID,
                action_type="transfer",
                description="Transfer funds",
                requested_by=USER_ID,
                estimated_impact={"financial_value": 500},
            )
        )
        task = await service.create_human_review(
            HumanReviewCreate(
                org_id=ORG_ID,
                task_type="approval",
                title="Review transfer",
                description="Please review",
                request_id=str(request.id),
                assigned_to=USER_ID,
            )
        )
        assert task.status == "pending"
        completed = await service.complete_human_review(str(task.id), "Approved by human", USER_ID)
        assert completed.status == "completed"
        refreshed = await service.get_action_request(str(request.id))
        assert refreshed.status == ApprovalStatus.APPROVED

    @pytest.mark.asyncio
    async def test_generate_explainability_report(self, service):
        report = await service.generate_explainability_report(
            ExplainabilityCreate(
                org_id=ORG_ID,
                agent_id=AGENT_ID,
                report_type="action_approval",
                summary="Reasoning summary",
                reasoning_steps=[{"step": 1, "description": "Assess risk"}],
                confidence_score=0.9,
            )
        )
        assert report.summary == "Reasoning summary"
        assert report.confidence_score == 0.9

    @pytest.mark.asyncio
    async def test_create_workflow(self, service):
        workflow = await service.create_workflow(
            WorkflowCreate(
                org_id=ORG_ID,
                name="CFO Approval",
                trigger_action_types=["transaction"],
                trigger_risk_levels=["critical"],
                steps=[{"role": "cfo", "order": 1}],
            )
        )
        assert workflow.name == "CFO Approval"
        assert workflow.steps[0]["role"] == "cfo"

    @pytest.mark.asyncio
    async def test_governance_summary(self, service):
        await service.create_action_request(
            ActionRequestCreate(
                org_id=ORG_ID,
                agent_id=AGENT_ID,
                action_type="transfer",
                description="Transfer funds",
                requested_by=USER_ID,
                estimated_impact={"financial_value": 500},
            )
        )
        await service.create_action_request(
            ActionRequestCreate(
                org_id=ORG_ID,
                agent_id=AGENT_ID,
                action_type="transaction",
                description="Large transaction",
                requested_by=USER_ID,
                estimated_impact={"financial_value": 500_000},
            )
        )
        summary = await service.get_governance_summary(ORG_ID)
        assert summary["total_requests"] == 2
        assert summary["escalated"] == 1

    @pytest.mark.asyncio
    async def test_record_execution(self, service, db):
        request = await service.create_action_request(
            ActionRequestCreate(
                org_id=ORG_ID,
                agent_id=AGENT_ID,
                action_type="query",
                description="Query",
                requested_by=USER_ID,
                estimated_impact={"financial_value": 100},
            )
        )
        updated = await service.record_execution(str(request.id), {"success": True})
        assert updated.executed_at is not None
        assert updated.execution_result["success"] is True

    @pytest.mark.asyncio
    async def test_explainability_report_linked_to_request(self, service, db):
        request = await service.create_action_request(
            ActionRequestCreate(
                org_id=ORG_ID,
                agent_id=AGENT_ID,
                action_type="query",
                description="Query",
                requested_by=USER_ID,
                estimated_impact={"financial_value": 100},
            )
        )
        report = await service.generate_explainability_report(
            ExplainabilityCreate(
                org_id=ORG_ID,
                agent_id=AGENT_ID,
                request_id=str(request.id),
                report_type="action_approval",
                summary="Linked report",
            )
        )
        assert report.request_id == request.id
        fetched = await service.get_explainability_report(str(report.id))
        assert fetched.id == report.id


class TestWorkflowCreate:
    @pytest.mark.asyncio
    async def test_workflow_create_dataclass(self):
        data = WorkflowCreate(
            org_id=ORG_ID,
            name="Test",
            trigger_action_types=["x"],
            trigger_risk_levels=["high"],
            steps=[{"role": "manager"}],
        )
        assert data.name == "Test"
        assert data.steps[0]["role"] == "manager"


class TestHumanReviewCreate:
    @pytest.mark.asyncio
    async def test_human_review_create_dataclass(self):
        data = HumanReviewCreate(
            org_id=ORG_ID,
            task_type="approval",
            title="Review",
            description="Please review",
            assigned_to=USER_ID,
        )
        assert data.assigned_to == USER_ID
        assert data.priority == "medium"


class TestExplainabilityCreate:
    @pytest.mark.asyncio
    async def test_explainability_create_dataclass(self):
        data = ExplainabilityCreate(
            org_id=ORG_ID,
            agent_id=AGENT_ID,
            report_type="test",
            summary="Summary",
        )
        assert data.confidence_score == 0.0
        assert data.limitations == []


class TestTrustRouter:
    def test_router_exists(self):
        assert trust_router is not None
        assert trust_router.prefix == "/trust"

    def test_routes_registered(self):
        routes = {r.path for r in trust_router.routes}
        assert "/trust/policies" in routes
        assert "/trust/action-requests" in routes
        assert "/trust/workflows" in routes
        assert "/trust/human-reviews" in routes
        assert "/trust/explainability" in routes
        assert "/trust/summary" in routes
