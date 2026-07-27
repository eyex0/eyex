from __future__ import annotations
import secrets

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import UnauthorizedException
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.database import get_db_session
from app.models.user import User
from app.schemas.auth import LoginRequest, RefreshRequest, RegisterRequest, TokenResponse
from app.schemas.user import UserRead

auth_router = APIRouter(prefix="/auth", tags=["Authentication"])


@auth_router.post("/register", response_model=UserRead, status_code=201)
async def register(body: RegisterRequest, db: AsyncSession = Depends(get_db_session)):
    from sqlalchemy import select

    existing = await db.execute(select(User).where(User.email == body.email))
    if existing.scalar_one_or_none():
        from app.core.exceptions import ValidationException

        raise ValidationException("Email already registered")

    user = User(
        email=body.email,
        hashed_password=hash_password(body.password),
        full_name=body.full_name,
    )
    db.add(user)
    await db.flush()
    await db.refresh(user)
    return UserRead.model_validate(user)


@auth_router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, db: AsyncSession = Depends(get_db_session)):
    from sqlalchemy import select

    result = await db.execute(select(User).where(User.email == body.email))
    user = result.scalar_one_or_none()

    if not user or not verify_password(body.password, user.hashed_password):
        raise UnauthorizedException("Invalid email or password")

    access_token, expires_in = create_access_token(str(user.id))
    refresh_token, _ = create_refresh_token(str(user.id))

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=expires_in,
    )


@auth_router.post("/refresh", response_model=TokenResponse)
async def refresh(body: RefreshRequest):
    payload = decode_token(body.refresh_token)
    if not payload or payload.get("type") != "refresh":
        raise UnauthorizedException("Invalid or expired refresh token")

    user_id = payload.get("sub")
    if not user_id:
        raise UnauthorizedException("Invalid refresh token payload")

    access_token, expires_in = create_access_token(user_id)
    new_refresh, _ = create_refresh_token(user_id)

    return TokenResponse(
        access_token=access_token,
        refresh_token=new_refresh,
        expires_in=expires_in,
    )

from pydantic import BaseModel


class GoogleAuthRequest(BaseModel):
    supabase_access_token: str


@auth_router.post("/google", response_model=TokenResponse)
async def google_login(body: GoogleAuthRequest, db: AsyncSession = Depends(get_db_session)):
    """Exchange a Supabase Google OAuth token for a πX JWT."""
    import httpx
    from app.config import get_settings

    settings = get_settings()

    # Verify the Supabase token by calling Supabase's user endpoint
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(
            f"{settings.supabase_url}/auth/v1/user",
            headers={
                "Authorization": f"Bearer {body.supabase_access_token}",
                "apikey": settings.supabase_anon_key,
            },
        )
        if resp.status_code != 200:
            raise UnauthorizedException("Invalid or expired Google OAuth token")

        supabase_user = resp.json()

    email = supabase_user.get("email")
    if not email:
        raise UnauthorizedException("No email returned from Google OAuth")

    # Find or create the user
    from sqlalchemy import select

    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()

    if not user:
        # Create new user from Google OAuth
        user_metadata = supabase_user.get("user_metadata", {})
        full_name = user_metadata.get("full_name") or user_metadata.get("name") or email.split("@")[0]
        user = User(
            email=email,
            hashed_password=hash_password(secrets.token_urlsafe(32)),  # Random password for OAuth users
            full_name=full_name,
        )
        db.add(user)
        await db.flush()
        await db.refresh(user)

    # Generate πX JWT tokens
    access_token, expires_in = create_access_token(str(user.id))
    refresh_token, _ = create_refresh_token(str(user.id))

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=expires_in,
    )
