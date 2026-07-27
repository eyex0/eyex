"""
πX Agent Factory — Agent Runtime integration.

Generates company-specific agents from the Intelligence Profile.
Instead of hardcoded agent roles, the factory reads the profile's
recommended_agents configuration and creates agents tailored to the company.

Retail → Sales Intelligence Agent, Inventory Agent, Customer Insights Agent
Manufacturing → Production Optimization Agent, Quality Agent, Supply Chain Agent
"""
from __future__ import annotations

import json
import logging
from typing import Any

from packages.cognitive_kernel.intelligence_profile.context_provider import ProfileContextProvider

logger = logging.getLogger("pix.agent_runtime.factory")


class AgentFactory:
    """Creates company-specific AI agents from Intelligence Profile."""

    def __init__(
        self,
        context_provider: ProfileContextProvider | None = None,
    ):
        self.context_provider = context_provider

    async def create_agents(
        self,
        organization_id: str,
        context_provider: ProfileContextProvider | None = None,
    ) -> list[dict]:
        """
        Generate agent configurations from the org's intelligence profile.

        Returns a list of agent configs with:
            - name, role, description, tools, system_prompt (profile-aware)
        """
        provider = context_provider or self.context_provider
        if not provider:
            raise ValueError("ProfileContextProvider is required for AgentFactory")

        profile_ctx = await provider.get_context(organization_id)
        agent_configs = profile_ctx.get("agents", [])

        if not agent_configs:
            logger.info("No agents defined in profile for org %s", organization_id)
            return []

        # Enrich each agent with profile context
        enriched_agents = []
        for config in agent_configs:
            agent = self._build_agent(config, profile_ctx, organization_id)
            enriched_agents.append(agent)

        logger.info("Created %d agents for org %s (industry: %s)",
                     len(enriched_agents), organization_id,
                     profile_ctx.get("company_identity", {}).get("industry"))
        return enriched_agents

    def _build_agent(
        self, config: dict, profile_ctx: dict, organization_id: str
    ) -> dict:
        """Build a single agent configuration with profile context."""
        identity = profile_ctx.get("company_identity", {})
        industry = identity.get("industry", "generic")

        # Build system prompt with company context
        kpi_list = [k["name"] for k in profile_ctx.get("kpis", [])]
        entity_types = [e["entity_type"] for e in profile_ctx.get("ontology", [])]
        glossary_terms = [t["term"] for t in profile_ctx.get("glossary", [])[:10]]

        system_prompt = f"""You are {config.get('name', 'an AI agent')} for a {industry} company.

Your role: {config.get('role', 'Provide intelligent analysis and recommendations')}

Company context:
- Industry: {industry}
- Business model: {identity.get('business_model', 'N/A')}
- Region: {identity.get('region', 'N/A')}

Company KPIs you should monitor: {', '.join(kpi_list) if kpi_list else 'Not defined'}
Company entity types: {', '.join(entity_types) if entity_types else 'Not defined'}
Company terminology: {', '.join(glossary_terms) if glossary_terms else 'Not defined'}

When analyzing data or making recommendations, always reference company-specific
KPIs, terminology, and entity types. Do not use generic business terms when
company-specific terms are available.

You operate within the organization's intelligence profile and must respect
the company's business model and operational context."""

        return {
            "agent_name": config.get("name", "Unnamed Agent"),
            "agent_role": config.get("role", "analyst"),
            "description": config.get("role", ""),
            "industry": industry,
            "organization_id": organization_id,
            "profile_id": profile_ctx.get("profile_id"),
            "system_prompt": system_prompt,
            "kpis_monitored": kpi_list,
            "entity_types": entity_types,
            "tools": config.get("tools", self._default_tools(config, profile_ctx)),
            "ai_preferences": profile_ctx.get("ai_preferences", {}),
        }

    def _default_tools(self, config: dict, profile_ctx: dict) -> list[dict]:
        """Generate default tools based on agent role and profile."""
        role = config.get("role", "").lower()
        tools = [
            {"name": "query_memory", "description": "Search company memory and knowledge"},
            {"name": "search_knowledge_graph", "description": "Search the company knowledge graph"},
        ]

        # Add KPI-related tools if KPIs exist
        if profile_ctx.get("kpis"):
            tools.append({
                "name": "query_kpis",
                "description": "Query company KPI values and targets",
            })

        # Add role-specific tools
        if "sales" in role or "revenue" in role:
            tools.append({"name": "analyze_revenue", "description": "Analyze revenue trends and patterns"})
        elif "inventory" in role or "stock" in role:
            tools.append({"name": "check_inventory", "description": "Check inventory levels and turnover"})
        elif "quality" in role:
            tools.append({"name": "analyze_quality", "description": "Analyze quality metrics and defects"})
        elif "risk" in role:
            tools.append({"name": "assess_risk", "description": "Assess risk factors and exposure"})
        elif "production" in role:
            tools.append({"name": "monitor_production", "description": "Monitor production metrics and OEE"})

        # Decision-making tool for all agents
        tools.append({
            "name": "create_decision",
            "description": "Create a profile-aware decision recommendation",
        })

        return tools

    async def get_agent_by_name(
        self, organization_id: str, agent_name: str
    ) -> dict | None:
        """Get a specific agent by name."""
        agents = await self.create_agents(organization_id)
        for agent in agents:
            if agent["agent_name"].lower() == agent_name.lower():
                return agent
        return None
