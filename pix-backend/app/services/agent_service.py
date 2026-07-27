from __future__ import annotations

import logging

from app.agents.graph import AgentGraph
from app.core.context import org_id_ctx
from packages.cognitive-kernel.memory-engine import PersistentMemory
from app.schemas.agent import AgentRequest, AgentStep, WorkflowResult

logger = logging.getLogger("pix.services.agent")

_GRAPH_CACHE: dict[int, AgentGraph] = {}


class AgentOrchestratorService:
    def __init__(self, memory_service: PersistentMemory | None = None, org_id: str | None = None) -> None:
        self.memory_service = memory_service
        self.org_id = org_id
        self.graph = self._get_cached_graph(memory_service)

    @staticmethod
    def _get_cached_graph(memory_service: PersistentMemory | None) -> AgentGraph:
        mem_id = id(memory_service) if memory_service else 0
        if mem_id not in _GRAPH_CACHE:
            graph = AgentGraph(memory_service=memory_service)
            graph.build()
            _GRAPH_CACHE[mem_id] = graph
        return _GRAPH_CACHE[mem_id]

    async def execute(self, request: AgentRequest) -> WorkflowResult:
        token = None
        if self.org_id is not None:
            token = org_id_ctx.set(self.org_id)
        try:
            result = await self.graph.run(
                request=request.input,
                thread_id=request.thread_id,
            )

            steps = [
                AgentStep(
                    node=step["node"],
                    output=step.get("status", "unknown"),
                    duration_ms=step.get("duration_ms", 0),
                )
                for step in result.get("nodes_executed", [])
            ]

            if result.get("status") == "failed":
                return WorkflowResult(
                    success=False,
                    output=result.get("error", "Unknown error"),
                    steps=steps,
                    thread_id=result.get("request_id"),
                    error=result.get("error"),
                )

            response = (
                result.get("final_response")
                or self._build_summary(result)
                or "Workflow completed. No output generated."
            )

            return WorkflowResult(
                success=True,
                output=response,
                steps=steps,
                thread_id=result.get("request_id"),
            )

        except Exception as exc:
            logger.exception("Agent orchestration failed")
            return WorkflowResult(
                success=False,
                output=str(exc),
                error=str(exc),
                thread_id=request.thread_id,
            )
        finally:
            if token is not None:
                org_id_ctx.reset(token)

    @staticmethod
    def _build_summary(result: dict) -> str | None:
        parts: list[str] = []
        if result.get("planner_result"):
            p = result["planner_result"]
            parts.append(f"**Plan:** {p.get('plan', '')[:200]}")
        if result.get("researcher_result"):
            r = result["researcher_result"]
            parts.append(f"**Research:** {r.get('summary', '')[:200]}")
        if result.get("coder_result"):
            c = result["coder_result"]
            files = [f["path"] for f in c.get("files", [])]
            parts.append(f"**Generated:** {', '.join(files) if files else c.get('explanation', '')[:200]}")
        if result.get("reviewer_result"):
            rv = result["reviewer_result"]
            parts.append(f"**Review:** Score {rv.get('score', 'N/A')}/100 — {'Approved' if rv.get('approved', True) else 'Changes needed'}")
        if result.get("tester_result"):
            t = result["tester_result"]
            n = len(t.get("test_files", []))
            parts.append(f"**Tests:** {n} test file(s)")
        if result.get("documenter_result"):
            d = result["documenter_result"]
            n = len(d.get("files", []))
            parts.append(f"**Docs:** {n} document(s)")
        if result.get("devops_result"):
            dv = result["devops_result"]
            n = len(dv.get("config_files", []))
            parts.append(f"**DevOps:** {n} config file(s)")

        return "\n".join(parts) if parts else None
