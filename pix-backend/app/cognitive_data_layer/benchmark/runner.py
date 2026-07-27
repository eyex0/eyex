from __future__ import annotations

import time
import tracemalloc
from pathlib import Path
from typing import Any

from app.cognitive_data_layer.benchmark.dataset_generator import generate_benchmark_datasets
from app.cognitive_data_layer.pipeline import CognitiveDataPipeline


class BenchmarkRunner:
    """Run the CDL against benchmark datasets and collect metrics."""

    def __init__(self) -> None:
        self.pipeline = CognitiveDataPipeline()
        self.results: list[dict[str, Any]] = []

    async def run(self, dataset_dir: Path | str) -> list[dict[str, Any]]:
        paths = generate_benchmark_datasets(dataset_dir)
        self.results = []
        for path in paths:
            tracemalloc.start()
            start_time = time.perf_counter()
            try:
                result = await self.pipeline.process(path, company_id=f"company_{path.stem}")
                success = True
                error = None
            except Exception as exc:  # noqa: BLE001
                result = {}
                success = False
                error = str(exc)
            elapsed = time.perf_counter() - start_time
            _, peak = tracemalloc.get_traced_memory()
            tracemalloc.stop()

            canonical = result.get("canonical")
            self.results.append(
                {
                    "industry": path.stem,
                    "path": str(path),
                    "success": success,
                    "error": error,
                    "processing_time_ms": round(elapsed * 1000, 2),
                    "peak_memory_mb": round(peak / (1024 * 1024), 2),
                    "tables": len(canonical.sheets) if canonical else 0,
                    "columns": sum(len(t.columns) for s in canonical.sheets for t in s.tables)
                    if canonical
                    else 0,
                    "entities": list(canonical.entities.keys()) if canonical else [],
                    "quality_issues": len(canonical.quality_issues) if canonical else 0,
                    "low_confidence": len(
                        result.get("confidence_report", {}).get("low_confidence", [])
                    ),
                    "knowledge_graph_nodes": len(
                        result.get("knowledge_graph", {}).get("nodes", [])
                    ),
                }
            )
        return self.results

    def accuracy_metrics(self) -> dict[str, float]:
        if not self.results:
            return {}
        total = len(self.results)
        successes = sum(1 for r in self.results if r["success"])
        avg_quality = sum(r["quality_issues"] for r in self.results) / max(total, 1)
        avg_confidence_flags = sum(r["low_confidence"] for r in self.results) / max(total, 1)
        return {
            "success_rate": successes / total,
            "avg_quality_issues": avg_quality,
            "avg_low_confidence_flags": avg_confidence_flags,
            "avg_processing_time_ms": sum(r["processing_time_ms"] for r in self.results) / total,
            "avg_peak_memory_mb": sum(r["peak_memory_mb"] for r in self.results) / total,
        }

    def failure_report(self) -> list[dict[str, Any]]:
        return [r for r in self.results if not r["success"]]


async def run_benchmark(dataset_dir: Path | str) -> tuple[list[dict[str, Any]], dict[str, float]]:
    runner = BenchmarkRunner()
    results = await runner.run(dataset_dir)
    return results, runner.accuracy_metrics()
