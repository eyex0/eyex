from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

logger = logging.getLogger("pix.marketplace")


@dataclass
class AgentManifest:
    """Specification for a marketplace agent."""

    id_: str
    name: str
    version: str
    author: str
    description: str
    category: str  # industry|function|utility
    industry: str = "general"
    agent_class: str = ""
    entry_point: str = ""
    tags: list[str] = field(default_factory=list)
    tools: list[str] = field(default_factory=list)
    config_schema: dict[str, Any] = field(default_factory=dict)
    dependencies: list[str] = field(default_factory=list)
    is_official: bool = False
    rating: float = 0.0
    install_count: int = 0
    created_at: str = ""
    updated_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id_, "name": self.name, "version": self.version,
            "author": self.author, "description": self.description,
            "category": self.category, "industry": self.industry,
            "tags": self.tags, "tools": self.tools,
            "is_official": self.is_official, "rating": self.rating,
            "install_count": self.install_count,
            "created_at": self.created_at, "updated_at": self.updated_at,
        }


@dataclass
class InstalledAgent:
    """An agent installed in a specific organization's workspace."""

    manifest: AgentManifest
    org_id: str
    config: dict[str, Any] = field(default_factory=dict)
    enabled: bool = True
    installed_at: str = ""
    last_used_at: str | None = None


class MarketplaceAgent(ABC):
    """Base class for marketplace agents.

    Third-party developers extend this class to create custom agents.
    """

    @abstractmethod
    def execute(self, input_text: str, context: dict[str, Any] | None = None) -> dict[str, Any]:
        ...

    @property
    @abstractmethod
    def manifest(self) -> AgentManifest:
        ...


class MarketplaceRegistry:
    """Registry for discovering, installing, and managing agents.

    Supports both official πX agents and third-party agents.
    """

    def __init__(self) -> None:
        self._manifests: dict[str, AgentManifest] = {}
        self._installed: dict[str, list[InstalledAgent]] = {}
        self._custom_agents: dict[str, type[MarketplaceAgent]] = {}
        self._register_official()

    def _register_official(self) -> None:
        """Register πX's official agent set as marketplace listings."""
        official = [
            AgentManifest(
                id_="pix-ceo", name="CEO Agent", version="1.0.0",
                author="πX Technologies", description="Strategic vision and direction setting",
                category="function", industry="general",
                agent_class="CEOAgent", is_official=True,
                tags=["strategy", "executive", "leadership"],
                created_at=datetime.now(UTC).isoformat(),
            ),
            AgentManifest(
                id_="pix-cfo", name="CFO Agent", version="1.0.0",
                author="πX Technologies", description="Financial analysis and planning",
                category="function", industry="general",
                agent_class="CFOAgent", is_official=True,
                tags=["finance", "analysis", "planning"],
                created_at=datetime.now(UTC).isoformat(),
            ),
            AgentManifest(
                id_="pix-coo", name="COO Agent", version="1.0.0",
                author="πX Technologies", description="Operational optimization and scaling",
                category="function", industry="general",
                agent_class="COOAgent", is_official=True,
                tags=["operations", "scaling", "process"],
                created_at=datetime.now(UTC).isoformat(),
            ),
            AgentManifest(
                id_="pix-risk", name="Risk Agent", version="1.0.0",
                author="πX Technologies", description="Risk assessment and mitigation",
                category="function", industry="general",
                agent_class="RiskAgent", is_official=True,
                tags=["risk", "compliance", "security"],
                created_at=datetime.now(UTC).isoformat(),
            ),
            AgentManifest(
                id_="pix-analyst", name="Analyst Agent", version="1.0.0",
                author="πX Technologies", description="Business data analysis and trend detection",
                category="function", industry="general",
                agent_class="AnalystAgent", is_official=True,
                tags=["analysis", "data", "trends"],
                created_at=datetime.now(UTC).isoformat(),
            ),
            AgentManifest(
                id_="pix-strategist", name="Strategist Agent", version="1.0.0",
                author="πX Technologies", description="Strategic recommendation generation",
                category="function", industry="general",
                agent_class="StrategistAgent", is_official=True,
                tags=["strategy", "recommendations"],
                created_at=datetime.now(UTC).isoformat(),
            ),
            AgentManifest(
                id_="pix-decision", name="Decision Agent", version="1.0.0",
                author="πX Technologies", description="Executive decision synthesis",
                category="function", industry="general",
                agent_class="DecisionAgent", is_official=True,
                tags=["decisions", "synthesis", "executive"],
                created_at=datetime.now(UTC).isoformat(),
            ),
        ]
        for manifest in official:
            self._manifests[manifest.id_] = manifest

        # Register industry-specific editions
        for industry in ["manufacturing", "healthcare", "logistics", "finance", "retail"]:
            for base_id in ["ceo", "cfo", "coo", "risk"]:
                ind_manifest = AgentManifest(
                    id_=f"pix-{industry}-{base_id}",
                    name=f"{base_id.upper()} Agent ({industry.title()})",
                    version="1.0.0",
                    author="πX Technologies",
                    description=f"{base_id.upper()} analysis specialized for {industry}",
                    category="industry",
                    industry=industry,
                    agent_class=f"{base_id.title()}Agent",
                    is_official=True,
                    tags=[industry, base_id],
                    created_at=datetime.now(UTC).isoformat(),
                )
                self._manifests[ind_manifest.id_] = ind_manifest

    def search(
        self, query: str = "", category: str = "",
        industry: str = "", tags: list[str] | None = None,
    ) -> list[AgentManifest]:
        results = list(self._manifests.values())
        if query:
            q = query.lower()
            results = [
                m for m in results
                if q in m.name.lower() or q in m.description.lower() or q in m.author.lower()
            ]
        if category:
            results = [m for m in results if m.category == category]
        if industry:
            results = [m for m in results if m.industry == industry]
        if tags:
            results = [m for m in results if any(t in m.tags for t in tags)]
        return sorted(results, key=lambda m: (m.is_official, m.install_count), reverse=True)

    def get_manifest(self, agent_id: str) -> AgentManifest | None:
        return self._manifests.get(agent_id)

    def register_third_party(self, manifest: AgentManifest, agent_class: type[MarketplaceAgent]) -> None:
        if manifest.id_ in self._manifests and self._manifests[manifest.id_].is_official:
            raise ValueError(f"Cannot override official agent: {manifest.id_}")
        self._manifests[manifest.id_] = manifest
        self._custom_agents[manifest.id_] = agent_class
        logger.info("Registered third-party agent: %s v%s by %s", manifest.id_, manifest.version, manifest.author)

    def install(self, agent_id: str, org_id: str, config: dict[str, Any] | None = None) -> InstalledAgent | None:
        manifest = self._manifests.get(agent_id)
        if not manifest:
            logger.warning("Cannot install unknown agent: %s", agent_id)
            return None
        installed = InstalledAgent(
            manifest=manifest, org_id=org_id,
            config=config or {}, enabled=True,
            installed_at=datetime.now(UTC).isoformat(),
        )
        if org_id not in self._installed:
            self._installed[org_id] = []
        self._installed[org_id].append(installed)
        self._manifests[agent_id].install_count += 1
        logger.info("Installed agent %s for org %s", agent_id, org_id)
        return installed

    def uninstall(self, agent_id: str, org_id: str) -> bool:
        if org_id not in self._installed:
            return False
        before = len(self._installed[org_id])
        self._installed[org_id] = [a for a in self._installed[org_id] if a.manifest.id_ != agent_id]
        return len(self._installed[org_id]) < before

    def list_installed(self, org_id: str) -> list[InstalledAgent]:
        return self._installed.get(org_id, [])

    def get_installed(self, agent_id: str, org_id: str) -> InstalledAgent | None:
        for a in self._installed.get(org_id, []):
            if a.manifest.id_ == agent_id:
                return a
        return None

    def get_categories(self) -> list[dict[str, Any]]:
        cats: dict[str, int] = {}
        for m in self._manifests.values():
            cats[m.category] = cats.get(m.category, 0) + 1
        return [{"name": k, "count": v} for k, v in cats.items()]

    def get_industries(self) -> list[dict[str, Any]]:
        inds: dict[str, int] = {}
        for m in self._manifests.values():
            inds[m.industry] = inds.get(m.industry, 0) + 1
        return [{"name": k, "count": v} for k, v in inds.items()]


# Agent SDK template for third-party developers
AGENT_SDK_TEMPLATE = '''
from pix.marketplace import MarketplaceAgent, AgentManifest
from datetime import datetime, timezone
from typing import Any

class MyCustomAgent(MarketplaceAgent):
    @property
    def manifest(self) -> AgentManifest:
        return AgentManifest(
            id_="my-custom-agent",
            name="My Custom Agent",
            version="1.0.0",
            author="Your Name",
            description="Description of what your agent does",
            category="utility",
            industry="general",
            tags=["custom"],
            created_at=datetime.now(timezone.utc).isoformat(),
        )

    def execute(self, input_text: str, context: dict[str, Any] | None = None) -> dict[str, Any]:
        # Your agent logic here
        return {
            "output": f"Processed: {input_text}",
            "confidence": 0.95,
            "agent": self.manifest.name,
        }
'''


_marketplace: MarketplaceRegistry | None = None


def get_marketplace_registry() -> MarketplaceRegistry:
    global _marketplace
    if _marketplace is None:
        _marketplace = MarketplaceRegistry()
    return _marketplace
