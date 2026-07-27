"""
πX Dynamic Dashboard Engine — Integration tests across 3 industries.

Verifies that the same codebase produces different intelligence dashboards
for Retail, Manufacturing, and SaaS companies based on their Intelligence Profile.
"""
import pytest
from packages.cognitive_kernel.dashboard_engine.composition_engine import DashboardCompositionEngine
from packages.cognitive_kernel.dashboard_engine.role_based_generator import RoleBasedDashboardGenerator
from packages.cognitive_kernel.dashboard_engine.widget_registry import WidgetRegistry, WidgetType, WidgetCategory
from packages.cognitive_kernel.dashboard_engine.dashboard_agent import DashboardIntelligenceAgent
from packages.cognitive_kernel.dashboard_engine.customization import UserCustomizationManager

ORG_ID = "test-org-001"


# ── Profile contexts for each industry ──

RETAIL_PROFILE = {
    "org_id": ORG_ID,
    "industry": "retail",
    "company_identity": {"name": "Acme Retail Co"},
    "kpis": [
        {"name": "Revenue", "source_column": "NET_REV", "target": 5000000, "aggregation": "sum", "format": "currency", "unit": "$"},
        {"name": "Sell-out", "source_column": "SELL_OUT", "target": 100000, "aggregation": "sum"},
        {"name": "Inventory Turnover", "source_column": "INV_TURN", "target": 4.0, "aggregation": "avg", "format": "number"},
        {"name": "Margin", "source_column": "MARGIN", "target": 0.35, "aggregation": "avg", "format": "percentage"},
    ],
    "ontology": {"entities": {"store": {"attributes": ["store_id", "location"]}, "product": {"attributes": ["sku", "category"]}, "customer": {"attributes": ["cust_name", "email"]}}},
    "data_sources": [{"type": "xlsx", "name": "sales_data.xlsx"}],
    "agents": [{"name": "Sales Intelligence Agent", "type": "sales"}, {"name": "Inventory Agent", "type": "inventory"}],
    "confidence": {"overall": 0.92},
}

MANUFACTURING_PROFILE = {
    "org_id": ORG_ID,
    "industry": "manufacturing",
    "company_identity": {"name": "Precision Manufacturing Inc"},
    "kpis": [
        {"name": "OEE", "source_column": "OEE_VAL", "target": 0.85, "aggregation": "avg", "format": "percentage"},
        {"name": "Quality Rate", "source_column": "DEFECT_RATE", "target": 0.98, "aggregation": "avg", "format": "percentage"},
        {"name": "Production Volume", "source_column": "PROD_VOL", "target": 50000, "aggregation": "sum"},
    ],
    "ontology": {"entities": {"machine": {"attributes": ["machine_id", "type"]}, "production_line": {"attributes": ["line_id", "capacity"]}, "work_order": {"attributes": ["wo_id", "status"]}}},
    "data_sources": [{"type": "csv", "name": "production_log.csv"}],
    "agents": [{"name": "Production Optimization Agent", "type": "production"}, {"name": "Quality Agent", "type": "quality"}],
    "confidence": {"overall": 0.88},
}

SAAS_PROFILE = {
    "org_id": ORG_ID,
    "industry": "saas",
    "company_identity": {"name": "CloudScale SaaS"},
    "kpis": [
        {"name": "MRR", "source_column": "MRR", "target": 500000, "aggregation": "sum", "format": "currency", "unit": "$"},
        {"name": "Churn Rate", "source_column": "CHURN", "target": 0.02, "aggregation": "avg", "format": "percentage"},
        {"name": "Activation Rate", "source_column": "ACTIVATION", "target": 0.75, "aggregation": "avg", "format": "percentage"},
        {"name": "Customer Health Score", "source_column": "CHS", "target": 80, "aggregation": "avg"},
    ],
    "ontology": {"entities": {"account": {"attributes": ["account_id", "plan"]}, "user": {"attributes": ["user_id", "last_active"]}, "subscription": {"attributes": ["sub_id", "status"]}}},
    "data_sources": [{"type": "api", "name": "billing_api"}],
    "agents": [{"name": "Customer Success Agent", "type": "success"}, {"name": "Churn Prediction Agent", "type": "churn"}],
    "confidence": {"overall": 0.90},
}


# ── Widget Registry Tests ──

class TestWidgetRegistry:
    def test_registry_has_15_widgets(self):
        registry = WidgetRegistry()
        assert len(registry.all_widgets()) == 15

    def test_widgets_across_4_categories(self):
        registry = WidgetRegistry()
        categories = {w.category for w in registry.all_widgets()}
        assert len(categories) == 4

    def test_executive_category_has_4_widgets(self):
        registry = WidgetRegistry()
        exec_widgets = registry.get_by_category(WidgetCategory.EXECUTIVE)
        assert len(exec_widgets) == 4

    def test_all_widgets_have_component_name(self):
        registry = WidgetRegistry()
        for w in registry.all_widgets():
            assert w.component_name != ""

    def test_can_satisfy(self):
        registry = WidgetRegistry()
        # KPI card needs metric_name + current_value
        assert registry.can_satisfy(WidgetType.KPI_CARD, {"metric_name", "current_value"})
        assert not registry.can_satisfy(WidgetType.KPI_CARD, {"metric_name"})


# ── Composition Engine Tests ──

class TestCompositionEngine:
    def test_retail_dashboard_generation(self):
        engine = DashboardCompositionEngine()
        dash = engine.compose(ORG_ID, RETAIL_PROFILE, role="ceo")
        assert dash.industry == "retail"
        assert "Acme Retail Co" in dash.title
        assert len(dash.layout) > 0
        # Should have KPI cards
        kpi_cards = [w for w in dash.layout if w.type == WidgetType.KPI_CARD]
        assert len(kpi_cards) >= 3  # Retail has 4 KPIs, CEO gets 4

    def test_manufacturing_dashboard_generation(self):
        engine = DashboardCompositionEngine()
        dash = engine.compose(ORG_ID, MANUFACTURING_PROFILE, role="coo")
        assert dash.industry == "manufacturing"
        assert "Precision Manufacturing" in dash.title
        # Should have KPI cards for manufacturing metrics
        kpi_labels = [w.label for w in dash.layout if w.type == WidgetType.KPI_CARD]
        assert any("OEE" in label or "Quality" in label or "Production" in label for label in kpi_labels)

    def test_saas_dashboard_generation(self):
        engine = DashboardCompositionEngine()
        dash = engine.compose(ORG_ID, SAAS_PROFILE, role="ceo")
        assert dash.industry == "saas"
        assert "CloudScale" in dash.title
        kpi_labels = [w.label for w in dash.layout if w.type == WidgetType.KPI_CARD]
        assert any("MRR" in label or "Churn" in label or "Activation" in label for label in kpi_labels)

    def test_dashboard_to_json(self):
        engine = DashboardCompositionEngine()
        dash = engine.compose(ORG_ID, RETAIL_PROFILE, role="ceo")
        j = dash.to_json()
        assert "dashboard_id" in j
        assert "layout" in j
        assert isinstance(j["layout"], list)
        assert all("component" in w for w in j["layout"])

    def test_different_industries_different_dashboards(self):
        engine = DashboardCompositionEngine()
        retail = engine.compose(ORG_ID, RETAIL_PROFILE, role="ceo")
        mfg = engine.compose(ORG_ID, MANUFACTURING_PROFILE, role="ceo")
        saas = engine.compose(ORG_ID, SAAS_PROFILE, role="ceo")
        # Different KPI labels
        retail_kpis = {w.label for w in retail.layout if w.type == WidgetType.KPI_CARD}
        mfg_kpis = {w.label for w in mfg.layout if w.type == WidgetType.KPI_CARD}
        saas_kpis = {w.label for w in saas.layout if w.type == WidgetType.KPI_CARD}
        assert retail_kpis != mfg_kpis
        assert retail_kpis != saas_kpis
        assert mfg_kpis != saas_kpis

    def test_dashboard_has_intelligence_widgets(self):
        engine = DashboardCompositionEngine()
        dash = engine.compose(ORG_ID, RETAIL_PROFILE, role="ceo")
        # Should always have decision queue and AI recommendation
        widget_types = {w.type for w in dash.layout}
        assert WidgetType.DECISION_QUEUE in widget_types
        assert WidgetType.AI_RECOMMENDATION in widget_types

    def test_dashboard_has_data_quality(self):
        engine = DashboardCompositionEngine()
        dash = engine.compose(ORG_ID, RETAIL_PROFILE, role="ceo")
        widget_types = {w.type for w in dash.layout}
        assert WidgetType.DATA_QUALITY_SCORE in widget_types


# ── Role-Based Generation Tests ──

class TestRoleBasedGeneration:
    def test_ceo_gets_goal_progress(self):
        gen = RoleBasedDashboardGenerator()
        dash = gen.generate(ORG_ID, RETAIL_PROFILE, "ceo")
        widget_types = {w.type for w in dash.layout}
        # CEO with targets should get goal progress widgets
        assert WidgetType.GOAL_PROGRESS in widget_types or WidgetType.ALERT_PANEL in widget_types

    def test_cfo_gets_forecast(self):
        gen = RoleBasedDashboardGenerator()
        dash = gen.generate(ORG_ID, RETAIL_PROFILE, "cfo")
        widget_types = {w.type for w in dash.layout}
        assert WidgetType.FORECAST_CHART in widget_types

    def test_co0_gets_workflow(self):
        gen = RoleBasedDashboardGenerator()
        dash = gen.generate(ORG_ID, MANUFACTURING_PROFILE, "coo")
        widget_types = {w.type for w in dash.layout}
        assert WidgetType.WORKFLOW_MONITOR in widget_types
        assert WidgetType.DISTRIBUTION_CHART in widget_types

    def test_cto_gets_knowledge_graph(self):
        gen = RoleBasedDashboardGenerator()
        dash = gen.generate(ORG_ID, SAAS_PROFILE, "cto")
        widget_types = {w.type for w in dash.layout}
        assert WidgetType.KNOWLEDGE_GRAPH_VIEW in widget_types
        assert WidgetType.AGENT_STATUS in widget_types

    def test_generate_all_roles(self):
        gen = RoleBasedDashboardGenerator()
        dashboards = gen.generate_all_roles(ORG_ID, RETAIL_PROFILE)
        assert len(dashboards) == 7
        for role, dash in dashboards.items():
            assert dash.role == role
            assert len(dash.layout) > 0

    def test_agent_status_shown_when_agents_exist(self):
        gen = RoleBasedDashboardGenerator()
        # Retail has agents
        dash = gen.generate(ORG_ID, RETAIL_PROFILE, "ceo")
        widget_types = {w.type for w in dash.layout}
        assert WidgetType.AGENT_STATUS in widget_types


# ── Dashboard Intelligence Agent Tests ──

class TestDashboardIntelligenceAgent:
    def test_recommendation_includes_reasoning(self):
        agent = DashboardIntelligenceAgent()
        rec = agent.recommend(ORG_ID, RETAIL_PROFILE, "cfo")
        assert len(rec.reasoning) > 50
        assert "CFO" in rec.reasoning or "Financial" in rec.reasoning
        assert "Acme Retail" in rec.reasoning

    def test_recommendation_confidence(self):
        agent = DashboardIntelligenceAgent()
        rec = agent.recommend(ORG_ID, RETAIL_PROFILE, "ceo")
        assert 0 < rec.confidence <= 1.0

    def test_recommendation_widgets_not_empty(self):
        agent = DashboardIntelligenceAgent()
        rec = agent.recommend(ORG_ID, MANUFACTURING_PROFILE, "coo")
        assert len(rec.recommended_widgets) > 0
        assert all("component" in w for w in rec.recommended_widgets)

    def test_alternative_roles(self):
        agent = DashboardIntelligenceAgent()
        rec = agent.recommend(ORG_ID, SAAS_PROFILE, "ceo")
        assert len(rec.alternative_roles) <= 3
        assert "ceo" not in rec.alternative_roles

    def test_saas_recommends_cto_first(self):
        agent = DashboardIntelligenceAgent()
        rec = agent.recommend(ORG_ID, SAAS_PROFILE, "ceo")
        # SaaS should prioritize CTO view
        assert rec.alternative_roles[0] == "cto"


# ── Customization Tests ──

class TestCustomization:
    def test_save_and_retrieve_preferences(self):
        mgr = UserCustomizationManager()
        mgr.save_preferences("org1", "user1", "ceo", hidden_widgets=["w1", "w2"])
        prefs = mgr.get_preferences("org1", "user1")
        assert prefs is not None
        assert "w1" in prefs.hidden_widgets

    def test_hide_widget(self):
        mgr = UserCustomizationManager()
        mgr.save_preferences("org1", "user2", "ceo")
        mgr.hide_widget("org1", "user2", "widget_abc")
        prefs = mgr.get_preferences("org1", "user2")
        assert "widget_abc" in prefs.hidden_widgets

    def test_unhide_widget(self):
        mgr = UserCustomizationManager()
        mgr.save_preferences("org1", "user3", "ceo", hidden_widgets=["w1"])
        mgr.unhide_widget("org1", "user3", "w1")
        prefs = mgr.get_preferences("org1", "user3")
        assert "w1" not in prefs.hidden_widgets

    def test_add_custom_widget(self):
        mgr = UserCustomizationManager()
        mgr.save_preferences("org1", "user4", "executive")
        widget = mgr.add_widget("org1", "user4", "kpi_card", "Custom Revenue", {"metric": "Revenue"})
        assert widget["type"] == "kpi_card"
        assert widget["label"] == "Custom Revenue"
        assert widget["custom"] is True

    def test_reset_preferences(self):
        mgr = UserCustomizationManager()
        mgr.save_preferences("org1", "user5", "ceo", hidden_widgets=["w1"])
        mgr.reset("org1", "user5")
        assert mgr.get_preferences("org1", "user5") is None

    def test_update_layout(self):
        mgr = UserCustomizationManager()
        mgr.save_preferences("org1", "user6", "ceo")
        mgr.update_layout("org1", "user6", {"w1": [0, 0], "w2": [0, 1]})
        prefs = mgr.get_preferences("org1", "user6")
        assert prefs.layout_overrides["w1"] == [0, 0]

    def test_hidden_widgets_filter_composition(self):
        engine = DashboardCompositionEngine()
        prefs = {"hidden_widgets": ["widget_0", "widget_1"]}
        dash = engine.compose(ORG_ID, RETAIL_PROFILE, role="ceo", user_preferences=prefs)
        widget_ids = {w.id for w in dash.layout}
        assert "widget_0" not in widget_ids
        assert "widget_1" not in widget_ids


# ── Cross-Industry Differentiation Tests ──

class TestIndustryDifferentiation:
    def test_retail_has_revenue_kpi(self):
        engine = DashboardCompositionEngine()
        dash = engine.compose(ORG_ID, RETAIL_PROFILE, role="ceo")
        kpi_labels = [w.label for w in dash.layout if w.type == WidgetType.KPI_CARD]
        assert any("Revenue" in label for label in kpi_labels)

    def test_manufacturing_has_oee_kpi(self):
        engine = DashboardCompositionEngine()
        dash = engine.compose(ORG_ID, MANUFACTURING_PROFILE, role="ceo")
        kpi_labels = [w.label for w in dash.layout if w.type == WidgetType.KPI_CARD]
        assert any("OEE" in label for label in kpi_labels)

    def test_saas_has_mrr_kpi(self):
        engine = DashboardCompositionEngine()
        dash = engine.compose(ORG_ID, SAAS_PROFILE, role="ceo")
        kpi_labels = [w.label for w in dash.layout if w.type == WidgetType.KPI_CARD]
        assert any("MRR" in label for label in kpi_labels)

    def test_same_code_different_output(self):
        engine = DashboardCompositionEngine()
        gen = RoleBasedDashboardGenerator(composition_engine=engine)
        retail = gen.generate(ORG_ID, RETAIL_PROFILE, "ceo")
        mfg = gen.generate(ORG_ID, MANUFACTURING_PROFILE, "ceo")
        saas = gen.generate(ORG_ID, SAAS_PROFILE, "ceo")
        # Titles should be different
        assert retail.title != mfg.title
        assert retail.title != saas.title
        # Subtitles should mention industry
        assert "retail" in retail.subtitle.lower()
        assert "manufacturing" in mfg.subtitle.lower()
        assert "saas" in saas.subtitle.lower()
