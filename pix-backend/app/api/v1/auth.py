from __future__ import annotations

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
