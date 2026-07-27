from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password, verify_password
from app.models.user import User
from app.schemas.auth import LoginRequest, RegisterRequest


class AuthService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def register(self, body: RegisterRequest) -> User:
        existing = await self.db.execute(select(User).where(User.email == body.email))
        if existing.scalar_one_or_none():
            from app.core.exceptions import ValidationException

            raise ValidationException("Email already registered")

        user = User(
            email=body.email,
            hashed_password=hash_password(body.password),
            full_name=body.full_name,
        )
        self.db.add(user)
        await self.db.flush()
        await self.db.refresh(user)
        return user

    async def authenticate(self, body: LoginRequest) -> User:
        result = await self.db.execute(select(User).where(User.email == body.email))
        user = result.scalar_one_or_none()
        if not user or not verify_password(body.password, user.hashed_password):
            from app.core.exceptions import UnauthorizedException

            raise UnauthorizedException("Invalid email or password")
        return user
