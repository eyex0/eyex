"""
πX PII Protection — Detects and masks PII before AI processing.

Runs BEFORE embedding, LLM calls, and vector storage.
Detects: emails, phone numbers, personal IDs, financial sensitive fields.
Applies: masking, flagging, and access policy enforcement.
"""
from __future__ import annotations

import hashlib
import logging
import re
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger("pix.data_intelligence.pii")


# PII detection patterns
PII_PATTERNS = {
    "email": re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'),
    "phone": re.compile(r'\b(?:\+?(\d{1,3})?[-. ]?)?\(?\d{1,4}\)?[-. ]?\d{3,5}[-. ]?\d{3,5}\b'),
    "ssn": re.compile(r'\b\d{3}-\d{2}-\d{4}\b'),
    "credit_card": re.compile(r'\b(?:\d{4}[-\s]?){3}\d{4}\b'),
    "iban": re.compile(r'\b[A-Z]{2}\d{2}[A-Z0-9]{4}\d{7}([A-Z0-9]?){0,16}\b'),
    "ip_address": re.compile(r'\b(?:\d{1,3}\.){3}\d{1,3}\b'),
}

# PII column name patterns
PII_COLUMN_PATTERNS = {
    "email": ["email", "e-mail", "email_address", "mail"],
    "phone": ["phone", "tel", "mobile", "telephone", "phone_number"],
    "ssn": ["ssn", "social_security", "national_id", "passport"],
    "credit_card": ["credit_card", "card_number", "cc_number", "pan"],
    "iban": ["iban", "account_no", "account_number", "bank_account"],
    "personal_id": ["personal_id", "id_number", "national_id", "tax_id", "fiscal_code"],
    "address": ["address", "street", "zip", "postal", "city"],
    "name": ["first_name", "last_name", "full_name", "customer_name", "patient_name"],
    "date_of_birth": ["dob", "date_of_birth", "birth_date", "birthday"],
}


@dataclass
class PIIDetection:
    column_name: str
    pii_type: str
    confidence: float = 0.0
    detection_method: str = "pattern"  # pattern, column_name, content
    sample_masked: str = ""
    action: str = "mask"  # mask, flag, block
    row_count_affected: int = 0

    def to_dict(self) -> dict:
        return {
            "column_name": self.column_name,
            "pii_type": self.pii_type,
            "confidence": self.confidence,
            "detection_method": self.detection_method,
            "action": self.action,
            "row_count_affected": self.row_count_affected,
        }


@dataclass
class PIIProtectionResult:
    detections: list[PIIDetection] = field(default_factory=list)
    columns_masked: list[str] = field(default_factory=list)
    columns_flagged: list[str] = field(default_factory=list)
    columns_blocked: list[str] = field(default_factory=list)
    total_pii_columns: int = 0
    safe_to_process: bool = True

    def to_dict(self) -> dict:
        return {
            "detections": [d.to_dict() for d in self.detections],
            "columns_masked": self.columns_masked,
            "columns_flagged": self.columns_flagged,
            "columns_blocked": self.columns_blocked,
            "total_pii_columns": self.total_pii_columns,
            "safe_to_process": self.safe_to_process,
        }


class PIIProtector:
    """Detects and protects PII before AI processing."""

    # Columns that should block processing entirely
    BLOCK_TYPES = {"credit_card", "ssn", "passport"}

    # Columns that should be masked
    MASK_TYPES = {"email", "phone", "iban", "personal_id", "address", "name", "date_of_birth", "ip_address"}

    def detect_in_columns(self, columns: list[dict]) -> PIIProtectionResult:
        """Detect PII in column definitions."""
        result = PIIProtectionResult()

        for col in columns:
            name = col.get("name", "")
            sample_values = col.get("sample_values", [])

            # Check column name patterns
            pii_type = self._detect_by_column_name(name)

            # If not found by name, check sample values
            if not pii_type and sample_values:
                pii_type = self._detect_by_content(sample_values)

            if pii_type:
                detection = PIIDetection(
                    column_name=name,
                    pii_type=pii_type,
                    confidence=0.85 if pii_type else 0.5,
                    detection_method="column_name" if self._detect_by_column_name(name) else "content",
                    action=self._determine_action(pii_type),
                    row_count_affected=col.get("row_count", 0),
                )
                result.detections.append(detection)

                if detection.action == "mask":
                    result.columns_masked.append(name)
                elif detection.action == "flag":
                    result.columns_flagged.append(name)
                elif detection.action == "block":
                    result.columns_blocked.append(name)
                    result.safe_to_process = False

        result.total_pii_columns = len(result.detections)
        return result

    def mask_value(self, value: str, pii_type: str) -> str:
        """Mask a single PII value."""
        if not value or not isinstance(value, str):
            return value

        if pii_type == "email":
            parts = value.split("@")
            if len(parts) == 2:
                return f"{parts[0][:2]}***@{parts[1]}"
            return "***"

        if pii_type in ("phone", "ssn", "credit_card", "iban"):
            # Keep first 2 and last 2 characters
            if len(value) > 4:
                return f"{value[:2]}{'*' * (len(value) - 4)}{value[-2:]}"
            return "****"

        if pii_type == "name":
            parts = value.split()
            if len(parts) >= 2:
                return f"{parts[0][0]}*** {parts[-1][0]}***"
            return f"{value[0] if value else '*'}***"

        if pii_type == "address":
            return "***REDACTED ADDRESS***"

        if pii_type == "date_of_birth":
            return "**/**/****"

        # Default: hash
        return hashlib.sha256(value.encode()).hexdigest()[:16]

    def mask_dataframe(self, df, columns_to_mask: list[str], pii_types: dict[str, str] | None = None):
        """Mask PII columns in a pandas DataFrame."""
        import pandas as pd
        pii_types = pii_types or {}
        df_masked = df.copy()
        for col_name in columns_to_mask:
            if col_name in df_masked.columns:
                pii_type = pii_types.get(col_name, "default")
                df_masked[col_name] = df_masked[col_name].apply(
                    lambda v: self.mask_value(str(v), pii_type) if pd.notna(v) else v
                )
        return df_masked

    def mask_text(self, text: str) -> str:
        """Mask PII patterns in free text."""
        masked = text
        for pii_type, pattern in PII_PATTERNS.items():
            masked = pattern.sub(f"[REDACTED_{pii_type.upper()}]", masked)
        return masked

    def _detect_by_column_name(self, name: str) -> str | None:
        """Detect PII type from column name."""
        name_lower = name.lower().strip()
        for pii_type, keywords in PII_COLUMN_PATTERNS.items():
            if any(kw in name_lower for kw in keywords):
                return pii_type
        return None

    def _detect_by_content(self, sample_values: list) -> str | None:
        """Detect PII type from sample values."""
        for value in sample_values[:5]:
            if not isinstance(value, str):
                continue
            for pii_type, pattern in PII_PATTERNS.items():
                if pattern.search(value):
                    return pii_type
        return None

    def _determine_action(self, pii_type: str) -> str:
        """Determine protection action for a PII type."""
        if pii_type in self.BLOCK_TYPES:
            return "block"
        if pii_type in self.MASK_TYPES:
            return "mask"
        return "flag"
