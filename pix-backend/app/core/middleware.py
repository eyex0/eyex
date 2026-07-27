from __future__ import annotations

import logging
import re
import time
import uuid
import traceback
from collections import defaultdict
from collections.abc import Awaitable, Callable

from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.core.metrics import MetricsMiddleware

logger = logging.getLogger("pix.core.middleware")
settings = get_settings()

_MAX_REQUEST_BODY = 10 * 1024 * 1024
_IP_RE = re.compile(r"^\d{1,3}(\.\d{1,3}){3}$")


def _get_client_ip(request: Request) -> str:
    forwarded = request.headers.get("X-Forwarded-For") or request.headers.get("x-forwarded-for")
    if forwarded:
        first = forwarded.split(",")[0].strip()
        if _IP_RE.match(first):
            return first
    return request.client.host if request.client else "unknown"


class RequestLogMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        request_id = str(uuid.uuid4())[:8]
        start = time.perf_counter()
        method = request.method
        path = request.url.path

        body_size = request.headers.get("content-length")
        if body_size and int(body_size) > _MAX_REQUEST_BODY:
            logger.warning(
                "[%s] %s %s — body too large: %s bytes",
                request_id, method, path, body_size,
            )
            return JSONResponse(
                status_code=413,
                content={
                    "error": "Request body too large",
                    "detail": f"Maximum size is {_MAX_REQUEST_BODY} bytes",
                },
            )

        try:
            response = await call_next(request)
        except Exception as exc:
            elapsed = time.perf_counter() - start
            tb = traceback.format_exc()
            logger.error(
                "[%s] %s %s — UNHANDLED EXCEPTION after %.0fms: %s\n%s",
                request_id, method, path, elapsed * 1000, exc, tb,
            )
            return JSONResponse(
                status_code=500,
                content={
                    "error": str(exc),
                    "detail": tb,
                    "status_code": 500,
                    "request_id": request_id,
                },
            )

        elapsed = time.perf_counter() - start
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Response-Time-MS"] = str(round(elapsed * 1000, 2))

        logger.info(
            "[%s] %s %s — %d (%.0fms)",
            request_id, method, path, response.status_code, elapsed * 1000,
        )
        return response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; script-src 'self'; "
            "style-src 'self' 'unsafe-inline'; img-src 'self' data:;"
        )
        if settings.is_production:
            response.headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains; preload"
            )
        return response


class TokenBucket:
    def __init__(self, rate: float, burst: int) -> None:
        self.rate = rate
        self.burst = burst
        self.tokens = float(burst)
        self.last_refill = time.monotonic()

    def consume(self) -> bool:
        now = time.monotonic()
        elapsed = now - self.last_refill
        self.tokens = min(self.burst, self.tokens + elapsed * self.rate)
        self.last_refill = now
        if self.tokens >= 1.0:
            self.tokens -= 1.0
            return True
        return False

    @property
    def wait_seconds(self) -> float:
        if self.tokens >= 1.0:
            return 0.0
        return (1.0 - self.tokens) / self.rate if self.rate > 0 else float("inf")


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(
        self,
        app: FastAPI,
        enabled: bool = True,
        requests_per_minute: int = 100,
        auth_requests_per_minute: int = 20,
    ) -> None:
        super().__init__(app)
        self.enabled = enabled
        self.rate = requests_per_minute / 60.0
        self.burst = max(20, requests_per_minute // 5)
        self.auth_rate = auth_requests_per_minute / 60.0
        self.auth_burst = max(5, auth_requests_per_minute // 5)
        self.buckets: dict[str, TokenBucket] = defaultdict(
            lambda: TokenBucket(self.rate, self.burst)
        )
        self.auth_buckets: dict[str, TokenBucket] = defaultdict(
            lambda: TokenBucket(self.auth_rate, self.auth_burst)
        )

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        if not self.enabled:
            return await call_next(request)

        client_ip = _get_client_ip(request)
        path = request.url.path

        if path.startswith("/api/v1/auth/"):
            bucket = self.auth_buckets[client_ip]
        else:
            bucket = self.buckets[client_ip]

        if not bucket.consume():
            retry_after = max(1, int(bucket.wait_seconds))
            logger.warning("Rate limit exceeded for %s on %s", client_ip, path)
            return JSONResponse(
                status_code=429,
                content={
                    "error": "Too Many Requests",
                    "detail": "Rate limit exceeded. Try again shortly.",
                },
                headers={"Retry-After": str(retry_after)},
            )

        return await call_next(request)


def setup_middleware(app: FastAPI) -> None:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
        expose_headers=["X-Request-ID", "X-Response-Time-MS"],
    )
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(RequestLogMiddleware)
    app.add_middleware(MetricsMiddleware)
    if settings.rate_limit_enabled:
        app.add_middleware(
            RateLimitMiddleware,
            enabled=settings.rate_limit_enabled,
            requests_per_minute=settings.rate_limit_requests_per_minute,
        )
