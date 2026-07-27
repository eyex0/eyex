from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pandas as pd

from app.cognitive_data_layer.canonical.model import (
    CanonicalColumn,
    CanonicalRelationship,
    ColumnSemanticType,
)
from app.cognitive_data_layer.semantic import SemanticUnderstandingEngine


@dataclass
class SchemaDiscoveryResult:
    columns: list[CanonicalColumn]
    primary_keys: list[str]
    foreign_keys: list[CanonicalRelationship]
    is_time_series: bool
    categories: list[str]


class SchemaDiscoverer:
    """Detect schema, keys, relationships, and temporal structure from tables."""

    def __init__(self, semantic_engine: SemanticUnderstandingEngine | None = None) -> None:
        self.semantic_engine = semantic_engine or SemanticUnderstandingEngine()

    def discover(
        self,
        table_name: str,
        df: pd.DataFrame,
        all_tables: dict[str, pd.DataFrame] | None = None,
    ) -> SchemaDiscoveryResult:
        all_tables = all_tables or {}
        columns = self._analyze_columns(df)
        primary_keys = self._detect_primary_keys(df, columns)
        foreign_keys = self._detect_foreign_keys(table_name, df, columns, all_tables)
        is_time_series = self._detect_time_series(columns, df)
        categories = self._detect_categories(columns, df)

        return SchemaDiscoveryResult(
            columns=columns,
            primary_keys=primary_keys,
            foreign_keys=foreign_keys,
            is_time_series=is_time_series,
            categories=categories,
        )

    def _analyze_columns(self, df: pd.DataFrame) -> list[CanonicalColumn]:
        columns: list[CanonicalColumn] = []
        for col in df.columns:
            series = df[col]
            sample_values = series.dropna().head(5).tolist()
            inferred_type = self._infer_dtype(series)
            semantic_type = self._map_semantic_type(inferred_type, col, sample_values)
            mapping = self.semantic_engine.infer_entity(col, sample_values)

            columns.append(
                CanonicalColumn(
                    name=str(col),
                    original_name=str(col),
                    semantic_type=semantic_type,
                    inferred_type=inferred_type,
                    entity_type=mapping.entity_type,
                    confidence=mapping.confidence,
                    explanation=mapping.explanation,
                    sample_values=sample_values,
                    null_count=int(series.isna().sum()),
                    unique_count=int(series.nunique()),
                )
            )
        return columns

    def _infer_dtype(self, series: pd.Series) -> str:
        if pd.api.types.is_datetime64_any_dtype(series):
            return "datetime"
        if pd.api.types.is_integer_dtype(series):
            return "integer"
        if pd.api.types.is_float_dtype(series):
            return "float"
        if pd.api.types.is_bool_dtype(series):
            return "boolean"
        return "string"

    def _map_semantic_type(
        self, inferred_type: str, column_name: str, sample_values: list[Any]
    ) -> ColumnSemanticType:
        lower_name = column_name.lower()
        if any(k in lower_name for k in ["id", "number", "code", "key"]):
            return ColumnSemanticType.IDENTIFIER
        if inferred_type in ("datetime", "date"):
            return ColumnSemanticType.DATE
        if inferred_type in ("integer", "float"):
            if any(k in lower_name for k in ["price", "cost", "amount", "revenue", "salary"]):
                return ColumnSemanticType.CURRENCY
            if any(k in lower_name for k in ["qty", "quantity", "count", "units"]):
                return ColumnSemanticType.QUANTITY
            if any(k in lower_name for k in ["rate", "pct", "percentage", "ratio"]):
                return ColumnSemanticType.PERCENTAGE
            return ColumnSemanticType.NUMERIC
        if inferred_type == "boolean":
            return ColumnSemanticType.BOOLEAN
        if any(k in lower_name for k in ["email", "e-mail"]):
            return ColumnSemanticType.EMAIL
        if any(k in lower_name for k in ["phone", "mobile", "tel"]):
            return ColumnSemanticType.PHONE
        if any(k in lower_name for k in ["address", "street", "city", "country"]):
            return ColumnSemanticType.ADDRESS
        if sample_values:
            unique_ratio = len(set(sample_values)) / len(sample_values)
            if unique_ratio <= 0.5 or len(set(sample_values)) <= 5:
                return ColumnSemanticType.CATEGORY
        return ColumnSemanticType.TEXT

    def _detect_primary_keys(self, df: pd.DataFrame, columns: list[CanonicalColumn]) -> list[str]:
        candidates: list[str] = []
        for col in columns:
            series = df[col.name]
            if col.semantic_type == ColumnSemanticType.IDENTIFIER:
                if series.nunique() == len(df) and series.notna().all():
                    candidates.append(col.name)
        # Fallback: first unique non-null column
        if not candidates:
            for col in columns:
                series = df[col.name]
                if series.nunique() == len(df) and series.notna().all():
                    candidates.append(col.name)
                    break
        return candidates

    def _detect_foreign_keys(
        self,
        table_name: str,
        df: pd.DataFrame,
        columns: list[CanonicalColumn],
        all_tables: dict[str, pd.DataFrame],
    ) -> list[CanonicalRelationship]:
        relationships: list[CanonicalRelationship] = []
        for col in columns:
            if col.semantic_type != ColumnSemanticType.IDENTIFIER:
                continue
            for other_table, other_df in all_tables.items():
                if other_table == table_name:
                    continue
                for other_col in other_df.columns:
                    if other_col.lower() == col.name.lower():
                        overlap = set(df[col.name].dropna().unique()) & set(
                            other_df[other_col].dropna().unique()
                        )
                        if overlap:
                            relationships.append(
                                CanonicalRelationship(
                                    source_table=table_name,
                                    source_column=col.name,
                                    target_table=other_table,
                                    target_column=other_col,
                                    relationship_type="foreign_key",
                                    confidence=min(1.0, len(overlap) / 10),
                                    explanation=f"Shared values with {other_table}.{other_col}",
                                )
                            )
        return relationships

    def _detect_time_series(self, columns: list[CanonicalColumn], df: pd.DataFrame) -> bool:
        date_cols = [c for c in columns if c.semantic_type == ColumnSemanticType.DATE]
        if not date_cols:
            return False
        numeric_cols = [
            c
            for c in columns
            if c.semantic_type in (ColumnSemanticType.NUMERIC, ColumnSemanticType.CURRENCY)
        ]
        return len(date_cols) > 0 and len(numeric_cols) > 0

    def _detect_categories(self, columns: list[CanonicalColumn], df: pd.DataFrame) -> list[str]:
        return [c.name for c in columns if c.semantic_type == ColumnSemanticType.CATEGORY]
