from __future__ import annotations

import logging
import secrets

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ForbiddenException, NotFoundException, ValidationException
from app.core.security import hash_password
from app.database import get_db_session
from app.dependencies import get_current_user
from app.models.organization import Organization, OrganizationMember
from app.models.user import User
from app.models.workspace import (
    AgentConfig,
    ApiKey,
    TaskExecution,
    Workspace,
    WorkspaceMember,
)
from app.schemas.workspace import (
    AgentConfigRead,
    AgentConfigUpdate,
    ApiKeyCreate,
    ApiKeyCreated,
    ApiKeyList,
    ApiKeyRead,
    TaskExecutionList,
    TaskExecutionRead,
    WorkspaceCreate,
    WorkspaceList,
    WorkspaceMemberAdd,
    WorkspaceMemberRead,
    WorkspaceMemberUpdate,
    WorkspaceRead,
    WorkspaceUpdate,
)

logger = logging.getLogger("pix.api.workspaces")

workspaces_router = APIRouter(prefix="/workspaces", tags=["Workspaces"])


async def _get_org_for_user(db: AsyncSession, user_id: str) -> Organization:
    result = await db.execute(
        select(Organization)
        .join(OrganizationMember)
        .where(
            OrganizationMember.user_id == user_id,
            OrganizationMember.role.in_(["admin", "owner"]),
        )
    )
    org = result.scalar_one_or_none()
    if not org:
        result = await db.execute(
            select(Organization)
            .join(OrganizationMember)
            .where(OrganizationMember.user_id == user_id)
        )
        org = result.scalar_one_or_none()
    if not org:
        raise NotFoundException("Organization")
    return org


async def _get_workspace_for_user(
    db: AsyncSession, workspace_id: str, user_id: str, require_admin: bool = False
) -> Workspace:
    result = await db.execute(
        select(Workspace).where(Workspace.id == workspace_id)
    )
    ws = result.scalar_one_or_none()
    if not ws:
        raise NotFoundException("Workspace")

    membership = await db.execute(
        select(WorkspaceMember).where(
            WorkspaceMember.workspace_id == workspace_id,
            WorkspaceMember.user_id == user_id,
        )
    )
    member = membership.scalar_one_or_none()
    if not member:
        org = await db.execute(
            select(Organization).join(OrganizationMember).where(
                OrganizationMember.user_id == user_id,
                OrganizationMember.role.in_(["admin", "owner"]),
                Organization.id == ws.organization_id,
            )
        )
        if not org.scalar_one_or_none():
            raise ForbiddenException("Not a member of this workspace")

    if require_admin and member and member.role not in ("admin", "owner"):
        raise ForbiddenException("Admin access required")

    return ws


@workspaces_router.get("", response_model=WorkspaceList)
async def list_workspaces(
    db: AsyncSession = Depends(get_db_session),
    user: User = Depends(get_current_user),
):
    org = await _get_org_for_user(db, str(user.id))
    result = await db.execute(
        select(Workspace).where(Workspace.organization_id == org.id).order_by(Workspace.created_at)
    )
    workspaces = result.scalars().all()
    items = []
    for ws in workspaces:
        member_count = await db.scalar(
            select(func.count()).select_from(WorkspaceMember).where(WorkspaceMember.workspace_id == ws.id)
        )
        data = WorkspaceRead.model_validate(ws)
        data.member_count = member_count or 0
        items.append(data)
    return WorkspaceList(workspaces=items, total=len(items))


@workspaces_router.post("", response_model=WorkspaceRead, status_code=201)
async def create_workspace(
    body: WorkspaceCreate,
    db: AsyncSession = Depends(get_db_session),
    user: User = Depends(get_current_user),
):
    org = await _get_org_for_user(db, str(user.id))

    existing = await db.execute(
        select(Workspace).where(
            Workspace.organization_id == org.id,
            Workspace.slug == body.slug,
        )
    )
    if existing.scalar_one_or_none():
        raise ValidationException(f"Workspace slug '{body.slug}' already exists")

    ws = Workspace(
        organization_id=org.id,
        name=body.name,
        slug=body.slug,
        description=body.description,
        is_default=body.is_default,
    )
    db.add(ws)
    await db.flush()

    membership = WorkspaceMember(
        workspace_id=ws.id,
        user_id=user.id,
        role="admin",
    )
    db.add(membership)

    for role in ("supervisor", "planner", "researcher", "coder", "reviewer", "tester", "documenter", "devops"):
        cfg = AgentConfig(
            workspace_id=ws.id,
            agent_role=role,
            display_name=role.capitalize(),
            is_enabled=True,
        )
        db.add(cfg)

    await db.refresh(ws)
    return WorkspaceRead.model_validate(ws)


@workspaces_router.get("/{workspace_id}", response_model=WorkspaceRead)
async def get_workspace(
    workspace_id: str,
    db: AsyncSession = Depends(get_db_session),
    user: User = Depends(get_current_user),
):
    ws = await _get_workspace_for_user(db, workspace_id, str(user.id))
    member_count = await db.scalar(
        select(func.count()).select_from(WorkspaceMember).where(WorkspaceMember.workspace_id == ws.id)
    )
    data = WorkspaceRead.model_validate(ws)
    data.member_count = member_count or 0
    return data


@workspaces_router.patch("/{workspace_id}", response_model=WorkspaceRead)
async def update_workspace(
    workspace_id: str,
    body: WorkspaceUpdate,
    db: AsyncSession = Depends(get_db_session),
    user: User = Depends(get_current_user),
):
    ws = await _get_workspace_for_user(db, workspace_id, str(user.id), require_admin=True)
    if body.name is not None:
        ws.name = body.name
    if body.description is not None:
        ws.description = body.description
    if body.settings is not None:
        ws.settings = body.settings
    await db.flush()
    await db.refresh(ws)
    return WorkspaceRead.model_validate(ws)


@workspaces_router.delete("/{workspace_id}", status_code=204)
async def delete_workspace(
    workspace_id: str,
    db: AsyncSession = Depends(get_db_session),
    user: User = Depends(get_current_user),
):
    ws = await _get_workspace_for_user(db, workspace_id, str(user.id), require_admin=True)
    await db.delete(ws)


@workspaces_router.get("/{workspace_id}/members", response_model=list[WorkspaceMemberRead])
async def list_members(
    workspace_id: str,
    db: AsyncSession = Depends(get_db_session),
    user: User = Depends(get_current_user),
):
    ws = await _get_workspace_for_user(db, workspace_id, str(user.id))
    result = await db.execute(
        select(WorkspaceMember, User.email, User.full_name)
        .join(User, WorkspaceMember.user_id == User.id)
        .where(WorkspaceMember.workspace_id == ws.id)
    )
    rows = result.all()
    items = []
    for member, email, full_name in rows:
        data = WorkspaceMemberRead.model_validate(member)
        data.user_email = email
        data.user_name = full_name
        items.append(data)
    return items


@workspaces_router.post("/{workspace_id}/members", response_model=WorkspaceMemberRead, status_code=201)
async def add_member(
    workspace_id: str,
    body: WorkspaceMemberAdd,
    db: AsyncSession = Depends(get_db_session),
    user: User = Depends(get_current_user),
):
    ws = await _get_workspace_for_user(db, workspace_id, str(user.id), require_admin=True)

    target = await db.get(User, body.user_id)
    if not target:
        raise NotFoundException("User")

    existing = await db.execute(
        select(WorkspaceMember).where(
            WorkspaceMember.workspace_id == ws.id,
            WorkspaceMember.user_id == body.user_id,
        )
    )
    if existing.scalar_one_or_none():
        raise ValidationException("User is already a member")

    member = WorkspaceMember(
        workspace_id=ws.id,
        user_id=body.user_id,
        role=body.role,
    )
    db.add(member)
    await db.flush()
    await db.refresh(member)

    data = WorkspaceMemberRead.model_validate(member)
    data.user_email = target.email
    data.user_name = target.full_name
    return data


@workspaces_router.patch("/{workspace_id}/members/{member_id}", response_model=WorkspaceMemberRead)
async def update_member_role(
    workspace_id: str,
    member_id: str,
    body: WorkspaceMemberUpdate,
    db: AsyncSession = Depends(get_db_session),
    user: User = Depends(get_current_user),
):
    await _get_workspace_for_user(db, workspace_id, str(user.id), require_admin=True)
    result = await db.execute(
        select(WorkspaceMember).where(WorkspaceMember.id == member_id)
    )
    member = result.scalar_one_or_none()
    if not member:
        raise NotFoundException("Member")
    member.role = body.role
    await db.flush()
    await db.refresh(member)
    return WorkspaceMemberRead.model_validate(member)


@workspaces_router.delete("/{workspace_id}/members/{member_id}", status_code=204)
async def remove_member(
    workspace_id: str,
    member_id: str,
    db: AsyncSession = Depends(get_db_session),
    user: User = Depends(get_current_user),
):
    await _get_workspace_for_user(db, workspace_id, str(user.id), require_admin=True)
    result = await db.execute(
        select(WorkspaceMember).where(WorkspaceMember.id == member_id)
    )
    member = result.scalar_one_or_none()
    if not member:
        raise NotFoundException("Member")
    await db.delete(member)


@workspaces_router.get("/{workspace_id}/agents", response_model=list[AgentConfigRead])
async def list_agent_configs(
    workspace_id: str,
    db: AsyncSession = Depends(get_db_session),
    user: User = Depends(get_current_user),
):
    ws = await _get_workspace_for_user(db, workspace_id, str(user.id))
    result = await db.execute(
        select(AgentConfig)
        .where(AgentConfig.workspace_id == ws.id)
        .order_by(AgentConfig.agent_role)
    )
    return [AgentConfigRead.model_validate(cfg) for cfg in result.scalars().all()]


@workspaces_router.patch("/{workspace_id}/agents/{config_id}", response_model=AgentConfigRead)
async def update_agent_config(
    workspace_id: str,
    config_id: str,
    body: AgentConfigUpdate,
    db: AsyncSession = Depends(get_db_session),
    user: User = Depends(get_current_user),
):
    await _get_workspace_for_user(db, workspace_id, str(user.id), require_admin=True)
    result = await db.execute(
        select(AgentConfig).where(
            AgentConfig.id == config_id,
            AgentConfig.workspace_id == workspace_id,
        )
    )
    cfg = result.scalar_one_or_none()
    if not cfg:
        raise NotFoundException("Agent config")
    if body.display_name is not None:
        cfg.display_name = body.display_name
    if body.description is not None:
        cfg.description = body.description
    if body.is_enabled is not None:
        cfg.is_enabled = body.is_enabled
    if body.model is not None:
        cfg.model = body.model
    if body.temperature is not None:
        cfg.temperature = body.temperature
    if body.max_tokens is not None:
        cfg.max_tokens = body.max_tokens
    if body.config is not None:
        cfg.config = body.config
    await db.flush()
    await db.refresh(cfg)
    return AgentConfigRead.model_validate(cfg)


@workspaces_router.get("/{workspace_id}/tasks", response_model=TaskExecutionList)
async def list_tasks(
    workspace_id: str,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    status_filter: str | None = Query(None, alias="status"),
    db: AsyncSession = Depends(get_db_session),
    user: User = Depends(get_current_user),
):
    ws = await _get_workspace_for_user(db, workspace_id, str(user.id))
    query = select(TaskExecution).where(TaskExecution.workspace_id == ws.id)
    count_query = select(func.count()).select_from(TaskExecution).where(TaskExecution.workspace_id == ws.id)
    if status_filter:
        query = query.where(TaskExecution.status == status_filter)
        count_query = count_query.where(TaskExecution.status == status_filter)
    query = query.order_by(TaskExecution.created_at.desc()).offset((page - 1) * per_page).limit(per_page)
    result = await db.execute(query)
    tasks = [TaskExecutionRead.model_validate(t) for t in result.scalars().all()]
    total = await db.scalar(count_query)
    return TaskExecutionList(tasks=tasks, total=total or 0, page=page, per_page=per_page)


@workspaces_router.get("/{workspace_id}/tasks/{task_id}", response_model=TaskExecutionRead)
async def get_task(
    workspace_id: str,
    task_id: str,
    db: AsyncSession = Depends(get_db_session),
    user: User = Depends(get_current_user),
):
    await _get_workspace_for_user(db, workspace_id, str(user.id))
    result = await db.execute(
        select(TaskExecution).where(
            TaskExecution.id == task_id,
            TaskExecution.workspace_id == workspace_id,
        )
    )
    task = result.scalar_one_or_none()
    if not task:
        raise NotFoundException("Task")
    return TaskExecutionRead.model_validate(task)


@workspaces_router.get("/{workspace_id}/api-keys", response_model=ApiKeyList)
async def list_api_keys(
    workspace_id: str,
    db: AsyncSession = Depends(get_db_session),
    user: User = Depends(get_current_user),
):
    await _get_workspace_for_user(db, workspace_id, str(user.id), require_admin=True)
    result = await db.execute(
        select(ApiKey).where(ApiKey.workspace_id == workspace_id).order_by(ApiKey.created_at.desc())
    )
    keys = [ApiKeyRead.model_validate(k) for k in result.scalars().all()]
    return ApiKeyList(api_keys=keys, total=len(keys))


@workspaces_router.post("/{workspace_id}/api-keys", response_model=ApiKeyCreated, status_code=201)
async def create_api_key(
    workspace_id: str,
    body: ApiKeyCreate,
    db: AsyncSession = Depends(get_db_session),
    user: User = Depends(get_current_user),
):
    await _get_workspace_for_user(db, workspace_id, str(user.id), require_admin=True)

    raw_key = f"pix_{secrets.token_urlsafe(32)}"
    key_hash = hash_password(raw_key)
    key_prefix = raw_key[:16]

    api_key = ApiKey(
        workspace_id=workspace_id,
        user_id=user.id,
        name=body.name,
        key_hash=key_hash,
        key_prefix=key_prefix,
        expires_at=body.expires_at,
        permissions=body.permissions,
    )
    db.add(api_key)
    await db.flush()
    await db.refresh(api_key)

    data = ApiKeyCreated.model_validate(api_key)
    data.raw_key = raw_key
    return data


@workspaces_router.delete("/{workspace_id}/api-keys/{key_id}", status_code=204)
async def delete_api_key(
    workspace_id: str,
    key_id: str,
    db: AsyncSession = Depends(get_db_session),
    user: User = Depends(get_current_user),
):
    await _get_workspace_for_user(db, workspace_id, str(user.id), require_admin=True)
    result = await db.execute(
        select(ApiKey).where(ApiKey.id == key_id, ApiKey.workspace_id == workspace_id)
    )
    key = result.scalar_one_or_none()
    if not key:
        raise NotFoundException("API key")
    await db.delete(key)
