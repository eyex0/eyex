from pydantic import BaseModel


class SystemStatus(BaseModel):
    status: str
    uptime_seconds: float
    sessions_active: int
    workflows_completed: int
    workflows_failed: int
    memory_health: dict | None = None
    tools_count: int


class SessionInfo(BaseModel):
    session_id: str
    message_count: int
    last_activity: str | None = None


class SessionList(BaseModel):
    sessions: list[SessionInfo]


class WorkflowStatusResponse(BaseModel):
    thread_id: str
    status: str
    steps: list[dict] = []
    output: str | None = None
    error: str | None = None
