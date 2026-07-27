from __future__ import annotations

from typing import Any

import pandas as pd

from app.cognitive_data_layer.canonical.model import (
    CanonicalColumn,
    DataQualityIssue,
    DataQualitySeverity,
)


class DataQualityEngine:
    """Detect missing values, duplicates, outliers, and inconsistencies."""

    def analyze(
        self, table_name: str, df: pd.DataFrame, columns: list[CanonicalColumn]
    ) -> list[DataQualityIssue]:
        issues: list[DataQualityIssue] = []
        issues.extend(self._check_missing_values(table_name, df, columns))
        issues.extend(self._check_duplicates(table_name, df, columns))
        issues.extend(self._check_outliers(table_name, df, columns))
        issues.extend(self._check_date_consistency(table_name, df, columns))
        issues.extend(self._check_currency_consistency(table_name, df, columns))
        return issues

    def _check_missing_values(
        self, table_name: str, df: pd.DataFrame, columns: list[CanonicalColumn]
    ) -> list[DataQualityIssue]:
        issues: list[DataQualityIssue] = []
        for col in columns:
            null_count = df[col.name].isna().sum()
            if null_count > 0:
                pct = null_count / len(df)
                severity = DataQualitySeverity.WARNING if pct < 0.1 else DataQualitySeverity.ERROR
                issues.append(
                    DataQualityIssue(
                        issue_type="missing_values",
                        severity=severity,
                        table=table_name,
                        column=col.name,
                        row_indices=df[df[col.name].isna()].index.tolist(),
                        message=f"{null_count} missing values ({pct:.1%})",
                        suggestion="Impute or collect missing data",
                    )
                )
        return issues

    def _check_duplicates(
        self, table_name: str, df: pd.DataFrame, columns: list[CanonicalColumn]
    ) -> list[DataQualityIssue]:
        issues: list[DataQualityIssue] = []
        dupes = df[df.duplicated(keep=False)]
        if not dupes.empty:
            issues.append(
                DataQualityIssue(
                    issue_type="duplicate_rows",
                    severity=DataQualitySeverity.WARNING,
                    table=table_name,
                    message=f"{len(dupes)} duplicate rows",
                    suggestion="Deduplicate rows",
                )
            )
        return issues

    def _check_outliers(
        self, table_name: str, df: pd.DataFrame, columns: list[CanonicalColumn]
    ) -> list[DataQualityIssue]:
        issues: list[DataQualityIssue] = []
        for col in columns:
            if col.semantic_type not in ("numeric", "currency"):
                continue
            series = pd.to_numeric(df[col.name], errors="coerce").dropna()
            if len(series) < 10:
                continue
            q1 = series.quantile(0.25)
            q3 = series.quantile(0.75)
            iqr = q3 - q1
            lower = q1 - 1.5 * iqr
            upper = q3 + 1.5 * iqr
            outliers = series[(series < lower) | (series > upper)]
            if not outliers.empty:
                issues.append(
                    DataQualityIssue(
                        issue_type="outliers",
                        severity=DataQualitySeverity.INFO,
                        table=table_name,
                        column=col.name,
                        row_indices=outliers.index.tolist(),
                        message=f"{len(outliers)} outliers detected",
                        suggestion="Review extreme values",
                    )
                )
        return issues

    def _check_date_consistency(
        self, table_name: str, df: pd.DataFrame, columns: list[CanonicalColumn]
    ) -> list[DataQualityIssue]:
        issues: list[DataQualityIssue] = []
        for col in columns:
            if col.semantic_type != "date":
                continue
            parsed = pd.to_datetime(df[col.name], errors="coerce", dayfirst=False)
            invalid = df[parsed.isna() & df[col.name].notna()]
            if not invalid.empty:
                issues.append(
                    DataQualityIssue(
                        issue_type="invalid_dates",
                        severity=DataQualitySeverity.WARNING,
                        table=table_name,
                        column=col.name,
                        row_indices=invalid.index.tolist(),
                        message=f"{len(invalid)} invalid date values",
                        suggestion="Standardize date formats",
                    )
                )
        return issues

    def _check_currency_consistency(
        self, table_name: str, df: pd.DataFrame, columns: list[CanonicalColumn]
    ) -> list[DataQualityIssue]:
        issues: list[DataQualityIssue] = []
        for col in columns:
            if col.semantic_type != "currency":
                continue
            values = df[col.name].astype(str)
            currency_symbols = values.str.extract(r"([A-Z]{3}|[$€£¥])")[0].dropna().unique()
            if len(currency_symbols) > 1:
                issues.append(
                    DataQualityIssue(
                        issue_type="currency_inconsistency",
                        severity=DataQualitySeverity.WARNING,
                        table=table_name,
                        column=col.name,
                        message=f"Multiple currencies: {list(currency_symbols)}",
                        suggestion="Normalize currency amounts",
                    )
                )
        return issues

    def generate_report(self, issues: list[DataQualityIssue]) -> dict[str, Any]:
        by_severity: dict[str, int] = {}
        by_type: dict[str, int] = {}
        for issue in issues:
            by_severity[issue.severity.value] = by_severity.get(issue.severity.value, 0) + 1
            by_type[issue.issue_type] = by_type.get(issue.issue_type, 0) + 1
        return {
            "total_issues": len(issues),
            "by_severity": by_severity,
            "by_type": by_type,
            "issues": [
                {
                    "type": i.issue_type,
                    "severity": i.severity.value,
                    "table": i.table,
                    "column": i.column,
                    "message": i.message,
                    "suggestion": i.suggestion,
                }
                for i in issues
            ],
        }
