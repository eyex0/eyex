from __future__ import annotations

from typing import Any

import pandas as pd

from app.cognitive_data_layer.canonical.model import (
    CanonicalDataset,
    CanonicalRow,
    CanonicalSheet,
    CanonicalTable,
)
from app.cognitive_data_layer.schema import SchemaDiscoverer


class CanonicalBuilder:
    """Convert parsed raw data into πX's canonical representation."""

    def __init__(self, schema_discoverer: SchemaDiscoverer | None = None) -> None:
        self.schema_discoverer = schema_discoverer or SchemaDiscoverer()

    def build(
        self, source_name: str, source_format: str, parsed_sheets: list[dict[str, Any]]
    ) -> CanonicalDataset:
        dataframes = {sheet["name"]: sheet["data"] for sheet in parsed_sheets}
        sheets: list[CanonicalSheet] = []

        for idx, sheet in enumerate(parsed_sheets):
            df = sheet["data"]
            tables: list[CanonicalTable] = []

            # Each sheet is a table for now; future: table segmentation
            discovery = self.schema_discoverer.discover(
                table_name=sheet["name"], df=df, all_tables=dataframes
            )

            rows = [
                CanonicalRow(index=i, values=row.to_dict(), metadata={}) for i, row in df.iterrows()
            ]

            tables.append(
                CanonicalTable(
                    name=sheet["name"],
                    original_name=sheet["name"],
                    columns=discovery.columns,
                    rows=rows,
                    primary_keys=discovery.primary_keys,
                    metadata={
                        "is_time_series": discovery.is_time_series,
                        "foreign_keys": discovery.foreign_keys,
                    },
                )
            )

            sheets.append(CanonicalSheet(name=sheet["name"], index=idx, tables=tables))

        # Collect relationships across tables
        all_relationships: list[Any] = []
        entities: dict = {}
        for sheet in sheets:
            for table in sheet.tables:
                all_relationships.extend(table.metadata.get("foreign_keys", []))
                for col in table.columns:
                    if col.entity_type:
                        entities.setdefault(col.entity_type, []).append(table.name)

        dataset = CanonicalDataset(
            source_name=source_name,
            source_format=source_format,
            sheets=sheets,
            relationships=all_relationships,
            entities=entities,
        )
        return dataset

    def _dataframe_to_rows(self, df: pd.DataFrame) -> list[CanonicalRow]:
        return [CanonicalRow(index=i, values=row.to_dict()) for i, row in df.iterrows()]
