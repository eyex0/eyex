"""
πX User Customization Manager — Lets users personalize their dashboards.

Users can: add widgets, remove widgets, rearrange layout, save preferences.
Stored as dashboard_preferences per user per org.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from .composition_engine import WidgetInstance
from .widget_registry import WidgetRegistry, WidgetType


@dataclass
class UserDashboardPreferences:
    org_id: str
    user_id: str
    role: str
    hidden_widgets: list[str] = field(default_factory=list)
    custom_widgets: list[dict[str, Any]] = field(default_factory=list)
    layout_overrides: dict[str, list[int]] = field(default_factory=dict)  # widget_id → [row, col]
    size_overrides: dict[str, list[int]] = field(default_factory=dict)  # widget_id → [cols, rows]
    custom_title: str | None = None
    pinned_widgets: list[str] = field(default_factory=list)
    saved_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())

    def to_json(self) -> dict[str, Any]:
        return {
            "org_id": self.org_id,
            "user_id": self.user_id,
            "role": self.role,
            "hidden_widgets": self.hidden_widgets,
            "custom_widgets": self.custom_widgets,
            "layout_overrides": self.layout_overrides,
            "size_overrides": self.size_overrides,
            "custom_title": self.custom_title,
            "pinned_widgets": self.pinned_widgets,
            "saved_at": self.saved_at,
        }


class UserCustomizationManager:
    """Manages user dashboard customizations."""

    def __init__(self, registry: WidgetRegistry | None = None) -> None:
        self.registry = registry or WidgetRegistry()
        # In production, this persists to dashboard_preferences table
        self._prefs: dict[str, UserDashboardPreferences] = {}

    def _key(self, org_id: str, user_id: str) -> str:
        return f"{org_id}:{user_id}"

    def get_preferences(self, org_id: str, user_id: str) -> UserDashboardPreferences | None:
        return self._prefs.get(self._key(org_id, user_id))

    def save_preferences(
        self,
        org_id: str,
        user_id: str,
        role: str,
        hidden_widgets: list[str] | None = None,
        custom_widgets: list[dict[str, Any]] | None = None,
        layout_overrides: dict[str, list[int]] | None = None,
        size_overrides: dict[str, list[int]] | None = None,
        custom_title: str | None = None,
        pinned_widgets: list[str] | None = None,
    ) -> UserDashboardPreferences:
        prefs = UserDashboardPreferences(
            org_id=org_id,
            user_id=user_id,
            role=role,
            hidden_widgets=hidden_widgets or [],
            custom_widgets=custom_widgets or [],
            layout_overrides=layout_overrides or {},
            size_overrides=size_overrides or {},
            custom_title=custom_title,
            pinned_widgets=pinned_widgets or [],
        )
        self._prefs[self._key(org_id, user_id)] = prefs
        return prefs

    def add_widget(
        self,
        org_id: str,
        user_id: str,
        widget_type: str,
        label: str,
        config: dict[str, Any],
    ) -> dict[str, Any]:
        """Add a custom widget to the user's dashboard."""
        spec = self.registry.get(WidgetType(widget_type))
        if not spec:
            raise ValueError(f"Unknown widget type: {widget_type}")

        widget = {
            "id": f"custom_{user_id}_{len(self._prefs.get(self._key(org_id, user_id), UserDashboardPreferences(org_id, user_id, '')).custom_widgets)}",
            "type": widget_type,
            "label": label,
            "config": config,
            "component": spec.component_name,
            "category": spec.category.value,
            "size": list(spec.default_size),
            "custom": True,
        }

        prefs = self._prefs.get(self._key(org_id, user_id))
        if prefs:
            prefs.custom_widgets.append(widget)
        return widget

    def hide_widget(self, org_id: str, user_id: str, widget_id: str) -> None:
        prefs = self._prefs.get(self._key(org_id, user_id))
        if prefs and widget_id not in prefs.hidden_widgets:
            prefs.hidden_widgets.append(widget_id)

    def unhide_widget(self, org_id: str, user_id: str, widget_id: str) -> None:
        prefs = self._prefs.get(self._key(org_id, user_id))
        if prefs and widget_id in prefs.hidden_widgets:
            prefs.hidden_widgets.remove(widget_id)

    def update_layout(
        self,
        org_id: str,
        user_id: str,
        positions: dict[str, list[int]],
    ) -> None:
        prefs = self._prefs.get(self._key(org_id, user_id))
        if prefs:
            prefs.layout_overrides.update(positions)

    def reset(self, org_id: str, user_id: str) -> None:
        """Reset to auto-generated dashboard."""
        self._prefs.pop(self._key(org_id, user_id), None)
