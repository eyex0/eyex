"""
πX Relationship Discovery Engine — Automatically discovers entity relationships.

Discovers relationships like:
  Customer → Orders, Product → Sales, Store → Revenue, Machine → Defects

Based on:
  - Column name patterns (shared entity references across columns)
  - Foreign key patterns (ID columns matching across tables)
  - Statistical similarity (correlated columns)
  - Value overlap (shared unique values between columns)
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

import pandas as pd

logger = logging.getLogger("pix.data_intelligence.relationships")


@dataclass
class DiscoveredRelationship:
    source_column: str
    target_column: str
    relation_type: str  # foreign_key, metric_of, dimension_of, correlates_with
    confidence: float = 0.0
    evidence: str = ""
    source_entity: str | None = None
    target_entity: str | None = None

    def to_dict(self) -> dict:
        return {
            "source_column": self.source_column,
            "target_column": self.target_column,
            "relation_type": self.relation_type,
            "confidence": self.confidence,
            "evidence": self.evidence,
            "source_entity": self.source_entity,
            "target_entity": self.target_entity,
        }


class RelationshipDiscoveryEngine:
    """Discovers relationships between columns and entities in data."""

    def discover(
        self,
        df: pd.DataFrame,
        column_mappings: list[dict] | None = None,
        sheets: dict[str, pd.DataFrame] | None = None,
    ) -> list[dict]:
        """
        Discover all relationships in a dataset.

        Args:
            df: Main dataframe to analyze
            column_mappings: Semantic mappings from the profiler
            sheets: Multiple sheets for cross-table relationship discovery

        Returns: list of relationship dicts
        """
        relationships: list[DiscoveredRelationship] = []

        # 1. Within-table relationships (metric_of, dimension_of)
        relationships.extend(self._discover_metric_dimension(df, column_mappings or []))

        # 2. Foreign key detection within table
        relationships.extend(self._discover_foreign_keys_single_table(df, column_mappings or []))

        # 3. Cross-table relationships (if multiple sheets provided)
        if sheets:
            relationships.extend(self._discover_cross_table(sheets, column_mappings or []))

        # 4. Statistical correlations
        relationships.extend(self._discover_correlations(df))

        # Deduplicate and sort by confidence
        unique = self._deduplicate(relationships)
        unique.sort(key=lambda r: r.confidence, reverse=True)

        return [r.to_dict() for r in unique]

    def _discover_metric_dimension(
        self, df: pd.DataFrame, mappings: list[dict]
    ) -> list[DiscoveredRelationship]:
        """Discover metric → dimension relationships (e.g., Revenue → by Store)."""
        relationships = []

        # Identify metric and dimension columns from mappings
        metrics = [m for m in mappings if m.get("is_metric") or m.get("semantic_type") in ("currency", "numeric")]
        dimensions = [m for m in mappings if m.get("semantic_type") in ("identifier", "category", "text")
                      and not m.get("is_metric")]

        for metric in metrics:
            for dim in dimensions:
                # Skip if same column
                if metric["source_column"] == dim["source_column"]:
                    continue
                # Check if the dimension has reasonable cardinality (not too unique, not constant)
                col = df.get(dim["source_column"])
                if col is None:
                    continue
                nunique = col.nunique()
                if 2 <= nunique <= min(len(df) * 0.5, 100):
                    relationships.append(DiscoveredRelationship(
                        source_column=metric["source_column"],
                        target_column=dim["source_column"],
                        relation_type="metric_of",
                        confidence=0.6,
                        evidence=f"'{metric['source_column']}' is a metric that can be grouped by '{dim['source_column']}' ({nunique} categories)",
                        source_entity=metric.get("entity"),
                        target_entity=dim.get("entity"),
                    ))

        return relationships

    def _discover_foreign_keys_single_table(
        self, df: pd.DataFrame, mappings: list[dict]
    ) -> list[DiscoveredRelationship]:
        """Detect foreign key patterns within a single table."""
        relationships = []

        id_columns = [col for col in df.columns
                      if str(col).lower().endswith("_id") or str(col).lower().endswith("_no")
                      or str(col).lower().endswith("id") or str(col).lower().endswith("code")]

        for id_col in id_columns:
            for other_col in df.columns:
                if id_col == other_col:
                    continue
                # Check if id_col name contains other_col's entity
                id_name = str(id_col).lower()
                other_name = str(other_col).lower()
                # E.g., "Store_ID" contains "store" → relationship between Store and this table
                if other_name in id_name and other_name != id_name:
                    mapping = next((m for m in mappings if m["source_column"] == str(other_col)), None)
                    entity = mapping.get("entity") if mapping else other_name
                    relationships.append(DiscoveredRelationship(
                        source_column=str(id_col),
                        target_column=str(other_col),
                        relation_type="foreign_key",
                        confidence=0.70,
                        evidence=f"'{id_col}' appears to reference '{other_col}' (name containment pattern)",
                        target_entity=entity,
                    ))

        return relationships

    def _discover_cross_table(
        self, sheets: dict[str, pd.DataFrame], mappings: list[dict]
    ) -> list[DiscoveredRelationship]:
        """Discover relationships across multiple sheets/tables."""
        relationships = []
        sheet_names = list(sheets.keys())

        for i, sheet1 in enumerate(sheet_names):
            df1 = sheets[sheet1]
            for sheet2 in sheet_names[i+1:]:
                df2 = sheets[sheet2]
                # Find shared column names
                shared = set(df1.columns) & set(df2.columns)
                for col in shared:
                    # Check value overlap
                    vals1 = set(df1[col].dropna().unique())
                    vals2 = set(df2[col].dropna().unique())
                    overlap = vals1 & vals2
                    if overlap and len(overlap) > 1:
                        overlap_ratio = len(overlap) / min(len(vals1), len(vals2))
                        if overlap_ratio > 0.5:
                            relationships.append(DiscoveredRelationship(
                                source_column=f"{sheet1}.{col}",
                                target_column=f"{sheet2}.{col}",
                                relation_type="cross_table_reference",
                                confidence=min(0.90, overlap_ratio),
                                evidence=f"High value overlap ({overlap_ratio:.0%}) between '{sheet1}.{col}' and '{sheet2}.{col}'",
                            ))

                # Find ID columns in sheet1 that match column names in sheet2
                for col1 in df1.columns:
                    col1_str = str(col1).lower()
                    if col1_str.endswith("_id") or col1_str.endswith("id"):
                        base = col1_str.replace("_id", "").replace("id", "")
                        for col2 in df2.columns:
                            if str(col2).lower() == base or str(col2).lower().startswith(base):
                                relationships.append(DiscoveredRelationship(
                                    source_column=f"{sheet1}.{col1}",
                                    target_column=f"{sheet2}.{col2}",
                                    relation_type="cross_table_fk",
                                    confidence=0.65,
                                    evidence=f"'{col1}' in {sheet1} likely references '{col2}' in {sheet2}",
                                ))
                                break

        return relationships

    def _discover_correlations(self, df: pd.DataFrame) -> list[DiscoveredRelationship]:
        """Discover statistically correlated numeric columns."""
        relationships = []
        numeric_cols = df.select_dtypes(include=["number"]).columns.tolist()

        if len(numeric_cols) < 2:
            return relationships

        try:
            corr = df[numeric_cols].corr()
            for i, col1 in enumerate(numeric_cols):
                for col2 in numeric_cols[i+1:]:
                    if col1 == col2:
                        continue
                    val = corr.loc[col1, col2]
                    if pd.notna(val) and abs(val) > 0.7:
                        relationships.append(DiscoveredRelationship(
                            source_column=str(col1),
                            target_column=str(col2),
                            relation_type="correlates_with",
                            confidence=round(min(abs(val), 1.0), 4),
                            evidence=f"Correlation coefficient: {val:.3f} ({'positive' if val > 0 else 'negative'})",
                        ))
        except Exception as exc:
            logger.debug("Correlation analysis failed: %s", exc)

        return relationships

    @staticmethod
    def _deduplicate(relationships: list[DiscoveredRelationship]) -> list[DiscoveredRelationship]:
        """Remove duplicate relationships."""
        seen = set()
        unique = []
        for r in relationships:
            key = (r.source_column, r.target_column, r.relation_type)
            if key not in seen:
                seen.add(key)
                unique.append(r)
        return unique
