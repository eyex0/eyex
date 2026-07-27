"""Tests for the DecisionEngine."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from packages.cognitive_kernel.decision_engine.decision_engine import DecisionEngine
from packages.cognitive_kernel.decision_engine.risk_analyzer import RiskAnalyzer
from packages.cognitive_kernel.decision_engine.confidence_scorer import ConfidenceScorer
from packages.cognitive_kernel.decision_engine.alternatives_generator import AlternativesGenerator


class TestRiskAnalyzer:
    @pytest.mark.asyncio
    async def test_analyze_risks_success(self):
        analyzer = RiskAnalyzer()
        # Mock the gateway
        mock_response = MagicMock()
        mock_response.content = '[{"description": "Market risk", "probability": 0.3, "impact": 0.5, "category": "market", "mitigation": "Hedge"}]'
        analyzer.gateway = MagicMock()
        analyzer.gateway.generate = AsyncMock(return_value=mock_response)

        result = await analyzer.analyze_risks("test context", [{"content": "evidence"}])
        assert "risks" in result
        assert len(result["risks"]) == 1
        assert result["risks"][0]["risk_score"] == 0.15  # 0.3 * 0.5
        assert result["overall_risk_level"] == "LOW"

    @pytest.mark.asyncio
    async def test_analyze_risks_failure(self):
        analyzer = RiskAnalyzer()
        analyzer.gateway = MagicMock()
        analyzer.gateway.generate = AsyncMock(side_effect=Exception("API error"))

        result = await analyzer.analyze_risks("test", [])
        assert result["risks"] == []
        assert result["overall_risk_level"] == "unknown"


class TestAlternativesGenerator:
    @pytest.mark.asyncio
    async def test_generate_success(self):
        gen = AlternativesGenerator()
        mock_response = MagicMock()
        mock_response.content = '[{"title": "Option A", "description": "First option", "pros": [], "cons": [], "estimated_cost": "low", "estimated_impact": "medium", "feasibility": 0.8}]'
        gen.gateway = MagicMock()
        gen.gateway.generate = AsyncMock(return_value=mock_response)

        alternatives = await gen.generate("test question", {})
        assert len(alternatives) == 1
        assert alternatives[0]["title"] == "Option A"
        assert "id" in alternatives[0]

    @pytest.mark.asyncio
    async def test_generate_failure(self):
        gen = AlternativesGenerator()
        gen.gateway = MagicMock()
        gen.gateway.generate = AsyncMock(side_effect=Exception("API error"))

        alternatives = await gen.generate("test", {})
        assert len(alternatives) == 1
        assert alternatives[0]["id"] == "default"


class TestDecisionEngine:
    @pytest.mark.asyncio
    async def test_decide_returns_structure(self):
        engine = DecisionEngine()
        # Mock all dependencies
        engine.gateway = MagicMock()
        mock_response = MagicMock()
        mock_response.content = '["Step 1", "Step 2"]'
        engine.gateway.generate = AsyncMock(return_value=mock_response)

        engine.memory = MagicMock()
        engine.memory.recall_all = AsyncMock(return_value={"key": "value"})

        engine.graph_store = MagicMock()
        engine.graph_store.get_graph_stats = AsyncMock(return_value={"node_count": 10, "edge_count": 5})
        engine.graph_store.search_nodes = AsyncMock(return_value=[])

        result = await engine.decide("Should we expand?", "org_123")
        assert "decision_id" in result
        assert "question" in result
        assert "evidence" in result
        assert "reasoning_chain" in result
        assert "risks" in result
        assert "recommendation" in result
        assert "confidence" in result
        assert "alternatives" in result
        assert 0.0 <= result["confidence"] <= 1.0
