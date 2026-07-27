"""
πX Enterprise Agent OS API — /api/v1/agents

Endpoints:
  POST   /agents/create          → Create agent from profile
  GET    /agents                  → List agents
  GET    /agents/{id}             → Get agent details
  POST   /agents/{id}/execute     → Execute query on agent
  POST   /agents/{id}/pause       → Pause agent
  POST   /agents/{id}/resume       → Resume agent
  POST   /agents/{id}/stop        → Stop agent
  GET    /agents/{id}/memory       → Get agent memory
  GET    /agents/{id}/performance  → Get agent performance
  GET    /agents/tools            → List available tools
  GET    /agents/types             → List agent types for industry
  POST   /agents/orchestrate      → Multi-agent orchestration
  GET    /agents/{id}/evaluations → Get evaluation records
"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Query

agent_os_router = APIRouter(prefix="/agents", tags=["Agent OS"])

# Lazy singletons
_manager = None
_supervisor = None
_eval_loop = None


def _get_manager():
    global _manager
    if _manager is None:
        from packages.cognitive_kernel.agent_os.agent_manager import AgentManager
        _manager = AgentManager()
    return _manager


def _get_supervisor():
    global _supervisor
    if _supervisor is None:
        from packages.cognitive_kernel.agent_os.agent_supervisor import AgentSupervisor
        _supervisor = AgentSupervisor(manager=_get_manager())
    return _supervisor


def _get_eval_loop():
    global _eval_loop
    if _eval_loop is None:
        from packages.cognitive_kernel.agent_os.evaluation_loop import AgentEvaluationLoop
        _eval_loop = AgentEvaluationLoop(memory=_get_manager().memory)
    return _eval_loop


def _mock_profile(org_id: str) -> dict[str, Any]:
    return {
        "org_id": org_id,
        "industry": "retail",
        "company_identity": {"name": "Organization"},
        "kpis": [{"name": "Revenue"}, {"name": "Sell-out"}],
        "ontology": {"entities": {"customer": {}, "product": {}, "store": {}}},
    }


@agent_os_router.post("/create")
async def create_agent(body: dict = None) -> dict:
    mgr = _get_manager()
    from packages.cognitive_kernel.agent_os.agent_registry import AgentType
    agent_type = AgentType(body.get("agent_type", "sales_intelligence"))
    profile_ctx = body.get("profile_context", _mock_profile(body.get("org_id", "")))
    agent = mgr.create_agent_from_profile(
        org_id=body.get("org_id", ""),
        profile_context=profile_ctx,
        agent_type=agent_type,
        custom_label=body.get("label"),
    )
    return {
        "agent_id": agent.id,
        "type": agent.spec.type.value,
        "label": agent.spec.label,
        "industry": agent.spec.industry,
        "role": agent.spec.role,
        "status": agent.status.value,
        "tools": agent.spec.tools,
        "kpis_monitored": agent.spec.kpis_monitored,
        "goals": agent.spec.goals,
    }


@agent_os_router.get("")
async def list_agents(org_id: str = Query(...)) -> dict:
    mgr = _get_manager()
    agents = mgr.registry.list_instances(org_id)
    return {
        "agents": [
            {
                "agent_id": a.id,
                "type": a.spec.type.value,
                "label": a.spec.label,
                "purpose": a.spec.purpose,
                "status": a.status.value,
                "conversations": a.conversation_count,
                "decisions": a.decision_count,
                "performance_score": a.performance_score,
                "last_active": a.last_active,
            }
            for a in agents
        ]
    }


@agent_os_router.get("/types")
async def list_types(industry: str = Query("generic")) -> dict:
    from packages.cognitive_kernel.agent_os.agent_registry import AgentRegistry
    registry = AgentRegistry()
    specs = registry.get_types_for_industry(industry)
    return {
        "types": [
            {
                "type": s.type.value,
                "label": s.label,
                "purpose": s.purpose,
                "industry": s.industry,
                "role": s.role,
                "tools": s.tools,
                "kpis_monitored": s.kpis_monitored,
                "goals": s.goals,
            }
            for s in specs
        ]
    }


@agent_os_router.get("/tools")
async def list_tools() -> dict:
    from packages.cognitive_kernel.agent_os.tool_registry import ToolRegistry
    registry = ToolRegistry()
    return {
        "tools": [
            t.to_dict() for t in registry.all_tools()
        ]
    }


@agent_os_router.get("/{agent_id}")
async def get_agent(agent_id: str) -> dict:
    mgr = _get_manager()
    inst = mgr.registry.get_instance(agent_id)
    if not inst:
        raise HTTPException(status_code=404, detail="Agent not found")
    return {
        "agent_id": inst.id,
        "type": inst.spec.type.value,
        "label": inst.spec.label,
        "purpose": inst.spec.purpose,
        "industry": inst.spec.industry,
        "role": inst.spec.role,
        "tools": inst.spec.tools,
        "knowledge_access": inst.spec.knowledge_access,
        "kpis_monitored": inst.spec.kpis_monitored,
        "goals": inst.spec.goals,
        "status": inst.status.value,
        "conversations": inst.conversation_count,
        "decisions": inst.decision_count,
        "performance_score": inst.performance_score,
    }


@agent_os_router.post("/{agent_id}/execute")
async def execute_agent(agent_id: str, body: dict = None) -> dict:
    mgr = _get_manager()
    result = mgr.execute(
        agent_id=agent_id,
        query=body.get("query", ""),
        profile_context=body.get("profile_context"),
    )
    return {
        "agent_id": result.agent_id,
        "response": result.response,
        "tools_used": result.tools_used,
        "decisions_created": result.decisions_created,
        "confidence": result.confidence,
        "execution_time_ms": result.execution_time_ms,
        "error": result.error,
    }


@agent_os_router.post("/{agent_id}/pause")
async def pause_agent(agent_id: str) -> dict:
    mgr = _get_manager()
    success = mgr.pause(agent_id)
    return {"paused": success}


@agent_os_router.post("/{agent_id}/resume")
async def resume_agent(agent_id: str) -> dict:
    mgr = _get_manager()
    success = mgr.resume(agent_id)
    return {"resumed": success}


@agent_os_router.post("/{agent_id}/stop")
async def stop_agent(agent_id: str) -> dict:
    mgr = _get_manager()
    success = mgr.stop(agent_id)
    return {"stopped": success}


@agent_os_router.get("/{agent_id}/memory")
async def get_memory(agent_id: str, memory_type: str = Query(None), limit: int = Query(10)) -> dict:
    mgr = _get_manager()
    entries = mgr.get_memory(agent_id, memory_type, limit)
    return {"agent_id": agent_id, "memory": entries}


@agent_os_router.get("/{agent_id}/performance")
async def get_performance(agent_id: str) -> dict:
    mgr = _get_manager()
    perf = mgr.get_performance(agent_id)
    eval_loop = _get_eval_loop()
    perf["evaluation"] = eval_loop.get_performance_trend(agent_id)
    return perf


@agent_os_router.get("/{agent_id}/evaluations")
async def get_evaluations(agent_id: str, limit: int = Query(50)) -> dict:
    eval_loop = _get_eval_loop()
    return {"agent_id": agent_id, "evaluations": eval_loop.get_all_records(agent_id, limit)}


@agent_os_router.post("/orchestrate")
async def orchestrate(body: dict = None) -> dict:
    sup = _get_supervisor()
    mgr = _get_manager()
    org_id = body.get("org_id", "")
    query = body.get("query", "")
    profile_ctx = body.get("profile_context", _mock_profile(org_id))
    agents = mgr.registry.list_instances(org_id)
    result = sup.orchestrate(org_id, query, agents, profile_ctx)
    return {
        "query": result.query,
        "synthesized_response": result.synthesized_response,
        "confidence": result.confidence,
        "contributing_agents": result.contributing_agents,
        "delegated_tasks": [
            {
                "agent_id": t.agent_id,
                "agent_label": t.agent_label,
                "query": t.query,
                "response": t.result.response if t.result else None,
                "tools_used": t.result.tools_used if t.result else [],
                "error": t.result.error if t.result else None,
            }
            for t in result.delegated_tasks
        ],
    }
