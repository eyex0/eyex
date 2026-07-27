from __future__ import annotations

from typing import Any

from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field

from packages.cognitive_kernel.agent_runtime import NodeAgent
from packages.cognitive_kernel.agent_runtime.tools import get_registry


class ResearchOutput(BaseModel):
    findings: str = Field(description="Detailed research findings and analysis")
    summary: str = Field(description="Executive summary of the research (2-3 sentences)")
    sources: list[str] = Field(description="Sources, references, or reasoning chains used")
    recommendations: list[str] = Field(description="Actionable recommendations based on findings")
    confidence: float = Field(description="Confidence score 0.0-1.0", ge=0.0, le=1.0)
    open_questions: list[str] = Field(description="Remaining open questions or areas needing further investigation")


SYSTEM_PROMPT = """You are the **Research Agent** for πX Technologies QORX.

Your role is to gather information, analyze options, and provide thorough research on any topic.

**Responsibilities:**
1. Analyze the research question deeply
2. Consider multiple approaches, technologies, and perspectives
3. Use available tools (file reading, web search) to gather real data
4. Evaluate trade-offs between different options
5. Provide concrete, actionable recommendations
6. Be honest about uncertainty and knowledge limits

**Research methodology:**
- Start with the core question — what exactly needs to be decided?
- Gather facts from available sources
- Compare alternatives with pros/cons
- Consider: performance, security, cost, maintainability, scalability
- Conclude with clear recommendations

**Output rules:**
- Be specific (mention actual technologies, versions, patterns)
- Include confidence levels for each finding
- Flag areas where more information is needed
- Prioritize actionable insights over general information"""


class ResearchAgent(NodeAgent):
    @property
    def name(self) -> str:
        return "Researcher"

    @property
    def description(self) -> str:
        return "Gathers information, analyzes options, and provides evidence-based research and recommendations"

    @property
    def system_prompt(self) -> str:
        return SYSTEM_PROMPT

    @property
    def output_schema(self) -> type[BaseModel]:
        return ResearchOutput

    @property
    def tools(self) -> list[BaseTool]:
        return get_registry().get_tools_for_role("researcher")

    def _fallback_output(self, input_text: str, error: str) -> BaseModel:
        return ResearchOutput(
            findings=f"Research could not be completed due to: {error}. Using general knowledge.",
            summary=f"Fallback analysis for: {input_text[:200]}",
            sources=["General knowledge (fallback)"],
            recommendations=["Re-run research when LLM is available", "Check documentation manually"],
            confidence=0.3,
            open_questions=["Full research was not possible — verify all findings"],
        )


def create_research_agent(settings, **kwargs: Any) -> ResearchAgent:
    return ResearchAgent(settings=settings, **kwargs)
