"""πX Integration Tests — Intelligence Profile integration scenarios."""
import pytest
from unittest.mock import AsyncMock, MagicMock
from packages.cognitive_kernel.intelligence_profile.industry_templates import IndustryTemplateRegistry
from packages.cognitive_kernel.intelligence_profile.profile_core import IntelligenceProfile
from packages.cognitive_kernel.intelligence_profile.context_provider import ProfileContextProvider


class TestScenario1Retail:
    def setup_method(self):
        self.columns = [
            {"name": "Cust Name", "sample_values": ["Acme Corp"], "dtype": "object"},
            {"name": "NET_REV", "sample_values": [12500], "dtype": "float64"},
            {"name": "Store", "sample_values": ["Store A"], "dtype": "object"},
        ]
        self.registry = IndustryTemplateRegistry()

    def test_heuristic_retail_detection(self):
        col_str = " ".join(c["name"].lower() for c in self.columns)
        assert "store" in col_str and "net_rev" in col_str

    def test_retail_template_entities(self):
        template = self.registry.get_template("retail")
        types = [e["entity_type"] for e in template.entities]
        assert "store" in types and "customer" in types and "product" in types

    def test_retail_template_kpis(self):
        template = self.registry.get_template("retail")
        names = [k["name"] for k in template.kpis]
        assert "revenue" in names and "sell_out" in names

    def test_retail_template_agents(self):
        template = self.registry.get_template("retail")
        assert any("Sales" in a["name"] for a in template.recommended_agents)

    def test_retail_customer_alias(self):
        template = self.registry.get_template("retail")
        for e in template.entities:
            if e["entity_type"] == "customer":
                assert "cust" in [a.lower() for a in e["aliases"]]

    def test_retail_glossary(self):
        template = self.registry.get_template("retail")
        assert "Sell-out" in [t["term"] for t in template.terminology]


class TestScenario2Manufacturing:
    def setup_method(self):
        self.columns = [
            {"name": "Machine_ID", "dtype": "object"},
            {"name": "Defect_Count", "dtype": "int64"},
            {"name": "Production_Time", "dtype": "float64"},
        ]
        self.registry = IndustryTemplateRegistry()

    def test_heuristic_manufacturing_detection(self):
        assert "production_time" in " ".join(c["name"].lower() for c in self.columns)

    def test_manufacturing_template_entities(self):
        template = self.registry.get_template("manufacturing")
        assert "equipment" in [e["entity_type"] for e in template.entities]

    def test_manufacturing_template_kpis(self):
        template = self.registry.get_template("manufacturing")
        names = [k["name"] for k in template.kpis]
        assert "oee" in names and "cycle_time" in names

    def test_manufacturing_agents(self):
        template = self.registry.get_template("manufacturing")
        assert any("Production" in a["name"] for a in template.recommended_agents)

    def test_manufacturing_equipment_alias(self):
        template = self.registry.get_template("manufacturing")
        for e in template.entities:
            if e["entity_type"] == "equipment":
                assert "machine" in [a.lower() for a in e["aliases"]]

    def test_different_from_retail(self):
        mfg = {e["entity_type"] for e in self.registry.get_template("manufacturing").entities}
        retail = {e["entity_type"] for e in self.registry.get_template("retail").entities}
        assert mfg != retail
        assert "equipment" in mfg and "store" in retail


class TestProfileContextProvider:
    def test_empty_context(self):
        ctx = ProfileContextProvider._empty_context("org")
        assert ctx["profile_id"] is None
        assert ctx["ontology"] == [] and ctx["kpis"] == []

    def test_cache_invalidation(self):
        provider = ProfileContextProvider.__new__(ProfileContextProvider)
        provider._cache = {"org1": {}, "org2": {}}
        provider._cache_ttl_seconds = 300
        provider.invalidate_cache("org1")
        assert "org1" not in provider._cache and "org2" in provider._cache
        provider.invalidate_cache()
        assert len(provider._cache) == 0


class TestAgentFactory:
    def test_retail_agent(self):
        from packages.cognitive_kernel.agent_runtime.agent_factory import AgentFactory
        factory = AgentFactory()
        t = IndustryTemplateRegistry().get_template("retail")
        ctx = {
            "profile_id": "t", "company_identity": {"industry": "retail"},
            "ontology": [{"entity_type": e["entity_type"], "aliases": e.get("aliases", [])} for e in t.entities],
            "kpis": [{"name": k["name"]} for k in t.kpis],
            "glossary": [], "agents": t.recommended_agents, "ai_preferences": {},
        }
        agent = factory._build_agent(t.recommended_agents[0], ctx, "org")
        assert agent["industry"] == "retail"
        assert "query_kpis" in [tool["name"] for tool in agent["tools"]]

    def test_manufacturing_agent(self):
        from packages.cognitive_kernel.agent_runtime.agent_factory import AgentFactory
        factory = AgentFactory()
        t = IndustryTemplateRegistry().get_template("manufacturing")
        ctx = {
            "profile_id": "t", "company_identity": {"industry": "manufacturing"},
            "ontology": [{"entity_type": e["entity_type"], "aliases": e.get("aliases", [])} for e in t.entities],
            "kpis": [{"name": k["name"]} for k in t.kpis],
            "glossary": [], "agents": t.recommended_agents, "ai_preferences": {},
        }
        agent = factory._build_agent(t.recommended_agents[0], ctx, "org")
        assert agent["industry"] == "manufacturing"
        assert "oee" in agent["kpis_monitored"]
        assert "monitor_production" in [tool["name"] for tool in agent["tools"]]

    def test_base_tools(self):
        from packages.cognitive_kernel.agent_runtime.agent_factory import AgentFactory
        factory = AgentFactory()
        ctx = {"profile_id": "t", "company_identity": {"industry": "generic"}, "ontology": [], "kpis": [], "glossary": [], "agents": [], "ai_preferences": {}}
        agent = factory._build_agent({"name": "T", "role": "analyst"}, ctx, "org")
        names = [t["name"] for t in agent["tools"]]
        assert "query_memory" in names and "create_decision" in names


class TestProfileAwareIngestion:
    def test_detect_retail_entities(self):
        from packages.cognitive_kernel.ingestion.profile_aware_pipeline import ProfileAwareIngestionPipeline
        p = ProfileAwareIngestionPipeline.__new__(ProfileAwareIngestionPipeline)
        t = IndustryTemplateRegistry().get_template("retail")
        ctx = {"ontology": t.entities, "glossary": []}
        detected = p._detect_entities([{"name": "Cust Name"}, {"name": "Store"}], ctx, {})
        types = [d["entity_type"] for d in detected]
        assert "customer" in types and "store" in types

    def test_detect_manufacturing_entities(self):
        from packages.cognitive_kernel.ingestion.profile_aware_pipeline import ProfileAwareIngestionPipeline
        p = ProfileAwareIngestionPipeline.__new__(ProfileAwareIngestionPipeline)
        t = IndustryTemplateRegistry().get_template("manufacturing")
        ctx = {"ontology": t.entities, "glossary": []}
        detected = p._detect_entities([{"name": "Machine_ID"}], ctx, {})
        assert "equipment" in [d["entity_type"] for d in detected]

    def test_business_context_includes_industry(self):
        from packages.cognitive_kernel.ingestion.profile_aware_pipeline import ProfileAwareIngestionPipeline
        p = ProfileAwareIngestionPipeline.__new__(ProfileAwareIngestionPipeline)
        ctx = {"company_identity": {"industry": "retail"}, "glossary": [], "kpis": [{"name": "revenue"}]}
        result = p._build_business_context(ctx)
        assert "retail" in result


class TestProfileAwareAIGateway:
    @pytest.mark.asyncio
    async def test_private_routes_local(self):
        from packages.cognitive_kernel.ai_gateway.profile_aware_gateway import ProfileAwareAIGateway
        from packages.cognitive_kernel.ai_gateway.providers.base import GenerateRequest
        mock_gw = AsyncMock()
        mock_gw.generate = AsyncMock(return_value=MagicMock(content="x"))
        mock_prov = AsyncMock()
        mock_prov.get_ai_policy = AsyncMock(return_value={"privacy_level": "private", "preferred_models": {"primary": "ollama:llama3"}, "data_sensitivity": "high"})
        gw = ProfileAwareAIGateway(gateway=mock_gw, context_provider=mock_prov)
        req = GenerateRequest(prompt="test")
        await gw.generate(req, "org")
        assert req.provider == "ollama" and req.model == "ollama:llama3"

    @pytest.mark.asyncio
    async def test_standard_uses_preferred(self):
        from packages.cognitive_kernel.ai_gateway.profile_aware_gateway import ProfileAwareAIGateway
        from packages.cognitive_kernel.ai_gateway.providers.base import GenerateRequest
        mock_gw = AsyncMock()
        mock_gw.generate = AsyncMock(return_value=MagicMock(content="x"))
        mock_prov = AsyncMock()
        mock_prov.get_ai_policy = AsyncMock(return_value={"privacy_level": "standard", "preferred_models": {"primary": "openai:gpt-4o"}})
        gw = ProfileAwareAIGateway(gateway=mock_gw, context_provider=mock_prov)
        req = GenerateRequest(prompt="test")
        await gw.generate(req, "org")
        assert req.model == "openai:gpt-4o"
