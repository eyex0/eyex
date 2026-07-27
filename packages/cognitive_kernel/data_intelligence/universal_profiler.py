"""
πX Universal Data Profiler — Profiles ANY enterprise data source.

Input: XLSX, CSV, PDF tables, DOCX tables, Database tables, API responses
Output: dataset_profile, columns, detected_entities, detected_metrics,
        relationships, quality_score, confidence

Works with any column names, any schema, any industry.
"""
from __future__ import annotations

import io
import json
import logging
from dataclasses import dataclass, field
from typing import Any

import pandas as pd

logger = logging.getLogger("pix.data_intelligence.profiler")


@dataclass
class ColumnProfile:
    name: str
    dtype: str
    semantic_type: str = "unknown"  # identifier, text, numeric, currency, date, boolean, category, email, phone
    sample_values: list = field(default_factory=list)
    null_count: int = 0
    null_percentage: float = 0.0
    unique_count: int = 0
    unique_percentage: float = 0.0
    min_value: Any = None
    max_value: Any = None
    mean_value: Any = None
    std_value: Any = None
    inferred_entity: str | None = None
    inferred_meaning: str | None = None
    confidence: float = 0.0
    is_metric: bool = False
    is_identifier: bool = False
    is_pii: bool = False
    metadata: dict = field(default_factory=dict)


@dataclass
class DatasetProfile:
    source_name: str
    source_type: str  # xlsx, csv, pdf, docx, database, api
    row_count: int = 0
    column_count: int = 0
    columns: list[ColumnProfile] = field(default_factory=list)
    detected_entities: list[dict] = field(default_factory=list)
    detected_metrics: list[dict] = field(default_factory=list)
    relationships: list[dict] = field(default_factory=list)
    quality_score: float = 0.0
    confidence: float = 0.0
    sheet_names: list[str] = field(default_factory=list)
    has_time_dimension: bool = False
    has_geographic_dimension: bool = False
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "source_name": self.source_name,
            "source_type": self.source_type,
            "row_count": self.row_count,
            "column_count": self.column_count,
            "columns": [
                {
                    "name": c.name, "dtype": c.dtype, "semantic_type": c.semantic_type,
                    "sample_values": c.sample_values[:5],
                    "null_count": c.null_count, "null_percentage": c.null_percentage,
                    "unique_count": c.unique_count, "unique_percentage": c.unique_percentage,
                    "inferred_entity": c.inferred_entity,
                    "inferred_meaning": c.inferred_meaning,
                    "confidence": c.confidence,
                    "is_metric": c.is_metric, "is_identifier": c.is_identifier, "is_pii": c.is_pii,
                }
                for c in self.columns
            ],
            "detected_entities": self.detected_entities,
            "detected_metrics": self.detected_metrics,
            "relationships": self.relationships,
            "quality_score": self.quality_score,
            "confidence": self.confidence,
            "sheet_names": self.sheet_names,
            "has_time_dimension": self.has_time_dimension,
            "has_geographic_dimension": self.has_geographic_dimension,
        }


class UniversalDataProfiler:
    """Profiles any data source and extracts business meaning."""

    def __init__(self, mapping_engine=None, quality_engine=None):
        self.mapping_engine = mapping_engine
        self.quality_engine = quality_engine

    def profile_excel(self, content: bytes, source_name: str = "upload.xlsx") -> list[DatasetProfile]:
        """Profile an Excel file — one profile per sheet."""
        profiles = []
        xls = pd.ExcelFile(io.BytesIO(content), engine="openpyxl")
        for sheet_name in xls.sheet_names:
            df = xls.parse(sheet_name)
            profile = self._profile_dataframe(df, source_name, "xlsx", sheet_name)
            profiles.append(profile)
        return profiles

    def profile_csv(self, content: bytes, source_name: str = "upload.csv") -> DatasetProfile:
        """Profile a CSV file."""
        df = pd.read_csv(io.BytesIO(content))
        return self._profile_dataframe(df, source_name, "csv")

    def profile_dataframe(self, df: pd.DataFrame, source_name: str = "dataframe") -> DatasetProfile:
        """Profile a pandas DataFrame (used for DB tables, API responses)."""
        return self._profile_dataframe(df, source_name, "dataframe")

    def profile_pdf_tables(self, tables: list[pd.DataFrame], source_name: str = "document.pdf") -> list[DatasetProfile]:
        """Profile tables extracted from PDF."""
        profiles = []
        for i, df in enumerate(tables):
            profile = self._profile_dataframe(df, source_name, "pdf", f"table_{i}")
            profiles.append(profile)
        return profiles

    def profile_api_response(self, data: list[dict], source_name: str = "api_response") -> DatasetProfile:
        """Profile an API response (list of JSON objects)."""
        df = pd.DataFrame(data)
        return self._profile_dataframe(df, source_name, "api")

    def _profile_dataframe(
        self,
        df: pd.DataFrame,
        source_name: str,
        source_type: str,
        sheet_name: str | None = None,
    ) -> DatasetProfile:
        """Core profiling logic — works with any DataFrame."""
        profile = DatasetProfile(
            source_name=source_name,
            source_type=source_type,
            row_count=len(df),
            column_count=len(df.columns),
        )
        if sheet_name:
            profile.sheet_names = [sheet_name]

        # Profile each column
        for col_name in df.columns:
            col_profile = self._profile_column(str(col_name), df[col_name])
            profile.columns.append(col_profile)

        # Detect entities, metrics, dimensions
        profile.detected_entities = self._detect_entities(profile.columns)
        profile.detected_metrics = self._detect_metrics(profile.columns)
        profile.has_time_dimension = any(c.semantic_type == "date" for c in profile.columns)
        profile.has_geographic_dimension = self._detect_geographic(df)

        # Calculate overall confidence
        if profile.columns:
            avg_conf = sum(c.confidence for c in profile.columns) / len(profile.columns)
            profile.confidence = round(avg_conf, 4)

        # Calculate quality score
        profile.quality_score = self._calculate_quality_score(df, profile.columns)

        return profile

    def _profile_column(self, name: str, series: pd.Series) -> ColumnProfile:
        """Profile a single column."""
        col = ColumnProfile(name=name, dtype=str(series.dtype))
        col.sample_values = series.dropna().head(5).tolist()
        col.null_count = int(series.isna().sum())
        col.null_percentage = round(col.null_count / max(len(series), 1) * 100, 2)
        col.unique_count = int(series.nunique())
        col.unique_percentage = round(col.unique_count / max(len(series), 1) * 100, 2)

        # Infer semantic type
        col.semantic_type = self._infer_semantic_type(name, series)
        col.is_identifier = col.semantic_type == "identifier"
        col.is_pii = self._check_pii(name, series)

        # Numeric stats
        if col.semantic_type in ("numeric", "currency"):
            col.min_value = float(series.min()) if not series.isna().all() else None
            col.max_value = float(series.max()) if not series.isna().all() else None
            col.mean_value = float(series.mean()) if not series.isna().all() else None
            col.std_value = float(series.std()) if not series.isna().all() else None
            col.is_metric = True

        # Infer entity/meaning using mapping engine if available
        if self.mapping_engine:
            mapping = self.mapping_engine.map_column(name, col.sample_values)
            col.inferred_entity = mapping.get("entity")
            col.inferred_meaning = mapping.get("meaning")
            col.confidence = mapping.get("confidence", 0.0)
        else:
            col.confidence = 0.5 if col.semantic_type != "unknown" else 0.2

        return col

    def _infer_semantic_type(self, name: str, series: pd.Series) -> str:
        """Infer the semantic type of a column."""
        dtype = str(series.dtype)
        name_lower = name.lower()

        # Check by name patterns first
        if any(kw in name_lower for kw in ["email", "mail", "e-mail"]):
            return "email"
        if any(kw in name_lower for kw in ["phone", "tel", "mobile", "fax"]):
            return "phone"
        if any(kw in name_lower for kw in ["date", "time", "timestamp", "created", "updated", "_at", "_dt"]):
            return "date"
        if any(kw in name_lower for kw in ["rev", "revenue", "amount", "price", "cost", "value", "salary", "balance", "total"]):
            if dtype in ("int64", "float64", "float32", "int32"):
                return "currency"
        if any(kw in name_lower for kw in ["id", "code", "no", "number", "ref", "key"]):
            if series.nunique() / max(len(series), 1) > 0.8:
                return "identifier"
        if dtype == "bool":
            return "boolean"
        if dtype in ("int64", "float64", "float32", "int32"):
            if series.nunique() / max(len(series), 1) > 0.9:
                return "numeric"
            return "category"
        # Check if it looks like a date
        if dtype == "object":
            sample = series.dropna().head(5).tolist()
            if sample and all(isinstance(v, str) and len(v) >= 8 and any(sep in v for sep in ["-", "/", ":"]) for v in sample):
                try:
                    pd.to_datetime(series.head(20))
                    return "date"
                except (ValueError, TypeError):
                    pass
        if series.nunique() / max(len(series), 1) < 0.05 and series.nunique() < 50:
            return "category"
        return "text"

    def _check_pii(self, name: str, series: pd.Series) -> bool:
        """Quick PII check based on column name."""
        name_lower = name.lower()
        pii_keywords = ["ssn", "social_security", "passport", "national_id", "credit_card", "card_number",
                        "iban", "account_no", "pin", "password", "secret", "private_key"]
        return any(kw in name_lower for kw in pii_keywords)

    def _detect_entities(self, columns: list[ColumnProfile]) -> list[dict]:
        """Detect entity types from column profiles."""
        entities = []
        seen = set()
        for col in columns:
            if col.inferred_entity and col.inferred_entity not in seen:
                entities.append({
                    "entity_type": col.inferred_entity,
                    "source_column": col.name,
                    "confidence": col.confidence,
                })
                seen.add(col.inferred_entity)
            elif col.is_identifier and col.inferred_entity is None:
                # Infer entity from identifier name
                entity_guess = self._guess_entity_from_name(col.name)
                if entity_guess and entity_guess not in seen:
                    entities.append({
                        "entity_type": entity_guess,
                        "source_column": col.name,
                        "confidence": 0.4,
                    })
                    seen.add(entity_guess)
        return entities

    def _detect_metrics(self, columns: list[ColumnProfile]) -> list[dict]:
        """Detect metric columns (numeric/currency that aren't identifiers)."""
        metrics = []
        for col in columns:
            if col.is_metric and not col.is_identifier:
                metrics.append({
                    "name": col.name,
                    "semantic_type": col.semantic_type,
                    "inferred_meaning": col.inferred_meaning or col.name,
                    "confidence": col.confidence,
                    "min": col.min_value,
                    "max": col.max_value,
                    "mean": col.mean_value,
                })
        return metrics

    def _detect_geographic(self, df: pd.DataFrame) -> bool:
        """Check if any column looks geographic."""
        geo_keywords = ["country", "region", "state", "city", "address", "location", "zip", "postal", "lat", "lon", "store"]
        return any(any(kw in str(col).lower() for kw in geo_keywords) for col in df.columns)

    def _guess_entity_from_name(self, name: str) -> str | None:
        """Guess entity type from column name when no mapping engine is available."""
        name_lower = name.lower()
        patterns = {
            "customer": ["cust", "client", "buyer", "account_name"],
            "product": ["product", "item", "sku", "merchandise"],
            "employee": ["employee", "staff", "worker", "operator"],
            "store": ["store", "shop", "branch", "location"],
            "machine": ["machine", "equipment", "asset"],
            "supplier": ["supplier", "vendor", "provider"],
            "project": ["project", "job", "task", "work_order"],
            "patient": ["patient", "beneficiary", "member"],
        }
        for entity, keywords in patterns.items():
            if any(kw in name_lower for kw in keywords):
                return entity
        return None

    def _calculate_quality_score(self, df: pd.DataFrame, columns: list[ColumnProfile]) -> float:
        """Calculate overall data quality score (0.0–1.0)."""
        if df.empty:
            return 0.0
        scores = []
        for col in columns:
            col_score = 1.0
            col_score -= col.null_percentage / 100 * 0.4  # Missing values
            if col.unique_count == 0:
                col_score -= 0.3  # All null
            if col.unique_count == 1 and col.semantic_type not in ("boolean", "category"):
                col_score -= 0.2  # Constant value
            scores.append(max(0.0, col_score))
        return round(sum(scores) / max(len(scores), 1), 4)
