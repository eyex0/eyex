from __future__ import annotations

from pathlib import Path
from typing import Any


class ReportGenerator:
    """Generate CDL validation reports."""

    def __init__(self, results: list[dict[str, Any]], metrics: dict[str, float]) -> None:
        self.results = results
        self.metrics = metrics

    def generate_all(self, output_dir: Path | str) -> dict[str, Path]:
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        reports = {
            "PROJECT_AUDIT_REPORT.md": self._project_audit_report(),
            "DATA_UNDERSTANDING_REPORT.md": self._data_understanding_report(),
            "MAPPING_REPORT.md": self._mapping_report(),
            "CONFIDENCE_REPORT.md": self._confidence_report(),
            "PERFORMANCE_REPORT.md": self._performance_report(),
            "FAILURE_REPORT.md": self._failure_report(),
            "RECOMMENDATIONS.md": self._recommendations(),
        }
        paths: dict[str, Path] = {}
        for filename, content in reports.items():
            path = output_dir / filename
            path.write_text(content, encoding="utf-8")
            paths[filename] = path
        return paths

    def _project_audit_report(self) -> str:
        lines = ["# Project Audit Report\n", "## Cognitive Data Layer Validation\n"]
        lines.append(f"Total datasets: {len(self.results)}\n")
        lines.append(f"Success rate: {self.metrics.get('success_rate', 0):.1%}\n")
        lines.append(f"Average quality issues: {self.metrics.get('avg_quality_issues', 0):.1f}\n")
        lines.append(
            f"Average low-confidence flags: {self.metrics.get('avg_low_confidence_flags', 0):.1f}\n"
        )
        lines.append("\n## Dataset Summary\n")
        for r in self.results:
            summary = (
                f"- **{r['industry']}**: success={r['success']}, "
                f"tables={r['tables']}, columns={r['columns']}, "
                f"entities={r['entities']}\n"
            )
            lines.append(summary)
        return "".join(lines)

    def _data_understanding_report(self) -> str:
        lines = ["# Data Understanding Report\n", "## Entity Detection\n"]
        for r in self.results:
            lines.append(f"### {r['industry']}\n")
            lines.append(f"- Detected entities: {r['entities']}\n")
            lines.append(f"- Knowledge graph nodes: {r['knowledge_graph_nodes']}\n")
            lines.append(f"- Quality issues: {r['quality_issues']}\n")
        return "".join(lines)

    def _mapping_report(self) -> str:
        lines = ["# Mapping Report\n", "## Semantic Mapping Coverage\n"]
        total_entities = sum(len(r["entities"]) for r in self.results)
        lines.append(f"Total entity mappings across datasets: {total_entities}\n")
        for r in self.results:
            lines.append(f"- **{r['industry']}**: {r['entities']}\n")
        return "".join(lines)

    def _confidence_report(self) -> str:
        lines = ["# Confidence Report\n", "## Low Confidence Mappings\n"]
        avg_flags = self.metrics.get("avg_low_confidence_flags", 0)
        lines.append(f"Average low-confidence flags per dataset: {avg_flags:.2f}\n\n")
        for r in self.results:
            lines.append(f"- **{r['industry']}**: {r['low_confidence']} low-confidence flags\n")
        return "".join(lines)

    def _performance_report(self) -> str:
        lines = ["# Performance Report\n", "## Timing and Resource Usage\n"]
        lines.append(
            f"Average processing time: {self.metrics.get('avg_processing_time_ms', 0):.2f} ms\n"
        )
        lines.append(f"Average peak memory: {self.metrics.get('avg_peak_memory_mb', 0):.2f} MB\n\n")
        lines.append("| Industry | Time (ms) | Memory (MB) |\n")
        lines.append("|---|---|---|\n")
        for r in self.results:
            lines.append(
                f"| {r['industry']} | {r['processing_time_ms']} | {r['peak_memory_mb']} |\n"
            )
        return "".join(lines)

    def _failure_report(self) -> str:
        lines = ["# Failure Report\n", "## Processing Failures\n"]
        failures = [r for r in self.results if not r["success"]]
        if not failures:
            lines.append("No failures detected.\n")
        for r in failures:
            lines.append(f"- **{r['industry']}**: {r['error']}\n")
        return "".join(lines)

    def _recommendations(self) -> str:
        lines = ["# Recommendations\n", "## Improvements for Cognitive Data Layer\n"]
        if self.metrics.get("avg_low_confidence_flags", 0) > 2:
            lines.append("- Expand canonical alias dictionary to reduce low-confidence mappings.\n")
        if self.metrics.get("avg_quality_issues", 0) > 5:
            lines.append("- Add data cleaning recommendations and auto-imputation suggestions.\n")
        if self.metrics.get("success_rate", 1.0) < 1.0:
            lines.append("- Improve parser robustness for malformed or unsupported file layouts.\n")
        lines.append("- Add LLM-based semantic inference for ambiguous column names.\n")
        lines.append("- Expand industry-specific vocabulary and terminology.\n")
        return "".join(lines)


def generate_reports(
    results: list[dict[str, Any]], metrics: dict[str, float], output_dir: Path | str
) -> dict[str, Path]:
    return ReportGenerator(results, metrics).generate_all(output_dir)
