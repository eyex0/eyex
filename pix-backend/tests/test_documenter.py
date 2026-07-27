from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.agents.documenter import DocumentationAgent, DocumentationOutput, DocFile, create_documentation_agent


def test_documenter_schema():
    output = DocumentationOutput(
        files=[DocFile(path="docs/api.md", content="# API Docs", title="API Reference", audience="developer")],
        summary="Created API docs",
        key_decisions=["Use REST"],
        missing_docs=["Admin guide"],
        recommendations=["Add examples"],
    )
    assert len(output.files) == 1
    assert output.files[0].audience == "developer"


@pytest.mark.asyncio
async def test_documenter_fallback():
    agent = create_documentation_agent()
    mock_llm = AsyncMock()
    structured_chain = AsyncMock()
    structured_chain.ainvoke.side_effect = Exception("LLM error")
    mock_llm.with_structured_output = MagicMock(return_value=structured_chain)
    mock_llm.bind_tools = MagicMock(return_value=structured_chain)
    agent.llm = mock_llm
    result = await agent.execute("Document the API", session_id="test")
    assert isinstance(result, DocumentationOutput)
    assert len(result.files) == 0
