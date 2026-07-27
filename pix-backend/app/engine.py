from dataclasses import dataclass, field
from typing import Any


@dataclass
class ReasoningStep:
    description: str = ""
    evidence: str = ""
    confidence: float = 0.5


@dataclass
class ReasoningChain:
    problem: str = ""
    steps: list[ReasoningStep] = field(default_factory=list)
    conclusion: str = ""
    overall_confidence: float = 0.5
    
    def to_prompt_context(self) -> str:
        """Convert chain to a prompt context string."""
        lines = [f"Problem: {self.problem}"]
        for i, s in enumerate(self.steps, 1):
            lines.append(f"Step {i}: {s.description} (confidence: {s.confidence:.0%})")
            if s.evidence:
                lines.append(f"  Evidence: {s.evidence}")
        lines.append(f"Conclusion: {self.conclusion}")
        return "\n".join(lines)


class IntelligenceEngine:
    def analyze(self, pattern: str, context: dict | None = None, **kw) -> ReasoningChain:
        context = context or {}
        query = context.get("query", "")
        return ReasoningChain(
            problem=query or "Unspecified problem",
            steps=[
                ReasoningStep(description=f"Applied {pattern} pattern", evidence="Context analysis", confidence=0.7),
                ReasoningStep(description="Identified contributing factors", evidence="Pattern complete", confidence=0.65),
            ],
            conclusion=f"Analysis of '{query}' using {pattern} suggests further investigation.",
            overall_confidence=0.68,
        )

    def evaluate_with_framework(self, framework: str, options: list | None = None) -> list:
        options = options or []
        scored = []
        for i, opt in enumerate(options):
            if isinstance(opt, str):
                opt = {"name": opt, "description": ""}
            scored.append({**opt, "score": 0.5 + (i * 0.1), "framework": framework, "recommendation": "Consider" if i == 0 else "Alternative"})
        if not scored:
            scored = [{"name": "default", "score": 0.5, "framework": framework}]
        return scored


    def list_patterns(self) -> list:
        return [
            {"name": "root_cause", "description": "Root cause analysis — identify underlying factors"},
            {"name": "trend_analysis", "description": "Trend analysis — detect patterns over time"},
            {"name": "comparison", "description": "Comparative analysis — compare entities or periods"},
            {"name": "prediction", "description": "Predictive analysis — forecast outcomes"},
            {"name": "risk_assessment", "description": "Risk assessment — evaluate probability and impact"},
            {"name": "opportunity", "description": "Opportunity analysis — identify growth potential"},
        ]

    def list_frameworks(self) -> list:
        return [
            {"name": "swot", "description": "Strengths, Weaknesses, Opportunities, Threats"},
            {"name": "porter", "description": "Porter's Five Forces — competitive analysis"},
            {"name": "balanced_scorecard", "description": "Balanced Scorecard — multi-perspective performance"},
            {"name": "okr", "description": "Objectives and Key Results — goal alignment"},
            {"name": "pestle", "description": "Political, Economic, Social, Technological, Legal, Environmental"},
            {"name": "cost_benefit", "description": "Cost-Benefit Analysis — financial evaluation"},
        ]

    def get_insights(self, org_id: str) -> list:
        return [{"org_id": org_id, "insight": "No insights available"}]


_engine = IntelligenceEngine()
def get_intelligence_engine(): return _engine
