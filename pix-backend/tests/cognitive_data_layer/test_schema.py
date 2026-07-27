from __future__ import annotations

import pandas as pd

from app.cognitive_data_layer.schema import SchemaDiscoverer


class TestSchemaDiscoverer:
    def test_detect_primary_key(self):
        df = pd.DataFrame({"id": [1, 2, 3], "name": ["a", "b", "c"]})
        discoverer = SchemaDiscoverer()
        result = discoverer.discover("users", df)
        assert "id" in result.primary_keys

    def test_detect_time_series(self):
        df = pd.DataFrame(
            {
                "date": pd.to_datetime(["2026-01-01", "2026-01-02"]),
                "revenue": [100.0, 200.0],
            }
        )
        discoverer = SchemaDiscoverer()
        result = discoverer.discover("sales", df)
        assert result.is_time_series is True

    def test_detect_categories(self):
        df = pd.DataFrame({"status": ["active", "active", "inactive"], "value": [1, 2, 3]})
        discoverer = SchemaDiscoverer()
        result = discoverer.discover("items", df)
        assert "status" in result.categories

    def test_foreign_key_detection(self):
        orders = pd.DataFrame({"order_id": [1, 2], "customer_id": [10, 11]})
        customers = pd.DataFrame({"customer_id": [10, 11], "name": ["A", "B"]})
        discoverer = SchemaDiscoverer()
        result = discoverer.discover("orders", orders, all_tables={"customers": customers})
        assert len(result.foreign_keys) > 0
        assert result.foreign_keys[0].target_table == "customers"
