from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.agents.planner import PlannerAgent, PlannerOutput, create_planner_agent


def test_planner_schema():
    output = PlannerOutput(
        plan="Build authentication system",
        steps=["Design DB schema", "Implement JWT auth", "Create login API", "Add tests"],
        step_details=[
            {"index": 0, "description": "Design DB schema", "agent": "coder", "effort": "30 min", "dependencies": []},
            {"index": 1, "description": "Implement JWT auth", "agent": "coder", "effort": "1 hour", "dependencies": [0]},
        ],
        estimated_effort="2 hours",
        risks=["None"],
        recommendations=["Use bcrypt"],
    )
    assert output.plan == "Build authentication system"
    assert len(output.steps) == 4
    assert output.estimated_effort == "2 hours"


@pytest.mark.asyncio
async def test_planner_fallback():
    agent = create_planner_agent()
    mock_llm = AsyncMock()
    structured_chain = AsyncMock()
    structured_chain.ainvoke.side_effect = Exception("LLM error")
    mock_llm.with_structured_output = MagicMock(return_value=structured_chain)
    mock_llm.bind_tools = MagicMock(return_value=structured_chain)
    agent.llm = mock_llm
    result = await agent.execute("Build a login page", session_id="test-session")
    assert isinstance(result, PlannerOutput)
    assert "Fallback" in result.plan
    assert len(result.steps) == 5


@pytest.mark.asyncio
async def test_planner_node():
    agent = create_planner_agent()
    node = agent.create_node()
    with patch.object(agent, "execute") as mock_execute:
        mock_execute.return_value = PlannerOutput(
            plan="Test plan",
            steps=["Step 1"],
            step_details=[{"index": 0, "description": "Step 1", "agent": "coder", "effort": "1h", "dependencies": []}],
            estimated_effort="1h",
            risks=[],
            recommendations=[],
        )
        result = await node({"request": "Test", "thread_id": "t1"})
        assert "planner_result" in result
        assert result["planner_result"]["plan"] == "Test plan"
