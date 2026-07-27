from __future__ import annotations

from io import BytesIO
from pathlib import Path

import pandas as pd
import pytest

from app.cognitive_data_layer.parser import (
    get_parser_registry,
    parse_source,
    register_default_parsers,
)
from app.cognitive_data_layer.parser.plugins import CSVParser, ExcelParser


@pytest.fixture(autouse=True)
def _reset_registry():
    registry = get_parser_registry()
    registry._parsers.clear()
    register_default_parsers()


class TestCSVParser:
    @pytest.mark.asyncio
    async def test_parse_csv(self, tmp_path: Path):
        path = tmp_path / "test.csv"
        path.write_text("Customer,Revenue,Date\nA,100,2026-01-01\nB,200,2026-01-02\n")
        result = await parse_source(path)
        df = result.raw_data["sheets"][0]["data"]
        assert list(df.columns) == ["Customer", "Revenue", "Date"]
        assert len(df) == 2


class TestExcelParser:
    @pytest.mark.asyncio
    async def test_parse_excel(self, tmp_path: Path):
        path = tmp_path / "test.xlsx"
        df = pd.DataFrame({"Client": ["X", "Y"], "Amount": [10, 20]})
        df.to_excel(path, index=False, sheet_name="Sales")
        result = await parse_source(path)
        assert result.format == "excel"
        assert result.raw_data["sheets"][0]["name"] == "Sales"


class TestJSONParser:
    @pytest.mark.asyncio
    async def test_parse_json(self, tmp_path: Path):
        path = tmp_path / "test.json"
        path.write_text('[{"Customer": "A", "Sales": 100}]')
        result = await parse_source(path)
        df = result.raw_data["sheets"][0]["data"]
        assert "Customer" in df.columns


class TestParserRegistry:
    def test_list_parsers(self):
        registry = get_parser_registry()
        names = registry.list_parsers()
        assert "csv" in names
        assert "excel" in names

    def test_csv_can_parse(self):
        parser = CSVParser()
        assert parser.can_parse("data.csv") is True
        assert parser.can_parse("data.xlsx") is False

    def test_excel_can_parse_bytes(self):
        parser = ExcelParser()
        bio = BytesIO()
        pd.DataFrame({"x": [1]}).to_excel(bio, index=False)
        assert parser.can_parse(bio) is True
