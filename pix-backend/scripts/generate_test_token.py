"""Generate a backend JWT access token for local API testing.

Usage:
    cd pix-backend
    python scripts/generate_test_token.py [email]

The token is signed with APP_SECRET_KEY and can be used against protected
endpoints when Supabase auth is not configured locally:
    curl -H "Authorization: Bearer <token>" http://localhost:8000/api/v1/workspaces
"""
from __future__ import annotations

import asyncio
import os
import sys
from uuid import UUID

backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, backend_dir)

from sqlalchemy import select  # noqa: E402
from sqlalchemy.ext.asyncio import AsyncSession  # noqa: E402

from app.core.security import create_access_token  # noqa: E402
from app.database import async_session_factory  # noqa: E402
from app.models.user import User  # noqa: E402

DEFAULT_EMAIL = "demo@pix.local"


async def generate(email: str) -> str:
    async with async_session_factory() as session:  # type: ignore[var-annotated]
        user = await _fetch_user(session, email)
        token, _expires_in = create_access_token(str(user.id))
        return token


async def _fetch_user(session: AsyncSession, email: str) -> User:
    result = await session.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    if not user:
        raise RuntimeError(f"User not found: {email}. Run scripts/seed_demo.py first.")
    # Validate UUID shape
    UUID(str(user.id))
    return user


if __name__ == "__main__":
    email = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_EMAIL
    try:
        token = asyncio.run(generate(email))
        print(token)
    except Exception as exc:  # pragma: no cover - CLI helper
        print(f"Failed to generate token: {exc}", file=sys.stderr)
        sys.exit(1)
