from __future__ import annotations

import logging
import re
from collections.abc import AsyncGenerator
from uuid import UUID

from fastapi import Depends, Header, HTTPException
from sqlalchemy import select

from app.config import get_settings
from app.core.context import org_id_ctx
from app.core.exceptions import ForbiddenException, UnauthorizedException
from app.core.quota import get_quota_service
from app.core.security import decode_token, hash_password
from app.core.supabase_auth import decode_supabase_token, is_supabase_token
from app.database import async_session_factory
from app.models.organization import Organization, OrganizationMember
from app.models.user import User

logger = logging.getLogger("pix.dependencies")


async def get_token_from_header(authorization: str = Header(..., alias="Authorization")) -> str:
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise HTTPException(status_code=401, detail="Invalid authorization header")
    return token


def _raise_auth_error(error: str) -> None:
    if error == "expired":
        raise UnauthorizedException("Token has expired")
    raise UnauthorizedException("Invalid token")


def _slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug[:48] or "pix-org"


async def _sync_supabase_user(payload: dict) -> User:
    user_id = payload.get("sub")
    if not user_id:
        raise UnauthorizedException("Invalid token")

    try:
        user_uuid = UUID(user_id)
    except ValueError:
        raise UnauthorizedException("Invalid token")

    metadata = payload.get("user_metadata") or {}
    email = (payload.get("email") or metadata.get("email") or f"{user_id}@supabase.local").strip()
    full_name = (
        metadata.get("full_name")
        or metadata.get("name")
        or payload.get("full_name")
        or email.split("@")[0]
        or "πX User"
    )
    avatar_url = metadata.get("avatar_url") or payload.get("avatar_url")

    async with async_session_factory() as session:
        user = await session.get(User, user_uuid)
        if user is None:
            user = User(
                id=user_uuid,
                email=email,
                hashed_password=hash_password(f"supabase-{user_id}"),
                full_name=full_name,
                avatar_url=avatar_url,
            )
            session.add(user)
        else:
            user.email = email
            user.full_name = full_name
            user.avatar_url = avatar_url
            user.is_active = True

        await session.flush()

        member_result = await session.execute(
            select(OrganizationMember).where(OrganizationMember.user_id == user_uuid)
        )
        membership = member_result.scalar_one_or_none()
        if membership is None:
            org_name = (
                metadata.get("organization_name")
                or metadata.get("company_name")
                or full_name
                or email.split("@")[0]
                or "πX Organization"
            )
            slug_base = _slugify(org_name)
            slug = slug_base
            suffix = user_id.replace("-", "")[:6] or "org"

            while True:
                slug_result = await session.execute(
                    select(Organization.id).where(Organization.slug == slug)
                )
                if slug_result.scalar_one_or_none() is None:
                    break
                slug = f"{slug_base}-{suffix}"

            organization = Organization(name=org_name, slug=slug, owner_id=user_uuid)
            session.add(organization)
            await session.flush()
            session.add(
                OrganizationMember(
                    organization_id=organization.id,
                    user_id=user_uuid,
                    role="owner",
                )
            )

        await session.commit()
        await session.refresh(user)
        return user


async def _resolve_user_from_payload(payload: dict) -> User:
    user_id = payload.get("sub")
    if not user_id:
        raise UnauthorizedException("Invalid token")

    try:
        user_uuid = UUID(user_id)
    except ValueError:
        raise UnauthorizedException("Invalid token")

    async with async_session_factory() as session:
        user = await session.get(User, user_uuid)
        if not user:
            logger.info("Auto-provisioning backend identity for Supabase user %s", user_id)
            return await _sync_supabase_user(payload)
        return user


async def get_current_user(token: str = Depends(get_token_from_header)) -> User:
    """Authenticate via backend JWT or Supabase JWT.

    Supports the existing backend JWT tokens for direct API usage and
    Supabase access tokens sent by the frontend.
    """
    if is_supabase_token(token):
        payload = decode_supabase_token(token)
        err = payload.get("error")
        if err:
            _raise_auth_error(err)
        return await _resolve_user_from_payload(payload)

    payload = decode_token(token)
    err = payload.get("error")
    if err:
        _raise_auth_error(err)
    return await _resolve_user_from_payload(payload)


async def get_current_user_optional(
    authorization: str | None = Header(None, alias="Authorization"),
) -> User | None:
    if not authorization:
        return None
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        return None
    try:
        return await get_current_user(token)
    except Exception:
        return None


def require_admin() -> Depends:
    """Dependency factory for endpoints restricted to superusers."""
    async def _require_admin(user: User = Depends(get_current_user)) -> User:
        if not user.is_superuser:
            from app.core.exceptions import ForbiddenException
            raise ForbiddenException("Admin access required")
        return user
    return Depends(_require_admin)


def require_active_user() -> Depends:
    """Dependency factory for endpoints restricted to active users."""
    async def _require_active(user: User = Depends(get_current_user)) -> User:
        if not user.is_active:
            raise UnauthorizedException("Account is disabled")
        return user
    return Depends(_require_active)


async def get_current_org_id(
    user: User = Depends(get_current_user),
    x_org_id: str | None = Header(None, alias="X-Organization-Id"),
) -> AsyncGenerator[str, None]:
    """Resolve the current organization/workspace for the authenticated user.

    Uses the X-Organization-Id header when provided and the user is a member,
    otherwise falls back to the user's first organization, then 'default'.
    Sets a context variable so downstream services can read the org id without
    threading it through every call.
    """
    org_id: str | None = None
    user_org_ids = {str(m.organization_id) for m in user.organizations}

    if x_org_id:
        if x_org_id in user_org_ids:
            org_id = x_org_id
        else:
            raise ForbiddenException("User is not a member of this organization")
    elif user_org_ids:
        org_id = next(iter(user_org_ids))
    else:
        org_id = "default"

    token = org_id_ctx.set(org_id)
    try:
        yield org_id
    finally:
        org_id_ctx.reset(token)


def require_chat_quota() -> Depends:
    """Dependency factory that enforces the daily chat message limit per user."""
    async def _check_quota(user: User = Depends(get_current_user)) -> None:
        settings = get_settings()
        limit = settings.chat_daily_message_limit
        if limit <= 0:
            return
        service = get_quota_service()
        allowed, count = await service.check_and_increment(
            str(user.id), "chat_messages", limit
        )
        if not allowed:
            from fastapi import HTTPException

            raise HTTPException(
                status_code=429,
                detail=(
                    f"Daily chat limit reached ({limit} messages). "
                    f"Current usage: {count}."
                ),
            )

    return Depends(_check_quota)


def require_intelligence_quota() -> Depends:
    """Dependency factory that enforces the daily intelligence request limit per user."""
    async def _check_quota(user: User = Depends(get_current_user)) -> None:
        settings = get_settings()
        limit = settings.intelligence_daily_request_limit
        if limit <= 0:
            return
        service = get_quota_service()
        allowed, count = await service.check_and_increment(
            str(user.id), "intelligence_requests", limit
        )
        if not allowed:
            from fastapi import HTTPException

            raise HTTPException(
                status_code=429,
                detail=(
                    f"Daily intelligence request limit reached ({limit}). "
                    f"Current usage: {count}."
                ),
            )

    return Depends(_check_quota)
