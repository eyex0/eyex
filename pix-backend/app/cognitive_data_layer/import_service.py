from __future__ import annotations

import json
import logging
import time
import uuid
from pathlib import Path
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.cognitive_data_layer.parser import parse_source
from app.models.data_import import ImportReport, UniversalRecord

logger = logging.getLogger(__name__)


class ImportService:
    @staticmethod
    async def import_dataset(
        session: AsyncSession,
        dataset_id: uuid.UUID,
        file_content: bytes,
        file_hint: str,
        mappings: dict[str, str],
    ) -> dict[str, Any]:
        """
        Parses a file, applies mappings, validates rows, and imports into universal_records.
        """
        start_time = time.time()

        # Parse the raw data using existing Cognitive Data parsers
        parsed = await parse_source(file_content, hint=file_hint)
        sheets = parsed.raw_data.get("sheets", [])

        total_rows = 0
        imported_rows = 0
        failed_rows = 0
        skipped_rows = 0
        error_summary: dict[str, int] = {}
        
        all_records = []

        if not sheets:
            raise ValueError("No sheets or data found in the file")

        # Process the first sheet by default
        df = sheets[0]["data"]
        total_rows = len(df)

        for index, row in df.iterrows():
            row_dict = row.to_dict()
            mapped_data = {}
            is_valid = True
            validation_errors = []

            # Map the original columns to their assigned semantic types
            for orig_col, val in row_dict.items():
                target_col = mappings.get(orig_col)
                if not target_col:
                    # If column is unmapped, we can either skip it or keep it with original name
                    target_col = orig_col
                
                # Basic validation based on target_col
                if val is None or str(val).strip() == "":
                    # Depending on strictness, we might flag empty values
                    pass
                elif target_col == "email" and "@" not in str(val):
                    is_valid = False
                    validation_errors.append({"column": orig_col, "error": "Invalid email format"})
                    error_summary["invalid_email"] = error_summary.get("invalid_email", 0) + 1
                
                mapped_data[target_col] = val

            if is_valid:
                imported_rows += 1
            else:
                failed_rows += 1

            record = UniversalRecord(
                dataset_id=dataset_id,
                row_index=index,
                data=mapped_data,
                is_valid=is_valid,
                validation_errors=validation_errors if validation_errors else None,
            )
            all_records.append(record)

        # Bulk insert records
        session.add_all(all_records)

        processing_time_ms = int((time.time() - start_time) * 1000)

        # Create import report
        report = ImportReport(
            dataset_id=dataset_id,
            total_rows=total_rows,
            imported_rows=imported_rows,
            failed_rows=failed_rows,
            skipped_rows=skipped_rows,
            duplicate_rows=0,
            processing_time_ms=processing_time_ms,
            error_summary=error_summary if error_summary else None,
        )
        session.add(report)

        await session.commit()

        return {
            "dataset_id": str(dataset_id),
            "total_rows": total_rows,
            "imported_rows": imported_rows,
            "failed_rows": failed_rows,
            "skipped_rows": skipped_rows,
            "processing_time_ms": processing_time_ms,
            "error_summary": error_summary,
        }
