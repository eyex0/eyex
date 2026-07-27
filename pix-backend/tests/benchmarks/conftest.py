"""Benchmark fixtures and utilities."""
import pytest


@pytest.fixture
def benchmark_sample_data():
    return {
        "short_message": "Hello",
        "medium_message": "Write a Python function to calculate fibonacci numbers.",
        "long_message": "Write a complete REST API for a task management system with users, projects, tasks, comments, tags, file attachments, notifications, activity logging, search, pagination, sorting, filtering, authentication, authorization, rate limiting, caching, webhooks, and comprehensive error handling." * 3,
    }


def format_benchmark_result(name: str, duration_ms: float, iterations: int = 1) -> str:
    avg = duration_ms / iterations
    return f"{name}: {avg:.2f}ms avg over {iterations} iteration(s)"
