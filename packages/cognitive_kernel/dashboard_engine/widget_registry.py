"""
πX Widget Registry — 15 widget types across 4 categories.

Every widget is reusable and dynamically instantiated from JSON.
Widgets declare their data requirements so the composition engine
can match them to available profile data.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class WidgetCategory(StrEnum):
    EXECUTIVE = "executive"
    ANALYTICS = "analytics"
    INTELLIGENCE = "intelligence"
    OPERATIONS = "operations"


class WidgetType(StrEnum):
    # Executive
    KPI_CARD = "kpi_card"
    TREND_CHART = "trend_chart"
    GOAL_PROGRESS = "goal_progress"
    ALERT_PANEL = "alert_panel"
    # Analytics
    DISTRIBUTION_CHART = "distribution_chart"
    CORRELATION_MATRIX = "correlation_matrix"
    FORECAST_CHART = "forecast_chart"
    DATA_QUALITY_SCORE = "data_quality_score"
    # Intelligence
    DECISION_QUEUE = "decision_queue"
    KNOWLEDGE_GRAPH_VIEW = "knowledge_graph_view"
    AI_RECOMMENDATION = "ai_recommendation"
    SIMULATION_RESULT = "simulation_result"
    # Operations
    AGENT_STATUS = "agent_status"
    WORKFLOW_MONITOR = "workflow_monitor"
    MEMORY_TIMELINE = "memory_timeline"


@dataclass
class WidgetSpec:
    """Specification for a widget type — what it needs and how it renders."""
    type: WidgetType
    category: WidgetCategory
    label: str
    description: str
    icon: str  # Material icon name or SVG path key
    min_data_keys: list[str]  # minimum data keys required
    optional_data_keys: list[str] = field(default_factory=list)
    default_size: tuple[int, int] = (1, 1)  # (cols, rows) in grid
    config_schema: dict[str, Any] = field(default_factory=dict)
    component_name: str = ""  # React component name for frontend rendering


class WidgetRegistry:
    """Registry of all available widgets. No hardcoding — widgets match to profile data dynamically."""

    def __init__(self) -> None:
        self._widgets: dict[WidgetType, WidgetSpec] = {}
        self._register_all()

    def _register_all(self) -> None:
        # ── Executive ──
        self._register(WidgetSpec(
            type=WidgetType.KPI_CARD,
            category=WidgetCategory.EXECUTIVE,
            label="KPI Card",
            description="Single metric with value, delta, and target",
            icon="trending_up",
            min_data_keys=["metric_name", "current_value"],
            optional_data_keys=["target_value", "previous_value", "unit"],
            default_size=(1, 1),
            config_schema={
                "metric": {"type": "string", "required": True},
                "source_column": {"type": "string", "required": False},
                "aggregation": {"type": "string", "enum": ["sum", "avg", "count", "max", "min"], "default": "sum"},
                "format": {"type": "string", "default": "number"},
            },
            component_name="KPIComponent",
        ))
        self._register(WidgetSpec(
            type=WidgetType.TREND_CHART,
            category=WidgetCategory.EXECUTIVE,
            label="Trend Chart",
            description="Time-series line chart for metric over period",
            icon="show_chart",
            min_data_keys=["metric_name", "time_dimension"],
            optional_data_keys=["comparison_metric", "forecast"],
            default_size=(2, 1),
            config_schema={
                "metric": {"type": "string", "required": True},
                "time_dimension": {"type": "string", "required": True},
                "period": {"type": "string", "enum": ["daily", "weekly", "monthly", "quarterly"], "default": "monthly"},
                "chart_type": {"type": "string", "enum": ["line", "area", "bar"], "default": "line"},
            },
            component_name="ChartComponent",
        ))
        self._register(WidgetSpec(
            type=WidgetType.GOAL_PROGRESS,
            category=WidgetCategory.EXECUTIVE,
            label="Goal Progress",
            description="Progress bar toward KPI target",
            icon="flag",
            min_data_keys=["kpi_name", "current_value", "target_value"],
            default_size=(1, 1),
            config_schema={
                "kpi": {"type": "string", "required": True},
                "show_benchmark": {"type": "boolean", "default": True},
            },
            component_name="GoalProgressComponent",
        ))
        self._register(WidgetSpec(
            type=WidgetType.ALERT_PANEL,
            category=WidgetCategory.EXECUTIVE,
            label="Alert Panel",
            description="Active alerts from data quality, KPI thresholds, and decisions",
            icon="warning",
            min_data_keys=["alerts"],
            default_size=(1, 1),
            config_schema={
                "severity_filter": {"type": "string", "enum": ["all", "critical", "warning", "info"], "default": "all"},
                "max_items": {"type": "integer", "default": 10},
            },
            component_name="AlertPanelComponent",
        ))

        # ── Analytics ──
        self._register(WidgetSpec(
            type=WidgetType.DISTRIBUTION_CHART,
            category=WidgetCategory.ANALYTICS,
            label="Distribution Chart",
            description="Histogram or pie chart showing value distribution",
            icon="pie_chart",
            min_data_keys=["dimension", "metric"],
            default_size=(2, 1),
            config_schema={
                "dimension": {"type": "string", "required": True},
                "metric": {"type": "string", "required": True},
                "chart_type": {"type": "string", "enum": ["histogram", "pie", "donut"], "default": "histogram"},
            },
            component_name="ChartComponent",
        ))
        self._register(WidgetSpec(
            type=WidgetType.CORRELATION_MATRIX,
            category=WidgetCategory.ANALYTICS,
            label="Correlation Matrix",
            description="Heatmap of correlations between numeric metrics",
            icon="grid_on",
            min_data_keys=["metrics"],
            default_size=(2, 2),
            config_schema={
                "metrics": {"type": "array", "required": True},
                "method": {"type": "string", "enum": ["pearson", "spearman"], "default": "pearson"},
            },
            component_name="CorrelationMatrixComponent",
        ))
        self._register(WidgetSpec(
            type=WidgetType.FORECAST_CHART,
            category=WidgetCategory.ANALYTICS,
            label="Forecast Chart",
            description="Predictive forecast for a metric using historical data",
            icon="insights",
            min_data_keys=["metric_name", "historical_values", "time_dimension"],
            default_size=(2, 1),
            config_schema={
                "metric": {"type": "string", "required": True},
                "horizon": {"type": "string", "default": "3_months"},
                "confidence_interval": {"type": "boolean", "default": True},
            },
            component_name="ChartComponent",
        ))
        self._register(WidgetSpec(
            type=WidgetType.DATA_QUALITY_SCORE,
            category=WidgetCategory.ANALYTICS,
            label="Data Quality Score",
            description="Overall data quality score with breakdown by dimension",
            icon="verified",
            min_data_keys=["quality_report"],
            default_size=(1, 1),
            config_schema={
                "show_breakdown": {"type": "boolean", "default": True},
            },
            component_name="DataQualityComponent",
        ))

        # ── Intelligence ──
        self._register(WidgetSpec(
            type=WidgetType.DECISION_QUEUE,
            category=WidgetCategory.INTELLIGENCE,
            label="Decision Queue",
            description="Pending decisions with status and priority",
            icon="account_tree",
            min_data_keys=["decisions"],
            default_size=(2, 1),
            config_schema={
                "status_filter": {"type": "string", "enum": ["all", "pending", "approved", "rejected"], "default": "pending"},
                "max_items": {"type": "integer", "default": 10},
            },
            component_name="DecisionComponent",
        ))
        self._register(WidgetSpec(
            type=WidgetType.KNOWLEDGE_GRAPH_VIEW,
            category=WidgetCategory.INTELLIGENCE,
            label="Knowledge Graph View",
            description="Interactive graph of entities and relationships",
            icon="hub",
            min_data_keys=["nodes", "edges"],
            default_size=(2, 2),
            config_schema={
                "layout": {"type": "string", "enum": ["force", "hierarchical", "radial"], "default": "force"},
                "entity_filter": {"type": "array", "required": False},
            },
            component_name="KnowledgeGraphComponent",
        ))
        self._register(WidgetSpec(
            type=WidgetType.AI_RECOMMENDATION,
            category=WidgetCategory.INTELLIGENCE,
            label="AI Recommendation",
            description="Contextual AI-generated recommendation card",
            icon="lightbulb",
            min_data_keys=["recommendation"],
            default_size=(1, 1),
            config_schema={
                "context": {"type": "string", "required": False},
                "confidence_threshold": {"type": "number", "default": 0.7},
            },
            component_name="AIRecommendationComponent",
        ))
        self._register(WidgetSpec(
            type=WidgetType.SIMULATION_RESULT,
            category=WidgetCategory.INTELLIGENCE,
            label="Simulation Result",
            description="Monte Carlo or scenario simulation results",
            icon="science",
            min_data_keys=["simulation_results"],
            default_size=(2, 1),
            config_schema={
                "show_histogram": {"type": "boolean", "default": True},
                "show_scenarios": {"type": "boolean", "default": True},
            },
            component_name="SimulationComponent",
        ))

        # ── Operations ──
        self._register(WidgetSpec(
            type=WidgetType.AGENT_STATUS,
            category=WidgetCategory.OPERATIONS,
            label="Agent Status",
            description="Status of AI agents in the organization",
            icon="smart_toy",
            min_data_keys=["agents"],
            default_size=(1, 1),
            config_schema={
                "show_inactive": {"type": "boolean", "default": False},
            },
            component_name="AgentStatusComponent",
        ))
        self._register(WidgetSpec(
            type=WidgetType.WORKFLOW_MONITOR,
            category=WidgetCategory.OPERATIONS,
            label="Workflow Monitor",
            description="Active workflow runs and their progress",
            icon="workflow",
            min_data_keys=["workflows"],
            default_size=(2, 1),
            config_schema={
                "status_filter": {"type": "string", "enum": ["all", "running", "completed", "failed"], "default": "running"},
            },
            component_name="WorkflowMonitorComponent",
        ))
        self._register(WidgetSpec(
            type=WidgetType.MEMORY_TIMELINE,
            category=WidgetCategory.OPERATIONS,
            label="Memory Timeline",
            description="Chronological view of ingested memories and events",
            icon="timeline",
            min_data_keys=["events"],
            default_size=(2, 1),
            config_schema={
                "max_items": {"type": "integer", "default": 20},
                "event_types": {"type": "array", "required": False},
            },
            component_name="MemoryTimelineComponent",
        ))

    def _register(self, spec: WidgetSpec) -> None:
        self._widgets[spec.type] = spec

    def get(self, widget_type: WidgetType) -> WidgetSpec | None:
        return self._widgets.get(widget_type)

    def get_by_category(self, category: WidgetCategory) -> list[WidgetSpec]:
        return [w for w in self._widgets.values() if w.category == category]

    def all_widgets(self) -> list[WidgetSpec]:
        return list(self._widgets.values())

    def can_satisfy(self, widget_type: WidgetType, available_keys: set[str]) -> bool:
        """Check if available profile data can satisfy a widget's requirements."""
        spec = self.get(widget_type)
        if not spec:
            return False
        return all(k in available_keys for k in spec.min_data_keys)
