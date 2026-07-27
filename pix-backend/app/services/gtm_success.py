from __future__ import annotations

import logging
import uuid
from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import and_, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.gtm import (
    BusinessImpactMeasurement,
    CustomerFeedback,
    CustomerHealth,
    CustomerHealthStatus,
    CustomerSuccessReport,
    RetentionWorkflow,
    UsageMetric,
)

logger = logging.getLogger("pix.services.gtm.success")


@dataclass
class HealthScoreWeights:
    usage: float = 0.25
    engagement: float = 0.20
    satisfaction: float = 0.20
    support: float = 0.15
    adoption: float = 0.20


class CustomerHealthService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.weights = HealthScoreWeights()

    async def calculate_health(self, org_id: str) -> CustomerHealth:
        usage_score = await self._calculate_usage_score(org_id)
        engagement_score = await self._calculate_engagement_score(org_id)
        satisfaction_score = await self._calculate_satisfaction_score(org_id)
        support_score = await self._calculate_support_score(org_id)
        adoption_score = await self._calculate_adoption_score(org_id)

        overall = int(
            usage_score * self.weights.usage
            + engagement_score * self.weights.engagement
            + satisfaction_score * self.weights.satisfaction
            + support_score * self.weights.support
            + adoption_score * self.weights.adoption
        )

        status = self._determine_status(overall)
        risk_factors = self._identify_risk_factors(
            usage_score, engagement_score, satisfaction_score, support_score, adoption_score
        )
        positive_signals = self._identify_positive_signals(
            usage_score, engagement_score, satisfaction_score, support_score, adoption_score
        )
        churn_prob = self._calculate_churn_probability(overall, risk_factors)

        result = await self.db.execute(
            select(CustomerHealth).where(CustomerHealth.org_id == uuid.UUID(org_id))
        )
        health = result.scalar_one_or_none()

        if not health:
            health = CustomerHealth(org_id=uuid.UUID(org_id))
            self.db.add(health)

        health.overall_score = overall
        health.status = status
        health.usage_score = usage_score
        health.engagement_score = engagement_score
        health.satisfaction_score = satisfaction_score
        health.support_score = support_score
        health.adoption_score = adoption_score
        health.last_calculated = datetime.now(UTC)
        health.risk_factors = risk_factors
        health.positive_signals = positive_signals
        health.churn_probability = churn_prob
        health.next_review_at = datetime.now(UTC) + timedelta(days=30)

        await self.db.commit()
        await self.db.refresh(health)
        return health

    async def _calculate_usage_score(self, org_id: str) -> int:
        since = datetime.now(UTC) - timedelta(days=30)
        result = await self.db.execute(
            select(func.count(UsageMetric.id)).where(
                and_(UsageMetric.org_id == uuid.UUID(org_id), UsageMetric.period_start >= since)
            )
        )
        count = result.scalar() or 0
        return min(100, count * 5)

    async def _calculate_engagement_score(self, org_id: str) -> int:
        since = datetime.now(UTC) - timedelta(days=7)
        result = await self.db.execute(
            select(func.count(UsageMetric.id)).where(
                and_(UsageMetric.org_id == uuid.UUID(org_id), UsageMetric.period_start >= since)
            )
        )
        weekly = result.scalar() or 0
        return min(100, weekly * 10)

    async def _calculate_satisfaction_score(self, org_id: str) -> int:
        result = await self.db.execute(
            select(func.avg(CustomerFeedback.rating)).where(CustomerFeedback.org_id == uuid.UUID(org_id))
        )
        avg = result.scalar()
        if avg is None:
            return 80
        return int(min(100, avg * 20))

    async def _calculate_support_score(self, org_id: str) -> int:
        return 90

    async def _calculate_adoption_score(self, org_id: str) -> int:
        return 75

    def _determine_status(self, score: int) -> CustomerHealthStatus:
        if score >= 80:
            return CustomerHealthStatus.HEALTHY
        elif score >= 60:
            return CustomerHealthStatus.AT_RISK
        elif score >= 40:
            return CustomerHealthStatus.CRITICAL
        return CustomerHealthStatus.CHURNED

    def _identify_risk_factors(self, *scores: int) -> list[dict]:
        factors = []
        labels = ["usage", "engagement", "satisfaction", "support", "adoption"]
        for label, score in zip(labels, scores):
            if score < 50:
                factors.append({"factor": label, "score": score, "severity": "high"})
            elif score < 70:
                factors.append({"factor": label, "score": score, "severity": "medium"})
        return factors

    def _identify_positive_signals(self, *scores: int) -> list[dict]:
        signals = []
        labels = ["usage", "engagement", "satisfaction", "support", "adoption"]
        for label, score in zip(labels, scores):
            if score >= 80:
                signals.append({"signal": label, "score": score, "strength": "strong"})
            elif score >= 70:
                signals.append({"signal": label, "score": score, "strength": "moderate"})
        return signals

    def _calculate_churn_probability(self, overall: int, risk_factors: list[dict]) -> float:
        base = max(0, (100 - overall) / 100)
        risk_multiplier = 1 + len(risk_factors) * 0.1
        return min(1.0, base * risk_multiplier)

    async def get_health(self, org_id: str) -> CustomerHealth | None:
        result = await self.db.execute(select(CustomerHealth).where(CustomerHealth.org_id == uuid.UUID(org_id)))
        return result.scalar_one_or_none()

    async def list_at_risk(self, threshold: int = 70) -> list[CustomerHealth]:
        result = await self.db.execute(
            select(CustomerHealth).where(CustomerHealth.overall_score < threshold)
        )
        return list(result.scalars().all())

    async def record_usage(self, org_id: str, metric_name: str, value: float, period_start: datetime, period_end: datetime, metadata: dict | None = None) -> UsageMetric:
        metric = UsageMetric(
            org_id=uuid.UUID(org_id),
            metric_name=metric_name,
            metric_value=value,
            period_start=period_start,
            period_end=period_end,
            meta_data=metadata,
        )
        self.db.add(metric)
        await self.db.commit()
        await self.db.refresh(metric)
        return metric

    async def get_usage_history(self, org_id: str, metric_name: str | None = None, days: int = 30) -> list[UsageMetric]:
        since = datetime.now(UTC) - timedelta(days=days)
        query = select(UsageMetric).where(and_(UsageMetric.org_id == uuid.UUID(org_id), UsageMetric.period_start >= since))
        if metric_name:
            query = query.where(UsageMetric.metric_name == metric_name)
        query = query.order_by(UsageMetric.period_start)
        result = await self.db.execute(query)
        return list(result.scalars().all())


class CustomerFeedbackService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def submit_feedback(
        self,
        org_id: str,
        user_id: str,
        feedback_type: str,
        rating: int,
        comment: str | None = None,
        feature_area: str | None = None,
        metadata: dict | None = None,
    ) -> CustomerFeedback:
        feedback = CustomerFeedback(
            org_id=uuid.UUID(org_id),
            user_id=uuid.UUID(user_id),
            feedback_type=feedback_type,
            rating=rating,
            comment=comment,
            feature_area=feature_area,
            sentiment=self._analyze_sentiment(rating, comment),
            meta_data=metadata,
        )
        self.db.add(feedback)
        await self.db.commit()
        await self.db.refresh(feedback)
        return feedback

    def _analyze_sentiment(self, rating: int, comment: str | None) -> str:
        if rating >= 4:
            return "positive"
        elif rating >= 3:
            return "neutral"
        return "negative"

    async def get_feedback_summary(self, org_id: str, days: int = 30) -> dict[str, Any]:
        since = datetime.now(UTC) - timedelta(days=days)
        result = await self.db.execute(
            select(CustomerFeedback).where(
                and_(CustomerFeedback.org_id == uuid.UUID(org_id), CustomerFeedback.created_at >= since)
            )
        )
        feedbacks = list(result.scalars().all())

        if not feedbacks:
            return {"total": 0, "avg_rating": 0, "by_type": {}, "sentiment": {}}

        by_type = defaultdict(list)
        sentiment_count = defaultdict(int)
        for f in feedbacks:
            by_type[f.feedback_type].append(f.rating)
            sentiment_count[f.sentiment] += 1

        return {
            "total": len(feedbacks),
            "avg_rating": sum(f.rating for f in feedbacks) / len(feedbacks),
            "by_type": {k: sum(v) / len(v) for k, v in by_type.items()},
            "sentiment": dict(sentiment_count),
        }


class RetentionWorkflowService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def trigger_workflow(self, org_id: str, workflow_type: str, trigger: str, metadata: dict | None = None) -> RetentionWorkflow:
        existing = await self.db.execute(
            select(RetentionWorkflow).where(
                and_(RetentionWorkflow.org_id == uuid.UUID(org_id), RetentionWorkflow.workflow_type == workflow_type, RetentionWorkflow.status == "active")
            )
        )
        if existing.scalar_one_or_none():
            raise ValueError(f"Active {workflow_type} workflow already exists for org {org_id}")

        workflow = RetentionWorkflow(
            org_id=uuid.UUID(org_id),
            workflow_type=workflow_type,
            trigger=trigger,
            meta_data=metadata,
        )
        self.db.add(workflow)
        await self.db.commit()
        await self.db.refresh(workflow)
        return workflow

    async def add_action(self, workflow_id: str, action: dict) -> RetentionWorkflow:
        result = await self.db.execute(select(RetentionWorkflow).where(RetentionWorkflow.id == uuid.UUID(workflow_id)))
        workflow = result.scalar_one_or_none()
        if not workflow:
            raise ValueError("Workflow not found")
        workflow.actions = workflow.actions + [action]
        await self.db.commit()
        await self.db.refresh(workflow)
        return workflow

    async def complete_workflow(self, workflow_id: str, outcome: str) -> RetentionWorkflow:
        result = await self.db.execute(select(RetentionWorkflow).where(RetentionWorkflow.id == uuid.UUID(workflow_id)))
        workflow = result.scalar_one_or_none()
        if not workflow:
            raise ValueError("Workflow not found")
        workflow.status = "completed"
        workflow.completed_at = datetime.now(UTC)
        workflow.outcome = outcome
        await self.db.commit()
        await self.db.refresh(workflow)
        return workflow

    async def get_active_workflows(self, org_id: str) -> list[RetentionWorkflow]:
        result = await self.db.execute(
            select(RetentionWorkflow).where(and_(RetentionWorkflow.org_id == uuid.UUID(org_id), RetentionWorkflow.status == "active"))
        )
        return list(result.scalars().all())


class CustomerSuccessReportService:
    def __init__(self, db: AsyncSession, health_service: CustomerHealthService) -> None:
        self.db = db
        self.health_service = health_service

    async def generate_report(self, org_id: str, period_days: int = 30) -> CustomerSuccessReport:
        period_end = datetime.now(UTC)
        period_start = period_end - timedelta(days=period_days)

        health = await self.health_service.get_health(org_id)
        if not health:
            health = await self.health_service.calculate_health(org_id)

        usage = await self._get_usage_summary(org_id, period_start, period_end)
        adoption = await self._get_adoption_metrics(org_id, period_start, period_end)
        impact = await self._get_business_impact(org_id, period_start, period_end)

        recommendations = await self._generate_recommendations(health, usage, adoption)
        risks = await self._identify_risks(health)
        next_steps = await self._define_next_steps(health, recommendations)

        report = CustomerSuccessReport(
            org_id=uuid.UUID(org_id),
            period_start=period_start,
            period_end=period_end,
            health_score=health.overall_score,
            usage_summary=usage,
            adoption_metrics=adoption,
            business_impact=impact,
            recommendations=recommendations,
            risks=risks,
            next_steps=next_steps,
        )
        self.db.add(report)
        await self.db.commit()
        await self.db.refresh(report)
        return report

    async def _get_usage_summary(self, org_id: str, start: datetime, end: datetime) -> dict:
        result = await self.db.execute(
            select(UsageMetric).where(
                and_(UsageMetric.org_id == uuid.UUID(org_id), UsageMetric.period_start >= start, UsageMetric.period_end <= end)
            )
        )
        metrics = list(result.scalars().all())

        by_name = defaultdict(list)
        for m in metrics:
            by_name[m.metric_name].append(m.metric_value)

        return {
            "total_metrics": len(metrics),
            "by_metric": {k: {"avg": sum(v) / len(v), "count": len(v)} for k, v in by_name.items()},
            "period_days": (end - start).days,
        }

    async def _get_adoption_metrics(self, org_id: str, start: datetime, end: datetime) -> dict:
        return {
            "active_users": 0,
            "feature_adoption": {},
            "agent_usage": {},
            "report_views": 0,
        }

    async def _get_business_impact(self, org_id: str, start: datetime, end: datetime) -> dict:
        result = await self.db.execute(
            select(BusinessImpactMeasurement).where(
                and_(BusinessImpactMeasurement.org_id == uuid.UUID(org_id), BusinessImpactMeasurement.measured_at >= start, BusinessImpactMeasurement.measured_at <= end)
            )
        )
        measurements = list(result.scalars().all())

        return {
            "measurements": [
                {
                    "metric": m.metric_name,
                    "baseline": m.baseline_value,
                    "current": m.current_value,
                    "change_pct": m.change_percentage,
                    "target": m.target_value,
                }
                for m in measurements
            ],
            "total_impact": sum(m.change_percentage for m in measurements) if measurements else 0,
        }

    async def _generate_recommendations(self, health: CustomerHealth, usage: dict, adoption: dict) -> list[dict]:
        recs = []
        if health.usage_score < 70:
            recs.append({"type": "usage", "priority": "high", "title": "Increase platform usage", "description": "Schedule training session to drive adoption"})
        if health.adoption_score < 70:
            recs.append({"type": "adoption", "priority": "high", "title": "Improve feature adoption", "description": "Enable additional agents for their industry"})
        if health.satisfaction_score < 70:
            recs.append({"type": "satisfaction", "priority": "critical", "title": "Address satisfaction concerns", "description": "Schedule executive check-in"})
        return recs

    async def _identify_risks(self, health: CustomerHealth) -> list[dict]:
        risks = []
        for factor in health.risk_factors:
            risks.append({"factor": factor["factor"], "severity": factor["severity"], "description": f"Low {factor['factor']} score: {factor['score']}"})
        if health.churn_probability > 0.3:
            risks.append({"factor": "churn", "severity": "high", "description": f"Churn probability: {health.churn_probability:.0%}"})
        return risks

    async def _define_next_steps(self, health: CustomerHealth, recommendations: list[dict]) -> list[dict]:
        return [
            {"step": "Review health report with customer", "owner": "CSM", "due_in_days": 7},
            {"step": "Implement top recommendations", "owner": "CSM + Engineering", "due_in_days": 30},
            {"step": "Schedule next health check", "owner": "CSM", "due_in_days": 30},
        ]

    async def get_report(self, report_id: str) -> CustomerSuccessReport | None:
        result = await self.db.execute(select(CustomerSuccessReport).where(CustomerSuccessReport.id == uuid.UUID(report_id)))
        return result.scalar_one_or_none()

    async def list_reports(self, org_id: str, limit: int = 10) -> list[CustomerSuccessReport]:
        result = await self.db.execute(
            select(CustomerSuccessReport).where(CustomerSuccessReport.org_id == uuid.UUID(org_id)).order_by(desc(CustomerSuccessReport.generated_at)).limit(limit)
        )
        return list(result.scalars().all())


class BusinessImpactService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def record_measurement(
        self,
        org_id: str,
        measurement_type: str,
        metric_name: str,
        baseline_value: float,
        current_value: float,
        target_value: float | None = None,
        unit: str = "",
        attribution: list[dict] | None = None,
        metadata: dict | None = None,
    ) -> BusinessImpactMeasurement:
        change_pct = ((current_value - baseline_value) / baseline_value * 100) if baseline_value != 0 else 0
        measurement = BusinessImpactMeasurement(
            org_id=uuid.UUID(org_id),
            measurement_type=measurement_type,
            metric_name=metric_name,
            baseline_value=baseline_value,
            current_value=current_value,
            target_value=target_value,
            unit=unit,
            change_percentage=change_pct,
            is_positive=change_pct >= 0,
            attribution=attribution or [],
            meta_data=metadata,
        )
        self.db.add(measurement)
        await self.db.commit()
        await self.db.refresh(measurement)
        return measurement

    async def get_impact_summary(self, org_id: str, measurement_type: str | None = None) -> dict[str, Any]:
        query = select(BusinessImpactMeasurement).where(BusinessImpactMeasurement.org_id == uuid.UUID(org_id))
        if measurement_type:
            query = query.where(BusinessImpactMeasurement.measurement_type == measurement_type)
        query = query.order_by(desc(BusinessImpactMeasurement.measured_at))
        result = await self.db.execute(query)
        measurements = list(result.scalars().all())

        return {
            "total_measurements": len(measurements),
            "positive_impact": sum(1 for m in measurements if m.is_positive),
            "negative_impact": sum(1 for m in measurements if not m.is_positive),
            "avg_change_pct": sum(m.change_percentage for m in measurements) / len(measurements) if measurements else 0,
            "measurements": [
                {
                    "type": m.measurement_type,
                    "metric": m.metric_name,
                    "baseline": m.baseline_value,
                    "current": m.current_value,
                    "change_pct": m.change_percentage,
                    "unit": m.unit,
                    "measured_at": m.measured_at.isoformat(),
                }
                for m in measurements
            ],
        }


_health_service: CustomerHealthService | None = None
_feedback_service: CustomerFeedbackService | None = None
_retention_service: RetentionWorkflowService | None = None
_report_service: CustomerSuccessReportService | None = None
_impact_service: BusinessImpactService | None = None


def get_health_service(db: AsyncSession) -> CustomerHealthService:
    global _health_service
    if _health_service is None:
        _health_service = CustomerHealthService(db)
    return _health_service


def get_feedback_service(db: AsyncSession) -> CustomerFeedbackService:
    global _feedback_service
    if _feedback_service is None:
        _feedback_service = CustomerFeedbackService(db)
    return _feedback_service


def get_retention_service(db: AsyncSession) -> RetentionWorkflowService:
    global _retention_service
    if _retention_service is None:
        _retention_service = RetentionWorkflowService(db)
    return _retention_service


def get_report_service(db: AsyncSession) -> CustomerSuccessReportService:
    global _report_service
    if _report_service is None:
        _report_service = CustomerSuccessReportService(db, get_health_service(db))
    return _report_service


def get_impact_service(db: AsyncSession) -> BusinessImpactService:
    global _impact_service
    if _impact_service is None:
        _impact_service = BusinessImpactService(db)
    return _impact_service
