from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.agents.reviewer import ReviewerAgent, ReviewOutput, ReviewIssue, create_reviewer_agent


def test_reviewer_schema():
    output = ReviewOutput(
        summary="Code looks good",
        issues=[ReviewIssue(severity="minor", category="style", location="app.py:10", description="Long line", suggestion="Break into two lines")],
        strengths=["Clean architecture"],
        recommendations=["Add more tests"],
        score=85,
        approved=False,
    )
    assert output.score == 85
    assert output.approved is False
    assert len(output.issues) == 1


@pytest.mark.asyncio
async def test_reviewer_fallback():
    agent = create_reviewer_agent()
    mock_llm = AsyncMock()
    structured_chain = AsyncMock()
    structured_chain.ainvoke.side_effect = Exception("LLM error")
    mock_llm.with_structured_output = MagicMock(return_value=structured_chain)
    mock_llm.bind_tools = MagicMock(return_value=structured_chain)
    agent.llm = mock_llm
    result = await agent.execute("Review this code", session_id="test")
    assert isinstance(result, ReviewOutput)
    assert result.score == 1
    assert result.approved is False


def test_issue_severity_validation():
    issue = ReviewIssue(severity="critical", category="security", location="auth.py", description="SQL injection risk", suggestion="Use parameterized queries")
    assert issue.severity == "critical"
