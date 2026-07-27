"""
πX Retry Handler — Exponential backoff with jitter for agent task execution.

Supports: configurable max retries, exponential backoff, circuit breaker pattern.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any, Callable
import asyncio
import random


class TaskState(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    RETRYING = "retrying"
    CIRCUIT_OPEN = "circuit_open"


@dataclass
class TaskAttempt:
    attempt_number: int
    started_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    finished_at: str = ""
    success: bool = False
    error: str = ""
    duration_ms: int = 0


@dataclass
class RetryConfig:
    max_retries: int = 3
    base_delay_seconds: float = 1.0
    max_delay_seconds: float = 60.0
    jitter: bool = True
    circuit_breaker_threshold: int = 5  # consecutive failures before opening circuit
    circuit_breaker_reset_seconds: float = 120.0  # how long to keep circuit open


class RetryHandler:
    """Handles retry logic with exponential backoff and circuit breaker."""

    def __init__(self, config: RetryConfig | None = None) -> None:
        self.config = config or RetryConfig()
        self._consecutive_failures: dict[str, int] = {}  # task_name → failures
        self._circuit_open_until: dict[str, datetime | None] = {}  # task_name → open until

    async def execute_with_retry(
        self,
        task_name: str,
        func: Callable,
        *args,
        **kwargs,
    ) -> Any:
        """Execute a function with retry and circuit breaker."""
        # Check circuit breaker
        if self._is_circuit_open(task_name):
            raise CircuitBreakerOpenError(f"Circuit breaker open for task '{task_name}'")

        last_error = None
        for attempt in range(1, self.config.max_retries + 1):
            try:
                result = await func(*args, **kwargs) if asyncio.iscoroutinefunction(func) else func(*args, **kwargs)
                self._on_success(task_name)
                return result
            except Exception as e:
                last_error = e
                if attempt < self.config.max_retries:
                    delay = self._compute_delay(attempt)
                    await asyncio.sleep(delay) if asyncio.iscoroutinefunction(func) else None
                self._on_failure(task_name)

        raise last_error  # type: ignore

    def _compute_delay(self, attempt: int) -> float:
        delay = self.config.base_delay_seconds * (2 ** (attempt - 1))
        delay = min(delay, self.config.max_delay_seconds)
        if self.config.jitter:
            delay *= (0.5 + random.random() * 0.5)
        return delay

    def _on_success(self, task_name: str) -> None:
        self._consecutive_failures[task_name] = 0
        self._circuit_open_until[task_name] = None

    def _on_failure(self, task_name: str) -> None:
        self._consecutive_failures[task_name] = self._consecutive_failures.get(task_name, 0) + 1
        if self._consecutive_failures[task_name] >= self.config.circuit_breaker_threshold:
            reset_time = datetime.now(UTC)
            from datetime import timedelta
            reset_time = reset_time + timedelta(seconds=self.config.circuit_breaker_reset_seconds)
            self._circuit_open_until[task_name] = reset_time

    def _is_circuit_open(self, task_name: str) -> bool:
        until = self._circuit_open_until.get(task_name)
        if until is None:
            return False
        if datetime.now(UTC) >= until:
            self._circuit_open_until[task_name] = None
            self._consecutive_failures[task_name] = 0
            return False
        return True

    def get_state(self, task_name: str) -> dict[str, Any]:
        return {
            "task_name": task_name,
            "consecutive_failures": self._consecutive_failures.get(task_name, 0),
            "circuit_open": self._is_circuit_open(task_name),
            "circuit_reset_at": str(self._circuit_open_until.get(task_name, "")),
        }


class CircuitBreakerOpenError(Exception):
    """Raised when the circuit breaker is open for a task."""
    pass
