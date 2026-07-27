from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger("pix.engine")


@dataclass
class ReasoningStep:
    description: str
    evidence: list[str] = field(default_factory=list)
    confidence: float = 0.0
    alternatives: list[str] = field(default_factory=list)


@dataclass
class ReasoningChain:
    problem: str
    steps: list[ReasoningStep] = field(default_factory=list)
    conclusion: str = ""
    overall_confidence: float = 0.0

    def add_step(self, description: str, evidence: list[str] | None = None, confidence: float = 0.0) -> ReasoningStep:
        step = ReasoningStep(description=description, evidence=evidence or [], confidence=confidence)
        self.steps.append(step)
        return step

    def finalize(self, conclusion: str) -> None:
        self.conclusion = conclusion
        if self.steps:
            self.overall_confidence = sum(s.confidence for s in self.steps) / len(self.steps)

    def to_prompt_context(self) -> str:
        parts = [f"Problem: {self.problem}"]
        for i, s in enumerate(self.steps, 1):
            parts.append(f"\nStep {i}: {s.description}")
            if s.evidence:
                parts.append("Evidence:")
                parts.extend(f"  - {e}" for e in s.evidence)
            parts.append(f"Confidence: {s.confidence:.0%}")
        parts.append(f"\nConclusion: {self.conclusion}")
        parts.append(f"Overall Confidence: {self.overall_confidence:.0%}")
        return "\n".join(parts)


class ReasoningPattern(ABC):
    """Base class for proprietary reasoning patterns."""

    @abstractmethod
    def name(self) -> str:
        ...

    @abstractmethod
    def apply(self, context: dict[str, Any]) -> ReasoningChain:
        ...


class SWOTAnalysis(ReasoningPattern):
    """Proprietary SWOT-based reasoning for business analysis."""

    def name(self) -> str:
        return "swot_analysis"

    def apply(self, context: dict[str, Any]) -> ReasoningChain:
        chain = ReasoningChain(problem=context.get("query", "Business analysis"))
        metrics = context.get("metrics", {})
        risks = context.get("risks", [])

        chain.add_step(
            "Evaluating internal strengths from operational metrics",
            evidence=[f"{k}: {v}" for k, v in list(metrics.items())[:5]],
            confidence=0.85,
        )
        chain.add_step(
            "Identifying weaknesses from risk factors and performance gaps",
            evidence=[r.get("description", str(r)) for r in risks[:3]],
            confidence=0.75,
        )
        chain.add_step(
            "Scanning external opportunities from market context",
            evidence=context.get("opportunities", []),
            confidence=0.65,
        )
        chain.add_step(
            "Analyzing external threats from competitive landscape",
            evidence=context.get("competitors", []),
            confidence=0.70,
        )
        chain.finalize(context.get("conclusion", "SWOT analysis completed"))
        return chain


class RootCauseAnalysis(ReasoningPattern):
    """Proprietary root cause analysis for problem detection."""

    def name(self) -> str:
        return "root_cause_analysis"

    def apply(self, context: dict[str, Any]) -> ReasoningChain:
        chain = ReasoningChain(problem=context.get("query", "Problem analysis"))
        symptoms = context.get("symptoms", [])
        chain.add_step(
            "Identifying observable symptoms",
            evidence=symptoms[:5],
            confidence=0.9,
        )
        chain.add_step(
            "Tracing symptom origins through causal chains",
            evidence=[f"Symptom: {s}" for s in symptoms[:3]],
            confidence=0.7,
        )
        chain.add_step(
            "Validating root cause against available data",
            evidence=context.get("evidence", []),
            confidence=0.8,
        )
        chain.finalize(context.get("root_cause", "Root cause identified"))
        return chain


class DecisionFramework:
    """Reusable decision framework for structured business decisions.

    Each framework encodes expert knowledge about a specific type of
    business decision (e.g., pricing, hiring, investment).
    """

    def __init__(
        self, name: str, description: str,
        criteria: list[str], weight_fn: str = "uniform",
    ) -> None:
        self.name = name
        self.description = description
        self.criteria = criteria
        self.weight_fn = weight_fn

    def evaluate(self, options: list[dict[str, Any]]) -> list[dict[str, Any]]:
        scored: list[dict[str, Any]] = []
        for option in options:
            total = 0.0
            details: dict[str, float] = {}
            for i, criterion in enumerate(self.criteria):
                score = option.get(criterion, 0.0)
                weight = 1.0 / len(self.criteria)
                total += score * weight
                details[criterion] = round(score, 2)
            scored.append({
                **option,
                "framework": self.name,
                "score": round(total, 2),
                "details": details,
            })
        scored.sort(key=lambda x: x["score"], reverse=True)
        return scored

    def to_prompt(self) -> str:
        criteria_str = "\n".join(f"  - {c}" for c in self.criteria)
        return f"""## Decision Framework: {self.name}
{self.description}

Evaluation Criteria:
{criteria_str}

Scoring: Each criterion scored 0-10. Final score = weighted average."""


# Registry of proprietary frameworks
DECISION_FRAMEWORKS: dict[str, DecisionFramework] = {
    "market_entry": DecisionFramework(
        "Market Entry Assessment",
        "Evaluate new market opportunities for expansion",
        criteria=[
            "market_size", "growth_rate", "regulatory_ease",
            "competitive_intensity", "cultural_fit", "talent_availability",
        ],
    ),
    "product_launch": DecisionFramework(
        "Product Launch Readiness",
        "Assess readiness for launching a new product or feature",
        criteria=[
            "market_demand", "technical_readiness", "team_capacity",
            "competitive_advantage", "revenue_potential", "time_to_market",
        ],
    ),
    "hiring_priority": DecisionFramework(
        "Hiring Priority Matrix",
        "Prioritize hiring decisions based on business impact",
        criteria=[
            "role_criticality", "time_sensitivity", "market_availability",
            "budget_impact", "team_gap_urgency",
        ],
    ),
    "investment_allocation": DecisionFramework(
        "Capital Allocation Framework",
        "Optimize resource allocation across business units",
        criteria=[
            "roi_potential", "strategic_alignment", "risk_level",
            "time_to_impact", "resource_requirement",
        ],
    ),
    "cost_optimization": DecisionFramework(
        "Cost Optimization Prioritization",
        "Identify and prioritize cost reduction opportunities",
        criteria=[
            "savings_potential", "implementation_effort", "business_impact",
            "employee_impact", "time_to_implement",
        ],
    ),
}


class IntelligenceEngine:
    """Proprietary business intelligence engine with reusable patterns and frameworks.

    This is πX's core moat — codified expert reasoning that improves
    over time and is difficult to replicate.
    """

    def __init__(self) -> None:
        self._patterns: dict[str, ReasoningPattern] = {}
        self._register_defaults()

    def _register_defaults(self) -> None:
        for pattern in [SWOTAnalysis(), RootCauseAnalysis()]:
            self._patterns[pattern.name()] = pattern

    def register_pattern(self, pattern: ReasoningPattern) -> None:
        self._patterns[pattern.name()] = pattern
        logger.info("Registered reasoning pattern: %s", pattern.name())

    def get_pattern(self, name: str) -> ReasoningPattern | None:
        return self._patterns.get(name)

    def list_patterns(self) -> list[str]:
        return list(self._patterns.keys())

    def analyze(self, pattern_name: str, context: dict[str, Any]) -> ReasoningChain:
        pattern = self._patterns.get(pattern_name)
        if not pattern:
            logger.warning("Unknown pattern: %s, falling back to SWOT", pattern_name)
            pattern = self._patterns["swot_analysis"]
        return pattern.apply(context)

    def get_framework(self, name: str) -> DecisionFramework | None:
        return DECISION_FRAMEWORKS.get(name)

    def list_frameworks(self) -> dict[str, str]:
        return {k: v.description for k, v in DECISION_FRAMEWORKS.items()}

    def evaluate_with_framework(
        self, framework_name: str, options: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        framework = self.get_framework(framework_name)
        if not framework:
            logger.warning("Unknown framework: %s", framework_name)
            return options
        return framework.evaluate(options)


_engine: IntelligenceEngine | None = None


def get_intelligence_engine() -> IntelligenceEngine:
    global _engine
    if _engine is None:
        _engine = IntelligenceEngine()
    return _engine
