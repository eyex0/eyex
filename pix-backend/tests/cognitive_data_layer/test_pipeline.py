from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from app.cognitive_data_layer import CognitiveDataPipeline
from app.cognitive_data_layer.canonical.model import EntityType


class TestCognitiveDataPipeline:
    @pytest.fixture
    def pipeline(self):
        return CognitiveDataPipeline()

    @pytest.mark.asyncio
    async def test_process_csv(self, pipeline: CognitiveDataPipeline, tmp_path: Path):
        path = tmp_path / "sample.csv"
        pd.DataFrame(
            {
                "Customer": ["A", "B", "C"],
                "Revenue": [100.0, 200.0, 300.0],
                "Date": ["2026-01-01", "2026-01-02", "2026-01-03"],
            }
        ).to_csv(path, index=False)
        result = await pipeline.process(path)
        assert result["format"] == "csv"
        assert EntityType.CUSTOMER in result["canonical"].entities
        assert EntityType.REVENUE in result["canonical"].entities
        assert "quality_report" in result

    @pytest.mark.asyncio
    async def test_process_excel(self, pipeline: CognitiveDataPipeline, tmp_path: Path):
        path = tmp_path / "sample.xlsx"
        with pd.ExcelWriter(path, engine="openpyxl") as writer:
            pd.DataFrame({"Client": ["X", "Y"], "Amount": [10, 20]}).to_excel(
                writer, sheet_name="Sales", index=False
            )
        result = await pipeline.process(path)
        assert result["format"] == "excel"
        assert result["canonical"].sheets[0].name == "Sales"

    @pytest.mark.asyncio
    async def test_company_learning(self, pipeline: CognitiveDataPipeline, tmp_path: Path):
        path = tmp_path / "sample.csv"
        pd.DataFrame({"Patron": ["A", "B"], "Spend": [10, 20]}).to_csv(path, index=False)
        await pipeline.process(path, company_id="restaurant_123")
        learned = pipeline.learning_system.get_mapping("restaurant_123", "Patron")
        assert learned is not None

    @pytest.mark.asyncio
    async def test_knowledge_graph(self, pipeline: CognitiveDataPipeline, tmp_path: Path):
        path = tmp_path / "sample.csv"
        pd.DataFrame({"Customer": ["A"], "Revenue": [100]}).to_csv(path, index=False)
        result = await pipeline.process(path)
        assert "knowledge_graph" in result
        assert len(result["knowledge_graph"]["nodes"]) > 0

    @pytest.mark.asyncio
    async def test_confidence_report(self, pipeline: CognitiveDataPipeline, tmp_path: Path):
        path = tmp_path / "sample.csv"
        pd.DataFrame({"Customer": ["A"], "Revenue": [100]}).to_csv(path, index=False)
        result = await pipeline.process(path)
        assert "confidence_report" in result
        assert "assessments" in result["confidence_report"]

    @pytest.mark.asyncio
    async def test_agent_insights(self, pipeline: CognitiveDataPipeline, tmp_path: Path):
        path = tmp_path / "sample.csv"
        pd.DataFrame({"Customer": ["A"], "Revenue": [100]}).to_csv(path, index=False)
        result = await pipeline.process(path)
        assert "agent_insights" in result
        assert "discovery" in result["agent_insights"]
        assert "business_context" in result["agent_insights"]
