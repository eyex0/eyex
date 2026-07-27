from __future__ import annotations

import os
from collections.abc import AsyncGenerator

import pytest
from httpx import ASGITransport, AsyncClient

os.environ.setdefault("OPENAI_API_KEY", "test-key-for-testing")
os.environ.setdefault("RATE_LIMIT_ENABLED", "false")

from app.config import get_settings
from app.main import app


@pytest.fixture
def settings():
    return get_settings()


@pytest.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
