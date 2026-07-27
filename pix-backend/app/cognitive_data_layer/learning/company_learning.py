from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.cognitive_data_layer.canonical.model import EntityType


class CompanyLearningSystem:
    """Remember company-specific mappings, terminology, and corrections."""

    def __init__(self, storage_path: Path | str | None = None) -> None:
        self.storage_path = Path(storage_path) if storage_path else None
        self._mappings: dict[str, dict[str, Any]] = {}
        self._terminology: dict[str, list[str]] = {}
        self._corrections: list[dict[str, Any]] = []
        if self.storage_path and self.storage_path.exists():
            self._load()

    def learn_mapping(
        self, company_id: str, column: str, entity_type: EntityType, confidence: float
    ) -> None:
        self._mappings.setdefault(company_id, {})[column.lower()] = {
            "entity_type": entity_type.value,
            "confidence": confidence,
            "occurrences": self._mappings.get(company_id, {})
            .get(column.lower(), {})
            .get("occurrences", 0)
            + 1,
        }
        self._save()

    def get_mapping(self, company_id: str, column: str) -> dict[str, Any] | None:
        return self._mappings.get(company_id, {}).get(column.lower())

    def learn_terminology(self, company_id: str, term: str, canonical: EntityType) -> None:
        self._terminology.setdefault(company_id, []).append(
            {"term": term, "canonical": canonical.value}
        )
        self._save()

    def record_correction(
        self, company_id: str, column: str, from_entity: EntityType, to_entity: EntityType
    ) -> None:
        self._corrections.append(
            {
                "company_id": company_id,
                "column": column,
                "from_entity": from_entity.value,
                "to_entity": to_entity.value,
            }
        )
        self.learn_mapping(company_id, column, to_entity, 1.0)

    def _load(self) -> None:
        if not self.storage_path:
            return
        try:
            with open(self.storage_path, encoding="utf-8") as f:
                data = json.load(f)
            self._mappings = data.get("mappings", {})
            self._terminology = data.get("terminology", {})
            self._corrections = data.get("corrections", [])
        except Exception:  # noqa: BLE001
            self._mappings = {}
            self._terminology = {}
            self._corrections = []

    def _save(self) -> None:
        if not self.storage_path:
            return
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.storage_path, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "mappings": self._mappings,
                    "terminology": self._terminology,
                    "corrections": self._corrections,
                },
                f,
                indent=2,
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "mappings": self._mappings,
            "terminology": self._terminology,
            "corrections": self._corrections,
        }
