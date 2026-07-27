from __future__ import annotations

from contextvars import ContextVar

org_id_ctx: ContextVar[str | None] = ContextVar("org_id", default=None)
