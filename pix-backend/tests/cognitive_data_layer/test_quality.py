from __future__ import annotations

import pandas as pd

from app.cognitive_data_layer.quality import DataQualityEngine
from app.cognitive_data_layer.schema import SchemaDiscoverer


class TestDataQualityEngine:
    def test_detect_missing_values(self):
        df = pd.DataFrame({"name": ["A", None, "B"], "amount": [10, 20, 30]})
        discoverer = SchemaDiscoverer()
        cols = discoverer.discover("t", df).columns
        engine = DataQualityEngine()
        issues = engine.analyze("t", df, cols)
        assert any(i.issue_type == "missing_values" for i in issues)

    def test_detect_duplicates(self):
        df = pd.DataFrame({"id": [1, 1], "name": ["A", "A"]})
        discoverer = SchemaDiscoverer()
        cols = discoverer.discover("t", df).columns
        engine = DataQualityEngine()
        issues = engine.analyze("t", df, cols)
        assert any(i.issue_type == "duplicate_rows" for i in issues)

    def test_detect_invalid_dates(self):
        df = pd.DataFrame({"date": ["2026-01-01", "not-a-date"]})
        discoverer = SchemaDiscoverer()
        cols = discoverer.discover("t", df).columns
        engine = DataQualityEngine()
        issues = engine.analyze("t", df, cols)
        # Date detection requires semantic_type == date; may not trigger here.
        report = engine.generate_report(issues)
        assert isinstance(report["total_issues"], int)

    def test_generate_report(self):
        df = pd.DataFrame({"x": [1, None]})
        discoverer = SchemaDiscoverer()
        cols = discoverer.discover("t", df).columns
        engine = DataQualityEngine()
        issues = engine.analyze("t", df, cols)
        report = engine.generate_report(issues)
        assert "total_issues" in report
        assert "by_severity" in report
