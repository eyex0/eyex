from __future__ import annotations

import json
import logging
from typing import Any

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect
from sqlalchemy import select

from app.database import async_session_factory
from app.models.workspace import Workspace, WorkspaceMember

logger = logging.getLogger("pix.api.activity")

activity_router = APIRouter(tags=["Activity"])


class ConnectionManager:
    def __init__(self):
        self._connections: dict[str, list[WebSocket]] = {}

    async def connect(self, workspace_id: str, ws: WebSocket):
        await ws.accept()
        if workspace_id not in self._connections:
            self._connections[workspace_id] = []
        self._connections[workspace_id].append(ws)

    def disconnect(self, workspace_id: str, ws: WebSocket):
        if workspace_id in self._connections:
            self._connections[workspace_id] = [c for c in self._connections[workspace_id] if c != ws]
            if not self._connections[workspace_id]:
                del self._connections[workspace_id]

    async def broadcast(self, workspace_id: str, event: dict[str, Any]):
        if workspace_id not in self._connections:
            return
        payload = json.dumps(event, default=str)
        dead = []
        for ws in self._connections[workspace_id]:
            try:
                await ws.send_text(payload)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(workspace_id, ws)

    async def broadcast_task_update(
        self,
        workspace_id: str,
        task_id: str,
        status: str,
        agent_role: str | None = None,
        message: str | None = None,
        extra: dict[str, Any] | None = None,
    ):
        event = {
            "type": "task_update",
            "task_id": task_id,
            "status": status,
            "agent_role": agent_role,
            "message": message,
        }
        if extra:
            event.update(extra)
        await self.broadcast(workspace_id, event)

    async def broadcast_agent_status(
        self,
        workspace_id: str,
        agent_role: str,
        status: str,
        message: str | None = None,
    ):
        event = {
            "type": "agent_status",
            "agent_role": agent_role,
            "status": status,
            "message": message,
        }
        await self.broadcast(workspace_id, event)


manager = ConnectionManager()


def get_activity_manager() -> ConnectionManager:
    return manager


@activity_router.websocket("/ws/activity/{workspace_id}")
async def activity_websocket(
    ws: WebSocket,
    workspace_id: str,
    token: str = Query(...),
):
    from app.core.security import decode_token

    payload = decode_token(token)
    if payload.get("error"):
        await ws.close(code=4001, reason="Invalid or expired token")
        return

    user_id = payload.get("sub")
    if not user_id:
        await ws.close(code=4001, reason="Invalid token payload")
        return

    async with async_session_factory() as db:
        ws_workspace = await db.get(Workspace, workspace_id)
        if not ws_workspace:
            await ws.close(code=4004, reason="Workspace not found")
            return

        membership = await db.execute(
            select(WorkspaceMember).where(
                WorkspaceMember.workspace_id == workspace_id,
                WorkspaceMember.user_id == user_id,
            )
        )
        if not membership.scalar_one_or_none():
            await ws.close(code=4003, reason="Not a member of this workspace")
            return

    await manager.connect(workspace_id, ws)
    logger.info("Activity WS connected: workspace=%s user=%s", workspace_id, user_id)

    try:
        while True:
            data = await ws.receive_text()
            try:
                msg = json.loads(data)
                msg_type = msg.get("type", "")
                if msg_type == "ping":
                    await ws.send_text(json.dumps({"type": "pong"}))
            except json.JSONDecodeError:
                pass
    except WebSocketDisconnect:
        manager.disconnect(workspace_id, ws)
        logger.info("Activity WS disconnected: workspace=%s", workspace_id)
    except Exception:
        manager.disconnect(workspace_id, ws)
        raise
