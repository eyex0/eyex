"""πX Universal Data Intelligence — Integration tests across 4 industries."""
import pytest
import pandas as pd
import numpy as np

from packages.cognitive_kernel.data_intelligence.universal_profiler import UniversalDataProfiler
from packages.cognitive_kernel.data_intelligence.semantic_mapping_v2 import SemanticMappingEngineV2
from packages.cognitive_kernel.data_intelligence.relationship_discovery import RelationshipDiscoveryEngine
from packages.cognitive_kernel.data_intelligence.data_quality import DataQualityIntelligence
from packages.cognitive_kernel.data_intelligence.pii_protection import PIIProtector
from packages.cognitive_kernel.intelligence_profile.industry_templates import IndustryTemplateRegistry


class TestRetailScenario:
    """Retail: Cust_Name, NET_REV, Store_ID → different intelligence model."""

    def setup_method(self):
        self.df = pd.DataFrame({
            "Cust_Name": ["Acme Corp", "Beta LLC", "Gamma Inc", "Delta SA", "Epsilon Ltd"],
            "NET_REV": [12500.00, 8900.50, 45600.00, 23000.00, 15000.00],
            "Store_ID": ["ST01", "ST02", "ST01", "ST03", "ST02"],
            "Date": ["2024-01-15", "2024-01-16", "2024-01-17", "2024-01-18", "2024-01-19"],
            "Quantity": [5, 12, 3, 8, 15],
        })
        self.profiler = UniversalDataProfiler()

    def test_profiles_all_columns(self):
        profile = self.profiler.profile_dataframe(self.df, "retail_data.xlsx")
        assert profile.row_count == 5
        assert profile.column_count == 5
        assert len(profile.columns) == 5

    def test_detects_currency_column(self):
        profile = self.profiler.profile_dataframe(self.df, "retail.xlsx")
        net_rev = next(c for c in profile.columns if c.name == "NET_REV")
        assert net_rev.semantic_type == "currency"
        assert net_rev.is_metric == True

    def test_detects_identifier_column(self):
        profile = self.profiler.profile_dataframe(self.df, "retail.xlsx")
        store_id = next(c for c in profile.columns if c.name == "Store_ID")
        assert store_id.semantic_type == "identifier"

    def test_detects_date_column(self):
        profile = self.profiler.profile_dataframe(self.df, "retail.xlsx")
        date_col = next(c for c in profile.columns if c.name == "Date")
        assert date_col.semantic_type == "date"

    def test_quality_score_generated(self):
        profile = self.profiler.profile_dataframe(self.df, "retail.xlsx")
        assert 0.0 <= profile.quality_score <= 1.0
        assert profile.quality_score > 0.5  # Clean data should score high

    def test_has_time_dimension(self):
        profile = self.profiler.profile_dataframe(self.df, "retail.xlsx")
        assert profile.has_time_dimension == True

    def test_has_geographic_dimension(self):
        profile = self.profiler.profile_dataframe(self.df, "retail.xlsx")
        # "Store" columns indicate geographic dimension
        assert profile.has_geographic_dimension == True

    def test_semantic_mapping_maps_net_rev(self):
        mapping_engine = SemanticMappingEngineV2()
        result = mapping_engine.map_column("NET_REV", [12500, 8900])
        assert result["entity"] == "revenue"
        assert result["confidence"] > 0.5

    def test_semantic_mapping_maps_cust_name(self):
        mapping_engine = SemanticMappingEngineV2()
        result = mapping_engine.map_column("Cust_Name", ["Acme Corp"])
        assert result["entity"] == "customer"
        assert result["confidence"] > 0.5

    def test_relationship_discovery_finds_store_to_revenue(self):
        engine = RelationshipDiscoveryEngine()
        mappings = [
            {"source_column": "NET_REV", "semantic_type": "currency", "is_metric": True, "entity": "revenue"},
            {"source_column": "Store_ID", "semantic_type": "identifier", "entity": "store"},
            {"source_column": "Cust_Name", "semantic_type": "text", "entity": "customer"},
        ]
        rels = engine.discover(self.df, mappings)
        # Should find that NET_REV can be grouped by Store_ID
        store_rels = [r for r in rels if "Store_ID" in r.get("target_column", "") and "NET_REV" in r.get("source_column", "")]
        assert len(store_rels) > 0

    def test_quality_analysis(self):
        quality = DataQualityIntelligence()
        report = quality.analyze(self.df, "retail.xlsx")
        assert report.row_count == 5
        assert report.overall_score > 0.8
        assert len(report.columns) == 5


class TestManufacturingScenario:
    """Manufacturing: Machine_ID, Defect_Count, Cycle_Time → different intelligence model."""

    def setup_method(self):
        self.df = pd.DataFrame({
            "Machine_ID": ["M-001", "M-002", "M-003", "M-004", "M-005"],
            "Defect_Count": [0, 2, 5, 1, 3],
            "Cycle_Time": [45.2, 52.1, 38.7, 49.5, 41.0],
            "Operator": ["John", "Mary", "Bob", "Alice", "Charlie"],
            "Shift": ["A", "B", "A", "B", "A"],
        })
        self.profiler = UniversalDataProfiler()

    def test_profiles_all_columns(self):
        profile = self.profiler.profile_dataframe(self.df, "mfg_data.xlsx")
        assert profile.row_count == 5
        assert profile.column_count == 5

    def test_detects_machine_as_identifier(self):
        profile = self.profiler.profile_dataframe(self.df, "mfg.xlsx")
        machine = next(c for c in profile.columns if c.name == "Machine_ID")
        assert machine.semantic_type == "identifier"

    def test_defect_count_is_numeric_metric(self):
        profile = self.profiler.profile_dataframe(self.df, "mfg.xlsx")
        defects = next(c for c in profile.columns if c.name == "Defect_Count")
        assert defects.semantic_type in ("numeric", "category")
        assert defects.is_metric == True

    def test_cycle_time_is_numeric(self):
        profile = self.profiler.profile_dataframe(self.df, "mfg.xlsx")
        cycle = next(c for c in profile.columns if c.name == "Cycle_Time")
        assert cycle.semantic_type == "numeric"
        assert cycle.is_metric == True

    def test_shift_is_category(self):
        profile = self.profiler.profile_dataframe(self.df, "mfg.xlsx")
        shift = next(c for c in profile.columns if c.name == "Shift")
        assert shift.semantic_type == "category"

    def test_semantic_mapping_maps_machine_id(self):
        engine = SemanticMappingEngineV2()
        result = engine.map_column("Machine_ID", ["M-001"])
        assert result["entity"] == "machine"
        assert result["confidence"] > 0.4

    def test_semantic_mapping_maps_cycle_time(self):
        engine = SemanticMappingEngineV2()
        result = engine.map_column("Cycle_Time", [45.2, 52.1])
        assert result["entity"] == "cycle_time"
        assert result["confidence"] > 0.4

    def test_no_time_dimension(self):
        profile = self.profiler.profile_dataframe(self.df, "mfg.xlsx")
        assert profile.has_time_dimension == False

    def test_different_from_retail(self):
        """Manufacturing data should produce different entity detection than retail."""
        retail_df = pd.DataFrame({
            "Cust_Name": ["A", "B"], "NET_REV": [100, 200], "Store_ID": ["S1", "S2"],
        })
        retail_profile = self.profiler.profile_dataframe(retail_df, "retail.xlsx")
        mfg_profile = self.profiler.profile_dataframe(self.df, "mfg.xlsx")
        retail_entities = {e["entity_type"] for e in retail_profile.detected_entities}
        mfg_entities = {e["entity_type"] for e in mfg_profile.detected_entities}
        assert retail_entities != mfg_entities


class TestFinanceScenario:
    """Finance: Account_No, Transaction_Value, Risk_Score → different intelligence model."""

    def setup_method(self):
        self.df = pd.DataFrame({
            "Account_No": ["ACC001", "ACC002", "ACC003", "ACC004"],
            "Transaction_Value": [150000, 25000, 500000, 10000],
            "Risk_Score": [0.2, 0.8, 0.1, 0.9],
            "Client_Name": ["Goldman", "Morgan", "Vanguard", "Blackrock"],
        })
        self.profiler = UniversalDataProfiler()

    def test_account_no_is_identifier(self):
        profile = self.profiler.profile_dataframe(self.df, "finance.xlsx")
        acc = next(c for c in profile.columns if c.name == "Account_No")
        assert acc.semantic_type == "identifier"
        assert acc.is_pii == True  # Account numbers are PII

    def test_transaction_value_is_currency(self):
        profile = self.profiler.profile_dataframe(self.df, "finance.xlsx")
        tv = next(c for c in profile.columns if c.name == "Transaction_Value")
        assert tv.semantic_type == "currency"

    def test_risk_score_is_numeric(self):
        profile = self.profiler.profile_dataframe(self.df, "finance.xlsx")
        rs = next(c for c in profile.columns if c.name == "Risk_Score")
        assert rs.semantic_type in ("numeric", "currency")

    def test_semantic_mapping_maps_account_no(self):
        engine = SemanticMappingEngineV2()
        result = engine.map_column("Account_No", ["ACC001"])
        assert result["entity"] == "account"
        assert result["confidence"] > 0.4

    def test_semantic_mapping_maps_risk_score(self):
        engine = SemanticMappingEngineV2()
        result = engine.map_column("Risk_Score", [0.2, 0.8])
        assert result["entity"] == "risk_score"

    def test_pii_detection_on_account_no(self):
        protector = PIIProtector()
        result = protector.detect_in_columns([
            {"name": "Account_No", "sample_values": ["ACC001", "ACC002"]},
            {"name": "Client_Name", "sample_values": ["Goldman", "Morgan"]},
        ])
        assert result.total_pii_columns >= 1
        assert "Account_No" in result.columns_masked or "Account_No" in result.columns_flagged

    def test_pii_detection_on_client_name(self):
        protector = PIIProtector()
        result = protector.detect_in_columns([
            {"name": "Client_Name", "sample_values": ["Goldman Sachs", "Morgan Stanley"]},
        ])
        assert result.total_pii_columns >= 1

    def test_pii_masking(self):
        protector = PIIProtector()
        masked = protector.mask_value("john.doe@example.com", "email")
        assert "john.doe@example.com" != masked
        assert "@" in masked

    def test_pii_text_masking(self):
        protector = PIIProtector()
        masked = protector.mask_text("Contact us at info@company.com or call 555-123-4567")
        assert "info@company.com" not in masked
        assert "555-123-4567" not in masked


class TestHealthcareScenario:
    """Healthcare: Patient_ID, Treatment_Code → different intelligence model."""

    def setup_method(self):
        self.df = pd.DataFrame({
            "Patient_ID": ["P-001", "P-002", "P-003", "P-004"],
            "Treatment_Code": ["T1A", "T2B", "T3C", "T4D"],
            "Outcome": ["Recovered", "Recovering", "Recovered", "Critical"],
            "Cost": [12500, 45000, 8900, 78000],
        })
        self.profiler = UniversalDataProfiler()

    def test_patient_id_is_identifier_and_pii(self):
        profile = self.profiler.profile_dataframe(self.df, "health.xlsx")
        pid = next(c for c in profile.columns if c.name == "Patient_ID")
        assert pid.semantic_type == "identifier"
        # Patient_ID contains "id" which should be flagged for PII review
        assert pid.is_pii == True

    def test_cost_is_currency(self):
        profile = self.profiler.profile_dataframe(self.df, "health.xlsx")
        cost = next(c for c in profile.columns if c.name == "Cost")
        assert cost.semantic_type == "currency"

    def test_semantic_mapping_maps_patient_id(self):
        engine = SemanticMappingEngineV2()
        result = engine.map_column("Patient_ID", ["P-001"])
        assert result["entity"] == "patient"

    def test_semantic_mapping_maps_treatment_code(self):
        engine = SemanticMappingEngineV2()
        result = engine.map_column("Treatment_Code", ["T1A", "T2B"])
        assert result["entity"] == "treatment"

    def test_pii_detection_patient_data(self):
        protector = PIIProtector()
        result = protector.detect_in_columns([
            {"name": "Patient_ID", "sample_values": ["P-001"]},
            {"name": "Patient_Name", "sample_values": ["John Doe"]},
        ])
        assert result.total_pii_columns >= 1

    def test_all_four_industries_produce_different_entities(self):
        """All 4 industries should produce different entity detection."""
        retail_df = pd.DataFrame({"Cust_Name": ["A"], "NET_REV": [100], "Store_ID": ["S1"]})
        mfg_df = pd.DataFrame({"Machine_ID": ["M1"], "Defect_Count": [0], "Cycle_Time": [45.0]})
        fin_df = pd.DataFrame({"Account_No": ["A1"], "Transaction_Value": [1000], "Risk_Score": [0.5]})
        health_df = pd.DataFrame({"Patient_ID": ["P1"], "Treatment_Code": ["T1"], "Cost": [100]})

        profiler = UniversalDataProfiler()
        retail = set(e["entity_type"] for e in profiler.profile_dataframe(retail_df).detected_entities)
        mfg = set(e["entity_type"] for e in profiler.profile_dataframe(mfg_df).detected_entities)
        fin = set(e["entity_type"] for e in profiler.profile_dataframe(fin_df).detected_entities)
        health = set(e["entity_type"] for e in profiler.profile_dataframe(health_df).detected_entities)

        # All should be different
        assert retail != mfg
        assert retail != fin
        assert retail != health
        assert mfg != fin
        assert mfg != health
        assert fin != health


class TestDataQualityIntelligence:
    """Tests for data quality analysis."""

    def test_clean_data_high_score(self):
        df = pd.DataFrame({"A": [1, 2, 3, 4, 5], "B": ["x", "y", "z", "w", "v"]})
        quality = DataQualityIntelligence()
        report = quality.analyze(df, "clean.xlsx")
        assert report.overall_score > 0.8

    def test_missing_values_detected(self):
        df = pd.DataFrame({"A": [1, None, 3, 4, None], "B": ["x", "y", None, "w", "v"]})
        quality = DataQualityIntelligence()
        report = quality.analyze(df, "missing.xlsx")
        assert report.missing_cells > 0
        col_a = next(c for c in report.columns if c.name == "A")
        assert col_a.completeness < 1.0

    def test_duplicates_detected(self):
        df = pd.DataFrame({"A": [1, 1, 2, 3, 4], "B": ["x", "x", "y", "z", "w"]})
        quality = DataQualityIntelligence()
        report = quality.analyze(df, "dups.xlsx")
        assert report.duplicate_rows > 0

    def test_recommendations_generated(self):
        df = pd.DataFrame({"A": [1, None, 3], "B": ["x", "x", "y"]})
        quality = DataQualityIntelligence()
        report = quality.analyze(df, "low_quality.xlsx")
        assert len(report.recommendations) > 0


class TestRelationshipDiscovery:
    """Tests for relationship discovery."""

    def test_metric_dimension_relationship(self):
        df = pd.DataFrame({
            "Revenue": [100, 200, 150, 300],
            "Store": ["A", "B", "A", "C"],
            "Product": ["P1", "P2", "P1", "P3"],
        })
        engine = RelationshipDiscoveryEngine()
        mappings = [
            {"source_column": "Revenue", "semantic_type": "currency", "is_metric": True},
            {"source_column": "Store", "semantic_type": "identifier"},
            {"source_column": "Product", "semantic_type": "identifier"},
        ]
        rels = engine.discover(df, mappings)
        store_rels = [r for r in rels if r.get("relation_type") == "metric_of" and r.get("target_column") == "Store"]
        assert len(store_rels) > 0

    def test_foreign_key_pattern(self):
        df = pd.DataFrame({
            "Store_ID": ["ST01", "ST02", "ST03"],
            "Store": ["Store A", "Store B", "Store C"],
            "Revenue": [100, 200, 300],
        })
        engine = RelationshipDiscoveryEngine()
        rels = engine.discover(df)
        fk_rels = [r for r in rels if r.get("relation_type") == "foreign_key"]
        assert len(fk_rels) > 0

    def test_correlation_detection(self):
        np.random.seed(42)
        df = pd.DataFrame({
            "Revenue": np.random.uniform(1000, 5000, 100),
            "Cost": np.random.uniform(500, 2500, 100),
        })
        df["Cost"] = df["Revenue"] * 0.5 + np.random.normal(0, 50, 100)  # Strong positive correlation
        engine = RelationshipDiscoveryEngine()
        rels = engine.discover(df)
        corr_rels = [r for r in rels if r.get("relation_type") == "correlates_with"]
        assert len(corr_rels) > 0
        assert corr_rels[0]["confidence"] > 0.7


class TestPIIProtection:
    """Tests for PII detection and masking."""

    def test_detect_email_column(self):
        protector = PIIProtector()
        result = protector.detect_in_columns([
            {"name": "Customer_Email", "sample_values": ["john@example.com", "jane@example.com"]},
            {"name": "Revenue", "sample_values": [100, 200]},
        ])
        assert result.total_pii_columns == 1
        assert "Customer_Email" in result.columns_masked

    def test_detect_phone_column(self):
        protector = PIIProtector()
        result = protector.detect_in_columns([
            {"name": "Phone_Number", "sample_values": ["555-123-4567"]},
        ])
        assert result.total_pii_columns >= 1

    def test_credit_card_blocked(self):
        protector = PIIProtector()
        result = protector.detect_in_columns([
            {"name": "Credit_Card_No", "sample_values": ["4532-1234-5678-9012"]},
        ])
        assert result.total_pii_columns >= 1
        assert "Credit_Card_No" in result.columns_masked or "Credit_Card_No" in result.columns_blocked

    def test_mask_email(self):
        protector = PIIProtector()
        masked = protector.mask_value("john.doe@example.com", "email")
        assert "john.doe@example.com" != masked
        assert "***" in masked
        assert "@" in masked

    def test_mask_phone(self):
        protector = PIIProtector()
        masked = protector.mask_value("555-123-4567", "phone")
        assert "555-123-4567" not in masked
        assert "***" in masked

    def test_mask_text(self):
        protector = PIIProtector()
        text = "Email: test@company.com, Phone: 555-123-4567"
        masked = protector.mask_text(text)
        assert "test@company.com" not in masked
        assert "555-123-4567" not in masked

    def test_safe_columns_not_flagged(self):
        protector = PIIProtector()
        result = protector.detect_in_columns([
            {"name": "Revenue", "sample_values": [100, 200]},
            {"name": "Store_ID", "sample_values": ["ST01", "ST02"]},
        ])
        assert result.total_pii_columns == 0
        assert result.safe_to_process == True

    def test_mask_dataframe(self):
        df = pd.DataFrame({
            "Email": ["john@example.com", "jane@test.org"],
            "Revenue": [100, 200],
        })
        protector = PIIProtector()
        masked_df = protector.mask_dataframe(df, ["Email"], {"Email": "email"})
        assert masked_df["Email"].iloc[0] != "john@example.com"
        assert masked_df["Revenue"].iloc[0] == 100  # Revenue not masked


class TestSemanticMappingV2:
    """Tests for the V2 semantic mapping engine."""

    def test_glossary_exact_match(self):
        engine = SemanticMappingEngineV2()
        result = engine.map_column(
            "NET_REV", [12500], profile_context={
                "glossary": [{"term": "Net Revenue", "aliases": ["net_rev", "net rev"], "maps_to_entity": "revenue"}],
            },
        )
        assert result["meaning"] == "Net Revenue"
        assert result["entity"] == "revenue"
        assert result["confidence"] >= 0.90
        assert result["method"] == "glossary"

    def test_ontology_alias_match(self):
        engine = SemanticMappingEngineV2()
        result = engine.map_column(
            "Cust Name", ["Acme Corp"], profile_context={
                "glossary": [],
                "ontology": [{"entity_type": "customer", "aliases": ["cust", "cust name", "customer name"]}],
            },
        )
        assert result["entity"] == "customer"
        assert result["method"] == "ontology"

    def test_template_match_retail(self):
        engine = SemanticMappingEngineV2(industry_templates=IndustryTemplateRegistry())
        result = engine.map_column(
            "Sell-out", [0.85], profile_context={
                "glossary": [], "ontology": [],
                "company_identity": {"industry": "retail"},
            },
        )
        assert result["confidence"] > 0.5
        assert result["method"] == "template"

    def test_heuristic_fallback(self):
        engine = SemanticMappingEngineV2()
        result = engine.map_column("revenue", [100, 200])
        assert result["entity"] == "revenue"
        assert result["method"] == "heuristic"

    def test_unknown_column_low_confidence(self):
        engine = SemanticMappingEngineV2()
        result = engine.map_column("xyz_unknown_column", [1, 2, 3])
        assert result["confidence"] < 0.3
        assert result["entity"] is None

    def test_batch_mapping(self):
        engine = SemanticMappingEngineV2()
        results = engine.map_columns_batch([
            {"name": "Revenue", "sample_values": [100]},
            {"name": "Customer_ID", "sample_values": ["C1"]},
            {"name": "Date", "sample_values": ["2024-01-01"]},
        ])
        assert len(results) == 3
        assert results[0]["entity"] == "revenue"
        assert results[1]["entity"] == "customer"
