"""πX Confidence Scorer — Calculate decision confidence."""
from __future__ import annotations


class ConfidenceScorer:
    """Scores decision confidence based on evidence, reasoning, and risks."""

    def score_decision(
        self, evidence: list[dict], reasoning: list[str], risks: list[dict]
    ) -> float:
        """Return confidence score 0.0-1.0."""
        # Evidence count factor (0.2)
        evidence_count = min(len(evidence) / 10, 1.0)

        # Evidence confidence factor (0.2)
        if evidence:
            avg_conf = sum(e.get("confidence", 0.5) for e in evidence) / len(evidence)
        else:
            avg_conf = 0.3

        # Reasoning depth factor (0.15)
        reasoning_depth = min(len(reasoning) / 5, 1.0)

        # Risk level inverse factor (0.25)
        if risks:
            max_risk = max(r.get("risk_score", 0.5) for r in risks)
        else:
            max_risk = 0.5
        risk_inverse = 1.0 - max_risk

        # Source diversity factor (0.2)
        sources = set(e.get("source", "unknown") for e in evidence)
        source_diversity = min(len(sources) / 3, 1.0)

        score = (
            evidence_count * 0.2
            + avg_conf * 0.2
            + reasoning_depth * 0.15
            + risk_inverse * 0.25
            + source_diversity * 0.2
        )
        return round(max(0.0, min(1.0, score)), 4)

    def explain_score(
        self, evidence: list[dict], reasoning: list[str], risks: list[dict]
    ) -> dict:
        """Return breakdown of confidence factors."""
        evidence_count = min(len(evidence) / 10, 1.0)
        if evidence:
            avg_conf = sum(e.get("confidence", 0.5) for e in evidence) / len(evidence)
        else:
            avg_conf = 0.3
        reasoning_depth = min(len(reasoning) / 5, 1.0)
        if risks:
            max_risk = max(r.get("risk_score", 0.5) for r in risks)
        else:
            max_risk = 0.5
        risk_inverse = 1.0 - max_risk
        sources = set(e.get("source", "unknown") for e in evidence)
        source_diversity = min(len(sources) / 3, 1.0)

        return {
            "overall": self.score_decision(evidence, reasoning, risks),
            "evidence_count": round(evidence_count, 4),
            "evidence_confidence": round(avg_conf, 4),
            "reasoning_depth": round(reasoning_depth, 4),
            "risk_level": round(risk_inverse, 4),
            "source_diversity": round(source_diversity, 4),
        }
