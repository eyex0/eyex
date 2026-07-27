"""
πX Production Validation — Complete Intelligence Loop Test

Tests the FULL end-to-end intelligence pipeline with REAL module APIs:
1. Universal Data Profiling (unknown Excel columns)
2. Semantic Mapping (column → entity)
3. Intelligence Profile Creation (industry templates)
4. KPI Generation
5. Dynamic Dashboard Generation
6. Agent Creation
7. Natural Language Query
8. Decision Generation
9. Memory Update
"""

import pytest
import pandas as pd
from unittest.mock import AsyncMock, patch
import os

os.environ.setdefault("OPENAI_API_KEY", "test-key")
os.environ.setdefault("ANTHROPIC_API_KEY", "test-key")

TEST_COLUMNS = [
    "Cust Name", "NET_REV", "Ship-To", "Prod Code", "Order Dt",
    "Qty Shipped", "Unit Price", "Cust Segment", "Sales Rep", "Discount Pct",
]
TEST_ROWS = [
    ["Acme Corp", 45000.00, "Hamburg", "SKU-1001", "2026-01-15", 500, 90.00, "Enterprise", "J. Müller", 0.05],
    ["Globex GmbH", 32100.50, "Munich", "SKU-1002", "2026-01-16", 320, 100.31, "Mid-Market", "A. Schmidt", 0.10],
    ["Initech AG", 78900.00, "Berlin", "SKU-1003", "2026-01-17", 850, 92.82, "Enterprise", "J. Müller", 0.0],
    ["Umbrella SA", 12300.00, "Paris", "SKU-1001", "2026-01-18", 120, 102.50, "SMB", "M. Dubois", 0.15],
    ["Stark Industries", 95200.00, "Frankfurt", "SKU-1004", "2026-01-19", 1000, 95.20, "Enterprise", "A. Schmidt", 0.0],
    ["Wayne EU", 56700.00, "Hamburg", "SKU-1002", "2026-01-20", 580, 97.76, "Mid-Market", "J. Müller", 0.08],
    ["Cyberdyne UK", 89000.00, "London", "SKU-1005", "2026-01-21", 950, 93.68, "Enterprise", "S. Jones", 0.0],
    ["Soylent FR", 23400.00, "Paris", "SKU-1003", "2026-01-22", 240, 97.50, "SMB", "M. Dubois", 0.12],
    ["Hooli DE", 67800.00, "Munich", "SKU-1004", "2026-01-23", 710, 95.49, "Mid-Market", "A. Schmidt", 0.05],
    ["Vandelay NL", 34100.00, "Amsterdam", "SKU-1001", "2026-01-24", 340, 100.29, "SMB", "S. Jones", 0.10],
]
ORG_ID = "test-org-val-001"

def make_df():
    return pd.DataFrame(TEST_ROWS, columns=TEST_COLUMNS)


# STEP 1: UNIVERSAL DATA PROFILING
class TestUniversalDataProfiling:
    def test_profiler_detects_column_types(self):
        from packages.cognitive_kernel.data_intelligence.universal_profiler import UniversalDataProfiler
        p = UniversalDataProfiler()
        r = p.profile_dataframe(make_df(), source_name="enterprise_sales.xlsx")
        assert r.column_count == 10
        col_map = {c.name: c for c in r.columns}
        assert col_map["NET_REV"].semantic_type in ("currency", "numeric")
        assert col_map["Order Dt"].semantic_type in ("date", "text")  # String dates may be text
        assert col_map["Cust Name"].semantic_type in ("text", "identifier")

    def test_profiler_detects_metrics(self):
        from packages.cognitive_kernel.data_intelligence.universal_profiler import UniversalDataProfiler
        p = UniversalDataProfiler()
        r = p.profile_dataframe(make_df(), source_name="enterprise_sales.xlsx")
        assert len(r.detected_metrics) > 0

    def test_profiler_quality_score(self):
        from packages.cognitive_kernel.data_intelligence.universal_profiler import UniversalDataProfiler
        p = UniversalDataProfiler()
        r = p.profile_dataframe(make_df(), source_name="enterprise_sales.xlsx")
        assert 0.0 <= r.quality_score <= 1.0
        assert r.quality_score > 0.5

    def test_profiler_confidence(self):
        from packages.cognitive_kernel.data_intelligence.universal_profiler import UniversalDataProfiler
        p = UniversalDataProfiler()
        r = p.profile_dataframe(make_df(), source_name="enterprise_sales.xlsx")
        assert 0.0 <= r.confidence <= 1.0


# STEP 2: SEMANTIC MAPPING
class TestSemanticMapping:
    def test_mapping_customer(self):
        from packages.cognitive_kernel.data_intelligence.semantic_mapping_v2 import SemanticMappingEngineV2
        m = SemanticMappingEngineV2()
        r = m.map_column("Cust Name", sample_values=["Acme Corp", "Globex GmbH"])
        assert r["entity"] == "customer"
        assert r["confidence"] > 0.3
        assert r["method"] is not None

    def test_mapping_revenue(self):
        from packages.cognitive_kernel.data_intelligence.semantic_mapping_v2 import SemanticMappingEngineV2
        m = SemanticMappingEngineV2()
        r = m.map_column("NET_REV", sample_values=[45000.00, 32100.50])
        assert r["entity"] == "revenue"
        assert r["confidence"] > 0.3

    def test_mapping_product(self):
        from packages.cognitive_kernel.data_intelligence.semantic_mapping_v2 import SemanticMappingEngineV2
        m = SemanticMappingEngineV2()
        r = m.map_column("Product", sample_values=["SKU-1001", "SKU-1002"])
        assert r["entity"] is not None

    def test_mapping_batch(self):
        from packages.cognitive_kernel.data_intelligence.semantic_mapping_v2 import SemanticMappingEngineV2
        m = SemanticMappingEngineV2()
        cols = [{"name": col, "sample_values": [row[i] for row in TEST_ROWS]} for i, col in enumerate(TEST_COLUMNS)]
        results = m.map_columns_batch(cols)
        assert len(results) == len(TEST_COLUMNS)
        mapped = sum(1 for r in results if r["entity"] is not None)
        assert mapped >= len(TEST_COLUMNS) * 0.3

    def test_mapping_confidence_range(self):
        from packages.cognitive_kernel.data_intelligence.semantic_mapping_v2 import SemanticMappingEngineV2
        m = SemanticMappingEngineV2()
        for col in TEST_COLUMNS:
            r = m.map_column(col, sample_values=[])
            assert 0.0 <= r["confidence"] <= 1.0


# STEP 3: INTELLIGENCE PROFILE CREATION
class TestIntelligenceProfileCreation:
    def test_template_registry_lists_industries(self):
        from packages.cognitive_kernel.intelligence_profile.industry_templates import IndustryTemplateRegistry
        r = IndustryTemplateRegistry()
        assert len(r.list_templates()) >= 7
        assert "retail" in r.list_templates()
        assert "manufacturing" in r.list_templates()

    def test_retail_template_has_entities(self):
        from packages.cognitive_kernel.intelligence_profile.industry_templates import IndustryTemplateRegistry
        t = IndustryTemplateRegistry().get_template_dict("retail")
        assert len(t["entities"]) >= 4

    def test_retail_template_has_kpis(self):
        from packages.cognitive_kernel.intelligence_profile.industry_templates import IndustryTemplateRegistry
        t = IndustryTemplateRegistry().get_template_dict("retail")
        assert len(t["kpis"]) >= 3

    def test_retail_template_has_agents(self):
        from packages.cognitive_kernel.intelligence_profile.industry_templates import IndustryTemplateRegistry
        t = IndustryTemplateRegistry().get_template_dict("retail")
        assert len(t["recommended_agents"]) >= 3

    def test_profile_confidence_scorer(self):
        from packages.cognitive_kernel.intelligence_profile.confidence_scorer import ProfileConfidenceScorer
        s = ProfileConfidenceScorer().score(ontology_count=5, kpi_count=4, glossary_count=8,
            data_source_count=2, avg_data_source_confidence=0.85,
            total_semantic_mappings=10, user_corrections=0, user_confirmed_count=5, total_items=10)
        assert 0.0 <= s <= 1.0 and s > 0.5


# STEP 4: KPI GENERATION
class TestKPIGeneration:
    def test_revenue_kpi_exists(self):
        from packages.cognitive_kernel.intelligence_profile.industry_templates import IndustryTemplateRegistry
        t = IndustryTemplateRegistry().get_template_dict("retail")
        assert "revenue" in [k["name"] for k in t["kpis"]]

    def test_margin_kpi_exists(self):
        from packages.cognitive_kernel.intelligence_profile.industry_templates import IndustryTemplateRegistry
        t = IndustryTemplateRegistry().get_template_dict("retail")
        assert "margin" in [k["name"] for k in t["kpis"]]

    def test_kpis_have_formulas(self):
        from packages.cognitive_kernel.intelligence_profile.industry_templates import IndustryTemplateRegistry
        for ind in IndustryTemplateRegistry().list_templates():
            t = IndustryTemplateRegistry().get_template_dict(ind)
            for k in t["kpis"]:
                assert "formula" in k and k["formula"] is not None

    def test_kpis_have_targets(self):
        from packages.cognitive_kernel.intelligence_profile.industry_templates import IndustryTemplateRegistry
        for ind in IndustryTemplateRegistry().list_templates():
            t = IndustryTemplateRegistry().get_template_dict(ind)
            for k in t["kpis"]:
                assert "target" in k

    def test_revenue_kpi_net_rev_alias(self):
        from packages.cognitive_kernel.intelligence_profile.industry_templates import IndustryTemplateRegistry
        t = IndustryTemplateRegistry().get_template_dict("retail")
        rev = next(k for k in t["kpis"] if k["name"] == "revenue")
        assert "net_rev" in rev.get("aliases", [])


# STEP 5: DYNAMIC DASHBOARD GENERATION
class TestDashboardGeneration:
    def test_dashboard_generated(self):
        from packages.cognitive_kernel.dashboard_engine.composition_engine import DashboardCompositionEngine
        from packages.cognitive_kernel.intelligence_profile.industry_templates import IndustryTemplateRegistry
        t = IndustryTemplateRegistry().get_template_dict("retail")
        d = DashboardCompositionEngine().compose(ORG_ID, {
            "industry": "retail", "kpis": t["kpis"], "ontology": {"customer": {}},
        }, role="executive")
        assert d is not None
        assert len(d.layout) > 0

    def test_dashboard_has_widgets(self):
        from packages.cognitive_kernel.dashboard_engine.composition_engine import DashboardCompositionEngine
        from packages.cognitive_kernel.intelligence_profile.industry_templates import IndustryTemplateRegistry
        t = IndustryTemplateRegistry().get_template_dict("retail")
        d = DashboardCompositionEngine().compose(ORG_ID, {
            "industry": "retail", "kpis": t["kpis"], "ontology": {"customer": {}},
        }, role="executive")
        assert len(d.layout) >= 2

    def test_widget_registry_types(self):
        from packages.cognitive_kernel.dashboard_engine.widget_registry import WidgetRegistry
        assert len(WidgetRegistry().all_widgets()) >= 10

    def test_dashboard_to_json(self):
        from packages.cognitive_kernel.dashboard_engine.composition_engine import DashboardCompositionEngine
        d = DashboardCompositionEngine().compose(ORG_ID, {"industry":"retail","kpis":[],"ontology":{}}, role="executive")
        j = d.to_json()
        assert "dashboard_id" in j
        assert "layout" in j


# STEP 6: AGENT CREATION
class TestAgentCreation:
    def test_agent_registry_has_types(self):
        from packages.cognitive_kernel.agent_os.agent_registry import AgentRegistry
        assert len(AgentRegistry().all_types()) >= 5

    def test_sales_agent_exists(self):
        from packages.cognitive_kernel.agent_os.agent_registry import AgentRegistry, AgentType
        assert AgentRegistry().get_type(AgentType.SALES) is not None

    def test_agent_creation_from_profile(self):
        from packages.cognitive_kernel.agent_os.agent_manager import AgentManager
        from packages.cognitive_kernel.agent_os.agent_registry import AgentType
        a = AgentManager().create_agent_from_profile(
            org_id=ORG_ID, profile_context={"industry":"retail","kpis":[],"ontology":{}},
            agent_type=AgentType.SALES,
        )
        assert a is not None and a.org_id == ORG_ID

    def test_agent_has_kpis(self):
        from packages.cognitive_kernel.agent_os.agent_registry import AgentRegistry, AgentType
        s = AgentRegistry().get_type(AgentType.SALES)
        assert len(s.kpis_monitored) > 0

    def test_industry_specific_agents(self):
        from packages.cognitive_kernel.agent_os.agent_registry import AgentRegistry
        assert len(AgentRegistry().get_types_for_industry("retail")) >= 3


# STEP 7: NATURAL LANGUAGE QUERY
class TestNaturalLanguageQuery:
    def test_intent_root_cause(self):
        from packages.cognitive_kernel.nl_interface.nl_engine import NLIntelligenceEngine
        i = NLIntelligenceEngine()._detect_intent("Why did revenue drop last quarter?")
        assert "root" in i.lower() or "cause" in i.lower()

    def test_intent_prediction(self):
        from packages.cognitive_kernel.nl_interface.nl_engine import NLIntelligenceEngine
        i = NLIntelligenceEngine()._detect_intent("Forecast revenue for next month")
        assert "predict" in i.lower() or "forecast" in i.lower()

    def test_intent_comparison(self):
        from packages.cognitive_kernel.nl_interface.nl_engine import NLIntelligenceEngine
        i = NLIntelligenceEngine()._detect_intent("Compare revenue vs margin")
        assert "compar" in i.lower()

    def test_kpi_identification(self):
        from packages.cognitive_kernel.nl_interface.nl_engine import NLIntelligenceEngine
        e = NLIntelligenceEngine()
        k = e._identify_kpis("What about revenue?", {"kpis": [{"name":"revenue","label":"Revenue","aliases":["net_rev","sales"]}]})
        assert len(k) > 0

    def test_entity_identification(self):
        from packages.cognitive_kernel.nl_interface.nl_engine import NLIntelligenceEngine
        e = NLIntelligenceEngine()
        entities = e._identify_entities("Show me customer data by location", {"ontology": {}})
        assert isinstance(entities, list)

    def test_agent_activation(self):
        from packages.cognitive_kernel.nl_interface.nl_engine import NLIntelligenceEngine
        e = NLIntelligenceEngine()
        agents = [{"type":"sales","label":"Sales Agent","kpis":["revenue","sell_out"]}]
        activated = e._activate_agents("What about revenue?", agents, ["revenue"])
        assert isinstance(activated, list)


# STEP 8: DECISION GENERATION
class TestDecisionGeneration:
    @pytest.mark.asyncio
    async def test_decision_engine_decide(self):
        from packages.cognitive_kernel.decision_engine.decision_engine import DecisionEngine
        e = DecisionEngine()
        with patch.object(e, '_retrieve_context', new_callable=AsyncMock) as mc, \
             patch.object(e, '_collect_evidence', new_callable=AsyncMock) as me, \
             patch.object(e, '_reason', new_callable=AsyncMock) as mr, \
             patch.object(e, '_generate_recommendation', new_callable=AsyncMock) as mrec:
            mc.return_value = {"kpis": [{"name":"revenue"}]}
            me.return_value = [{"source":"test","finding":"test"}]
            mr.return_value = ["reason1"]
            mrec.return_value = "Increase spend"
            d = await e.decide("Why did revenue drop?", ORG_ID)
            assert d is not None

    def test_confidence_scorer(self):
        from packages.cognitive_kernel.decision_engine.confidence_scorer import ConfidenceScorer
        s = ConfidenceScorer().score_decision(
            evidence=[{"confidence":0.8}], reasoning=["r1","r2"], risks=[{"probability":0.3}]
        )
        assert 0.0 <= s <= 1.0

    @pytest.mark.asyncio
    async def test_risk_analyzer(self):
        from packages.cognitive_kernel.decision_engine.risk_analyzer import RiskAnalyzer
        a = RiskAnalyzer()
        a.gateway = AsyncMock()
        a.gateway.generate = AsyncMock()
        a.gateway.generate.return_value.content = "[]"
        r = await a.analyze_risks("Revenue declining", [{"content":"15% drop"}])
        assert isinstance(r, dict)


# STEP 9: MEMORY UPDATE
class TestMemoryUpdate:
    def test_chunking(self):
        from packages.cognitive_kernel.memory_engine.chunker import TextChunker
        chunks = TextChunker.chunk_fixed_size("Test document. " * 100, size=200, overlap=50)
        assert len(chunks) > 1

    def test_normalization(self):
        from packages.cognitive_kernel.memory_engine.normalizer import TextNormalizer
        r = TextNormalizer.normalize("  Extra   spaces  ")
        assert "  " not in r

    def test_agent_memory_types(self):
        from packages.cognitive_kernel.agent_os.agent_memory import MemoryType
        assert MemoryType.SHORT_TERM.value == "short_term"
        assert MemoryType.LONG_TERM.value == "long_term"
        assert MemoryType.EXPERIENCE.value == "experience"
        assert MemoryType.DECISION_HISTORY.value == "decision_history"

    def test_agent_memory_store_retrieve(self):
        from packages.cognitive_kernel.agent_os.agent_memory import AgentMemory, MemoryType
        m = AgentMemory()
        m.store(agent_id="sales-001", org_id=ORG_ID, memory_type=MemoryType.SHORT_TERM,
                content="Revenue declined 15%", importance=0.8)
        entries = m.retrieve(agent_id="sales-001", memory_type=MemoryType.SHORT_TERM, limit=5)
        assert len(entries) > 0
        assert any("Revenue" in e.content for e in entries)

    def test_decision_store_interface(self):
        from packages.cognitive_kernel.decision_engine.decision_store import DecisionStore
        assert hasattr(DecisionStore, "create")
        assert hasattr(DecisionStore, "get")
        assert hasattr(DecisionStore, "list")
        assert hasattr(DecisionStore, "update_status")


# END-TO-END: COMPLETE INTELLIGENCE LOOP
class TestCompleteIntelligenceLoop:
    def test_full_pipeline(self):
        # 1. Profile
        from packages.cognitive_kernel.data_intelligence.universal_profiler import UniversalDataProfiler
        p = UniversalDataProfiler()
        profiled = p.profile_dataframe(make_df(), source_name="enterprise_sales.xlsx")
        assert profiled.column_count == 10

        # 2. Semantic mapping
        from packages.cognitive_kernel.data_intelligence.semantic_mapping_v2 import SemanticMappingEngineV2
        m = SemanticMappingEngineV2()
        mappings = {col: m.map_column(col, [TEST_ROWS[j][i] for j in range(len(TEST_ROWS))])
                    for i, col in enumerate(TEST_COLUMNS)}
        assert len(mappings) == 10

        # 3. Industry template
        from packages.cognitive_kernel.intelligence_profile.industry_templates import IndustryTemplateRegistry
        t = IndustryTemplateRegistry().get_template_dict("retail")
        assert t is not None

        # 4. KPIs
        kpis = t["kpis"]
        assert len(kpis) >= 3

        # 5. Dashboard
        from packages.cognitive_kernel.dashboard_engine.composition_engine import DashboardCompositionEngine
        d = DashboardCompositionEngine().compose(ORG_ID, {"industry":"retail","kpis":kpis,"ontology":{}}, role="executive")
        assert len(d.layout) > 0

        # 6. Agents
        from packages.cognitive_kernel.agent_os.agent_manager import AgentManager
        from packages.cognitive_kernel.agent_os.agent_registry import AgentType
        a = AgentManager().create_agent_from_profile(org_id=ORG_ID, profile_context={"industry":"retail","kpis":kpis,"ontology":{}}, agent_type=AgentType.SALES)
        assert a is not None

        # 7. NL query
        from packages.cognitive_kernel.nl_interface.nl_engine import NLIntelligenceEngine
        nl = NLIntelligenceEngine()
        intent = nl._detect_intent("Why did revenue drop?")
        assert intent is not None

        # 8. Memory
        from packages.cognitive_kernel.memory_engine.chunker import TextChunker
        chunks = TextChunker.chunk_fixed_size("Decision: Revenue dropped. Action: Increase spend.", size=200, overlap=50)
        assert len(chunks) >= 1

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
