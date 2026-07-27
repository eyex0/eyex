"""
πX Data Quality Intelligence — Quality scoring before ingestion.

Analyzes: missing values, duplicates, anomalies, invalid formats, inconsistent naming.
Generates a Data Quality Report with per-column and overall scores.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

import pandas as pd

logger = logging.getLogger("pix.data_intelligence.quality")


@dataclass
class ColumnQualityReport:
    name: str
    completeness: float = 1.0  # % non-null
    uniqueness: float = 0.0  # % unique
    validity: float = 1.0  # % valid format
    consistency: float = 1.0  # naming consistency
    anomaly_count: int = 0
    duplicate_count: int = 0
    issues: list[dict] = field(default_factory=list)
    overall_score: float = 1.0

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "completeness": round(self.completeness, 4),
            "uniqueness": round(self.uniqueness, 4),
            "validity": round(self.validity, 4),
            "consistency": round(self.consistency, 4),
            "anomaly_count": self.anomaly_count,
            "duplicate_count": self.duplicate_count,
            "issues": self.issues,
            "overall_score": round(self.overall_score, 4),
        }


@dataclass
class DataQualityReport:
    source_name: str
    row_count: int = 0
    column_count: int = 0
    columns: list[ColumnQualityReport] = field(default_factory=list)
    overall_score: float = 1.0
    duplicate_rows: int = 0
    missing_cells: int = 0
    total_cells: int = 0
    issues_summary: dict = field(default_factory=dict)
    recommendations: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "source_name": self.source_name,
            "row_count": self.row_count,
            "column_count": self.column_count,
            "columns": [c.to_dict() for c in self.columns],
            "overall_score": round(self.overall_score, 4),
            "duplicate_rows": self.duplicate_rows,
            "missing_cells": self.missing_cells,
            "total_cells": self.total_cells,
            "missing_percentage": round(self.missing_cells / max(self.total_cells, 1) * 100, 2),
            "issues_summary": self.issues_summary,
            "recommendations": self.recommendations,
        }


class DataQualityIntelligence:
    """Analyzes data quality before ingestion into πX."""

    def analyze(self, df: pd.DataFrame, source_name: str = "dataset") -> DataQualityReport:
        """Run full quality analysis on a DataFrame."""
        report = DataQualityReport(
            source_name=source_name,
            row_count=len(df),
            column_count=len(df.columns),
            total_cells=len(df) * len(df.columns),
        )

        # Overall duplicate rows
        report.duplicate_rows = int(df.duplicated().sum())

        # Analyze each column
        for col in df.columns:
            col_report = self._analyze_column(str(col), df[col])
            report.columns.append(col_report)
            report.missing_cells += col_report.duplicate_count  # Actually null count
            # Count missing
            report.missing_cells -= col_report.duplicate_count
            report.missing_cells += int(df[col].isna().sum())

        # Fix missing_cells calculation
        report.missing_cells = int(df.isna().sum().sum())

        # Overall score
        if report.columns:
            report.overall_score = sum(c.overall_score for c in report.columns) / len(report.columns)

        # Issue summary
        report.issues_summary = self._summarize_issues(report.columns)

        # Recommendations
        report.recommendations = self._generate_recommendations(report)

        return report

    def _analyze_column(self, name: str, series: pd.Series) -> ColumnQualityReport:
        col = ColumnQualityReport(name=name)

        # Completeness (non-null percentage)
        null_count = int(series.isna().sum())
        col.completeness = round(1 - null_count / max(len(series), 1), 4)

        # Uniqueness
        nunique = int(series.nunique())
        col.uniqueness = round(nunique / max(len(series), 1), 4)

        # Duplicates
        col.duplicate_count = int(len(series) - nunique - null_count)

        # Validity — check format consistency
        col.validity, validity_issues = self._check_validity(name, series)
        col.issues.extend(validity_issues)

        # Consistency — naming convention
        col.consistency = self._check_naming_consistency(name)

        # Anomalies — outliers in numeric data
        if series.dtype in ("int64", "float64", "float32", "int32"):
            col.anomaly_count, anomaly_issues = self._detect_anomalies(name, series)
            col.issues.extend(anomaly_issues)

        # Missing values issue
        if null_count > 0:
            pct = null_count / max(len(series), 1) * 100
            severity = "warning" if pct < 5 else "error" if pct < 20 else "critical"
            col.issues.append({
                "type": "missing_values",
                "severity": severity,
                "count": null_count,
                "percentage": round(pct, 2),
                "message": f"{null_count} missing values ({pct:.1f}%)",
            })

        # Duplicate issue
        if col.duplicate_count > 0 and col.uniqueness < 0.01:
            col.issues.append({
                "type": "constant_value",
                "severity": "warning",
                "message": f"Column has only {nunique} unique value(s)",
            })

        # Overall column score (weighted)
        col.overall_score = (
            col.completeness * 0.40
            + col.validity * 0.25
            + col.consistency * 0.15
            + min(col.uniqueness, 1.0) * 0.10
            + (1.0 if col.anomaly_count == 0 else 0.5) * 0.10
        )
        col.overall_score = max(0.0, min(1.0, col.overall_score))

        return col

    def _check_validity(self, name: str, series: pd.Series) -> tuple[float, list[dict]]:
        """Check format validity."""
        issues = []
        non_null = series.dropna()
        if non_null.empty:
            return 1.0, []

        validity = 1.0
        name_lower = name.lower()

        # Date validation
        if any(kw in name_lower for kw in ["date", "time", "_at"]):
            try:
                pd.to_datetime(non_null.head(50))
            except (ValueError, TypeError):
                invalid = sum(1 for v in non_null if not self._looks_like_date(str(v)))
                if invalid > 0:
                    validity = 1 - invalid / max(len(non_null), 1)
                    issues.append({"type": "invalid_date", "severity": "warning", "count": invalid})

        # Email validation
        if "email" in name_lower or "mail" in name_lower:
            invalid = sum(1 for v in non_null if "@" not in str(v))
            if invalid > 0:
                validity = 1 - invalid / max(len(non_null), 1)
                issues.append({"type": "invalid_email", "severity": "error", "count": invalid})

        # Numeric validation for numeric columns
        if series.dtype == "object" and any(kw in name_lower for kw in ["amount", "price", "cost", "rev", "value"]):
            non_numeric = sum(1 for v in non_null if not isinstance(v, (int, float)))
            if non_numeric > 0:
                validity = 1 - non_numeric / max(len(non_null), 1)
                issues.append({"type": "invalid_numeric", "severity": "error", "count": non_numeric})

        return round(validity, 4), issues

    def _check_naming_consistency(self, name: str) -> float:
        """Check naming convention consistency."""
        # Check for mixed conventions (camelCase + snake_case + spaces)
        has_underscore = "_" in name
        has_space = " " in name
        has_camel = any(c.isupper() for c in name[1:]) and not has_underscore and not has_space
        has_all_caps = name.isupper() and len(name) > 3

        # Consistent if only one convention
        conventions = sum([has_underscore, has_space, has_camel and not has_all_caps])
        if conventions <= 1:
            return 1.0
        return 0.7

    def _detect_anomalies(self, name: str, series: pd.Series) -> tuple[int, list[dict]]:
        """Detect outliers using IQR method."""
        issues = []
        non_null = series.dropna()
        if len(non_null) < 10:
            return 0, []

        q1 = non_null.quantile(0.25)
        q3 = non_null.quantile(0.75)
        iqr = q3 - q1
        if iqr == 0:
            return 0, []

        lower = q1 - 1.5 * iqr
        upper = q3 + 1.5 * iqr
        anomalies = non_null[(non_null < lower) | (non_null > upper)]
        count = len(anomalies)

        if count > 0:
            issues.append({
                "type": "anomaly",
                "severity": "info",
                "count": count,
                "message": f"{count} potential outliers detected (IQR method)",
            })

        return count, issues

    def _looks_like_date(self, value: str) -> bool:
        """Quick check if a string looks like a date."""
        return any(sep in value for sep in ["-", "/", ":"]) and len(value) >= 8

    def _summarize_issues(self, columns: list[ColumnQualityReport]) -> dict:
        """Summarize issues by type and severity."""
        summary = {"by_type": {}, "by_severity": {"info": 0, "warning": 0, "error": 0, "critical": 0}}
        for col in columns:
            for issue in col.issues:
                itype = issue.get("type", "unknown")
                severity = issue.get("severity", "info")
                summary["by_type"][itype] = summary["by_type"].get(itype, 0) + 1
                summary["by_severity"][severity] = summary["by_severity"].get(severity, 0) + 1
        return summary

    def _generate_recommendations(self, report: DataQualityReport) -> list[str]:
        """Generate actionable recommendations."""
        recs = []
        if report.missing_cells / max(report.total_cells, 1) > 0.05:
            recs.append("High missing value rate — consider imputation strategy before ingestion")
        if report.duplicate_rows > 0:
            recs.append(f"Remove {report.duplicate_rows} duplicate rows")
        low_quality_cols = [c.name for c in report.columns if c.overall_score < 0.6]
        if low_quality_cols:
            recs.append(f"Columns with low quality: {', '.join(low_quality_cols[:5])} — review before use")
        anomaly_cols = [c.name for c in report.columns if c.anomaly_count > 0]
        if anomaly_cols:
            recs.append(f"Columns with outliers: {', '.join(anomaly_cols[:5])} — verify data correctness")
        return recs
