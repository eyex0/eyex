from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any


class EntityType(StrEnum):
    CUSTOMER = "customer"
    EMPLOYEE = "employee"
    PRODUCT = "product"
    ORDER = "order"
    INVOICE = "invoice"
    DEPARTMENT = "department"
    PROJECT = "project"
    ASSET = "asset"
    REVENUE = "revenue"
    COST = "cost"
    SUPPLIER = "supplier"
    INVENTORY = "inventory"
    TRANSACTION = "transaction"
    BUSINESS_DATE = "business_date"
    UNKNOWN = "unknown"


class ColumnSemanticType(StrEnum):
    IDENTIFIER = "identifier"
    TEXT = "text"
    NUMERIC = "numeric"
    CURRENCY = "currency"
    DATE = "date"
    DATETIME = "datetime"
    BOOLEAN = "boolean"
    CATEGORY = "category"
    EMAIL = "email"
    PHONE = "phone"
    ADDRESS = "address"
    PERCENTAGE = "percentage"
    QUANTITY = "quantity"
    UNKNOWN = "unknown"


class DataQualitySeverity(StrEnum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class CanonicalColumn:
    name: str
    original_name: str
    semantic_type: ColumnSemanticType = ColumnSemanticType.UNKNOWN
    inferred_type: str = "object"
    entity_type: EntityType | None = None
    confidence: float = 0.0
    explanation: str = ""
    sample_values: list[Any] = field(default_factory=list)
    null_count: int = 0
    unique_count: int = 0
    metadata: dict = field(default_factory=dict)


@dataclass
class CanonicalRow:
    index: int
    values: dict[str, Any] = field(default_factory=dict)
    metadata: dict = field(default_factory=dict)


@dataclass
class CanonicalRelationship:
    source_table: str
    source_column: str
    target_table: str
    target_column: str
    relationship_type: str = "foreign_key"
    confidence: float = 0.0
    explanation: str = ""


@dataclass
class DataQualityIssue:
    issue_type: str
    severity: DataQualitySeverity
    table: str
    column: str | None = None
    row_indices: list[int] = field(default_factory=list)
    message: str = ""
    suggestion: str = ""


@dataclass
class CanonicalTable:
    name: str
    original_name: str
    columns: list[CanonicalColumn] = field(default_factory=list)
    rows: list[CanonicalRow] = field(default_factory=list)
    primary_keys: list[str] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)


@dataclass
class CanonicalSheet:
    name: str
    index: int
    tables: list[CanonicalTable] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)


@dataclass
class CanonicalDataset:
    source_name: str
    source_format: str
    sheets: list[CanonicalSheet] = field(default_factory=list)
    relationships: list[CanonicalRelationship] = field(default_factory=list)
    entities: dict[EntityType, list[str]] = field(default_factory=dict)
    quality_issues: list[DataQualityIssue] = field(default_factory=list)
    confidence: float = 0.0
    processing_metadata: dict = field(default_factory=dict)
    generated_at: datetime = field(default_factory=lambda: datetime.now(UTC))
