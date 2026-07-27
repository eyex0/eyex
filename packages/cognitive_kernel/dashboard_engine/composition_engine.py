"""
πX Dashboard Composition Engine — Generates dashboard layouts from Intelligence Profile.

Analyzes the org's profile (industry, KPIs, ontology, data sources, agents)
and produces a Dashboard Definition JSON. No hardcoded dashboards — everything
originates from the Intelligence Profile.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .widget_registry import (
    WidgetCategory,
    WidgetRegistry,
    WidgetSpec,
    WidgetType,
)


@dataclass
class WidgetInstance:
    """A widget placed on a dashboard with its configuration."""
    id: str
    type: WidgetType
    label: str
    config: dict[str, Any] = field(default_factory=dict)
    position: tuple[int, int] = (0, 0)  # (row, col) in grid
    size: tuple[int, int] = (1, 1)  # (cols, rows)
    data_keys: list[str] = field(default_factory=list)
    category: WidgetCategory = WidgetCategory.EXECUTIVE


@dataclass
class DashboardDefinition:
    """Complete dashboard definition — rendered from JSON on the frontend."""
    dashboard_id: str
    dashboard_type: str  # e.g. "Retail Executive", "Manufacturing Operations"
    title: str
    subtitle: str
    industry: str
    role: str
    layout: list[WidgetInstance] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_json(self) -> dict[str, Any]:
        return {
            "dashboard_id": self.dashboard_id,
            "dashboard_type": self.dashboard_type,
            "title": self.title,
            "subtitle": self.subtitle,
            "industry": self.industry,
            "role": self.role,
            "layout": [
                {
                    "id": w.id,
                    "type": w.type.value,
                    "label": w.label,
                    "config": w.config,
                    "position": list(w.position),
                    "size": list(w.size),
                    "data_keys": w.data_keys,
                    "category": w.category.value,
                    "component": self._component_for(w.type),
                }
                for w in self.layout
            ],
            "metadata": self.metadata,
        }

    @staticmethod
    def _component_for(wtype: WidgetType) -> str:
        """Map widget type to React component name."""
        _map = {
            WidgetType.KPI_CARD: "KPIComponent",
            WidgetType.TREND_CHART: "ChartComponent",
            WidgetType.GOAL_PROGRESS: "GoalProgressComponent",
            WidgetType.ALERT_PANEL: "AlertPanelComponent",
            WidgetType.DISTRIBUTION_CHART: "ChartComponent",
            WidgetType.CORRELATION_MATRIX: "CorrelationMatrixComponent",
            WidgetType.FORECAST_CHART: "ChartComponent",
            WidgetType.DATA_QUALITY_SCORE: "DataQualityComponent",
            WidgetType.DECISION_QUEUE: "DecisionComponent",
            WidgetType.KNOWLEDGE_GRAPH_VIEW: "KnowledgeGraphComponent",
            WidgetType.AI_RECOMMENDATION: "AIRecommendationComponent",
            WidgetType.SIMULATION_RESULT: "SimulationComponent",
            WidgetType.AGENT_STATUS: "AgentStatusComponent",
            WidgetType.WORKFLOW_MONITOR: "WorkflowMonitorComponent",
            WidgetType.MEMORY_TIMELINE: "MemoryTimelineComponent",
        }
        return _map.get(wtype, "GenericWidget")


class DashboardCompositionEngine:
    """Generates dashboards from Intelligence Profile data — fully adaptive."""

    def __init__(self, registry: WidgetRegistry | None = None) -> None:
        self.registry = registry or WidgetRegistry()

    def compose(
        self,
        org_id: str,
        profile_context: dict[str, Any],
        role: str = "executive",
        user_preferences: dict[str, Any] | None = None,
    ) -> DashboardDefinition:
        """Generate a dashboard definition from profile context."""
        industry = profile_context.get("industry", "generic")
        kpis = profile_context.get("kpis", [])
        ontology = profile_context.get("ontology", {})
        data_sources = profile_context.get("data_sources", [])
        agents = profile_context.get("agents", [])
        company_identity = profile_context.get("company_identity", {})
        company_name = company_identity.get("name", "Organization")

        # Determine dashboard type from industry + role
        dashboard_type = f"{industry.title()} {role.title()}"
        title = f"{company_name} — {dashboard_type}"
        subtitle = self._generate_subtitle(industry, role, kpis)

        # Build widgets based on available data
        layout = self._select_widgets(
            industry=industry,
            role=role,
            kpis=kpis,
            ontology=ontology,
            data_sources=data_sources,
            agents=agents,
            user_preferences=user_preferences or {},
        )

        return DashboardDefinition(
            dashboard_id=f"dash_{org_id}_{role}",
            dashboard_type=dashboard_type,
            title=title,
            subtitle=subtitle,
            industry=industry,
            role=role,
            layout=layout,
            metadata={
                "org_id": org_id,
                "generated_at": None,  # Set by caller
                "widget_count": len(layout),
                "profile_confidence": profile_context.get("confidence", {}),
                "available_kpis": [k.get("name", "") for k in kpis],
                "available_entities": list(ontology.get("entities", {}).keys()) if isinstance(ontology, dict) else [],
            },
        )

    def _generate_subtitle(self, industry: str, role: str, kpis: list) -> str:
        kpi_names = [k.get("name", "") for k in kpis[:3] if isinstance(k, dict)]
        kpi_str = " · ".join(kpi_names) if kpi_names else "discovering KPIs"
        return f"{industry.title()} intelligence · tracking: {kpi_str}"

    def _select_widgets(
        self,
        industry: str,
        role: str,
        kpis: list,
        ontology: dict,
        data_sources: list,
        agents: list,
        user_preferences: dict,
    ) -> list[WidgetInstance]:
        """Select and place widgets based on role, industry, and available data."""
        layout: list[WidgetInstance] = []
        row = 0
        col = 0
        max_cols = 4
        widget_idx = 0

        # ── KPI Cards from profile KPIs ──
        kpi_limit = self._kpi_limit_for_role(role)
        for kpi in kpis[:kpi_limit]:
            if not isinstance(kpi, dict):
                continue
            kpi_name = kpi.get("name", "Unknown KPI")
            source = kpi.get("source_column", kpi.get("formula", ""))
            target = kpi.get("target")

            widget = WidgetInstance(
                id=f"widget_{widget_idx}",
                type=WidgetType.KPI_CARD,
                label=kpi_name,
                config={
                    "metric": kpi_name,
                    "source_column": source,
                    "aggregation": kpi.get("aggregation", "sum"),
                    "format": kpi.get("format", "number"),
                    "target": target,
                    "unit": kpi.get("unit", ""),
                },
                position=(row, col),
                size=(1, 1),
                data_keys=["metric_name", "current_value"],
                category=WidgetCategory.EXECUTIVE,
            )
            layout.append(widget)
            widget_idx += 1
            col += 1
            if col >= max_cols:
                col = 0
                row += 1

        # ── Trend Chart for primary metric ──
        if kpis:
            primary_kpi = kpis[0] if isinstance(kpis[0], dict) else {"name": "Revenue"}
            trend = WidgetInstance(
                id=f"widget_{widget_idx}",
                type=WidgetType.TREND_CHART,
                label=f"{primary_kpi.get('name', 'Primary')} Trend",
                config={
                    "metric": primary_kpi.get("name", "Revenue"),
                    "time_dimension": "date",
                    "period": "monthly",
                    "chart_type": "area",
                },
                position=(row, col),
                size=(2, 1),
                data_keys=["metric_name", "time_dimension"],
                category=WidgetCategory.EXECUTIVE,
            )
            layout.append(trend)
            widget_idx += 1
            col += 2
            if col >= max_cols:
                col = 0
                row += 1

        # ── Role-specific widgets ──
        role_widgets = self._role_specific_widgets(role, kpis, agents, widget_idx)
        for w in role_widgets:
            w.position = (row, col)
            layout.append(w)
            widget_idx += 1
            col += w.size[0]
            if col >= max_cols:
                col = 0
                row += 1

        # ── Intelligence widgets (all roles get decision queue) ──
        decision_q = WidgetInstance(
            id=f"widget_{widget_idx}",
            type=WidgetType.DECISION_QUEUE,
            label="Decision Queue",
            config={"status_filter": "pending", "max_items": 10},
            position=(row, col),
            size=(2, 1),
            data_keys=["decisions"],
            category=WidgetCategory.INTELLIGENCE,
        )
        layout.append(decision_q)
        widget_idx += 1
        col += 2
        if col >= max_cols:
            col = 0
            row += 1

        # ── AI Recommendation ──
        ai_rec = WidgetInstance(
            id=f"widget_{widget_idx}",
            type=WidgetType.AI_RECOMMENDATION,
            label="AI Recommendation",
            config={"context": industry, "confidence_threshold": 0.7},
            position=(row, col),
            size=(1, 1),
            data_keys=["recommendation"],
            category=WidgetCategory.INTELLIGENCE,
        )
        layout.append(ai_rec)
        widget_idx += 1
        col += 1
        if col >= max_cols:
            col = 0
            row += 1

        # ── Data Quality ──
        dq = WidgetInstance(
            id=f"widget_{widget_idx}",
            type=WidgetType.DATA_QUALITY_SCORE,
            label="Data Quality",
            config={"show_breakdown": True},
            position=(row, col),
            size=(1, 1),
            data_keys=["quality_report"],
            category=WidgetCategory.ANALYTICS,
        )
        layout.append(dq)
        widget_idx += 1
        col += 1
        if col >= max_cols:
            col = 0
            row += 1

        # ── Agent Status (if agents exist) ──
        if agents:
            agent_w = WidgetInstance(
                id=f"widget_{widget_idx}",
                type=WidgetType.AGENT_STATUS,
                label="Agent Status",
                config={"show_inactive": False},
                position=(row, col),
                size=(1, 1),
                data_keys=["agents"],
                category=WidgetCategory.OPERATIONS,
            )
            layout.append(agent_w)
            widget_idx += 1
            col += 1
            if col >= max_cols:
                col = 0
                row += 1

        # ── Memory Timeline ──
        memory_w = WidgetInstance(
            id=f"widget_{widget_idx}",
            type=WidgetType.MEMORY_TIMELINE,
            label="Memory Timeline",
            config={"max_items": 20},
            position=(row, col),
            size=(2, 1),
            data_keys=["events"],
            category=WidgetCategory.OPERATIONS,
        )
        layout.append(memory_w)

        # Apply user customizations (remove/hide widgets)
        hidden = set(user_preferences.get("hidden_widgets", []))
        layout = [w for w in layout if w.id not in hidden]

        return layout

    def _kpi_limit_for_role(self, role: str) -> int:
        limits = {"ceo": 4, "cfo": 4, "coo": 3, "cto": 2, "executive": 4, "manager": 3, "analyst": 3}
        return limits.get(role.lower(), 4)

    def _role_specific_widgets(
        self, role: str, kpis: list, agents: list, start_idx: int
    ) -> list[WidgetInstance]:
        """Generate role-specific widgets beyond the standard KPI cards."""
        widgets: list[WidgetInstance] = []
        idx = start_idx

        role_lower = role.lower()

        if role_lower == "cfo":
            # CFO: Forecast + Correlation
            forecast_kpi = kpis[0] if kpis else {"name": "Revenue"}
            if isinstance(forecast_kpi, dict):
                widgets.append(WidgetInstance(
                    id=f"widget_{idx}",
                    type=WidgetType.FORECAST_CHART,
                    label=f"{forecast_kpi.get('name', 'Revenue')} Forecast",
                    config={
                        "metric": forecast_kpi.get("name", "Revenue"),
                        "horizon": "3_months",
                        "confidence_interval": True,
                    },
                    data_keys=["metric_name", "historical_values", "time_dimension"],
                    category=WidgetCategory.ANALYTICS,
                ))
                idx += 1
            kpi_names = [k.get("name", "") for k in kpis if isinstance(k, dict)]
            if len(kpi_names) >= 2:
                widgets.append(WidgetInstance(
                    id=f"widget_{idx}",
                    type=WidgetType.CORRELATION_MATRIX,
                    label="KPI Correlations",
                    config={"metrics": kpi_names, "method": "pearson"},
                    data_keys=["metrics"],
                    category=WidgetCategory.ANALYTICS,
                ))
                idx += 1

        elif role_lower == "coo":
            # COO: Distribution + Workflow
            widgets.append(WidgetInstance(
                id=f"widget_{idx}",
                type=WidgetType.DISTRIBUTION_CHART,
                label="Operations Distribution",
                config={"dimension": "department", "metric": "count", "chart_type": "histogram"},
                data_keys=["dimension", "metric"],
                category=WidgetCategory.ANALYTICS,
            ))
            idx += 1
            widgets.append(WidgetInstance(
                id=f"widget_{idx}",
                type=WidgetType.WORKFLOW_MONITOR,
                label="Workflow Monitor",
                config={"status_filter": "running"},
                data_keys=["workflows"],
                category=WidgetCategory.OPERATIONS,
            ))
            idx += 1

        elif role_lower == "cto":
            # CTO: Agent Status + Knowledge Graph + Workflow
            widgets.append(WidgetInstance(
                id=f"widget_{idx}",
                type=WidgetType.KNOWLEDGE_GRAPH_VIEW,
                label="Knowledge Graph",
                config={"layout": "force"},
                data_keys=["nodes", "edges"],
                category=WidgetCategory.INTELLIGENCE,
            ))
            idx += 1
            widgets.append(WidgetInstance(
                id=f"widget_{idx}",
                type=WidgetType.AGENT_STATUS,
                label="AI Agent Status",
                config={"show_inactive": True},
                data_keys=["agents"],
                category=WidgetCategory.OPERATIONS,
            ))
            idx += 1

        elif role_lower in ("ceo", "executive"):
            # CEO: Goal Progress + Alert Panel
            for kpi in kpis[:2]:
                if not isinstance(kpi, dict):
                    continue
                target = kpi.get("target")
                if target:
                    widgets.append(WidgetInstance(
                        id=f"widget_{idx}",
                        type=WidgetType.GOAL_PROGRESS,
                        label=f"{kpi.get('name', 'Goal')} Progress",
                        config={"kpi": kpi.get("name", ""), "show_benchmark": True},
                        data_keys=["kpi_name", "current_value", "target_value"],
                        category=WidgetCategory.EXECUTIVE,
                    ))
                    idx += 1
            widgets.append(WidgetInstance(
                id=f"widget_{idx}",
                type=WidgetType.ALERT_PANEL,
                label="Active Alerts",
                config={"severity_filter": "all", "max_items": 10},
                data_keys=["alerts"],
                category=WidgetCategory.EXECUTIVE,
            ))
            idx += 1

        return widgets
