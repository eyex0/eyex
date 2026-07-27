"""
πX Enterprise AI Agent OS — Integration tests across 2 industries.

Verifies that agents generated from different Intelligence Profiles
produce different intelligence — same platform, different agents.
"""
import pytest

from packages.cognitive_kernel.agent_os.agent_registry import AgentRegistry, AgentType, AgentStatus
from packages.cognitive_kernel.agent_os.agent_memory import AgentMemory, MemoryType
from packages.cognitive_kernel.agent_os.agent_manager import AgentManager
from packages.cognitive_kernel.agent_os.agent_supervisor import AgentSupervisor
from packages.cognitive_kernel.agent_os.tool_registry import ToolRegistry, ToolCategory
from packages.cognitive_kernel.agent_os.evaluation_loop import AgentEvaluationLoop
from packages.cognitive_kernel.agent_os.agent_security import AgentSecurity


ORG_ID = "test-org-001"

RETAIL_PROFILE = {
    "org_id": ORG_ID,
    "industry": "retail",
    "company_identity": {"name": "Acme Retail Co"},
    "kpis": [
        {"name": "Revenue", "source_column": "NET_REV"},
        {"name": "Sell-out", "source_column": "SELL_OUT"},
        {"name": "Inventory Turnover", "source_column": "INV_TURN"},
    ],
    "ontology": {"entities": {"customer": {}, "product": {}, "store": {}}},
    "agents": [],
    "confidence": {"overall": 0.92},
}

MANUFACTURING_PROFILE = {
    "org_id": ORG_ID,
    "industry": "manufacturing",
    "company_identity": {"name": "Precision Mfg Inc"},
    "kpis": [
        {"name": "OEE", "source_column": "OEE_VAL"},
        {"name": "Quality Rate", "source_column": "DEFECT_RATE"},
        {"name": "Production Volume", "source_column": "PROD_VOL"},
    ],
    "ontology": {"entities": {"equipment": {}, "work_order": {}, "product": {}}},
    "agents": [],
    "confidence": {"overall": 0.88},
}


class TestAgentRegistry:
    def test_registry_has_11_types(self):
        reg = AgentRegistry()
        assert len(reg.all_types()) >= 10

    def test_retail_types_include_sales(self):
        reg = AgentRegistry()
        types = reg.get_types_for_industry("retail")
        type_names = [s.type for s in types]
        assert AgentType.SALES in type_names
        assert AgentType.INVENTORY in type_names

    def test_manufacturing_types_include_production(self):
        reg = AgentRegistry()
        types = reg.get_types_for_industry("manufacturing")
        type_names = [s.type for s in types]
        assert AgentType.PRODUCTION in type_names
        assert AgentType.QUALITY in type_names

    def test_generic_types_always_available(self):
        reg = AgentRegistry()
        retail_types = reg.get_types_for_industry("retail")
        type_names = {s.type for s in retail_types}
        assert AgentType.FINANCE in type_names
        assert AgentType.STRATEGY in type_names


class TestAgentMemory:
    def test_store_and_retrieve_short_term(self):
        mem = AgentMemory()
        entry = mem.store("agent_1", ORG_ID, MemoryType.SHORT_TERM, "Test context", importance=0.8)
        assert entry.content == "Test context"
        results = mem.retrieve("agent_1", MemoryType.SHORT_TERM)
        assert len(results) == 1
        assert results[0].content == "Test context"

    def test_long_term_memory_persists(self):
        mem = AgentMemory()
        mem.store("agent_1", ORG_ID, MemoryType.LONG_TERM, "Company is in retail", importance=0.9)
        results = mem.retrieve("agent_1", MemoryType.LONG_TERM)
        assert len(results) == 1

    def test_experience_memory(self):
        mem = AgentMemory()
        mem.record_outcome("agent_1", ORG_ID, "Analyze revenue", "Revenue up 5%", 0.85)
        results = mem.retrieve("agent_1", MemoryType.EXPERIENCE)
        assert len(results) == 1
        assert "0.85" in results[0].content

    def test_short_term_limit_20(self):
        mem = AgentMemory()
        for i in range(25):
            mem.store("agent_1", ORG_ID, MemoryType.SHORT_TERM, f"Message {i}")
        results = mem.retrieve("agent_1", MemoryType.SHORT_TERM, limit=50)
        assert len(results) == 20

    def test_search(self):
        mem = AgentMemory()
        mem.store("agent_1", ORG_ID, MemoryType.LONG_TERM, "Revenue dropped in Q3", importance=0.9)
        results = mem.search("agent_1", "Revenue")
        assert len(results) >= 1

    def test_context_building(self):
        mem = AgentMemory()
        mem.store("a1", ORG_ID, MemoryType.SHORT_TERM, "Recent: customer asked about revenue")
        mem.store("a1", ORG_ID, MemoryType.LONG_TERM, "Company is Acme Retail", importance=0.9)
        ctx = mem.get_context("a1")
        assert "Recent" in ctx
        assert "Acme Retail" in ctx

    def test_stats(self):
        mem = AgentMemory()
        mem.store("a1", ORG_ID, MemoryType.SHORT_TERM, "s1")
        mem.store("a1", ORG_ID, MemoryType.LONG_TERM, "l1", importance=0.8)
        mem.record_outcome("a1", ORG_ID, "action", "outcome", 0.7)
        stats = mem.get_stats("a1")
        assert stats["total"] == 3
        assert stats["short_term"] == 1
        assert stats["long_term"] == 1
        assert stats["experience"] == 1


class TestToolRegistry:
    def test_has_9_tools(self):
        reg = ToolRegistry()
        assert len(reg.all_tools()) == 9

    def test_tools_in_3_categories(self):
        reg = ToolRegistry()
        cats = {t.category for t in reg.all_tools()}
        assert len(cats) == 3

    def test_data_tools(self):
        reg = ToolRegistry()
        data_tools = reg.get_by_category(ToolCategory.DATA)
        names = {t.name for t in data_tools}
        assert "query_database" in names
        assert "search_memory" in names
        assert "search_knowledge_graph" in names

    def test_analysis_tools(self):
        reg = ToolRegistry()
        analysis = reg.get_by_category(ToolCategory.ANALYSIS)
        names = {t.name for t in analysis}
        assert "kpi_analyzer" in names
        assert "forecast_tool" in names
        assert "simulation_tool" in names

    def test_business_tools(self):
        reg = ToolRegistry()
        business = reg.get_by_category(ToolCategory.BUSINESS)
        names = {t.name for t in business}
        assert "generate_report" in names
        assert "create_decision" in names

    def test_get_tools_for_agent(self):
        reg = ToolRegistry()
        tools = reg.get_tools_for_agent(["query_database", "kpi_analyzer", "nonexistent"])
        assert len(tools) == 2


class TestAgentSecurity:
    def test_ceo_full_access(self):
        sec = AgentSecurity()
        from packages.cognitive_kernel.agent_os.agent_registry import AgentSpec
        spec = AgentSpec(
            type=AgentType.STRATEGY, label="Strategy", purpose="test",
            industry="generic", role="ceo", tools=["query_database"],
            knowledge_access=["*"], data_access=["*"],
        )
        perm = sec.grant("agent_1", ORG_ID, spec)
        assert sec.check_data_access("agent_1", "anything")
        assert sec.check_entity_access("agent_1", "anything")

    def test_cfo_financial_only(self):
        sec = AgentSecurity()
        from packages.cognitive_kernel.agent_os.agent_registry import AgentSpec
        spec = AgentSpec(
            type=AgentType.FINANCE, label="Finance", purpose="test",
            industry="generic", role="cfo", tools=["query_database"],
            knowledge_access=["revenue", "cost"], data_access=["financial"],
        )
        perm = sec.grant("agent_2", ORG_ID, spec)
        assert sec.check_data_access("agent_2", "financial")
        assert not sec.check_data_access("agent_2", "employee_data")

    def test_hr_employee_only(self):
        sec = AgentSecurity()
        from packages.cognitive_kernel.agent_os.agent_registry import AgentSpec
        spec = AgentSpec(
            type=AgentType.HR, label="HR", purpose="test",
            industry="generic", role="chro", tools=["query_database"],
            knowledge_access=["employee"], data_access=["hr"],
        )
        perm = sec.grant("agent_3", ORG_ID, spec)
        assert sec.check_data_access("agent_3", "hr")
        assert not sec.check_data_access("agent_3", "financial")

    def test_sensitivity_check(self):
        sec = AgentSecurity()
        from packages.cognitive_kernel.agent_os.agent_registry import AgentSpec
        spec = AgentSpec(
            type=AgentType.FINANCE, label="Finance", purpose="test",
            industry="generic", role="cfo", tools=["query_database"],
            knowledge_access=["*"], data_access=["*"],
        )
        sec.grant("agent_4", ORG_ID, spec)
        assert sec.check_sensitivity("agent_4", "high")
        assert not sec.check_sensitivity("agent_4", "critical")

    def test_tool_access_enforced(self):
        sec = AgentSecurity()
        from packages.cognitive_kernel.agent_os.agent_registry import AgentSpec
        spec = AgentSpec(
            type=AgentType.SALES, label="Sales", purpose="test",
            industry="retail", role="cfo", tools=["query_database", "kpi_analyzer"],
            knowledge_access=["customer"], data_access=["sales"],
        )
        sec.grant("agent_5", ORG_ID, spec)
        assert sec.check_tool_access("agent_5", "query_database")
        assert not sec.check_tool_access("agent_5", "send_notification")

    def test_action_permission(self):
        sec = AgentSecurity()
        from packages.cognitive_kernel.agent_os.agent_registry import AgentSpec
        spec = AgentSpec(
            type=AgentType.SALES, label="Sales", purpose="test",
            industry="retail", role="cfo", tools=["query_database", "create_decision"],
            knowledge_access=["*"], data_access=["*"],
        )
        sec.grant("agent_6", ORG_ID, spec)
        assert sec.check_action("agent_6", "create_decision")
        assert not sec.check_action("agent_6", "send_notification")
        assert not sec.check_action("agent_6", "modify_data")


class TestAgentManager:
    def test_create_agent_from_retail_profile(self):
        mgr = AgentManager()
        agent = mgr.create_agent_from_profile(ORG_ID, RETAIL_PROFILE, AgentType.SALES)
        assert agent.spec.industry == "retail"
        assert agent.spec.label == "Sales Intelligence Agent"
        assert "Revenue" in agent.spec.kpis_monitored or "Sell-out" in agent.spec.kpis_monitored
        assert agent.status == AgentStatus.ACTIVE

    def test_create_agent_from_manufacturing_profile(self):
        mgr = AgentManager()
        agent = mgr.create_agent_from_profile(ORG_ID, MANUFACTURING_PROFILE, AgentType.PRODUCTION)
        assert agent.spec.industry == "manufacturing"
        assert "OEE" in agent.spec.kpis_monitored

    def test_create_all_agents_for_retail(self):
        mgr = AgentManager()
        agents = mgr.create_agents_for_industry(ORG_ID, RETAIL_PROFILE)
        types = {a.spec.type for a in agents}
        assert AgentType.SALES in types
        assert AgentType.INVENTORY in types
        assert AgentType.CUSTOMER in types

    def test_create_all_agents_for_manufacturing(self):
        mgr = AgentManager()
        agents = mgr.create_agents_for_industry(ORG_ID, MANUFACTURING_PROFILE)
        types = {a.spec.type for a in agents}
        assert AgentType.PRODUCTION in types
        assert AgentType.QUALITY in types
        assert AgentType.MAINTENANCE in types

    def test_agent_memory_initialized(self):
        mgr = AgentManager()
        agent = mgr.create_agent_from_profile(ORG_ID, RETAIL_PROFILE, AgentType.SALES)
        memory = mgr.get_memory(agent.id, "long_term")
        assert len(memory) >= 2
        assert any("Acme Retail" in m["content"] for m in memory)

    def test_execute_agent(self):
        mgr = AgentManager()
        agent = mgr.create_agent_from_profile(ORG_ID, RETAIL_PROFILE, AgentType.SALES)
        result = mgr.execute(agent.id, "Why did revenue drop last quarter?", RETAIL_PROFILE)
        assert result.error is None
        assert "Sales Intelligence Agent" in result.response
        assert len(result.tools_used) > 0

    def test_pause_and_resume(self):
        mgr = AgentManager()
        agent = mgr.create_agent_from_profile(ORG_ID, RETAIL_PROFILE, AgentType.INVENTORY)
        assert mgr.pause(agent.id)
        assert mgr.registry.get_instance(agent.id).status == AgentStatus.PAUSED
        assert mgr.resume(agent.id)
        assert mgr.registry.get_instance(agent.id).status == AgentStatus.ACTIVE

    def test_stop_agent(self):
        mgr = AgentManager()
        agent = mgr.create_agent_from_profile(ORG_ID, RETAIL_PROFILE, AgentType.CUSTOMER)
        assert mgr.stop(agent.id)
        inst = mgr.registry.get_instance(agent.id)
        assert inst.status == AgentStatus.STOPPED

    def test_execute_paused_agent_fails(self):
        mgr = AgentManager()
        agent = mgr.create_agent_from_profile(ORG_ID, RETAIL_PROFILE, AgentType.SALES)
        mgr.pause(agent.id)
        result = mgr.execute(agent.id, "test", RETAIL_PROFILE)
        assert result.error is not None
        assert "paused" in result.error

    def test_performance(self):
        mgr = AgentManager()
        agent = mgr.create_agent_from_profile(ORG_ID, RETAIL_PROFILE, AgentType.SALES)
        mgr.execute(agent.id, "What's the revenue trend?", RETAIL_PROFILE)
        perf = mgr.get_performance(agent.id)
        assert perf["conversations"] == 1
        assert "memory_stats" in perf

    def test_different_industries_different_agents(self):
        mgr = AgentManager()
        retail_agents = mgr.create_agents_for_industry(ORG_ID, RETAIL_PROFILE)
        mfg_agents = mgr.create_agents_for_industry(ORG_ID, MANUFACTURING_PROFILE)
        retail_types = {a.spec.type for a in retail_agents}
        mfg_types = {a.spec.type for a in mfg_agents}
        # Retail has sales/inventory/customer, manufacturing has production/quality/maintenance
        assert AgentType.SALES in retail_types and AgentType.SALES not in mfg_types
        assert AgentType.PRODUCTION in mfg_types and AgentType.PRODUCTION not in retail_types


class TestAgentSupervisor:
    def test_orchestrate_revenue_query(self):
        mgr = AgentManager()
        sup = AgentSupervisor(manager=mgr)
        agents = mgr.create_agents_for_industry(ORG_ID, RETAIL_PROFILE)
        result = sup.orchestrate(ORG_ID, "Why did revenue drop?", agents, RETAIL_PROFILE)
        assert result.synthesized_response != ""
        assert len(result.contributing_agents) > 0
        # Should involve sales agent at minimum
        labels = [t.agent_label for t in result.delegated_tasks]
        assert any("Sales" in l for l in labels)

    def test_orchestrate_quality_query(self):
        mgr = AgentManager()
        sup = AgentSupervisor(manager=mgr)
        agents = mgr.create_agents_for_industry(ORG_ID, MANUFACTURING_PROFILE)
        result = sup.orchestrate(ORG_ID, "Why are defects increasing?", agents, MANUFACTURING_PROFILE)
        labels = [t.agent_label for t in result.delegated_tasks]
        assert any("Quality" in l for l in labels)

    def test_orchestrate_combines_multiple_agents(self):
        mgr = AgentManager()
        sup = AgentSupervisor(manager=mgr)
        agents = mgr.create_agents_for_industry(ORG_ID, RETAIL_PROFILE)
        result = sup.orchestrate(ORG_ID, "Why did revenue drop and how does it affect inventory?", agents, RETAIL_PROFILE)
        # Should involve multiple agents
        assert len(result.contributing_agents) >= 2

    def test_orchestrate_confidence(self):
        mgr = AgentManager()
        sup = AgentSupervisor(manager=mgr)
        agents = mgr.create_agents_for_industry(ORG_ID, RETAIL_PROFILE)
        result = sup.orchestrate(ORG_ID, "What's the sales trend?", agents, RETAIL_PROFILE)
        assert 0 <= result.confidence <= 1


class TestEvaluationLoop:
    def test_evaluate_action(self):
        loop = AgentEvaluationLoop()
        rec = loop.evaluate(
            "agent_1", ORG_ID, "Analyze revenue", "Revenue up 5%",
            accuracy=0.9, confidence=0.8, business_impact=0.7, human_approved=True,
        )
        assert rec.score > 0.7
        assert rec.feedback == ""

    def test_human_rejection_lowers_score(self):
        loop = AgentEvaluationLoop()
        rec_approved = loop.evaluate("a1", ORG_ID, "act", "outcome", 0.8, 0.8, 0.8, True)
        rec_rejected = loop.evaluate("a2", ORG_ID, "act", "outcome", 0.8, 0.8, 0.8, False)
        assert rec_approved.score > rec_rejected.score

    def test_performance_trend(self):
        loop = AgentEvaluationLoop()
        for i in range(5):
            loop.evaluate("a1", ORG_ID, f"action_{i}", f"outcome_{i}",
                          accuracy=0.5 + i * 0.1, confidence=0.8, business_impact=0.7)
        trend = loop.get_performance_trend("a1")
        assert trend["total_actions"] == 5
        assert trend["trend"] == "improving"

    def test_records_stored(self):
        loop = AgentEvaluationLoop()
        loop.evaluate("a1", ORG_ID, "act", "outcome", 0.8, 0.8, 0.8)
        records = loop.get_all_records("a1")
        assert len(records) == 1
        assert records[0]["action"] == "act"


class TestCrossIndustryDifferentiation:
    def test_retail_agent_monitors_revenue(self):
        mgr = AgentManager()
        agent = mgr.create_agent_from_profile(ORG_ID, RETAIL_PROFILE, AgentType.SALES)
        assert "Revenue" in agent.spec.kpis_monitored

    def test_manufacturing_agent_monitors_oee(self):
        mgr = AgentManager()
        agent = mgr.create_agent_from_profile(ORG_ID, MANUFACTURING_PROFILE, AgentType.PRODUCTION)
        assert "OEE" in agent.spec.kpis_monitored

    def test_same_type_different_industry_different_context(self):
        mgr = AgentManager()
        retail_agent = mgr.create_agent_from_profile(ORG_ID, RETAIL_PROFILE, AgentType.FINANCE)
        mfg_agent = mgr.create_agent_from_profile(ORG_ID, MANUFACTURING_PROFILE, AgentType.FINANCE)
        # Same agent type, but industry-specific KPIs differ
        retail_mem = mgr.get_memory(retail_agent.id, "long_term")
        mfg_mem = mgr.get_memory(mfg_agent.id, "long_term")
        retail_text = " ".join(m["content"] for m in retail_mem)
        mfg_text = " ".join(m["content"] for m in mfg_mem)
        assert "retail" in retail_text.lower()
        assert "manufacturing" in mfg_text.lower()

    def test_agent_tools_match_role(self):
        mgr = AgentManager()
        cfo_agent = mgr.create_agent_from_profile(ORG_ID, RETAIL_PROFILE, AgentType.FINANCE)
        # CFO agent should have forecast and simulation tools
        assert "forecast_tool" in cfo_agent.spec.tools
        assert "simulation_tool" in cfo_agent.spec.tools
