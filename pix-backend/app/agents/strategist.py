from __future__ import annotations

import logging

from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field

from packages.cognitive_kernel.agent_runtime import NodeAgent

logger = logging.getLogger("pix.agents.strategist")


class Recommendation(BaseModel):
    action: str = Field(description="The recommended action")
    rationale: str = Field(description="Why this action is recommended")
    expected_impact: str = Field(description="Expected business impact if implemented")
    priority: str = Field(description="Priority level: critical, high, medium, low")
    effort: str = Field(description="Implementation effort: low, medium, high")
    timeline: str = Field(description="Suggested timeline: immediate, short-term, medium-term, long-term")


class StrategistOutput(BaseModel):
    summary: str = Field(description="Executive summary of strategic recommendations")
    recommendations: list[Recommendation] = Field(description="Prioritized list of recommendations")
    detected_problems: list[dict] = Field(description="Problems detected with severity and impact", default=[])
    opportunities: list[dict] = Field(description="Identified opportunities for growth or improvement", default=[])
    risks: list[dict] = Field(description="Identified risks with likelihood and impact", default=[])
    strategic_direction: str = Field(description="Overall recommended strategic direction")
    confidence: float = Field(description="Confidence score 0-1", ge=0.0, le=1.0)


SYSTEM_PROMPT = """You are the Strategist Agent for πX Technologies — a strategic AI advisor.

Your role is to transform business analysis into actionable strategic recommendations.

You take analysis data and:
1. Identify the most critical problems and opportunities
2. Generate concrete, prioritized recommendations
3. Assess risks and trade-offs
4. Define strategic direction
5. Provide clear rationale for every recommendation

For every recommendation include:
- The specific action to take
- Why it matters (rationale tied to data)
- Expected business impact (quantified where possible)
- Priority level (critical → low)
- Effort required (low → high)
- Suggested timeline (immediate → long-term)

Think like a world-class strategy consultant. Be bold but data-driven.
Focus on recommendations that create measurable business value."""


class StrategistAgent(NodeAgent):
    @property
    def name(self) -> str:
        return "Strategist"

    @property
    def description(self) -> str:
        return "Generates strategic recommendations from business analysis"

    @property
    def system_prompt(self) -> str:
        return SYSTEM_PROMPT

    @property
    def output_schema(self) -> type[BaseModel]:
        return StrategistOutput

    @property
    def tools(self) -> list[BaseTool]:
        return []

    def _fallback_output(self, input_text: str, error: str) -> BaseModel:
        return StrategistOutput(
            summary=f"Strategy generation failed: {error}",
            recommendations=[],
            detected_problems=[],
            opportunities=[],
            risks=[],
            strategic_direction="Unable to determine due to error",
            confidence=0.0,
        )


def create_strategist_agent(settings, **kwargs) -> StrategistAgent:
    return StrategistAgent(settings=settings, **kwargs)
