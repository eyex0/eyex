from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.agents.tester import TestingAgent, TestingOutput, TestFile, create_testing_agent


def test_tester_schema():
    output = TestingOutput(
        test_files=[TestFile(path="tests/test_app.py", content="def test_x(): pass", framework="pytest")],
        coverage_analysis="90% coverage",
        test_strategy="Unit tests",
        missing_tests=["Integration tests"],
        setup_instructions=["pip install pytest"],
        recommendations=["Add more edge cases"],
    )
    assert len(output.test_files) == 1
    assert output.test_files[0].framework == "pytest"


@pytest.mark.asyncio
async def test_tester_fallback():
    agent = create_testing_agent()
    mock_llm = AsyncMock()
    structured_chain = AsyncMock()
    structured_chain.ainvoke.side_effect = Exception("LLM error")
    mock_llm.with_structured_output = MagicMock(return_value=structured_chain)
    mock_llm.bind_tools = MagicMock(return_value=structured_chain)
    agent.llm = mock_llm
    result = await agent.execute("Test the auth module", session_id="test")
    assert isinstance(result, TestingOutput)
    assert len(result.test_files) == 0
