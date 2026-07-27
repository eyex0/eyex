from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from app.dependencies import get_current_user
from app.main import app


@pytest.fixture
async def authed_client() -> AsyncClient:
    async def mock_user():
        from app.models.user import User
        u = User(
            id="00000000-0000-0000-0000-000000000001",
            email="admin@test.com",
            hashed_password="x",
            is_superuser=True,
        )
        return u
    app.dependency_overrides[get_current_user] = mock_user
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_admin_stats_requires_auth():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/v1/admin/stats")
    assert resp.status_code in (401, 403, 422)


@pytest.mark.asyncio
async def test_admin_sessions_requires_auth():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/v1/admin/sessions")
    assert resp.status_code in (401, 403, 422)


@pytest.mark.asyncio
async def test_admin_agents_requires_auth():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/v1/admin/agents")
    assert resp.status_code in (401, 403, 422)


@pytest.mark.asyncio
async def test_admin_health_detailed_requires_auth():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/v1/admin/health/detailed")
    assert resp.status_code in (401, 403, 422)


@pytest.mark.asyncio
async def test_admin_stats_with_auth(authed_client: AsyncClient):
    resp = await authed_client.get("/api/v1/admin/stats")
    assert resp.status_code in (200, 422)


@pytest.mark.asyncio
async def test_admin_agents_with_auth(authed_client: AsyncClient):
    resp = await authed_client.get("/api/v1/admin/agents")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, dict)


@pytest.mark.asyncio
async def test_token_refresh_rejects_query_param():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/api/v1/auth/refresh?refresh_token=fake")
    assert resp.status_code in (405, 422)
