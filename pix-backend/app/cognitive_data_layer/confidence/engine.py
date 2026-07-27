from __future__ import annotations

from dataclasses import dataclass

from app.cognitive_data_layer.canonical.model import CanonicalColumn, EntityType


@dataclass
class ConfidenceAssessment:
    score: float
    explanation: str
    needs_clarification: bool
    suggested_entity: EntityType | None = None


class ConfidenceEngine:
    """Score mapping confidence and request clarification when uncertain."""

    def __init__(self, clarification_threshold: float = 0.5) -> None:
        self.clarification_threshold = clarification_threshold

    def assess(self, mapping: CanonicalColumn) -> ConfidenceAssessment:
        score = mapping.confidence
        reasons: list[str] = []

        if mapping.null_count > 0:
            score -= 0.05
            reasons.append(f"{mapping.null_count} null values")
        if mapping.unique_count <= 1:
            score -= 0.1
            reasons.append("low uniqueness")
        if mapping.entity_type == EntityType.UNKNOWN:
            score -= 0.2
            reasons.append("unknown entity")

        score = max(0.0, min(1.0, score))
        needs_clarification = score < self.clarification_threshold

        explanation = f"Base confidence {mapping.confidence}"
        if reasons:
            explanation += f"; adjustments: {', '.join(reasons)}"
        explanation += f"; final score {round(score, 2)}"

        return ConfidenceAssessment(
            score=round(score, 2),
            explanation=explanation,
            needs_clarification=needs_clarification,
            suggested_entity=mapping.entity_type,
        )

    def batch_assess(self, columns: list[CanonicalColumn]) -> dict[str, ConfidenceAssessment]:
        return {col.name: self.assess(col) for col in columns}
