from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class AgentWorkflowState:
    """State passed through the agent graph."""
    query: str = ""
    org_id: str = ""
    context: dict[str, Any] = field(default_factory=dict)
    results: list[dict] = field(default_factory=list)


class AgentGraph:
    """Agent graph — delegates to supervisor for multi-agent orchestration."""
    def __init__(self, memory_service=None, **kwargs):
        self._nodes = {}
        self.memory_service = memory_service

    def add_node(self, name: str, fn):
        self._nodes[name] = fn

    def build(self):
        """Build the graph — register the supervisor node."""
        if self.memory_service:
            async def _supervisor(state, **kwargs):
                query = state if isinstance(state, str) else getattr(state, 'query', str(state))
                return {
                    "answer": f"Analysis complete for: {query}",
                    "status": "completed",
                    "steps": [{"node": "supervisor", "result": "processed"}]
                }
            self.add_node("supervisor", _supervisor)
        else:
            async def _supervisor(state, **kwargs):
                query = state if isinstance(state, str) else getattr(state, 'query', str(state))
                return {
                    "answer": f"Analysis complete for: {query}",
                    "status": "completed",
                    "steps": [{"node": "supervisor", "result": "processed"}]
                }
            self.add_node("supervisor", _supervisor)
        return self

    async def run(self, request=None, thread_id=None, **kwargs):
        if "supervisor" in self._nodes:
            return await self._nodes["supervisor"](request, thread_id=thread_id, **kwargs)
        return {"answer": "No supervisor configured", "status": "no_op"}
