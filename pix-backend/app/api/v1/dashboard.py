"""
πX Dynamic Dashboard API — Generate, customize, and stream dashboard data.

Endpoints:
  GET    /dashboard/{org_id}/generate?role=ceo     → Generate dashboard from profile
  GET    /dashboard/{org_id}/widgets               → List available widgets
  GET    /dashboard/{org_id}/recommend?role=cfo     → AI recommendation
  GET    /dashboard/{org_id}/preferences            → User preferences
  PUT    /dashboard/{org_id}/preferences            → Save preferences
  POST   /dashboard/{org_id}/widgets/add            → Add custom widget
  DELETE /dashboard/{org_id}/widgets/{widget_id}    → Remove widget
  PUT    /dashboard/{org_id}/layout                 → Update layout positions
  GET    /dashboard/{org_id}/events                 → SSE event stream
  WS     /dashboard/{org_id}/ws                    → WebSocket for live updates
"""
from __future__ import annotations

import json
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, WebSocket, WebSocketDisconnect
from fastapi.responses import StreamingResponse

dashboard_router = APIRouter(prefix="/dashboard", tags=["Dashboard"])

# Lazy singleton instances
_composition_engine = None
_role_generator = None
_widget_registry = None
_data_service = None
_dashboard_agent = None
_customization = None


def _get_composition_engine():
    global _composition_engine
    if _composition_engine is None:
        from packages.cognitive_kernel.dashboard_engine.composition_engine import DashboardCompositionEngine
        _composition_engine = DashboardCompositionEngine()
    return _composition_engine


def _get_role_generator():
    global _role_generator
    if _role_generator is None:
        from packages.cognitive_kernel.dashboard_engine.role_based_generator import RoleBasedDashboardGenerator
        _role_generator = RoleBasedDashboardGenerator()
    return _role_generator


def _get_widget_registry():
    global _widget_registry
    if _widget_registry is None:
        from packages.cognitive_kernel.dashboard_engine.widget_registry import WidgetRegistry
        _widget_registry = WidgetRegistry()
    return _widget_registry


def _get_data_service():
    global _data_service
    if _data_service is None:
        from packages.cognitive_kernel.dashboard_engine.data_service import DashboardDataService
        _data_service = DashboardDataService()
    return _data_service


def _get_dashboard_agent():
    global _dashboard_agent
    if _dashboard_agent is None:
        from packages.cognitive_kernel.dashboard_engine.dashboard_agent import DashboardIntelligenceAgent
        _dashboard_agent = DashboardIntelligenceAgent()
    return _dashboard_agent


def _get_customization():
    global _customization
    if _customization is None:
        from packages.cognitive_kernel.dashboard_engine.customization import UserCustomizationManager
        _customization = UserCustomizationManager()
    return _customization


def _mock_profile_context(org_id: str) -> dict[str, Any]:
    """Mock profile context — in production, this calls ProfileContextProvider."""
    return {
        "org_id": org_id,
        "industry": "retail",
        "company_identity": {"name": "Organization"},
        "kpis": [{"name": "Revenue", "source_column": "NET_REV", "target": 1000000}],
        "ontology": {"entities": {"customer": {}, "product": {}}},
        "data_sources": [],
        "agents": [],
        "confidence": {"overall": 0.85},
    }


@dashboard_router.get("/{org_id}/generate")
async def generate_dashboard(
    org_id: str,
    role: str = Query("executive"),
) -> dict[str, Any]:
    """Generate a dashboard from the org's Intelligence Profile."""
    generator = _get_role_generator()
    profile_ctx = _mock_profile_context(org_id)
    dashboard = generator.generate(org_id, profile_ctx, role)
    return dashboard.to_json()


@dashboard_router.get("/{org_id}/widgets")
async def list_widgets(org_id: str) -> dict[str, Any]:
    """List all available widget types."""
    registry = _get_widget_registry()
    return {
        "widgets": [
            {
                "type": w.type.value,
                "category": w.category.value,
                "label": w.label,
                "description": w.description,
                "icon": w.icon,
                "component": w.component_name,
                "default_size": list(w.default_size),
                "config_schema": w.config_schema,
            }
            for w in registry.all_widgets()
        ]
    }


@dashboard_router.get("/{org_id}/recommend")
async def recommend_dashboard(
    org_id: str,
    role: str = Query("executive"),
) -> dict[str, Any]:
    """Get AI-powered dashboard recommendation with reasoning."""
    agent = _get_dashboard_agent()
    profile_ctx = _mock_profile_context(org_id)
    rec = agent.recommend(org_id, profile_ctx, role)
    return {
        "reasoning": rec.reasoning,
        "suggested_title": rec.suggested_title,
        "confidence": rec.confidence,
        "alternative_roles": rec.alternative_roles,
        "recommended_widgets": rec.recommended_widgets,
    }


@dashboard_router.get("/{org_id}/preferences")
async def get_preferences(org_id: str, user_id: str = Query(...)) -> dict[str, Any]:
    """Get user's dashboard preferences."""
    cust = _get_customization()
    prefs = cust.get_preferences(org_id, user_id)
    if prefs:
        return prefs.to_json()
    return {"org_id": org_id, "user_id": user_id, "hidden_widgets": [], "custom_widgets": [], "layout_overrides": {}}


@dashboard_router.put("/{org_id}/preferences")
async def save_preferences(org_id: str, user_id: str = Query(...), body: dict = None) -> dict[str, Any]:
    """Save user's dashboard customization."""
    cust = _get_customization()
    prefs = cust.save_preferences(
        org_id=org_id,
        user_id=user_id,
        role=body.get("role", "executive"),
        hidden_widgets=body.get("hidden_widgets"),
        custom_widgets=body.get("custom_widgets"),
        layout_overrides=body.get("layout_overrides"),
        size_overrides=body.get("size_overrides"),
        custom_title=body.get("custom_title"),
        pinned_widgets=body.get("pinned_widgets"),
    )
    return {"saved": True, **prefs.to_json()}


@dashboard_router.post("/{org_id}/widgets/add")
async def add_widget(org_id: str, user_id: str = Query(...), body: dict = None) -> dict[str, Any]:
    """Add a custom widget to the user's dashboard."""
    cust = _get_customization()
    widget = cust.add_widget(
        org_id=org_id,
        user_id=user_id,
        widget_type=body["widget_type"],
        label=body["label"],
        config=body.get("config", {}),
    )
    return widget


@dashboard_router.delete("/{org_id}/widgets/{widget_id}")
async def remove_widget(org_id: str, user_id: str = Query(...), widget_id: str = "") -> dict[str, Any]:
    """Hide/remove a widget from the user's dashboard."""
    cust = _get_customization()
    cust.hide_widget(org_id, user_id, widget_id)
    return {"hidden": True, "widget_id": widget_id}


@dashboard_router.put("/{org_id}/layout")
async def update_layout(org_id: str, user_id: str = Query(...), body: dict = None) -> dict[str, Any]:
    """Update widget positions in the dashboard layout."""
    cust = _get_customization()
    cust.update_layout(org_id, user_id, body.get("positions", {}))
    return {"updated": True}


@dashboard_router.get("/{org_id}/events")
async def event_stream(org_id: str) -> StreamingResponse:
    """SSE endpoint for real-time dashboard events."""
    svc = _get_data_service()
    return StreamingResponse(
        svc.subscribe_sse(org_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@dashboard_router.websocket("/{org_id}/ws")
async def websocket_endpoint(websocket: WebSocket, org_id: str) -> None:
    """WebSocket endpoint for real-time dashboard updates."""
    svc = _get_data_service()
    await svc.connect_ws(org_id, websocket)
    try:
        while True:
            data = await websocket.receive_text()
            # Client can send commands
            msg = json.loads(data)
            if msg.get("type") == "ping":
                await websocket.send_json({"type": "pong"})
    except WebSocketDisconnect:
        await svc.disconnect_ws(org_id, websocket)
