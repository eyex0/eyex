"""
πX Agent Manager — Create, start/stop, monitor lifecycle, manage permissions.

Integrates with the Agent Factory to generate agents from Intelligence Profile.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from .agent_registry import AgentRegistry, AgentSpec, AgentStatus, AgentType, AgentInstance
from .agent_memory import AgentMemory, MemoryType
from .agent_security import AgentSecurity
from .tool_registry import ToolRegistry


@dataclass
class AgentExecutionContext:
    """Context passed to an agent during execution."""
    agent_id: str
    org_id: str
    query: str
    profile_context: dict[str, Any]
    memory_context: str = ""
    tools_available: list[str] = None
    permissions: dict = None

    def __post_init__(self):
        self.tools_available = self.tools_available or []
        self.permissions = self.permissions or {}


@dataclass
class AgentExecutionResult:
    agent_id: str
    response: str
    tools_used: list[str]
    decisions_created: list[str]
    confidence: float = 0.0
    execution_time_ms: int = 0
    error: str | None = None


class AgentManager:
    """Manages the full lifecycle of AI agents."""

    def __init__(
        self,
        registry: AgentRegistry | None = None,
        memory: AgentMemory | None = None,
        security: AgentSecurity | None = None,
        tools: ToolRegistry | None = None,
    ) -> None:
        self.registry = registry or AgentRegistry()
        self.memory = memory or AgentMemory()
        self.security = security or AgentSecurity()
        self.tools = tools or ToolRegistry()

    def create_agent_from_profile(
        self,
        org_id: str,
        profile_context: dict[str, Any],
        agent_type: AgentType,
        custom_label: str | None = None,
    ) -> AgentInstance:
        """Create an agent customized from the company's Intelligence Profile."""
        spec = self.registry.get_type(agent_type)
        if not spec:
            raise ValueError(f"Unknown agent type: {agent_type}")

        company_name = profile_context.get("company_identity", {}).get("name", "the company")
        industry = profile_context.get("industry", spec.industry)
        kpis = profile_context.get("kpis", [])
        ontology = profile_context.get("ontology", {})

        # Customize the spec with profile data
        customized = AgentSpec(
            type=spec.type,
            label=custom_label or spec.label,
            purpose=spec.purpose,
            industry=industry,
            role=spec.role,
            tools=spec.tools,
            knowledge_access=self._filter_entities(spec.knowledge_access, ontology),
            data_access=spec.data_access,
            kpis_monitored=self._extract_kpi_names(kpis) or spec.kpis_monitored,
            system_prompt_template=spec.system_prompt_template,
            goals=spec.goals,
            policies=spec.policies,
        )

        instance = self.registry.create_instance(customized, org_id)
        self.security.grant(instance.id, org_id, customized)

        # Initialize agent memory with profile context
        self.memory.store(
            agent_id=instance.id,
            org_id=org_id,
            memory_type=MemoryType.LONG_TERM,
            content=f"Company: {company_name} | Industry: {industry} | Role: {spec.role}",
            metadata={"type": "profile_init"},
            importance=1.0,
        )
        self.memory.store(
            agent_id=instance.id,
            org_id=org_id,
            memory_type=MemoryType.LONG_TERM,
            content=f"KPIs monitored: {', '.join(customized.kpis_monitored)}",
            metadata={"type": "kpi_init"},
            importance=0.9,
        )

        return instance

    def create_agents_for_industry(
        self,
        org_id: str,
        profile_context: dict[str, Any],
    ) -> list[AgentInstance]:
        """Create all appropriate agents for a company based on its industry."""
        industry = profile_context.get("industry", "generic")
        specs = self.registry.get_types_for_industry(industry)
        agents = []
        for spec in specs:
            if spec.type == AgentType.CUSTOM:
                continue
            agent = self.create_agent_from_profile(org_id, profile_context, spec.type)
            agents.append(agent)
        return agents

    def execute(
        self,
        agent_id: str,
        query: str,
        profile_context: dict[str, Any] | None = None,
    ) -> AgentExecutionResult:
        """Execute a query on an agent."""
        import time
        start = time.time()

        instance = self.registry.get_instance(agent_id)
        if not instance:
            return AgentExecutionResult(
                agent_id=agent_id, response="", tools_used=[],
                decisions_created=[], error="Agent not found",
            )
        if instance.status != AgentStatus.ACTIVE:
            return AgentExecutionResult(
                agent_id=agent_id, response="", tools_used=[],
                decisions_created=[], error=f"Agent is {instance.status.value}",
            )

        # Build memory context
        memory_ctx = self.memory.get_context(agent_id)

        # Build system prompt
        system_prompt = self._build_system_prompt(instance.spec, profile_context or {})

        # Check permissions for tools
        available_tools = []
        for tool_name in instance.spec.tools:
            if self.security.check_tool_access(agent_id, tool_name):
                available_tools.append(tool_name)

        # Build response (in production, this calls the AI Gateway)
        # For now, produce a structured response
        company_name = (profile_context or {}).get("company_identity", {}).get("name", "the company")
        response = self._generate_response(
            instance.spec, query, system_prompt, memory_ctx, available_tools,
        )

        # Store in short-term memory
        self.memory.store(
            agent_id=agent_id,
            org_id=instance.org_id,
            memory_type=MemoryType.SHORT_TERM,
            content=f"Q: {query}\nA: {response[:200]}",
            metadata={"query": query},
        )

        # Update instance stats
        instance.conversation_count += 1
        instance.last_active = datetime.now(UTC).isoformat()

        elapsed = int((time.time() - start) * 1000)
        return AgentExecutionResult(
            agent_id=agent_id,
            response=response,
            tools_used=available_tools,
            decisions_created=[],
            confidence=0.75,
            execution_time_ms=elapsed,
        )

    def pause(self, agent_id: str) -> bool:
        inst = self.registry.get_instance(agent_id)
        if inst:
            self.registry.update_status(agent_id, AgentStatus.PAUSED)
            return True
        return False

    def resume(self, agent_id: str) -> bool:
        inst = self.registry.get_instance(agent_id)
        if inst:
            self.registry.update_status(agent_id, AgentStatus.ACTIVE)
            return True
        return False

    def stop(self, agent_id: str) -> bool:
        inst = self.registry.get_instance(agent_id)
        if inst:
            self.registry.update_status(agent_id, AgentStatus.STOPPED)
            return True
        return False

    def get_memory(self, agent_id: str, memory_type: str | None = None, limit: int = 10) -> list[dict]:
        mt = MemoryType(memory_type) if memory_type else None
        entries = self.memory.retrieve(agent_id, mt, limit=limit)
        return [e.to_dict() for e in entries]

    def get_performance(self, agent_id: str) -> dict[str, Any]:
        inst = self.registry.get_instance(agent_id)
        if not inst:
            return {}
        stats = self.memory.get_stats(agent_id)
        return {
            "agent_id": agent_id,
            "status": inst.status.value,
            "conversations": inst.conversation_count,
            "decisions": inst.decision_count,
            "performance_score": inst.performance_score,
            "memory_stats": stats,
            "last_active": inst.last_active,
        }

    def _build_system_prompt(self, spec: AgentSpec, profile_context: dict[str, Any]) -> str:
        company_name = profile_context.get("company_identity", {}).get("name", "the company")
        industry = profile_context.get("industry", spec.industry)
        kpis = spec.kpis_monitored or [k.get("name", "") for k in profile_context.get("kpis", []) if isinstance(k, dict)]
        entities = spec.knowledge_access if spec.knowledge_access != ["*"] else list(
            profile_context.get("ontology", {}).get("entities", {}).keys()
        ) if isinstance(profile_context.get("ontology"), dict) else []

        return spec.system_prompt_template.format(
            label=spec.label,
            company_name=company_name,
            industry=industry,
            goals=", ".join(spec.goals),
            kpis=", ".join(kpis),
            entities=", ".join(entities[:5]) if entities else "all",
        )

    def _generate_response(
        self, spec: AgentSpec, query: str, system_prompt: str, memory_ctx: str, tools: list[str],
    ) -> str:
        """Generate a response — in production, calls AI Gateway."""
        return (
            f"[{spec.label}] Based on my analysis as your {spec.label}:\n\n"
            f"Query: {query}\n\n"
            f"I'm monitoring: {', '.join(spec.kpis_monitored)}\n"
            f"Tools available: {', '.join(tools)}\n"
            f"Goals: {'; '.join(spec.goals)}\n\n"
            f"(Production: this response would be generated by the AI Gateway using "
            f"the system prompt with company context and tool results)"
        )

    def _filter_entities(self, entities: list[str], ontology: dict) -> list[str]:
        if "*" in entities:
            if isinstance(ontology, dict):
                return list(ontology.get("entities", {}).keys())
            return entities
        return entities

    def _extract_kpi_names(self, kpis: list) -> list[str]:
        return [k.get("name", "") for k in kpis if isinstance(k, dict)]
