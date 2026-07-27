from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.agents.researcher import ResearchAgent, ResearchOutput, create_research_agent


def test_researcher_schema():
    output = ResearchOutput(
        findings="PostgreSQL is the best choice",
        summary="Use PostgreSQL for relational data",
        sources=["PostgreSQL docs"],
        recommendations=["Use asyncpg driver"],
        confidence=0.9,
        open_questions=["Consider connection pooling"],
    )
    assert output.confidence == 0.9
    assert "PostgreSQL" in output.findings
    assert len(output.recommendations) == 1


@pytest.mark.asyncio
async def test_researcher_fallback():
    agent = create_research_agent()
    mock_llm = AsyncMock()
    structured_chain = AsyncMock()
    structured_chain.ainvoke.side_effect = Exception("LLM error")
    mock_llm.with_structured_output = MagicMock(return_value=structured_chain)
    mock_llm.bind_tools = MagicMock(return_value=structured_chain)
    agent.llm = mock_llm
    result = await agent.execute("Research best databases", session_id="test")
    assert isinstance(result, ResearchOutput)
    assert result.confidence == 0.3
    assert "Fallback" in result.summary
