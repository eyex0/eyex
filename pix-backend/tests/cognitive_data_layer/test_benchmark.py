from __future__ import annotations

from pathlib import Path

import pytest

from app.api.v1.cognitive_data import cognitive_data_router
from app.cognitive_data_layer.benchmark import (
    generate_benchmark_datasets,
    generate_reports,
    run_benchmark,
)


class TestCognitiveDataRouter:
    def test_router_exists(self):
        assert cognitive_data_router is not None
        assert cognitive_data_router.prefix == "/cognitive-data"

    def test_routes_registered(self):
        routes = {r.path for r in cognitive_data_router.routes}
        assert "/cognitive-data/process" in routes
        assert "/cognitive-data/supported-formats" in routes


class TestBenchmarkDatasetGenerator:
    def test_generates_20_datasets(self, tmp_path: Path):
        paths = generate_benchmark_datasets(tmp_path)
        assert len(paths) == 20
        assert all(p.exists() for p in paths)

    def test_datasets_are_excel(self, tmp_path: Path):
        paths = generate_benchmark_datasets(tmp_path)
        assert all(p.suffix == ".xlsx" for p in paths)


class TestBenchmarkRunner:
    @pytest.mark.asyncio
    async def test_run_benchmark(self, tmp_path: Path):
        dataset_dir = tmp_path / "datasets"
        paths = generate_benchmark_datasets(dataset_dir)
        results, metrics = await run_benchmark(dataset_dir)
        assert len(results) == len(paths)
        assert metrics["success_rate"] == 1.0

    @pytest.mark.asyncio
    async def test_generate_reports(self, tmp_path: Path):
        dataset_dir = tmp_path / "datasets"
        report_dir = tmp_path / "reports"
        generate_benchmark_datasets(dataset_dir)
        results, metrics = await run_benchmark(dataset_dir)
        paths = generate_reports(results, metrics, report_dir)
        assert len(paths) == 7
        assert all(p.exists() for p in paths.values())
