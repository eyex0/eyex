from __future__ import annotations

from typing import Any

from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field

from packages.cognitive-kernel.agent-runtime import NodeAgent
from packages.cognitive-kernel.agent-runtime.tools import get_registry


class PlannerOutput(BaseModel):
    plan: str = Field(description="High-level plan describing the overall approach and architecture")
    steps: list[str] = Field(description="Ordered list of concrete execution steps")
    step_details: list[dict[str, Any]] = Field(
        description="Per-step details: step index, description, assigned agent, estimated effort, dependencies"
    )
    estimated_effort: str = Field(description="Total estimated effort (e.g. '2-3 hours', '1-2 days')")
    risks: list[str] = Field(description="Potential risks or blockers")
    recommendations: list[str] = Field(description="Key recommendations and trade-off decisions")


SYSTEM_PROMPT = """You are the **Planner Agent** for πX Technologies QORX.

Your role is to decompose complex requests into a clear, actionable execution plan.

**Responsibilities:**
1. Analyze the request thoroughly — understand what is being asked, the context, and the constraints
2. Break the request into logical, sequential steps
3. Assign each step to the appropriate agent type (researcher, coder, reviewer, tester, documenter, devops)
4. Identify dependencies between steps
5. Estimate effort for each step and overall
6. Flag risks, assumptions, and open questions

**Output rules:**
- Steps must be concrete and actionable (not vague)
- Each step must specify which agent type owns it
- Dependencies should reference other step indices (0-based)
- Be realistic about effort estimates
- Flag any ambiguity or missing information immediately

**Examples of good plans:**
- Request: "Add a login page" → Steps: [Plan UX → Design API → Implement frontend → Implement backend → Add tests → Review]
- Request: "Research and implement RAG pipeline" → Steps: [Research vector DB options → Design architecture → Implement ingestion → Implement retrieval → Test → Document]"""


class PlannerAgent(NodeAgent):
    @property
    def name(self) -> str:
        return "Planner"

    @property
    def description(self) -> str:
        return "Decomposes complex requests into actionable execution plans with steps, effort estimates, and risks"

    @property
    def system_prompt(self) -> str:
        return SYSTEM_PROMPT

    @property
    def output_schema(self) -> type[BaseModel]:
        return PlannerOutput

    @property
    def tools(self) -> list[BaseTool]:
        return get_registry().get_tools_for_role("planner")

    def _fallback_output(self, input_text: str, error: str) -> BaseModel:
        return PlannerOutput(
            plan=f"Fallback plan for: {input_text[:200]}",
            steps=["Analyze requirements", "Implement solution", "Test", "Review", "Deploy"],
            step_details=[
                {"index": 0, "description": "Analyze requirements", "agent": "researcher", "effort": "30 min", "dependencies": []},
                {"index": 1, "description": "Implement solution", "agent": "coder", "effort": "2 hours", "dependencies": [0]},
                {"index": 2, "description": "Test implementation", "agent": "tester", "effort": "1 hour", "dependencies": [1]},
                {"index": 3, "description": "Review code", "agent": "reviewer", "effort": "30 min", "dependencies": [2]},
                {"index": 4, "description": "Deploy", "agent": "devops", "effort": "30 min", "dependencies": [3]},
            ],
            estimated_effort="4-5 hours",
            risks=["Plan created from fallback — review recommended"],
            recommendations=["Re-run planner with more context for accurate estimates"],
        )


def create_planner_agent(settings, **kwargs: Any) -> PlannerAgent:
    return PlannerAgent(settings=settings, **kwargs)
