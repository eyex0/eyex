"""
πX Dashboard Data Service — Real-time data layer with SSE/WebSocket support.

Provides live KPI updates, event-driven refresh, and WebSocket/SSE streaming
for dashboard widgets. Events: DATA_UPDATED, KPI_CHANGED, DECISION_CREATED,
AGENT_COMPLETED.
"""
from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any, AsyncIterator, Callable

from fastapi import WebSocket


class DashboardEventType(StrEnum):
    DATA_UPDATED = "DATA_UPDATED"
    KPI_CHANGED = "KPI_CHANGED"
    DECISION_CREATED = "DECISION_CREATED"
    DECISION_UPDATED = "DECISION_UPDATED"
    AGENT_COMPLETED = "AGENT_COMPLETED"
    AGENT_STARTED = "AGENT_STARTED"
    ALERT_TRIGGERED = "ALERT_TRIGGERED"
    PROFILE_UPDATED = "PROFILE_UPDATED"
    WORKFLOW_COMPLETED = "WORKFLOW_COMPLETED"
    QUALITY_CHANGED = "QUALITY_CHANGED"


@dataclass
class DashboardEvent:
    event_type: DashboardEventType
    org_id: str
    payload: dict[str, Any]
    timestamp: str = field(default_factory=lambda: datetime.now(UTC).isoformat())

    def to_json(self) -> dict[str, Any]:
        return {
            "event_type": self.event_type.value,
            "org_id": self.org_id,
            "payload": self.payload,
            "timestamp": self.timestamp,
        }


class DashboardDataService:
    """Real-time data service for dashboard updates via SSE and WebSocket."""

    def __init__(self) -> None:
        # org_id → set of WebSocket connections
        self._ws_connections: dict[str, set[WebSocket]] = {}
        # org_id → list of SSE subscriber queues
        self._sse_subscribers: dict[str, list[asyncio.Queue]] = {}
        # org_id → cached KPI values
        self._kpi_cache: dict[str, dict[str, Any]] = {}
        # Event history per org (last 100 events)
        self._event_history: dict[str, list[DashboardEvent]] = {}

    # ── WebSocket ──

    async def connect_ws(self, org_id: str, websocket: WebSocket) -> None:
        await websocket.accept()
        if org_id not in self._ws_connections:
            self._ws_connections[org_id] = set()
        self._ws_connections[org_id].add(websocket)

    async def disconnect_ws(self, org_id: str, websocket: WebSocket) -> None:
        if org_id in self._ws_connections:
            self._ws_connections[org_id].discard(websocket)
            if not self._ws_connections[org_id]:
                del self._ws_connections[org_id]

    async def _broadcast_ws(self, org_id: str, event: DashboardEvent) -> None:
        if org_id not in self._ws_connections:
            return
        dead: list[WebSocket] = []
        for ws in self._ws_connections[org_id]:
            try:
                await ws.send_json(event.to_json())
            except Exception:
                dead.append(ws)
        for ws in dead:
            self._ws_connections[org_id].discard(ws)

    # ── SSE ──

    async def subscribe_sse(self, org_id: str) -> AsyncIterator[str]:
        """Yield SSE-formatted events for an org."""
        queue: asyncio.Queue[DashboardEvent] = asyncio.Queue()
        if org_id not in self._sse_subscribers:
            self._sse_subscribers[org_id] = []
        self._sse_subscribers[org_id].append(queue)
        try:
            while True:
                event = await queue.get()
                yield f"data: {json.dumps(event.to_json())}\n\n"
        finally:
            if org_id in self._sse_subscribers:
                self._sse_subscribers[org_id].remove(queue)
                if not self._sse_subscribers[org_id]:
                    del self._sse_subscribers[org_id]

    async def _broadcast_sse(self, org_id: str, event: DashboardEvent) -> None:
        if org_id not in self._sse_subscribers:
            return
        for queue in self._sse_subscribers[org_id]:
            await queue.put(event)

    # ── Event Publishing ──

    async def publish_event(
        self,
        event_type: DashboardEventType,
        org_id: str,
        payload: dict[str, Any],
    ) -> DashboardEvent:
        event = DashboardEvent(
            event_type=event_type,
            org_id=org_id,
            payload=payload,
        )
        # Store in history
        if org_id not in self._event_history:
            self._event_history[org_id] = []
        self._event_history[org_id].append(event)
        self._event_history[org_id] = self._event_history[org_id][-100:]
        # Broadcast to all subscribers
        await self._broadcast_ws(org_id, event)
        await self._broadcast_sse(org_id, event)
        return event

    # ── KPI Cache ──

    async def update_kpi(self, org_id: str, kpi_name: str, value: Any) -> None:
        if org_id not in self._kpi_cache:
            self._kpi_cache[org_id] = {}
        old_value = self._kpi_cache[org_id].get(kpi_name)
        self._kpi_cache[org_id][kpi_name] = value
        if old_value != value:
            await self.publish_event(
                DashboardEventType.KPI_CHANGED,
                org_id,
                {"kpi": kpi_name, "old_value": old_value, "new_value": value},
            )

    async def get_kpis(self, org_id: str) -> dict[str, Any]:
        return self._kpi_cache.get(org_id, {})

    # ── Event History ──

    def get_event_history(self, org_id: str, limit: int = 50) -> list[dict[str, Any]]:
        events = self._event_history.get(org_id, [])
        return [e.to_json() for e in events[-limit:]]

    # ── Helper to emit from external systems ──

    async def on_data_updated(self, org_id: str, source: str, records: int) -> None:
        await self.publish_event(
            DashboardEventType.DATA_UPDATED,
            org_id,
            {"source": source, "records": records},
        )

    async def on_decision_created(self, org_id: str, decision_id: str, title: str) -> None:
        await self.publish_event(
            DashboardEventType.DECISION_CREATED,
            org_id,
            {"decision_id": decision_id, "title": title},
        )

    async def on_agent_completed(self, org_id: str, agent_name: str, result: Any) -> None:
        await self.publish_event(
            DashboardEventType.AGENT_COMPLETED,
            org_id,
            {"agent": agent_name, "result": result},
        )
