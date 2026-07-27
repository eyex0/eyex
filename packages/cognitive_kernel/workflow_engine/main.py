from __future__ import annotations

import asyncio
import logging
import time
import uuid
from typing import Any, Literal

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph
from typing_extensions import TypedDict

from packages.cognitive-kernel.agent-runtime import (
    NodeAgent,
    AgentMemory,
    create_analyst_agent,
    create_ceo_agent,
    create_cfo_agent,
    create_coding_agent,
    create_coo_agent,
    create_devops_agent,
    create_documentation_agent,
    create_planner_agent,
    create_research_agent,
    create_reviewer_agent,
    create_risk_agent,
    create_strategist_agent,
    SupervisorAgent,
    create_testing_agent,
)
from packages.cognitive-kernel.decision-engine import create_decision_agent

logger = logging.getLogger("pix.agents.graph")

MAX_WORKFLOW_ITERATIONS = 5

_GRAPH_MEMORY: Any = None


def _get_graph_memory():
    return _GRAPH_MEMORY


def _set_graph_memory(mem):
    global _GRAPH_MEMORY
    _GRAPH_MEMORY = mem


class AgentWorkflowState(TypedDict):
    request: str
    request_id: str
    classification: dict[str, Any] | None
    planner_result: dict[str, Any] | None
    researcher_result: dict[str, Any] | None
    coder_result: dict[str, Any] | None
    reviewer_result: dict[str, Any] | None
    tester_result: dict[str, Any] | None
    documenter_result: dict[str, Any] | None
    devops_result: dict[str, Any] | None
    analyst_result: dict[str, Any] | None
    strategist_result: dict[str, Any] | None
    decision_result: dict[str, Any] | None
    ceo_result: dict[str, Any] | None
    cfo_result: dict[str, Any] | None
    coo_result: dict[str, Any] | None
    risk_result: dict[str, Any] | None
    final_response: str | None
    error: str | None
    nodes_executed: list[dict[str, Any]]
    status: Literal["running", "completed", "failed", "pending"]
    iteration_count: int


def _rid(state: AgentWorkflowState) -> str:
    return state.get("request_id", "?")


def _record_node(
    state: AgentWorkflowState,
    node_name: str,
    status: str,
    duration_ms: float,
) -> list[dict[str, Any]]:
    prev = state.get("nodes_executed", [])
    return prev + [
        {"node": node_name, "status": status, "duration_ms": round(duration_ms, 2), "started_at": time.time()}
    ]


def _run_agent_node(agent_factory, result_key: str, memory_service=None, settings=None):
    async def node_fn(state: AgentWorkflowState) -> dict[str, Any]:
        rid = _rid(state)
        start = time.perf_counter()
        kw = {}
        if memory_service is not None:
            kw["memory_service"] = memory_service
        agent = agent_factory(settings=settings, **kw)
        try:
            request = state.get("request", "")
            context_parts = [request]
            prev = state.get(f"{result_key.replace('_result', '')}_result")
            if prev:
                context_parts.append(f"\nPrevious output:\n{prev.get('output', prev.get('summary', ''))}")
            input_text = "\n".join(context_parts)

            logger.info("[%s] %s node STARTED — input: %d chars", rid, result_key, len(input_text))
            output = await agent.execute(input_text, session_id=state.get("request_id"))
            elapsed = time.perf_counter() - start
            logger.info("[%s] %s node COMPLETED in %.0fms", rid, result_key, elapsed * 1000)

            return {
                result_key: output.model_dump(),
                "nodes_executed": _record_node(state, result_key.replace("_result", ""), "completed", elapsed),
                "status": "running",
                "iteration_count": state.get("iteration_count", 0),
            }
        except Exception as exc:
            elapsed = time.perf_counter() - start
            logger.error("[%s] %s node FAILED after %.0fms: %s", rid, result_key, elapsed * 1000, exc)
            return {
                result_key: {"error": str(exc), "success": False},
                "nodes_executed": _record_node(state, result_key.replace("_result", ""), "failed", elapsed),
                "error": str(exc),
                "status": "failed",
            }

    node_fn.__name__ = f"{result_key}_node"
    return node_fn


async def _supervisor_node(state: AgentWorkflowState, settings: Any) -> dict[str, Any]:
    rid = _rid(state)
    start = time.perf_counter()
    supervisor = SupervisorAgent(settings=settings)
    session_id = state.get("request_id")
    try:
        if session_id:
            mem = _get_graph_memory()
            if mem:
                await mem.get_conversation(session_id, limit=20)
        analysis = await supervisor.analyze(state["request"])
        classification = analysis["classification"]
        elapsed = time.perf_counter() - start
        logger.info("[%s] Supervisor classified as '%s' (%.1f%%)", rid, classification["category"], classification["confidence"] * 100)

        return {
            "classification": classification,
            "nodes_executed": _record_node(state, "supervisor", "completed", elapsed),
            "status": "running",
            "iteration_count": state.get("iteration_count", 0) + 1,
        }
    except Exception as exc:
        elapsed = time.perf_counter() - start
        logger.error("[%s] Supervisor failed: %s", rid, exc)
        return {
            "error": str(exc),
            "nodes_executed": _record_node(state, "supervisor", "failed", elapsed),
            "status": "failed",
        }


async def _responder_node(state: AgentWorkflowState) -> dict[str, Any]:
    rid = _rid(state)
    start = time.perf_counter()
    try:
        parts: list[str] = []
        cat = state.get("classification", {}).get("category", "general")

        if cat == "executive":
            if state.get("ceo_result"):
                c = state["ceo_result"]
                parts.append("# 🏢 Executive Team Report\n")
                parts.append("## CEO Strategic Vision\n")
                parts.append(f"**Vision:** {c.get('strategic_vision', '')}")
                if c.get("key_priorities"):
                    parts.append("### Key Priorities\n" + "\n".join(f"{i+1}. {p}" for i, p in enumerate(c["key_priorities"])))
                if c.get("growth_initiatives"):
                    parts.append("### Growth Initiatives\n" + "\n".join(f"- {g}" for g in c["growth_initiatives"]))
                if c.get("confidence_score") is not None:
                    parts.append(f"\n**Confidence:** {c['confidence_score']*100:.0f}%")

            if state.get("cfo_result"):
                f = state["cfo_result"]
                parts.append("\n## CFO Financial Analysis\n")
                parts.append(f"**Health:** {f.get('financial_health_assessment', '')}")
                if f.get("revenue_analysis"):
                    parts.append(f"**Revenue:** {f['revenue_analysis']}")
                if f.get("cost_optimization"):
                    parts.append("### Cost Optimization\n" + "\n".join(f"- {c}" for c in f["cost_optimization"]))
                if f.get("investment_priorities"):
                    parts.append("### Investment Priorities\n" + "\n".join(f"- {i}" for i in f["investment_priorities"]))

            if state.get("coo_result"):
                o = state["coo_result"]
                parts.append("\n## COO Operational Analysis\n")
                parts.append(f"**Efficiency:** {o.get('operational_efficiency', '')}")
                if o.get("process_improvements"):
                    parts.append("### Process Improvements\n" + "\n".join(f"- {p}" for p in o["process_improvements"]))
                if o.get("scalability_assessment"):
                    parts.append(f"**Scalability:** {o['scalability_assessment']}")

            if state.get("risk_result"):
                r = state["risk_result"]
                parts.append("\n## Risk Assessment\n")
                score = r.get("overall_risk_score", 0)
                parts.append(f"**Overall Risk Score:** {score*100:.0f}%")
                if r.get("identified_risks"):
                    parts.append("### Identified Risks\n")
                    for risk in r["identified_risks"]:
                        sev = risk.get("severity", "medium")
                        parts.append(f"- [{sev.upper()}] {risk.get('description', '')}")
                if r.get("opportunities"):
                    parts.append("### Opportunities\n" + "\n".join(f"- {o.get('description','')} (confidence: {o.get('confidence','N/A')})" for o in r["opportunities"]))
                if r.get("mitigation_strategies"):
                    parts.append("### Mitigation\n" + "\n".join(f"- {m}" for m in r["mitigation_strategies"]))
                if r.get("early_warnings"):
                    parts.append("### ⚠️ Early Warnings\n" + "\n".join(f"- {w}" for w in r["early_warnings"]))

        elif cat == "intelligence":
            if state.get("analyst_result"):
                a = state["analyst_result"]
                parts.append("## Business Analysis\n")
                parts.append(f"**Summary:** {a.get('summary', '')}")
                if a.get("key_findings"):
                    parts.append("### Key Findings\n" + "\n".join(f"- {f}" for f in a["key_findings"]))
                if a.get("trends"):
                    parts.append("### Trends\n" + "\n".join(f"- {t.get('metric','')}: {t.get('direction','')} ({t.get('magnitude','')})" for t in a["trends"]))

            if state.get("strategist_result"):
                s = state["strategist_result"]
                parts.append("\n## Strategic Recommendations\n")
                parts.append(f"**Direction:** {s.get('strategic_direction', '')}")
                for r in s.get("recommendations", []):
                    if isinstance(r, dict):
                        parts.append(f"\n### [{r.get('priority','medium').upper()}] {r.get('action','')}")
                        parts.append(f"**Why:** {r.get('rationale', '')}")
                        parts.append(f"**Impact:** {r.get('expected_impact', '')}")
                        parts.append(f"**Effort:** {r.get('effort','medium')} | **Timeline:** {r.get('timeline','medium-term')}")

            if state.get("decision_result"):
                d = state["decision_result"]
                parts.append("\n## Executive Decisions\n")
                parts.append(f"**{d.get('executive_summary', '')}**")
                if d.get("key_insights"):
                    parts.append("### Key Insights\n" + "\n".join(f"- {i}" for i in d["key_insights"]))
                if d.get("next_steps"):
                    parts.append("### Next Steps\n" + "\n".join(f"{i+1}. {s}" for i, s in enumerate(d["next_steps"])))
                if d.get("reasoning_chain"):
                    parts.append("### Reasoning\n" + "\n".join(f"{i+1}. {s}" for i, s in enumerate(d["reasoning_chain"])))
                if d.get("confidence") is not None:
                    parts.append(f"\n**Overall Confidence:** {d['confidence']*100:.0f}%")

        elif cat == "planning" and state.get("planner_result"):
            p = state["planner_result"]
            parts.append(f"## Plan\n{p.get('plan', '')}")
            steps = p.get("steps", [])
            if steps:
                parts.append("### Steps\n" + "\n".join(f"{i+1}. {s}" for i, s in enumerate(steps)))

        elif state.get("researcher_result"):
            r = state["researcher_result"]
            parts.append(f"## Research\n{r.get('summary', '')}")

        elif state.get("coder_result"):
            c = state["coder_result"]
            parts.append(f"## Code Generated\n{c.get('explanation', '')}")
            for f in c.get("files", []):
                parts.append(f"- `{f['path']}` ({f.get('language', 'code')})")

            if state.get("reviewer_result"):
                rv = state["reviewer_result"]
                score = rv.get("score", "N/A")
                parts.append(f"\n## Review (Score: {score}/100)")
                if rv.get("issues"):
                    for issue in rv["issues"]:
                        parts.append(f"- [{issue.get('severity','info')}] {issue.get('description','')}")

            if state.get("tester_result"):
                t = state["tester_result"]
                parts.append(f"\n## Tests\n{t.get('test_strategy', '')}")
                for tf in t.get("test_files", []):
                    parts.append(f"- `{tf['path']}` ({tf.get('framework', 'unknown')})")

            if state.get("documenter_result"):
                d = state["documenter_result"]
                parts.append(f"\n## Documentation\n{d.get('summary', '')}")

            if state.get("devops_result"):
                dv = state["devops_result"]
                parts.append(f"\n## DevOps\n{dv.get('cicd_pipeline', '')}")

        else:
            reasoning = state.get("classification", {}).get("reasoning", "")
            parts.append(f"**Analysis:** {reasoning}" if reasoning else "Request processed.")

        if not parts:
            parts.append("Request processed. No specific output to display.")

        elapsed = time.perf_counter() - start
        return {
            "final_response": "\n\n---\n\n".join(parts),
            "nodes_executed": _record_node(state, "responder", "completed", elapsed),
            "status": "completed",
        }
    except Exception as exc:
        elapsed = time.perf_counter() - start
        logger.error("[%s] Responder failed: %s", rid, exc)
        return {
            "error": str(exc),
            "nodes_executed": _record_node(state, "responder", "failed", elapsed),
            "status": "failed",
        }


def route_from_supervisor(state: AgentWorkflowState) -> str:
    if state.get("error") or state.get("status") == "failed":
        return END
    cat = state.get("classification", {}).get("category", "general")
    iteration = state.get("iteration_count", 0)
    if iteration > MAX_WORKFLOW_ITERATIONS:
        return "responder"

    routing = {
        "executive": "ceo",
        "intelligence": "analyst",
        "planning": "planner",
        "research": "researcher",
        "coding": "coder",
        "general": "responder",
    }
    return routing.get(cat, "responder")


def route_from_analyst(state: AgentWorkflowState) -> str:
    if state.get("analyst_result"):
        return "strategist"
    return "responder"


def route_from_strategist(state: AgentWorkflowState) -> str:
    if state.get("strategist_result"):
        return "decision"
    return "responder"


def route_from_decision(state: AgentWorkflowState) -> str:
    return "responder"


def route_from_ceo(state: AgentWorkflowState) -> str:
    if state.get("ceo_result"):
        return "cfo"
    return "responder"


def route_from_cfo(state: AgentWorkflowState) -> str:
    if state.get("cfo_result"):
        return "coo"
    return "responder"


def route_from_coo(state: AgentWorkflowState) -> str:
    if state.get("coo_result"):
        return "risk"
    return "responder"


def route_from_risk(state: AgentWorkflowState) -> str:
    return "responder"


def route_from_planner(state: AgentWorkflowState) -> str:
    plan = state.get("planner_result")
    if not plan:
        return "responder"
    steps = plan.get("step_details", [])
    assigned_agents = {s.get("agent", "") for s in steps}
    if "researcher" in assigned_agents:
        return "researcher"
    if "coder" in assigned_agents:
        return "coder"
    return "responder"


def route_from_researcher(state: AgentWorkflowState) -> str:
    research = state.get("researcher_result")
    if research and research.get("recommendations"):
        return "coder"
    return "responder"


def route_from_coder(state: AgentWorkflowState) -> list[str]:
    return ["reviewer", "tester"]


def route_from_quality_gate(state: AgentWorkflowState) -> str:
    # Prefer the decision materialized by the quality gate node.
    approved = state.get("approved")
    if approved is None:
        review = state.get("reviewer_result") or {}
        approved = review.get("approved", True)
        if not isinstance(approved, bool):
            approved = True
    iteration = state.get("iteration_count", 0)

    if not approved and iteration < MAX_WORKFLOW_ITERATIONS:
        return "coder"
    return "documenter"


def route_from_documenter(state: AgentWorkflowState) -> str:
    return "devops"


def route_from_devops(state: AgentWorkflowState) -> str:
    return "responder"


class AgentGraph:
    def __init__(self, memory_service=None, settings=None) -> None:
        self.graph: CompiledStateGraph | None = None
        self.checkpointer = MemorySaver()
        self.memory_service = memory_service
        self.settings = settings
        _set_graph_memory(memory_service)

    def build(self) -> CompiledStateGraph:
        workflow = StateGraph(AgentWorkflowState)
        ms = self.memory_service
        settings = self.settings

        workflow.add_node("supervisor", lambda state: _supervisor_node(state, settings))
        workflow.add_node("analyst", _run_agent_node(create_analyst_agent, "analyst_result", ms, settings))
        workflow.add_node("strategist", _run_agent_node(create_strategist_agent, "strategist_result", ms, settings))
        workflow.add_node("decision", _run_agent_node(create_decision_agent, "decision_result", ms, settings))
        workflow.add_node("ceo", _run_agent_node(create_ceo_agent, "ceo_result", ms, settings))
        workflow.add_node("cfo", _run_agent_node(create_cfo_agent, "cfo_result", ms, settings))
        workflow.add_node("coo", _run_agent_node(create_coo_agent, "coo_result", ms, settings))
        workflow.add_node("risk", _run_agent_node(create_risk_agent, "risk_result", ms, settings))
        workflow.add_node("planner", _run_agent_node(create_planner_agent, "planner_result", ms, settings))
        workflow.add_node("researcher", _run_agent_node(create_research_agent, "researcher_result", ms, settings))
        workflow.add_node("coder", _run_agent_node(create_coding_agent, "coder_result", ms, settings))
        workflow.add_node("reviewer", _run_agent_node(create_reviewer_agent, "reviewer_result", ms, settings))
        workflow.add_node("tester", _run_agent_node(create_testing_agent, "tester_result", ms, settings))
        workflow.add_node("quality_gate", _quality_gate_node)
        workflow.add_node("documenter", _run_agent_node(create_documentation_agent, "documenter_result", ms, settings))
        workflow.add_node("devops", _run_agent_node(create_devops_agent, "devops_result", ms, settings))
        workflow.add_node("responder", _responder_node)

        workflow.add_edge(START, "supervisor")

        workflow.add_conditional_edges("supervisor", route_from_supervisor, {
            "analyst": "analyst",
            "planner": "planner",
            "researcher": "researcher",
            "coder": "coder",
            "ceo": "ceo",
            "responder": "responder",
            END: END,
        })

        workflow.add_conditional_edges("analyst", route_from_analyst, {
            "strategist": "strategist",
            "responder": "responder",
        })

        workflow.add_conditional_edges("strategist", route_from_strategist, {
            "decision": "decision",
            "responder": "responder",
        })

        workflow.add_conditional_edges("decision", route_from_decision, {
            "responder": "responder",
        })

        workflow.add_conditional_edges("ceo", route_from_ceo, {
            "cfo": "cfo",
            "responder": "responder",
        })

        workflow.add_conditional_edges("cfo", route_from_cfo, {
            "coo": "coo",
            "responder": "responder",
        })

        workflow.add_conditional_edges("coo", route_from_coo, {
            "risk": "risk",
            "responder": "responder",
        })

        workflow.add_conditional_edges("risk", route_from_risk, {
            "responder": "responder",
        })

        workflow.add_conditional_edges("planner", route_from_planner, {
            "researcher": "researcher",
            "coder": "coder",
            "responder": "responder",
        })

        workflow.add_conditional_edges("researcher", route_from_researcher, {
            "coder": "coder",
            "responder": "responder",
        })

        workflow.add_conditional_edges("coder", route_from_coder)

        workflow.add_edge("reviewer", "quality_gate")
        workflow.add_edge("tester", "quality_gate")

        workflow.add_conditional_edges("quality_gate", route_from_quality_gate, {
            "coder": "coder",
            "documenter": "documenter",
        })

        workflow.add_edge("documenter", "devops")
        workflow.add_edge("devops", "responder")
        workflow.add_edge("responder", END)

        self.graph = workflow.compile(checkpointer=self.checkpointer)
        return self.graph

    async def run(
        self,
        request: str,
        thread_id: str | None = None,
    ) -> AgentWorkflowState:
        if not self.graph:
            self.build()

        run_id = thread_id or str(uuid.uuid4())

        initial: AgentWorkflowState = {
            "request": request,
            "request_id": run_id,
            "classification": None,
            "planner_result": None,
            "researcher_result": None,
            "coder_result": None,
            "reviewer_result": None,
            "tester_result": None,
            "documenter_result": None,
            "devops_result": None,
            "analyst_result": None,
            "strategist_result": None,
            "decision_result": None,
            "ceo_result": None,
            "cfo_result": None,
            "coo_result": None,
            "risk_result": None,
            "final_response": None,
            "error": None,
            "nodes_executed": [],
            "status": "pending",
            "iteration_count": 0,
        }

        try:
            config = {"configurable": {"thread_id": run_id}}
            timeout = self.settings.graph_timeout_seconds or 120
            final: AgentWorkflowState = await asyncio.wait_for(
                self.graph.ainvoke(initial, config), timeout=timeout
            )
            logger.info("[%s] Graph completed: status=%s, nodes=%d", run_id, final.get("status"), len(final.get("nodes_executed", [])))
            return final
        except asyncio.TimeoutError:
            logger.error("[%s] Graph execution timed out after %s seconds", run_id, timeout)
            return {
                **initial,
                "status": "failed",
                "error": f"Workflow timed out after {timeout} seconds",
                "nodes_executed": [{"node": "graph", "status": "timeout", "duration_ms": timeout * 1000, "started_at": time.time()}],
            }
        except Exception as exc:
            logger.exception("[%s] Graph execution failed", run_id)
            return {
                **initial,
                "status": "failed",
                "error": str(exc),
                "nodes_executed": [{"node": "graph", "status": "failed", "duration_ms": 0, "started_at": time.time()}],
            }


async def _quality_gate_node(state: AgentWorkflowState) -> dict[str, Any]:
    rid = _rid(state)
    start = time.perf_counter()
    review = state.get("reviewer_result") or {}
    tester = state.get("tester_result") or {}

    raw_approved = review.get("approved")
    approved = raw_approved if isinstance(raw_approved, bool) else True
    score = review.get("score", 75) if review else 75

    logger.info("[%s] Quality gate: approved=%s, score=%s, has_tests=%s", rid, approved, score, bool(tester))
    return {
        "nodes_executed": _record_node(state, "quality_gate", "completed", time.perf_counter() - start),
        "status": "running",
        "iteration_count": state.get("iteration_count", 0),
        "approved": approved,
        "score": score,
    }
