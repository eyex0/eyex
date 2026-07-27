from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class WorkspaceCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=256)
    slug: str = Field(..., min_length=1, max_length=128, pattern=r"^[a-z0-9-]+$")
    description: str | None = Field(None, max_length=2000)
    is_default: bool = False


class WorkspaceUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=256)
    description: str | None = Field(None, max_length=2000)
    settings: dict | None = None


class WorkspaceRead(BaseModel):
    id: str
    organization_id: str
    name: str
    slug: str
    description: str | None
    is_default: bool
    settings: dict | None
    created_at: datetime
    updated_at: datetime
    member_count: int = 0

    model_config = {"from_attributes": True}


class WorkspaceMemberAdd(BaseModel):
    user_id: str
    role: str = Field("member", pattern=r"^(admin|member|viewer)$")


class WorkspaceMemberUpdate(BaseModel):
    role: str = Field(..., pattern=r"^(admin|member|viewer)$")


class WorkspaceMemberRead(BaseModel):
    id: str
    workspace_id: str
    user_id: str
    role: str
    created_at: datetime
    user_email: str | None = None
    user_name: str | None = None

    model_config = {"from_attributes": True}


class WorkspaceList(BaseModel):
    workspaces: list[WorkspaceRead]
    total: int


class AgentConfigCreate(BaseModel):
    agent_role: str = Field(..., min_length=1, max_length=100)
    display_name: str = Field(..., min_length=1, max_length=256)
    description: str | None = Field(None, max_length=2000)
    is_enabled: bool = True
    model: str | None = Field(None, max_length=128)
    temperature: float | None = Field(None, ge=0.0, le=2.0)
    max_tokens: int | None = Field(None, ge=1, le=128000)
    config: dict | None = None


class AgentConfigUpdate(BaseModel):
    display_name: str | None = Field(None, min_length=1, max_length=256)
    description: str | None = Field(None, max_length=2000)
    is_enabled: bool | None = None
    model: str | None = Field(None, max_length=128)
    temperature: float | None = Field(None, ge=0.0, le=2.0)
    max_tokens: int | None = Field(None, ge=1, le=128000)
    config: dict | None = None


class AgentConfigRead(BaseModel):
    id: str
    workspace_id: str
    agent_role: str
    display_name: str
    description: str | None
    is_enabled: bool
    model: str | None
    temperature: float | None
    max_tokens: int | None
    config: dict | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class TaskExecutionRead(BaseModel):
    id: str
    workspace_id: str
    user_id: str | None
    session_id: str | None
    agent_role: str | None
    input_text: str | None
    output_text: str | None
    status: str
    duration_ms: int | None
    steps: dict | None
    error: str | None
    tokens_used: int | None
    cost: float | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class TaskExecutionList(BaseModel):
    tasks: list[TaskExecutionRead]
    total: int
    page: int
    per_page: int


class ApiKeyCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=256)
    expires_at: datetime | None = None
    permissions: dict | None = None


class ApiKeyRead(BaseModel):
    id: str
    workspace_id: str
    user_id: str
    name: str
    key_prefix: str
    is_active: bool
    last_used_at: datetime | None
    expires_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


class ApiKeyCreated(ApiKeyRead):
    raw_key: str


class ApiKeyList(BaseModel):
    api_keys: list[ApiKeyRead]
    total: int
