"""Tests for the ModelRouter."""
from packages.cognitive_kernel.ai_gateway.router import ModelRouter


class TestModelRouter:
    def setup_method(self):
        self.router = ModelRouter()

    def test_select_model_returns_valid(self):
        model = self.router.select_model(task_type="generation")
        assert ":" in model  # format is "provider:model"

    def test_select_model_embedding(self):
        model = self.router.select_model(task_type="embedding")
        assert "embedding" in model

    def test_select_model_complex_reasoning(self):
        model = self.router.select_model(task_type="complex_reasoning", complexity="high")
        assert model in self.router.model_scores

    def test_select_strategy_cheapest(self):
        model = self.router.select_strategy("cheapest")
        assert model in self.router.model_scores
        # Cheapest should have high cost score
        assert self.router.model_scores[model]["cost"] >= 0.9

    def test_select_strategy_fastest(self):
        model = self.router.select_strategy("fastest")
        assert self.router.model_scores[model]["speed"] >= 0.9

    def test_select_strategy_highest_quality(self):
        model = self.router.select_strategy("highest_quality")
        assert self.router.model_scores[model]["quality"] >= 0.9

    def test_get_fallback(self):
        fallbacks = self.router.get_fallback("openai")
        assert "anthropic" in fallbacks
        assert "google" in fallbacks

    def test_get_fallback_unknown(self):
        fallbacks = self.router.get_fallback("unknown_provider")
        assert "openai" in fallbacks  # default fallback

    def test_get_model_for_task(self):
        model = self.router.get_model_for_task("generation")
        assert model == "openai:gpt-4o"

    def test_all_strategies_return_valid(self):
        for strategy in ["cheapest", "fastest", "highest_quality", "balanced"]:
            model = self.router.select_strategy(strategy)
            assert model in self.router.model_scores
