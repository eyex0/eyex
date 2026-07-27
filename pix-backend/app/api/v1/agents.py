from __future__ import annotations

import logging

from fastapi import APIRouter, Depends

from app.schemas.agent import AgentRequest, WorkflowResult
from app.services.agent_service import AgentOrchestratorService

logger = logging.getLogger("pix.api.agents")

agents_router = APIRouter(prefix="/agents", tags=["Agents"])


async def get_agent_service() -> AgentOrchestratorService:
    return AgentOrchestratorService()


@agents_router.post("/execute", response_model=WorkflowResult)
async def execute_agent(
    body: AgentRequest,
    service: AgentOrchestratorService = Depends(get_agent_service),
) -> WorkflowResult:
    """Execute a request through the full multi-agent LangGraph workflow.

    The Supervisor classifies the request and routes dynamically through
    planner → researcher → coder → reviewer+tester (parallel) → documenter → devops.
    """
    result = await service.execute(body)
    logger.info(
        "Agent execution completed: success=%s, steps=%d, thread=%s",
        result.success, len(result.steps), result.thread_id,
    )
    return result


@agents_router.post("/classify", response_model=dict)
async def classify_request(
    body: AgentRequest,
    service: AgentOrchestratorService = Depends(get_agent_service),
) -> dict:
    """Classify a request without executing the full workflow."""
    from app.agents.supervisor import SupervisorAgent

    supervisor = SupervisorAgent()
    analysis = await supervisor.analyze(body.input)
    return {
        "request": body.input,
        "classification": analysis["classification"],
        "analysis": analysis["analysis"],
    }
