"""
πX Agent Security — Enterprise RBAC for agents.

No agent can access unauthorized information.
CEO Agent: full strategic access
CFO Agent: financial data only
HR Agent: employee data only
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .agent_registry import AgentSpec, AgentType


@dataclass
class AgentPermission:
    """Permission definition for an agent."""
    agent_id: str
    org_id: str
    allowed_tools: list[str] = field(default_factory=list)
    allowed_entities: list[str] = field(default_factory=list)  # entity types
    allowed_data_categories: list[str] = field(default_factory=list)
    data_sensitivity_max: str = "standard"  # standard, high, critical
    can_create_decisions: bool = False
    can_send_notifications: bool = False
    can_modify_data: bool = False  # Agents are read-only by default


class AgentSecurity:
    """Enforces RBAC on agent actions."""

    # Role → allowed data categories mapping
    ROLE_ACCESS: dict[str, list[str]] = {
        "ceo": ["*"],  # Full access
        "cfo": ["financial", "revenue", "cost", "margin", "transaction"],
        "coo": ["operations", "production", "inventory", "quality", "supply_chain"],
        "cto": ["system", "ai_usage", "data_pipelines", "agent_metrics"],
        "cmo": ["marketing", "customer", "campaigns", "promotions"],
        "chro": ["hr", "employee_data", "performance", "headcount"],
        "executive": ["*"],
        "manager": ["operations", "inventory", "sales"],
        "analyst": ["*"],  # Read-only access to everything
    }

    # Role → max data sensitivity
    ROLE_SENSITIVITY: dict[str, str] = {
        "ceo": "critical",
        "cfo": "high",
        "coo": "standard",
        "cto": "standard",
        "cmo": "standard",
        "chro": "high",
        "executive": "critical",
        "manager": "standard",
        "analyst": "standard",
    }

    def __init__(self) -> None:
        self._permissions: dict[str, AgentPermission] = {}

    def grant(self, agent_id: str, org_id: str, spec: AgentSpec) -> AgentPermission:
        """Grant permissions to an agent based on its spec and role."""
        role = spec.role.lower()
        data_categories = self.ROLE_ACCESS.get(role, [])
        sensitivity = self.ROLE_SENSITIVITY.get(role, "standard")

        perm = AgentPermission(
            agent_id=agent_id,
            org_id=org_id,
            allowed_tools=spec.tools,
            allowed_entities=spec.knowledge_access,
            allowed_data_categories=data_categories,
            data_sensitivity_max=sensitivity,
            can_create_decisions="create_decision" in spec.tools,
            can_send_notifications="send_notification" in spec.tools,
            can_modify_data=False,  # Agents are read-only by default
        )
        self._permissions[agent_id] = perm
        return perm

    def check_tool_access(self, agent_id: str, tool_name: str) -> bool:
        perm = self._permissions.get(agent_id)
        if not perm:
            return False
        return tool_name in perm.allowed_tools

    def check_entity_access(self, agent_id: str, entity_type: str) -> bool:
        perm = self._permissions.get(agent_id)
        if not perm:
            return False
        if "*" in perm.allowed_entities:
            return True
        return entity_type in perm.allowed_entities

    def check_data_access(self, agent_id: str, data_category: str) -> bool:
        perm = self._permissions.get(agent_id)
        if not perm:
            return False
        if "*" in perm.allowed_data_categories:
            return True
        return data_category in perm.allowed_data_categories

    def check_sensitivity(self, agent_id: str, sensitivity: str) -> bool:
        perm = self._permissions.get(agent_id)
        if not perm:
            return False
        levels = {"standard": 1, "high": 2, "critical": 3}
        return levels.get(sensitivity, 1) <= levels.get(perm.data_sensitivity_max, 1)

    def check_action(self, agent_id: str, action: str) -> bool:
        """Check if an agent can perform a specific action."""
        perm = self._permissions.get(agent_id)
        if not perm:
            return False
        if action == "create_decision":
            return perm.can_create_decisions
        if action == "send_notification":
            return perm.can_send_notifications
        if action == "modify_data":
            return perm.can_modify_data
        return False

    def get_permissions(self, agent_id: str) -> AgentPermission | None:
        return self._permissions.get(agent_id)
