"""Benchmark the agent orchestrator service execution time for different input sizes."""
from __future__ import annotations

import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.agent_service import AgentOrchestratorService


class TestOrchestratorInitBenchmark:
    def test_orchestrator_init_fast(self):
        times = []
        for _ in range(20):
            start = time.perf_counter()
            AgentOrchestratorService(memory_service=None)
            elapsed = (time.perf_counter() - start) * 1000
            times.append(elapsed)
        avg = sum(times) / len(times)
        assert avg < 50, f"Orchestrator init avg {avg:.2f}ms exceeded 50ms"


class TestBuildSummaryBenchmark:
    def test_build_summary_all_results(self):
        result = {
            "planner_result": {"plan": "Build a login API with JWT tokens"},
            "researcher_result": {"summary": "Research shows JWT is the best approach"},
            "coder_result": {"files": [{"path": "main.py"}, {"path": "auth.py"}], "explanation": "Created API"},
            "reviewer_result": {"approved": True, "score": 90},
            "tester_result": {"test_files": [{"path": "test_main.py"}]},
            "documenter_result": {"files": [{"path": "docs/api.md"}]},
            "devops_result": {"config_files": [{"path": "Dockerfile"}]},
        }
        times = []
        for _ in range(100):
            start = time.perf_counter()
            AgentOrchestratorService._build_summary(result)
            elapsed = (time.perf_counter() - start) * 1000
            times.append(elapsed)
        avg = sum(times) / len(times)
        assert avg < 10, f"_build_summary avg {avg:.2f}ms exceeded 10ms"

    def test_build_summary_partial_results(self):
        result = {
            "planner_result": {"plan": "Build a login API"},
            "coder_result": {"files": [{"path": "main.py"}], "explanation": "Created API"},
        }
        times = []
        for _ in range(100):
            start = time.perf_counter()
            AgentOrchestratorService._build_summary(result)
            elapsed = (time.perf_counter() - start) * 1000
            times.append(elapsed)
        avg = sum(times) / len(times)
        assert avg < 10, f"_build_summary partial avg {avg:.2f}ms exceeded 10ms"

    def test_build_summary_empty_result(self):
        result: dict = {}
        times = []
        for _ in range(100):
            start = time.perf_counter()
            AgentOrchestratorService._build_summary(result)
            elapsed = (time.perf_counter() - start) * 1000
            times.append(elapsed)
        avg = sum(times) / len(times)
        assert avg < 10, f"_build_summary empty avg {avg:.2f}ms exceeded 10ms"
