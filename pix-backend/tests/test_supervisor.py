from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from app.agents.supervisor import SupervisorAgent, SupervisorClassification


@pytest.mark.asyncio
async def test_supervisor_classify_fallback_on_error():
    agent = SupervisorAgent()
    mock_chain = AsyncMock()
    mock_chain.ainvoke.side_effect = Exception("LLM unavailable")
    with patch.object(agent, "prompt") as mock_prompt:
        mock_prompt.__or__.return_value = mock_chain
        result = await agent.classify("Hello, how are you?")
    assert isinstance(result, SupervisorClassification)
    assert result.category == "general"
    assert result.confidence == 0.5
    assert "Fallback" in result.reasoning


def test_supervisor_classification_schema():
    classification = SupervisorClassification(
        category="coding",
        confidence=0.92,
        reasoning="User asked to build a feature",
        suggested_agents=["researcher", "coder"],
        requires_decomposition=True,
    )
    dumped = classification.model_dump()
    assert dumped["category"] == "coding"
    assert dumped["confidence"] == 0.92
    assert len(dumped["suggested_agents"]) == 2
    assert dumped["requires_decomposition"] is True


@pytest.mark.asyncio
async def test_supervisor_analyze_structure():
    agent = SupervisorAgent()
    with patch.object(agent, "classify") as mock_classify:
        mock_classify.return_value = SupervisorClassification(
            category="research",
            confidence=0.85,
            reasoning="User wants information",
            suggested_agents=["researcher"],
            requires_decomposition=False,
        )
        result = await agent.analyze("What is the capital of France?")
        assert "classification" in result
        assert result["classification"]["category"] == "research"
        assert result["analysis"]["input_length"] == 30
        assert result["analysis"]["has_history"] is False
