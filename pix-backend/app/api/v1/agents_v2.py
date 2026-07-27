from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from app.agents.coder import create_coding_agent
from app.agents.devops import create_devops_agent
from app.agents.documenter import create_documentation_agent
from app.agents.planner import create_planner_agent
from app.agents.researcher import create_research_agent
from app.agents.reviewer import create_reviewer_agent
from app.agents.tester import create_testing_agent
from app.agents.tools.registry import get_registry
from app.api.dependencies import get_memory_service
from packages.cognitive_kernel.memory_engine import PersistentMemory
from app.config import settings

logger = logging.getLogger("pix.api.agents_v2")

agents_router = APIRouter(prefix="/agents", tags=["Agents"])

_AGENT_FACTORIES: dict[str, callable] = {
    "planner": create_planner_agent,
    "researcher": create_research_agent,
    "coder": create_coding_agent,
    "reviewer": create_reviewer_agent,
    "tester": create_testing_agent,
    "documenter": create_documentation_agent,
    "devops": create_devops_agent,
}


class ToolInfo(BaseModel):
    name: str
    description: str


class AgentInfo(BaseModel):
    role: str
    name: str
    description: str
    tools: list[ToolInfo] = []
    enabled: bool = True


class AgentListResponse(BaseModel):
    agents: list[AgentInfo]


class AgentExecuteRequest(BaseModel):
    input: str
    session_id: str | None = None


class AgentExecuteResponse(BaseModel):
    success: bool
    output: dict[str, Any] | str
    agent_name: str
    error: str | None = None


@agents_router.get("", response_model=AgentListResponse)
async def list_agents() -> AgentListResponse:
    registry = get_registry()
    agents = []

    for role, factory in _AGENT_FACTORIES.items():
        agent = factory(settings)
        tool_names = registry.get_tool_names_for_role(role)
        tools = [
            ToolInfo(name=t.name, description=t.description[:120])
            for t in (registry.get_tool(n) for n in tool_names)
            if t is not None
        ]
        agents.append(AgentInfo(
            role=role,
            name=agent.name,
            description=agent.description,
            tools=tools,
            enabled=True,
        ))

    return AgentListResponse(agents=agents)


@agents_router.get("/{role}", response_model=AgentInfo)
async def get_agent_detail(role: str) -> AgentInfo:
    factory = _AGENT_FACTORIES.get(role)
    if not factory:
        raise HTTPException(status_code=404, detail=f"Agent role '{role}' not found")

    agent = factory(settings)
    registry = get_registry()
    tool_names = registry.get_tool_names_for_role(role)
    tools = [
        ToolInfo(name=t.name, description=t.description[:120])
        for t in (registry.get_tool(n) for n in tool_names)
        if t is not None
    ]

    return AgentInfo(
        role=role,
        name=agent.name,
        description=agent.description,
        tools=tools,
        enabled=True,
    )


@agents_router.post("/{role}/execute", response_model=AgentExecuteResponse)
async def execute_agent_by_role(
    role: str,
    body: AgentExecuteRequest,
    request: Request,
    memory: PersistentMemory = Depends(get_memory_service),
) -> AgentExecuteResponse:
    factory = _AGENT_FACTORIES.get(role)
    if not factory:
        raise HTTPException(status_code=404, detail=f"Agent role '{role}' not found")

    agent = factory(settings, memory_service=memory)
    result = await agent.execute(body.input, session_id=body.session_id)

    return AgentExecuteResponse(
        success=True,
        output=result.model_dump() if isinstance(result, BaseModel) else str(result),
        agent_name=role,
    )
