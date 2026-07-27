from __future__ import annotations

import asyncio
import logging
import os
import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, TypeVar

F = TypeVar("F", bound=Callable[..., Any])

logger = logging.getLogger("pix.core.reliability")


@dataclass
class AgentRetryPolicy:
    max_retries: int = 3
    base_delay: float = 1.0
    max_delay: float = 30.0
    backoff_factor: float = 2.0
    retryable_exceptions: tuple = (Exception,)


@dataclass
class ExecutionRecord:
    agent_name: str
    status: str  # success | failed | retry
    duration_ms: float
    error: str | None = None
    attempt: int = 1
    timestamp: str = ""


class ReliabilityManager:
    """Handles error recovery, retries, logging, and monitoring."""

    def __init__(self, log_dir: str | None = None) -> None:
        self.records: list[ExecutionRecord] = []
        self.log_dir = log_dir or os.path.join(
            os.path.dirname(os.path.dirname(__file__)), "logs"
        )
        Path(self.log_dir).mkdir(parents=True, exist_ok=True)
        self._console_handler = self._setup_file_logging()

    def _setup_file_logging(self) -> logging.Handler:
        log_file = Path(self.log_dir) / f"pix_{datetime.now(UTC).strftime('%Y%m%d')}.log"
        handler = logging.FileHandler(str(log_file), encoding="utf-8")
        handler.setFormatter(logging.Formatter(
            "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        ))
        return handler

    async def execute_with_retry(
        self,
        agent_name: str,
        func: Callable[..., Any],
        *args: Any,
        policy: AgentRetryPolicy | None = None,
        **kwargs: Any,
    ) -> Any:
        policy = policy or AgentRetryPolicy()
        last_error: Exception | None = None

        for attempt in range(1, policy.max_retries + 1):
            start = time.perf_counter()
            try:
                result = func(*args, **kwargs)
                if asyncio.iscoroutine(result):
                    result = await result
                elapsed = (time.perf_counter() - start) * 1000
                self.records.append(ExecutionRecord(
                    agent_name=agent_name,
                    status="success",
                    duration_ms=round(elapsed, 2),
                    attempt=attempt,
                    timestamp=datetime.now(UTC).isoformat(),
                ))
                logger.info("[%s] Success on attempt %d/%d (%.0fms)", agent_name, attempt, policy.max_retries, elapsed)
                return result
            except policy.retryable_exceptions as exc:
                last_error = exc
                elapsed = (time.perf_counter() - start) * 1000
                self.records.append(ExecutionRecord(
                    agent_name=agent_name,
                    status="retry" if attempt < policy.max_retries else "failed",
                    duration_ms=round(elapsed, 2),
                    error=str(exc),
                    attempt=attempt,
                    timestamp=datetime.now(UTC).isoformat(),
                ))
                if attempt < policy.max_retries:
                    delay = min(policy.base_delay * (policy.backoff_factor ** (attempt - 1)), policy.max_delay)
                    logger.warning(
                        "[%s] Attempt %d/%d failed: %s. Retrying in %.1fs...",
                        agent_name, attempt, policy.max_retries, exc, delay,
                    )
                    await asyncio.sleep(delay)
                else:
                    logger.error("[%s] All %d attempts failed: %s", agent_name, policy.max_retries, exc)

        raise last_error or RuntimeError(f"{agent_name} failed after {policy.max_retries} attempts")

    def get_stats(self) -> dict[str, Any]:
        total = len(self.records)
        if total == 0:
            return {"total": 0, "success_rate": 1.0, "avg_duration_ms": 0}
        success_count = sum(1 for r in self.records if r.status == "success")
        avg_duration = sum(r.duration_ms for r in self.records) / total
        return {
            "total": total,
            "success_count": success_count,
            "failed_count": sum(1 for r in self.records if r.status == "failed"),
            "success_rate": round(success_count / total, 4),
            "avg_duration_ms": round(avg_duration, 2),
        }

    def get_recent_errors(self, limit: int = 10) -> list[dict[str, Any]]:
        return [
            {"agent": r.agent_name, "error": r.error, "attempt": r.attempt, "timestamp": r.timestamp}
            for r in self.records
            if r.status == "failed"
        ][-limit:]


_reliability: ReliabilityManager | None = None


def get_reliability_manager() -> ReliabilityManager:
    global _reliability
    if _reliability is None:
        _reliability = ReliabilityManager()
    return _reliability
