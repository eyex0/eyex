from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.agents.devops import DevOpsAgent, DevOpsOutput, ConfigFile, create_devops_agent


def test_devops_schema():
    output = DevOpsOutput(
        config_files=[ConfigFile(path="Dockerfile", content="FROM python:3.12", type="docker")],
        deployment_steps=["Build image", "Push to registry"],
        infrastructure_requirements=["Docker host"],
        cicd_pipeline="GitHub Actions build and deploy",
        monitoring_setup=["Prometheus metrics"],
        security_notes=["Use non-root user"],
        estimated_resources="2GB RAM, 1 CPU",
    )
    assert len(output.config_files) == 1
    assert output.config_files[0].type == "docker"


@pytest.mark.asyncio
async def test_devops_fallback():
    agent = create_devops_agent()
    mock_llm = AsyncMock()
    structured_chain = AsyncMock()
    structured_chain.ainvoke.side_effect = Exception("LLM error")
    mock_llm.with_structured_output = MagicMock(return_value=structured_chain)
    mock_llm.bind_tools = MagicMock(return_value=structured_chain)
    agent.llm = mock_llm
    result = await agent.execute("Set up CI/CD pipeline", session_id="test")
    assert isinstance(result, DevOpsOutput)
    assert len(result.config_files) == 0
