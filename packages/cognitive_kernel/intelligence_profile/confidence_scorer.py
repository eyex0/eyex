"""
πX Profile Confidence Scorer — Calculates confidence for inferred intelligence.

Aggregates sub-component confidences into an overall profile confidence score.
Factors: ontology coverage, KPI coverage, glossary coverage, data source confidence,
semantic mapping accuracy, correction rate.
"""
from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger("pix.intelligence_profile.confidence")


class ProfileConfidenceScorer:
    """Scores the overall confidence of an intelligence profile."""

    # Weights for each factor (must sum to 1.0)
    WEIGHTS = {
        "ontology_coverage": 0.20,    # How many entity types are defined
        "kpi_coverage": 0.15,         # How many KPIs are defined
        "glossary_coverage": 0.10,    # How many terms are defined
        "data_source_confidence": 0.20,  # Average confidence of data sources
        "semantic_accuracy": 0.20,    # Accuracy of semantic mappings (1 - correction_rate)
        "user_confirmed": 0.15,        # Percentage of items confirmed by user vs inferred
    }

    def score(
        self,
        ontology_count: int = 0,
        kpi_count: int = 0,
        glossary_count: int = 0,
        data_source_count: int = 0,
        avg_data_source_confidence: float = 0.0,
        total_semantic_mappings: int = 0,
        user_corrections: int = 0,
        user_confirmed_count: int = 0,
        total_items: int = 0,
    ) -> float:
        """Calculate overall profile confidence score (0.0–1.0)."""
        # Ontology coverage: 5+ entities = full coverage
        ontology_score = min(ontology_count / 5, 1.0)
        # KPI coverage: 3+ KPIs = full coverage
        kpi_score = min(kpi_count / 3, 1.0)
        # Glossary coverage: 10+ terms = full coverage
        glossary_score = min(glossary_count / 10, 1.0)
        # Data source confidence: average of source confidences
        ds_score = avg_data_source_confidence if data_source_count > 0 else 0.0
        # Semantic accuracy: 1 - correction_rate (fewer corrections = higher confidence)
        if total_semantic_mappings > 0:
            semantic_accuracy = 1.0 - min(user_corrections / total_semantic_mappings, 1.0)
        else:
            semantic_accuracy = 0.5  # neutral if no mappings yet
        # User confirmed ratio
        if total_items > 0:
            confirmed_ratio = user_confirmed_count / total_items
        else:
            confirmed_ratio = 0.0

        score = (
            ontology_score * self.WEIGHTS["ontology_coverage"]
            + kpi_score * self.WEIGHTS["kpi_coverage"]
            + glossary_score * self.WEIGHTS["glossary_coverage"]
            + ds_score * self.WEIGHTS["data_source_confidence"]
            + semantic_accuracy * self.WEIGHTS["semantic_accuracy"]
            + confirmed_ratio * self.WEIGHTS["user_confirmed"]
        )
        return round(max(0.0, min(1.0, score)), 4)

    def explain(
        self,
        ontology_count: int = 0,
        kpi_count: int = 0,
        glossary_count: int = 0,
        data_source_count: int = 0,
        avg_data_source_confidence: float = 0.0,
        total_semantic_mappings: int = 0,
        user_corrections: int = 0,
        user_confirmed_count: int = 0,
        total_items: int = 0,
    ) -> dict:
        """Return detailed breakdown of confidence factors."""
        overall = self.score(
            ontology_count, kpi_count, glossary_count,
            data_source_count, avg_data_source_confidence,
            total_semantic_mappings, user_corrections,
            user_confirmed_count, total_items,
        )
        return {
            "overall": overall,
            "ontology_coverage": round(min(ontology_count / 5, 1.0), 4),
            "kpi_coverage": round(min(kpi_count / 3, 1.0), 4),
            "glossary_coverage": round(min(glossary_count / 10, 1.0), 4),
            "data_source_confidence": round(avg_data_source_confidence, 4) if data_source_count > 0 else 0.0,
            "semantic_accuracy": round(
                1.0 - min(user_corrections / max(total_semantic_mappings, 1), 1.0), 4
            ) if total_semantic_mappings > 0 else 0.5,
            "user_confirmed_ratio": round(user_confirmed_count / max(total_items, 1), 4) if total_items > 0 else 0.0,
            "weights": self.WEIGHTS,
        }
