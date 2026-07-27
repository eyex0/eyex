"""Verify that local πX backend dependencies and services are reachable.

Usage:
    cd pix-backend
    python scripts/check_local.py
"""
from __future__ import annotations

import asyncio
import os
import socket
import sys

backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, backend_dir)

from app.config import get_settings  # noqa: E402


def _reachable(host: str, port: int, timeout: float = 1.0) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


async def check() -> None:
    settings = get_settings()
    print(f"APP_ENVIRONMENT={settings.app_environment}")
    print(f"DATABASE_URL={settings.database_url}")
    print(f"REDIS_URL={settings.redis_url}")

    # Parse Postgres host/port from URL (very simple parser for local dev)
    db_url = settings.database_url
    db_host, db_port = "localhost", 5432
    if "@" in db_url:
        host_port = db_url.split("@")[-1].split("/")[0]
        if ":" in host_port:
            db_host, db_port_str = host_port.split(":", 1)
            db_port = int(db_port_str)
        else:
            db_host = host_port

    redis_host, redis_port = "localhost", 6379
    redis_url = settings.redis_url
    if redis_url.startswith("redis://"):
        parts = redis_url.replace("redis://", "").split("/")[0]
        if "@" in parts:
            parts = parts.split("@")[-1]
        if ":" in parts:
            redis_host, redis_port_str = parts.split(":", 1)
            redis_port = int(redis_port_str)
        else:
            redis_host = parts

    checks = [
        ("PostgreSQL", db_host, db_port),
        ("Redis", redis_host, redis_port),
        ("Backend HTTP", "127.0.0.1", settings.port),
    ]

    all_ok = True
    for name, host, port in checks:
        ok = _reachable(host, port)
        status = "OK" if ok else "UNREACHABLE"
        print(f"{name} ({host}:{port}): {status}")
        if not ok:
            all_ok = False

    # Optional: check OpenAI key presence (do not print the key)
    placeholder_keys = {"sk-...", "sk-", "", "your-openai-key-here"}
    if not settings.openai_api_key or settings.openai_api_key in placeholder_keys:
        print("OPENAI_API_KEY: missing (AI features will fail)")
    elif not settings.openai_api_key.startswith("sk-"):
        print("OPENAI_API_KEY: appears invalid")
    else:
        print("OPENAI_API_KEY: present")

    if not settings.app_secret_key or settings.app_secret_key == "change-this-to-a-random-64-char-string":
        print("APP_SECRET_KEY: using placeholder (backend auth will fail)")
    else:
        print("APP_SECRET_KEY: present")

    if not all_ok:
        sys.exit(1)
    print("All local services reachable.")


if __name__ == "__main__":
    try:
        asyncio.run(check())
    except Exception as exc:  # pragma: no cover - CLI helper
        print(f"Check failed: {exc}", file=sys.stderr)
        sys.exit(1)
