"""Tests for the ConfidenceScorer."""
from packages.cognitive_kernel.decision_engine.confidence_scorer import ConfidenceScorer


class TestConfidenceScorer:
    def setup_method(self):
        self.scorer = ConfidenceScorer()

    def test_high_confidence(self):
        evidence = [
            {"source": "memory", "confidence": 0.9},
            {"source": "knowledge_graph", "confidence": 0.85},
            {"source": "document", "confidence": 0.8},
        ]
        reasoning = ["Step 1", "Step 2", "Step 3", "Step 4", "Step 5"]
        risks = [{"risk_score": 0.1}]
        score = self.scorer.score_decision(evidence, reasoning, risks)
        assert 0.7 < score < 1.0

    def test_low_confidence(self):
        evidence = [{"source": "default", "confidence": 0.3}]
        reasoning = ["Single step"]
        risks = [{"risk_score": 0.9}]
        score = self.scorer.score_decision(evidence, reasoning, risks)
        assert 0.0 < score < 0.4

    def test_empty_evidence(self):
        score = self.scorer.score_decision([], [], [])
        assert 0.0 <= score <= 1.0

    def test_explain_score(self):
        evidence = [{"source": "memory", "confidence": 0.8}]
        reasoning = ["Step 1", "Step 2"]
        risks = [{"risk_score": 0.3}]
        explanation = self.scorer.explain_score(evidence, reasoning, risks)
        assert "overall" in explanation
        assert "evidence_count" in explanation
        assert "evidence_confidence" in explanation
        assert "reasoning_depth" in explanation
        assert "risk_level" in explanation
        assert "source_diversity" in explanation

    def test_score_range(self):
        for _ in range(100):
            import random
            n_evidence = random.randint(0, 20)
            evidence = [{"source": f"src_{i%3}", "confidence": random.random()} for i in range(n_evidence)]
            reasoning = ["step"] * random.randint(0, 10)
            risks = [{"risk_score": random.random()} for _ in range(random.randint(0, 5))]
            score = self.scorer.score_decision(evidence, reasoning, risks)
            assert 0.0 <= score <= 1.0
