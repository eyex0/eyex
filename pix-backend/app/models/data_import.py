from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import Boolean, ForeignKey, Integer, String
from app.models.types import JSONBCompat
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class ImportReport(Base):
    __tablename__ = "import_reports"

    dataset_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("imported_datasets.id", ondelete="CASCADE"), index=True, nullable=False)
    total_rows: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    imported_rows: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    failed_rows: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    skipped_rows: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    duplicate_rows: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    processing_time_ms: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    error_summary: Mapped[dict[str, Any] | None] = mapped_column(JSONBCompat, nullable=True)


class UniversalRecord(Base):
    __tablename__ = "universal_records"

    dataset_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("imported_datasets.id", ondelete="CASCADE"), index=True, nullable=False)
    row_index: Mapped[int] = mapped_column(Integer, nullable=False)
    data: Mapped[dict[str, Any]] = mapped_column(JSONBCompat, nullable=False)
    is_valid: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    validation_errors: Mapped[list[dict[str, Any]] | None] = mapped_column(JSONBCompat, nullable=True)
