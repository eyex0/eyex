"""πX Dynamic Dashboard Engine — Generated intelligence interfaces."""
from .widget_registry import WidgetRegistry, WidgetType, WidgetCategory
from .composition_engine import DashboardCompositionEngine, DashboardDefinition
from .role_based_generator import RoleBasedDashboardGenerator
from .data_service import DashboardDataService
from .dashboard_agent import DashboardIntelligenceAgent
from .customization import UserCustomizationManager

__all__ = [
    "WidgetRegistry", "WidgetType", "WidgetCategory",
    "DashboardCompositionEngine", "DashboardDefinition",
    "RoleBasedDashboardGenerator",
    "DashboardDataService",
    "DashboardIntelligenceAgent",
    "UserCustomizationManager",
]
