from __future__ import annotations

from typing import Any

from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field

from packages.cognitive_kernel.agent_runtime import NodeAgent
from packages.cognitive_kernel.agent_runtime.tools import get_registry


class ReviewIssue(BaseModel):
    severity: str = Field(description="Severity: 'critical', 'major', 'minor', 'nitpick'")
    category: str = Field(description="Category: 'security', 'performance', 'correctness', 'style', 'maintainability', 'error_handling'")
    location: str = Field(description="File path or code location")
    description: str = Field(description="Clear description of the issue")
    suggestion: str = Field(description="Concrete fix or improvement suggestion")


class ReviewOutput(BaseModel):
    summary: str = Field(description="Overall review summary and quality assessment")
    issues: list[ReviewIssue] = Field(description="Issues found during review, ordered by severity")
    strengths: list[str] = Field(description="What the code does well")
    recommendations: list[str] = Field(description="Prioritized improvement recommendations")
    score: int = Field(description="Quality score 1-100", ge=1, le=100)
    approved: bool = Field(description="Whether the code/plan is approved as-is")


SYSTEM_PROMPT = """You are the **Reviewer Agent** for πX Technologies QORX.

Your role is to review code, plans, and documentation for quality, security, correctness, and maintainability.

**Review areas:**
1. **Security**: Injection risks, auth flaws, data exposure, secret handling
2. **Correctness**: Logic errors, edge cases, race conditions, boundary conditions
3. **Performance**: Inefficient algorithms, unnecessary allocations, N+1 queries
4. **Maintainability**: Code organization, naming, complexity, duplication
5. **Style**: Consistency with project conventions, readability
6. **Error handling**: Missing error handling, poor error messages, swallowing exceptions
7. **Testing**: Missing tests, untested paths, test quality

**Severity levels:**
- **critical**: Must fix before proceeding — security vulnerability or incorrect behavior
- **major**: Should fix — significant quality or correctness concern
- **minor**: Nice to fix — style, naming, or small improvements
- **nitpick**: Optional — personal preference or very minor

**Scoring guide:**
- 90-100: Excellent — ready to ship
- 70-89: Good — minor issues to address
- 50-69: Needs work — significant issues
- Below 50: Major rework required

Be constructive, specific, and actionable. Every issue must include a concrete suggestion."""


class ReviewerAgent(NodeAgent):
    @property
    def name(self) -> str:
        return "Reviewer"

    @property
    def description(self) -> str:
        return "Reviews code, plans, and documentation for security, correctness, performance, and quality"

    @property
    def system_prompt(self) -> str:
        return SYSTEM_PROMPT

    @property
    def output_schema(self) -> type[BaseModel]:
        return ReviewOutput

    @property
    def tools(self) -> list[BaseTool]:
        return get_registry().get_tools_for_role("reviewer")

    def _fallback_output(self, input_text: str, error: str) -> BaseModel:
        return ReviewOutput(
            summary=f"Review could not be completed due to: {error}",
            issues=[ReviewIssue(
                severity="critical",
                category="maintainability",
                location="review",
                description="The review agent encountered an error and could not complete the review",
                suggestion="Verify LLM availability and re-run the review",
            )],
            strengths=[],
            recommendations=["Re-run review when the agent is available"],
            score=1,
            approved=False,
        )


def create_reviewer_agent(settings, **kwargs: Any) -> ReviewerAgent:
    return ReviewerAgent(settings=settings, **kwargs)
