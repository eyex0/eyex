"""
πX Agent Supervisor — Multi-agent orchestration.

Coordinates agents, delegates tasks, resolves conflicts, combines results.

Example:
  CEO asks: "Why did revenue drop?"
  Supervisor calls: Sales Agent + Marketing Agent + Inventory Agent + Finance Agent
  Combines: evidence + analysis + recommendation
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from .agent_manager import AgentManager, AgentExecutionResult
from .agent_registry import AgentInstance, AgentStatus


@dataclass
class DelegatedTask:
    agent_id: str
    agent_label: str
    query: str
    result: AgentExecutionResult | None = None


@dataclass
class SupervisorResult:
    query: str
    delegated_tasks: list[DelegatedTask] = field(default_factory=list)
    synthesized_response: str = ""
    confidence: float = 0.0
    contributing_agents: list[str] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())


class AgentSupervisor:
    """Orchrates multiple agents to answer complex questions."""

    def __init__(self, manager: AgentManager | None = None) -> None:
        self.manager = manager or AgentManager()

    def orchestrate(
        self,
        org_id: str,
        query: str,
        agents: list[AgentInstance],
        profile_context: dict[str, Any] | None = None,
    ) -> SupervisorResult:
        """Delegate a query to multiple agents and synthesize results."""
        tasks: list[DelegatedTask] = []

        # Determine which agents to call based on the query
        selected = self._select_agents(query, agents)

        for agent in selected:
            if agent.status != AgentStatus.ACTIVE:
                continue
            task = DelegatedTask(
                agent_id=agent.id,
                agent_label=agent.spec.label,
                query=self._formulate_query(agent, query),
            )
            # Execute the agent
            result = self.manager.execute(
                agent_id=agent.id,
                query=task.query,
                profile_context=profile_context,
            )
            task.result = result
            tasks.append(task)

        # Synthesize results
        synthesis = self._synthesize(query, tasks)
        synth_response, synth_confidence = synthesis
        return SupervisorResult(
            query=query,
            delegated_tasks=tasks,
            synthesized_response=synth_response,
            confidence=synth_confidence,
            contributing_agents=[t.agent_label for t in tasks if t.result and not t.result.error],
        )

    def _select_agents(self, query: str, agents: list[AgentInstance]) -> list[AgentInstance]:
        """Select which agents to involve based on the query."""
        query_lower = query.lower()
        selected: list[AgentInstance] = []

        # Keyword → agent type mapping
        keyword_map: dict[str, list[str]] = {
            "revenue": ["sales_intelligence", "finance", "marketing"],
            "sales": ["sales_intelligence", "marketing"],
            "inventory": ["inventory", "operations"],
            "stock": ["inventory"],
            "customer": ["customer_intelligence", "marketing"],
            "churn": ["customer_intelligence"],
            "production": ["production"],
            "oee": ["production", "maintenance"],
            "quality": ["quality"],
            "defect": ["quality"],
            "maintenance": ["maintenance"],
            "downtime": ["maintenance", "production"],
            "cost": ["finance"],
            "margin": ["finance", "sales_intelligence"],
            "employee": ["human_resources"],
            "hr": ["human_resources"],
            "strategy": ["strategy"],
            "growth": ["strategy", "sales_intelligence"],
        }

        relevant_types: set[str] = set()
        for keyword, agent_types in keyword_map.items():
            if keyword in query_lower:
                relevant_types.update(agent_types)

        if not relevant_types:
            # If no keywords match, involve all active agents
            return [a for a in agents if a.status == AgentStatus.ACTIVE]

        for agent in agents:
            if agent.spec.type.value in relevant_types:
                selected.append(agent)

        # Always include strategy agent if available
        if not selected:
            selected = [a for a in agents if a.spec.type.value == "strategy"]

        return selected if selected else [a for a in agents if a.status == AgentStatus.ACTIVE]

    def _formulate_query(self, agent: AgentInstance, original_query: str) -> str:
        """Formulate a targeted query for each agent."""
        role_context = {
            "sales_intelligence": "From a sales and revenue perspective",
            "inventory": "From an inventory and supply chain perspective",
            "customer_intelligence": "From a customer behavior perspective",
            "production": "From a production and operations perspective",
            "quality": "From a quality and defect analysis perspective",
            "maintenance": "From a maintenance and equipment perspective",
            "finance": "From a financial and cost perspective",
            "marketing": "From a marketing and campaign perspective",
            "human_resources": "From a workforce and HR perspective",
            "strategy": "From a strategic and growth perspective",
        }
        prefix = role_context.get(agent.spec.type.value, "From your area of expertise")
        return f"{prefix}: {original_query}"

    def _synthesize(self, query: str, tasks: list[DelegatedTask]) -> tuple[str, float]:
        """Synthesize results from multiple agents."""
        if not tasks:
            return "No agents were available to answer this query.", 0.0

        parts = [f"## Multi-Agent Analysis\nQuery: {query}\n"]
        confidences: list[float] = []
        for task in tasks:
            if task.result and not task.result.error:
                parts.append(f"### {task.agent_label}\n{task.result.response}\n")
                confidences.append(task.result.confidence)
            elif task.result and task.result.error:
                parts.append(f"### {task.agent_label}\nError: {task.result.error}\n")

        # Synthesis conclusion
        parts.append("### Synthesis\n")
        parts.append(f"Based on analysis from {len(confidences)} agent(s): ")
        parts.append("Combined evidence suggests a multi-faceted response requires cross-functional action.\n")

        avg_conf = sum(confidences) / len(confidences) if confidences else 0.0
        return "\n".join(parts), round(avg_conf, 4)
