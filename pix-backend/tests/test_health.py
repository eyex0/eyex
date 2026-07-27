from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_check(client: AsyncClient):
    response = await client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ("ok", "degraded")
    assert data["service"] == "πX Technologies"
    assert "timestamp" in data
    assert "version" in data
    assert "dependencies" in data
    assert "uptime_seconds" in data
