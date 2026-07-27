from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.agents.coder import CodingAgent, CodingOutput, CodeFile, create_coding_agent


def test_coder_schema():
    output = CodingOutput(
        files=[CodeFile(path="src/app.py", content="print('hello')", language="python")],
        explanation="Simple hello world",
        dependencies=[],
        setup_instructions=["Run: python src/app.py"],
        breaking_changes=False,
        testing_notes=["Manual test"],
    )
    assert len(output.files) == 1
    assert output.files[0].path == "src/app.py"
    assert output.breaking_changes is False


@pytest.mark.asyncio
async def test_coder_fallback():
    agent = create_coding_agent()
    mock_llm = AsyncMock()
    structured_chain = AsyncMock()
    structured_chain.ainvoke.side_effect = Exception("LLM error")
    mock_llm.with_structured_output = MagicMock(return_value=structured_chain)
    mock_llm.bind_tools = MagicMock(return_value=structured_chain)
    agent.llm = mock_llm
    result = await agent.execute("Write a FastAPI app", session_id="test")
    assert isinstance(result, CodingOutput)
    assert len(result.files) == 0
    assert "failed" in result.explanation


@pytest.mark.asyncio
async def test_coder_node():
    agent = create_coding_agent()
    node = agent.create_node()
    with patch.object(agent, "execute") as mock_execute:
        mock_execute.return_value = CodingOutput(
            files=[CodeFile(path="main.py", content="x = 1", language="python")],
            explanation="Test",
            dependencies=[],
            setup_instructions=["run it"],
            breaking_changes=False,
            testing_notes=[],
        )
        result = await node({"request": "Write code", "thread_id": "t1"})
        assert "coder_result" in result
        assert result["coder_result"]["files"][0]["path"] == "main.py"
