from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, EmailStr


class UserCreate(BaseModel):
    email: EmailStr
    password: str
    full_name: str | None = None


class UserUpdate(BaseModel):
    full_name: str | None = None
    preferences: str | None = None


class UserRead(BaseModel):
    id: str
    email: str
    full_name: str | None
    is_active: bool
    is_superuser: bool
    created_at: datetime
    last_login_at: datetime | None
    avatar_url: str | None

    model_config = {"from_attributes": True}
