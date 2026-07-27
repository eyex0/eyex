"""Tests for ProfileConfidenceScorer."""
from packages.cognitive_kernel.intelligence_profile.confidence_scorer import ProfileConfidenceScorer


class TestProfileConfidenceScorer:
    def setup_method(self):
        self.scorer = ProfileConfidenceScorer()

    def test_empty_profile_low_confidence(self):
        score = self.scorer.score()
        assert 0.0 <= score < 0.3

    def test_full_profile_high_confidence(self):
        score = self.scorer.score(
            ontology_count=10, kpi_count=5, glossary_count=20,
            data_source_count=5, avg_data_source_confidence=0.9,
            total_semantic_mappings=100, user_corrections=2,
            user_confirmed_count=15, total_items=20,
        )
        assert score > 0.7

    def test_explain_returns_all_factors(self):
        explanation = self.scorer.explain(ontology_count=3, kpi_count=2)
        assert "overall" in explanation
        assert "ontology_coverage" in explanation
        assert "kpi_coverage" in explanation
        assert "glossary_coverage" in explanation
        assert "data_source_confidence" in explanation
        assert "semantic_accuracy" in explanation
        assert "user_confirmed_ratio" in explanation
        assert "weights" in explanation

    def test_score_always_in_range(self):
        import random
        for _ in range(50):
            score = self.scorer.score(
                ontology_count=random.randint(0, 50),
                kpi_count=random.randint(0, 30),
                glossary_count=random.randint(0, 100),
                data_source_count=random.randint(0, 10),
                avg_data_source_confidence=random.random(),
                total_semantic_mappings=random.randint(0, 500),
                user_corrections=random.randint(0, 100),
                user_confirmed_count=random.randint(0, 50),
                total_items=random.randint(0, 100),
            )
            assert 0.0 <= score <= 1.0
