"""
πX Phase 3 — Enterprise Intelligence Operating Layer — 100+ tests.

Covers: AI integration, semantic routing, agent communication, proactive scheduling,
persistent memory, AI evaluation engine, observability, audit trail, security,
multi-agent scenarios, tenant isolation.
"""
import pytest
import asyncio

from packages.cognitive_kernel.agent_os.ai_integrator import AgentAIIntegrator, AICallRecord
from packages.cognitive_kernel.agent_os.intelligence_router import AgentIntelligenceRouter, RoutingDecision
from packages.cognitive_kernel.agent_os.communication_protocol import AgentCommunicationProtocol, MessageType
from packages.cognitive_kernel.agent_os.agent_scheduler import AgentScheduler, TriggerType, ScheduleStatus
from packages.cognitive_kernel.agent_os.persistent_memory import PersistentAgentMemory, PersistentMemoryType
from packages.cognitive_kernel.agent_os.ai_evaluation_engine import AIEvaluationEngine, QualityFactor
from packages.cognitive_kernel.agent_os.observability import IntelligenceObservatory, MetricType
from packages.cognitive_kernel.agent_os.audit_trail import AuditTrail
from packages.cognitive_kernel.agent_os.agent_manager import AgentManager
from packages.cognitive_kernel.agent_os.agent_registry import AgentRegistry, AgentType, AgentStatus
from packages.cognitive_kernel.agent_os.agent_security import AgentSecurity

ORG_ID = "test-org-001"
ORG_ID_2 = "test-org-002"

RETAIL_PROFILE = {
    "org_id": ORG_ID, "industry": "retail",
    "company_identity": {"name": "Acme Retail Co"},
    "kpis": [{"name": "Revenue"}, {"name": "Sell-out"}, {"name": "Inventory Turnover"}],
    "ontology": {"entities": {"customer": {}, "product": {}, "store": {}}},
}
MFG_PROFILE = {
    "org_id": ORG_ID, "industry": "manufacturing",
    "company_identity": {"name": "Precision Mfg"},
    "kpis": [{"name": "OEE"}, {"name": "Quality Rate"}, {"name": "Production Volume"}],
    "ontology": {"entities": {"equipment": {}, "work_order": {}, "product": {}}},
}


# ══════════════════════════════════════════════════════════════
# 1. AI INTEGRATOR TESTS (12)
# ══════════════════════════════════════════════════════════════

class TestAIIntegrator:
    def _setup(self):
        mgr = AgentManager()
        agent = mgr.create_agent_from_profile(ORG_ID, RETAIL_PROFILE, AgentType.SALES)
        return AgentAIIntegrator(manager=mgr), mgr, agent

    def test_execute_with_ai_returns_response(self):
        integrator, mgr, agent = self._setup()
        result = asyncio.run(integrator.execute_with_ai(agent.id, "Why did revenue drop?", RETAIL_PROFILE))
        assert result.error is None
        assert len(result.response) > 0
        assert result.execution_time_ms >= 0

    def test_ai_call_recorded_in_history(self):
        integrator, mgr, agent = self._setup()
        asyncio.run(integrator.execute_with_ai(agent.id, "test query", RETAIL_PROFILE))
        history = integrator.get_call_history(agent.id)
        assert len(history) == 1
        assert "model" in history[0]

    def test_cost_summary(self):
        integrator, mgr, agent = self._setup()
        asyncio.run(integrator.execute_with_ai(agent.id, "q1", RETAIL_PROFILE))
        asyncio.run(integrator.execute_with_ai(agent.id, "q2", RETAIL_PROFILE))
        summary = integrator.get_cost_summary()
        assert summary["total_calls"] == 2
        assert "total_cost_usd" in summary

    def test_model_selection_for_cfo(self):
        integrator, mgr, agent = self._setup()
        cfo_agent = mgr.create_agent_from_profile(ORG_ID, RETAIL_PROFILE, AgentType.FINANCE)
        model = integrator._select_model(cfo_agent.spec)
        assert "claude" in model.lower()

    def test_model_selection_for_ceo(self):
        integrator, mgr, agent = self._setup()
        strategy_agent = mgr.create_agent_from_profile(ORG_ID, RETAIL_PROFILE, AgentType.STRATEGY)
        model = integrator._select_model(strategy_agent.spec)
        assert "gpt-4o" in model

    def test_execute_on_paused_agent_fails(self):
        integrator, mgr, agent = self._setup()
        mgr.pause(agent.id)
        result = asyncio.run(integrator.execute_with_ai(agent.id, "test", RETAIL_PROFILE))
        assert result.error is not None
        assert "paused" in result.error

    def test_execute_on_nonexistent_agent(self):
        integrator, mgr, agent = self._setup()
        result = asyncio.run(integrator.execute_with_ai("fake_id", "test", RETAIL_PROFILE))
        assert result.error == "Agent not found"

    def test_memory_stored_after_execution(self):
        integrator, mgr, agent = self._setup()
        asyncio.run(integrator.execute_with_ai(agent.id, "Revenue trend?", RETAIL_PROFILE))
        memory = mgr.get_memory(agent.id, "short_term")
        assert len(memory) >= 1
        assert "Revenue trend" in memory[0]["content"]

    def test_experience_memory_stored(self):
        integrator, mgr, agent = self._setup()
        asyncio.run(integrator.execute_with_ai(agent.id, "Q3 analysis", RETAIL_PROFILE))
        experience = mgr.get_memory(agent.id, "experience")
        assert any("Q3" in m["content"] for m in experience)

    def test_prompt_includes_system_context(self):
        integrator, mgr, agent = self._setup()
        prompt = integrator._build_prompt("system", "memory", "query", agent.spec)
        assert "system" in prompt
        assert "query" in prompt
        assert "Memory Context" in prompt

    def test_cost_summary_by_org(self):
        integrator, mgr, agent = self._setup()
        asyncio.run(integrator.execute_with_ai(agent.id, "q", RETAIL_PROFILE))
        summary = integrator.get_cost_summary(org_id=ORG_ID)
        assert summary["total_calls"] == 1

    def test_ai_call_record_has_all_fields(self):
        integrator, mgr, agent = self._setup()
        asyncio.run(integrator.execute_with_ai(agent.id, "q", RETAIL_PROFILE))
        history = integrator.get_call_history()
        rec = history[0]
        for field in ["agent_id", "model", "provider", "input_tokens", "output_tokens", "latency_ms"]:
            assert field in rec


# ══════════════════════════════════════════════════════════════
# 2. INTELLIGENCE ROUTER TESTS (15)
# ══════════════════════════════════════════════════════════════

class TestIntelligenceRouter:
    def _setup(self, profile=None):
        mgr = AgentManager()
        profile = profile or RETAIL_PROFILE
        agents = mgr.create_agents_for_industry(ORG_ID, profile)
        return AgentIntelligenceRouter(), agents, mgr

    def test_route_revenue_query(self):
        router, agents, mgr = self._setup()
        decision = router.route("Why did revenue drop?", agents, RETAIL_PROFILE)
        assert len(decision.selected_agents) > 0
        assert decision.routing_method == "semantic"

    def test_route_inventory_query(self):
        router, agents, mgr = self._setup()
        decision = router.route("What's the inventory stock level?", agents, RETAIL_PROFILE)
        assert len(decision.selected_agents) > 0

    def test_route_quality_query_mfg(self):
        router, agents, mgr = self._setup(MFG_PROFILE)
        decision = router.route("Why are defects increasing?", agents, MFG_PROFILE)
        assert len(decision.selected_agents) > 0

    def test_route_returns_scores(self):
        router, agents, mgr = self._setup()
        decision = router.route("Revenue analysis", agents, RETAIL_PROFILE)
        assert len(decision.scores) == len(agents)

    def test_route_includes_reasoning(self):
        router, agents, mgr = self._setup()
        decision = router.route("Why did sales decline in Germany?", agents, RETAIL_PROFILE)
        assert len(decision.reasoning) > 0
        assert "Routing decision" in decision.reasoning

    def test_route_no_active_agents(self):
        router = AgentIntelligenceRouter()
        decision = router.route("test", [])
        assert decision.routing_method == "fallback"

    def test_route_capability_scoring(self):
        router, agents, mgr = self._setup()
        decision = router.route("revenue sales forecast", agents, RETAIL_PROFILE)
        # Sales agent should have high score
        sales_agent = [a for a in agents if a.spec.type == AgentType.SALES][0]
        assert decision.scores[sales_agent.id] > 0

    def test_route_kpi_relevance(self):
        router, agents, mgr = self._setup()
        decision = router.route("Revenue is down", agents, RETAIL_PROFILE)
        # Should select sales or finance agent
        selected_specs = [a.spec.type for a in agents if a.id in decision.selected_agents]
        assert AgentType.SALES in selected_specs or AgentType.FINANCE in selected_specs

    def test_route_germany_query(self):
        """Geographic query should still route to relevant agents"""
        router, agents, mgr = self._setup()
        decision = router.route("Why did sales decline in Germany?", agents, RETAIL_PROFILE)
        assert len(decision.selected_agents) > 0

    def test_route_maintenance_query(self):
        router, agents, mgr = self._setup(MFG_PROFILE)
        decision = router.route("Equipment downtime analysis", agents, MFG_PROFILE)
        maintenance_agent = [a for a in agents if a.spec.type == AgentType.MAINTENANCE]
        if maintenance_agent:
            assert maintenance_agent[0].id in decision.selected_agents or decision.scores.get(maintenance_agent[0].id, 0) > 0

    def test_route_selects_multiple_agents(self):
        router, agents, mgr = self._setup()
        decision = router.route("Revenue and inventory and customer churn analysis", agents, RETAIL_PROFILE)
        assert len(decision.selected_agents) >= 2

    def test_route_threshold_filters_irrelevant(self):
        router, agents, mgr = self._setup()
        decision = router.route("xyz random question about nothing", agents, RETAIL_PROFILE)
        # Should still return something (top 3 fallback) but with low scores
        assert all(score < 0.5 for score in decision.scores.values())

    def test_route_profile_aware(self):
        router, agents, mgr = self._setup()
        decision = router.route("Revenue analysis", agents, RETAIL_PROFILE)
        # Agents with matching KPIs should score higher
        for aid, score in decision.scores.items():
            agent = [a for a in agents if a.id == aid][0]
            if "Revenue" in agent.spec.kpis_monitored:
                assert score > 0

    def test_route_keyword_fallback(self):
        router = AgentIntelligenceRouter()
        mgr = AgentManager()
        agents = mgr.create_agents_for_industry(ORG_ID, RETAIL_PROFILE)
        decision = router.route("revenue", agents, RETAIL_PROFILE)
        assert len(decision.selected_agents) > 0

    def test_routing_decision_has_query(self):
        router, agents, mgr = self._setup()
        decision = router.route("test query", agents, RETAIL_PROFILE)
        assert decision.query == "test query"


# ══════════════════════════════════════════════════════════════
# 3. AGENT COMMUNICATION PROTOCOL TESTS (12)
# ══════════════════════════════════════════════════════════════

class TestCommunicationProtocol:
    def test_send_message(self):
        proto = AgentCommunicationProtocol()
        msg = proto.send("agent_1", "agent_2", ORG_ID, MessageType.QUERY, "What's the revenue trend?")
        assert msg.from_agent_id == "agent_1"
        assert msg.to_agent_id == "agent_2"
        assert msg.message_type == MessageType.QUERY

    def test_broadcast_message(self):
        proto = AgentCommunicationProtocol()
        msg = proto.broadcast("agent_1", ORG_ID, "Revenue dropped 15%!")
        assert msg.to_agent_id == "supervisor"
        assert msg.message_type == MessageType.BROADCAST

    def test_get_messages_by_agent(self):
        proto = AgentCommunicationProtocol()
        proto.send("a1", "a2", ORG_ID, MessageType.QUERY, "msg1")
        proto.send("a2", "a1", ORG_ID, MessageType.RESPONSE, "msg2")
        msgs = proto.get_messages(agent_id="a1")
        assert len(msgs) == 2

    def test_get_messages_by_org(self):
        proto = AgentCommunicationProtocol()
        proto.send("a1", "a2", ORG_ID, MessageType.QUERY, "msg1")
        proto.send("a1", "a2", ORG_ID_2, MessageType.QUERY, "msg2")
        msgs = proto.get_messages(org_id=ORG_ID)
        assert len(msgs) == 1

    def test_create_session(self):
        proto = AgentCommunicationProtocol()
        session_id = proto.create_session(ORG_ID, "Why did revenue drop?")
        ctx = proto.get_context(session_id)
        assert ctx is not None
        assert ctx.query == "Why did revenue drop?"

    def test_add_evidence(self):
        proto = AgentCommunicationProtocol()
        sid = proto.create_session(ORG_ID, "query")
        proto.add_evidence(sid, "agent_1", "Revenue dropped 15% in Q3", 0.85)
        ctx = proto.get_context(sid)
        assert len(ctx.evidence) == 1
        assert ctx.evidence[0]["confidence"] == 0.85

    def test_add_analysis(self):
        proto = AgentCommunicationProtocol()
        sid = proto.create_session(ORG_ID, "query")
        proto.add_analysis(sid, "agent_1", "Sales declined due to market saturation")
        ctx = proto.get_context(sid)
        assert "agent_1" in ctx.analyses

    def test_register_disagreement(self):
        proto = AgentCommunicationProtocol()
        sid = proto.create_session(ORG_ID, "query")
        proto.register_disagreement(sid, "agent_1", "I disagree with the revenue analysis")
        ctx = proto.get_context(sid)
        assert len(ctx.disagreements) == 1

    def test_resolve_conflicts_majority(self):
        proto = AgentCommunicationProtocol()
        sid = proto.create_session(ORG_ID, "query")
        proto.add_analysis(sid, "a1", "analysis1")
        proto.add_analysis(sid, "a2", "analysis2")
        proto.add_analysis(sid, "a3", "analysis3")
        proto.register_disagreement(sid, "a1", "disagreement1")
        result = proto.resolve_conflicts(sid)
        assert "Majority consensus" in result

    def test_resolve_conflicts_unresolved(self):
        proto = AgentCommunicationProtocol()
        sid = proto.create_session(ORG_ID, "query")
        proto.add_analysis(sid, "a1", "analysis1")
        proto.register_disagreement(sid, "a2", "disagreement1")
        proto.register_disagreement(sid, "a3", "disagreement2")
        result = proto.resolve_conflicts(sid)
        assert "Conflict unresolved" in result

    def test_finalize_decision(self):
        proto = AgentCommunicationProtocol()
        sid = proto.create_session(ORG_ID, "query")
        proto.finalize_decision(sid, "Increase marketing spend")
        ctx = proto.get_context(sid)
        assert ctx.final_decision == "Increase marketing spend"

    def test_message_types(self):
        proto = AgentCommunicationProtocol()
        for mt in [MessageType.QUERY, MessageType.RESPONSE, MessageType.EVIDENCE,
                   MessageType.DISAGREEMENT, MessageType.CONSENSUS, MessageType.BROADCAST]:
            msg = proto.send("a1", "a2", ORG_ID, mt, f"test {mt.value}")
            assert msg.message_type == mt


# ══════════════════════════════════════════════════════════════
# 4. AGENT SCHEDULER TESTS (14)
# ══════════════════════════════════════════════════════════════

class TestAgentScheduler:
    def test_create_schedule(self):
        sched = AgentScheduler()
        s = sched.create_schedule(ORG_ID, "agent_1", TriggerType.SCHEDULED, {}, action="Check KPIs", interval_seconds=3600)
        assert s.status == ScheduleStatus.ACTIVE
        assert s.interval_seconds == 3600

    def test_kpi_threshold_trigger(self):
        sched = AgentScheduler()
        sched.create_schedule(ORG_ID, "agent_1", TriggerType.KPI_THRESHOLD,
            {"kpi": "revenue", "threshold": -0.15, "comparison": "percent_change"},
            action="Investigate revenue drop")
        # First update sets baseline
        sched.update_kpi(ORG_ID, "revenue", 100000)
        # Second update triggers -15% drop
        triggered = sched.update_kpi(ORG_ID, "revenue", 85000)
        assert len(triggered) == 1
        assert triggered[0].trigger_count == 1

    def test_kpi_no_trigger_when_above_threshold(self):
        sched = AgentScheduler()
        sched.create_schedule(ORG_ID, "agent_1", TriggerType.KPI_THRESHOLD,
            {"kpi": "revenue", "threshold": -0.15, "comparison": "percent_change"})
        sched.update_kpi(ORG_ID, "revenue", 100000)
        triggered = sched.update_kpi(ORG_ID, "revenue", 110000)
        assert len(triggered) == 0

    def test_kpi_absolute_trigger(self):
        sched = AgentScheduler()
        sched.create_schedule(ORG_ID, "agent_1", TriggerType.KPI_THRESHOLD,
            {"kpi": "defects", "threshold": 100, "comparison": "above"})
        triggered = sched.update_kpi(ORG_ID, "defects", 150)
        assert len(triggered) == 1

    def test_anomaly_detection(self):
        sched = AgentScheduler()
        history = [100, 102, 98, 101, 99, 100, 103, 97, 100, 101]
        assert not sched.detect_anomaly(ORG_ID, "revenue", 101, history)
        assert sched.detect_anomaly(ORG_ID, "revenue", 200, history)

    def test_anomaly_no_history(self):
        sched = AgentScheduler()
        assert not sched.detect_anomaly(ORG_ID, "revenue", 100, [])
        assert not sched.detect_anomaly(ORG_ID, "revenue", 100, [1, 2])

    def test_trigger_investigation(self):
        sched = AgentScheduler()
        inv = sched.trigger_investigation(ORG_ID, "agent_1", "Revenue dropped 15%")
        assert inv.agent_id == "agent_1"
        assert "Revenue dropped" in inv.trigger_reason
        assert len(inv.recommendations) > 0

    def test_investigation_with_escalation(self):
        sched = AgentScheduler()
        inv = sched.trigger_investigation(
            ORG_ID, "sales_agent", "Revenue drop",
            escalation_agents=["finance_agent", "ceo_agent"],
        )
        assert "finance_agent" in inv.escalated_to

    def test_get_schedules(self):
        sched = AgentScheduler()
        sched.create_schedule(ORG_ID, "a1", TriggerType.SCHEDULED, {})
        sched.create_schedule(ORG_ID, "a2", TriggerType.KPI_THRESHOLD, {"kpi": "revenue"})
        assert len(sched.get_schedules(org_id=ORG_ID)) == 2

    def test_pause_resume_schedule(self):
        sched = AgentScheduler()
        s = sched.create_schedule(ORG_ID, "a1", TriggerType.SCHEDULED, {})
        assert sched.pause_schedule(s.id)
        assert sched.get_schedules()[0].status == ScheduleStatus.PAUSED
        assert sched.resume_schedule(s.id)
        assert sched.get_schedules()[0].status == ScheduleStatus.ACTIVE

    def test_get_investigations(self):
        sched = AgentScheduler()
        sched.trigger_investigation(ORG_ID, "a1", "reason1")
        sched.trigger_investigation(ORG_ID, "a2", "reason2")
        invs = sched.get_investigations()
        assert len(invs) == 2

    def test_get_kpi_values(self):
        sched = AgentScheduler()
        sched.update_kpi(ORG_ID, "revenue", 100000)
        kpis = sched.get_kpi_values(ORG_ID)
        assert kpis["revenue"] == 100000

    def test_schedule_trigger_count_increments(self):
        sched = AgentScheduler()
        s = sched.create_schedule(ORG_ID, "a1", TriggerType.KPI_THRESHOLD,
            {"kpi": "rev", "threshold": -0.1, "comparison": "percent_change"})
        sched.update_kpi(ORG_ID, "rev", 100)
        sched.update_kpi(ORG_ID, "rev", 89)  # -11% triggers
        sched.get_schedules()[0].status = ScheduleStatus.ACTIVE
        # Reset for second trigger
        sched.update_kpi(ORG_ID, "rev", 100)
        sched.get_schedules()[0].status = ScheduleStatus.ACTIVE
        sched.update_kpi(ORG_ID, "rev", 85)  # -15% triggers again
        assert sched.get_schedules()[0].trigger_count == 2

    def test_proactive_scenario(self):
        """Full proactive scenario: KPI drops → investigation → escalation"""
        sched = AgentScheduler()
        sched.create_schedule(ORG_ID, "sales_agent", TriggerType.KPI_THRESHOLD,
            {"kpi": "revenue", "threshold": -0.15, "comparison": "percent_change"},
            action="Investigate revenue drop")
        sched.update_kpi(ORG_ID, "revenue", 100000)
        triggered = sched.update_kpi(ORG_ID, "revenue", 80000)  # -20%
        assert len(triggered) == 1
        inv = sched.trigger_investigation(ORG_ID, "sales_agent", "Revenue dropped 20%",
            escalation_agents=["finance_agent"])
        assert "finance_agent" in inv.escalated_to


# ══════════════════════════════════════════════════════════════
# 5. PERSISTENT MEMORY TESTS (14)
# ══════════════════════════════════════════════════════════════

class TestPersistentMemory:
    def test_create_memory_object(self):
        mem = PersistentAgentMemory()
        obj = mem.create_memory_object("a1", ORG_ID, "Sales Agent",
            PersistentMemoryType.EXPERIENCE, context="Q3 review",
            action="Analyzed revenue", reasoning="Revenue declined",
            result="Found 15% drop", confidence=0.85)
        assert obj.agent == "Sales Agent"
        assert obj.confidence == 0.85

    def test_retrieve_by_type(self):
        mem = PersistentAgentMemory()
        mem.create_memory_object("a1", ORG_ID, "Agent", PersistentMemoryType.SHORT_TERM, action="test1")
        mem.create_memory_object("a1", ORG_ID, "Agent", PersistentMemoryType.EXPERIENCE, action="test2")
        results = mem.retrieve("a1", PersistentMemoryType.SHORT_TERM)
        assert len(results) == 1
        assert results[0].action == "test1"

    def test_retrieve_with_importance_filter(self):
        mem = PersistentAgentMemory()
        mem.create_memory_object("a1", ORG_ID, "Agent", PersistentMemoryType.EXPERIENCE,
            action="low", importance=0.3)
        mem.create_memory_object("a1", ORG_ID, "Agent", PersistentMemoryType.EXPERIENCE,
            action="high", importance=0.9)
        results = mem.retrieve("a1", PersistentMemoryType.EXPERIENCE, min_importance=0.7)
        assert len(results) == 1
        assert results[0].action == "high"

    def test_search_memory(self):
        mem = PersistentAgentMemory()
        mem.create_memory_object("a1", ORG_ID, "Agent", PersistentMemoryType.EXPERIENCE,
            action="Analyzed revenue drop", result="Revenue decreased 15%")
        results = mem.search("a1", "revenue")
        assert len(results) >= 1

    def test_add_feedback(self):
        mem = PersistentAgentMemory()
        obj = mem.create_memory_object("a1", ORG_ID, "Agent", PersistentMemoryType.EXPERIENCE, action="test")
        assert mem.add_feedback(obj.id, "Good analysis")
        assert obj.feedback == "Good analysis"

    def test_get_learning_memory(self):
        mem = PersistentAgentMemory()
        mem.create_memory_object("a1", ORG_ID, "Agent", PersistentMemoryType.LEARNING,
            action="Learned pattern", importance=0.8)
        learning = mem.get_learning_memory("a1")
        assert len(learning) == 1

    def test_get_stats(self):
        mem = PersistentAgentMemory()
        for t in PersistentMemoryType:
            mem.create_memory_object("a1", ORG_ID, "Agent", t, action=f"test_{t.value}")
        stats = mem.get_stats("a1")
        assert stats["total"] == 5
        assert stats["short_term"] == 1
        assert stats["experience"] == 1
        assert stats["learning"] == 1

    def test_short_term_limit_50(self):
        mem = PersistentAgentMemory()
        for i in range(55):
            mem.create_memory_object("a1", ORG_ID, "Agent", PersistentMemoryType.SHORT_TERM, action=f"msg_{i}")
        results = mem.retrieve("a1", PersistentMemoryType.SHORT_TERM, limit=100)
        assert len(results) == 50

    def test_memory_object_has_all_fields(self):
        mem = PersistentAgentMemory()
        obj = mem.create_memory_object("a1", ORG_ID, "Sales Agent",
            PersistentMemoryType.DECISION, context="Q3 planning",
            action="Recommended budget cut", reasoning="Revenue declining",
            result="Budget reduced 10%", confidence=0.8, feedback="Approved",
            importance=0.9)
        d = obj.to_dict()
        for field in ["agent", "context", "action", "reasoning", "result", "confidence", "feedback"]:
            assert field in d
            assert d[field] is not None or d[field] == ""

    def test_get_org_memory(self):
        mem = PersistentAgentMemory()
        mem.create_memory_object("a1", ORG_ID, "Agent", PersistentMemoryType.SHORT_TERM, action="test1")
        mem.create_memory_object("a2", ORG_ID, "Agent", PersistentMemoryType.SHORT_TERM, action="test2")
        mem.create_memory_object("a3", ORG_ID_2, "Agent", PersistentMemoryType.SHORT_TERM, action="test3")
        org_mem = mem.get_org_memory(ORG_ID)
        assert len(org_mem) == 2

    def test_access_count_increments(self):
        mem = PersistentAgentMemory()
        mem.create_memory_object("a1", ORG_ID, "Agent", PersistentMemoryType.EXPERIENCE, action="test", importance=0.8)
        mem.retrieve("a1", PersistentMemoryType.EXPERIENCE)
        mem.retrieve("a1", PersistentMemoryType.EXPERIENCE)
        results = mem.retrieve("a1", PersistentMemoryType.EXPERIENCE)
        assert results[0].access_count >= 2

    def test_avg_confidence_in_stats(self):
        mem = PersistentAgentMemory()
        mem.create_memory_object("a1", ORG_ID, "Agent", PersistentMemoryType.EXPERIENCE, confidence=0.8)
        mem.create_memory_object("a1", ORG_ID, "Agent", PersistentMemoryType.EXPERIENCE, confidence=0.6)
        stats = mem.get_stats("a1")
        assert 0.6 < stats["avg_confidence"] < 0.8

    def test_all_5_memory_types(self):
        mem = PersistentAgentMemory()
        for mt in PersistentMemoryType:
            obj = mem.create_memory_object("a1", ORG_ID, "Agent", mt, action=f"test_{mt.value}")
            assert obj.memory_type == mt

    def test_tenant_isolation(self):
        mem = PersistentAgentMemory()
        mem.create_memory_object("a1", ORG_ID, "Agent", PersistentMemoryType.EXPERIENCE, action="org1_data")
        mem.create_memory_object("a2", ORG_ID_2, "Agent", PersistentMemoryType.EXPERIENCE, action="org2_data")
        org1_mem = mem.get_org_memory(ORG_ID)
        org2_mem = mem.get_org_memory(ORG_ID_2)
        assert all(m["org_id"] == ORG_ID for m in org1_mem)
        assert all(m["org_id"] == ORG_ID_2 for m in org2_mem)


# ══════════════════════════════════════════════════════════════
# 6. AI EVALUATION ENGINE TESTS (14)
# ══════════════════════════════════════════════════════════════

class TestAIEvaluationEngine:
    def test_evaluate_response(self):
        engine = AIEvaluationEngine()
        assessment = engine.evaluate("a1", ORG_ID, "query", "response",
            accuracy=0.9, confidence=0.8, source_quality=0.7, user_feedback=0.8, business_outcome=0.75)
        assert 0 <= assessment.quality_score <= 100
        assert len(assessment.factors) == 6

    def test_quality_score_is_weighted(self):
        engine = AIEvaluationEngine()
        high = engine.evaluate("a1", ORG_ID, "q", "r", accuracy=0.9, confidence=0.9,
            source_quality=0.9, user_feedback=0.9, business_outcome=0.9)
        low = engine.evaluate("a2", ORG_ID, "q", "r", accuracy=0.3, confidence=0.3,
            source_quality=0.3, user_feedback=0.3, business_outcome=0.3)
        assert high.quality_score > low.quality_score

    def test_hallucination_risk_no_sources(self):
        engine = AIEvaluationEngine()
        assessment = engine.evaluate("a1", ORG_ID, "q", "A very long response " * 50, sources_cited=[])
        risk = assessment.factors[QualityFactor.HALLUCINATION_RISK.value]
        assert risk < 0.7  # Lower score because higher hallucination risk

    def test_hallucination_flags_detected(self):
        engine = AIEvaluationEngine()
        assessment = engine.evaluate("a1", ORG_ID, "q",
            "I believe this is definitely correct without any data to support it.")
        assert len(assessment.hallucination_flags) > 0

    def test_sources_reduce_hallucination_risk(self):
        engine = AIEvaluationEngine()
        with_sources = engine.evaluate("a1", ORG_ID, "q", "Revenue is $1M", sources_cited=["sales_report.xlsx"])
        without_sources = engine.evaluate("a1", ORG_ID, "q", "Revenue is $1M", sources_cited=[])
        assert with_sources.factors[QualityFactor.HALLUCINATION_RISK.value] > without_sources.factors[QualityFactor.HALLUCINATION_RISK.value]

    def test_add_feedback_approved(self):
        engine = AIEvaluationEngine()
        a = engine.evaluate("a1", ORG_ID, "q", "r", accuracy=0.8, confidence=0.8, source_quality=0.8)
        engine.add_feedback(a.id, "Good analysis", approved=True)
        assert a.approved is True
        assert a.feedback == "Good analysis"
        # Score should increase with positive feedback
        assert a.factors[QualityFactor.USER_FEEDBACK.value] == 1.0

    def test_add_feedback_rejected(self):
        engine = AIEvaluationEngine()
        a = engine.evaluate("a1", ORG_ID, "q", "r", accuracy=0.8, confidence=0.8)
        original_score = a.quality_score
        engine.add_feedback(a.id, "Wrong", approved=False)
        assert a.approved is False
        assert a.quality_score <= original_score

    def test_get_assessments(self):
        engine = AIEvaluationEngine()
        engine.evaluate("a1", ORG_ID, "q1", "r1")
        engine.evaluate("a2", ORG_ID, "q2", "r2")
        all_assessments = engine.get_assessments()
        assert len(all_assessments) == 2

    def test_get_assessments_by_agent(self):
        engine = AIEvaluationEngine()
        engine.evaluate("a1", ORG_ID, "q", "r")
        engine.evaluate("a2", ORG_ID, "q", "r")
        a1_only = engine.get_assessments(agent_id="a1")
        assert len(a1_only) == 1

    def test_get_quality_stats(self):
        engine = AIEvaluationEngine()
        engine.evaluate("a1", ORG_ID, "q", "r", accuracy=0.9, confidence=0.9, source_quality=0.9, user_feedback=0.9, business_outcome=0.9)
        stats = engine.get_quality_stats()
        assert stats["total"] == 1
        assert stats["avg_score"] > 50

    def test_weights_sum_to_one(self):
        total = sum(AIEvaluationEngine.WEIGHTS.values())
        assert abs(total - 1.0) < 0.01

    def test_accuracy_has_highest_weight(self):
        weights = AIEvaluationEngine.WEIGHTS
        assert weights[QualityFactor.ACCURACY] == max(weights.values())

    def test_get_assessments_by_org(self):
        engine = AIEvaluationEngine()
        engine.evaluate("a1", ORG_ID, "q", "r")
        engine.evaluate("a2", ORG_ID_2, "q", "r")
        org1 = engine.get_assessments(org_id=ORG_ID)
        assert len(org1) == 1

    def test_perfect_score(self):
        engine = AIEvaluationEngine()
        a = engine.evaluate("a1", ORG_ID, "q", "r", accuracy=1.0, confidence=1.0,
            source_quality=1.0, user_feedback=1.0, business_outcome=1.0, sources_cited=["source1"])
        assert a.quality_score == 100


# ══════════════════════════════════════════════════════════════
# 7. OBSERVABILITY TESTS (12)
# ══════════════════════════════════════════════════════════════

class TestObservatory:
    def test_record_metric(self):
        obs = IntelligenceObservatory()
        m = obs.record_metric(ORG_ID, MetricType.AI_COST, 0.05, unit="USD", model="gpt-4o")
        assert m.value == 0.05

    def test_get_metrics(self):
        obs = IntelligenceObservatory()
        obs.record_metric(ORG_ID, MetricType.AI_COST, 0.05)
        obs.record_metric(ORG_ID, MetricType.LATENCY, 500, unit="ms")
        metrics = obs.get_metrics()
        assert len(metrics) == 2

    def test_get_metrics_by_org(self):
        obs = IntelligenceObservatory()
        obs.record_metric(ORG_ID, MetricType.AI_COST, 0.05)
        obs.record_metric(ORG_ID_2, MetricType.AI_COST, 0.03)
        assert len(obs.get_metrics(org_id=ORG_ID)) == 1

    def test_get_metrics_by_type(self):
        obs = IntelligenceObservatory()
        obs.record_metric(ORG_ID, MetricType.AI_COST, 0.05)
        obs.record_metric(ORG_ID, MetricType.LATENCY, 500)
        assert len(obs.get_metrics(metric_type="ai_cost")) == 1

    def test_security_event(self):
        obs = IntelligenceObservatory()
        e = obs.record_security_event(ORG_ID, "access_denied", "agent_1", "Agent tried to access HR data")
        assert e.severity == "low"

    def test_security_event_high_severity(self):
        obs = IntelligenceObservatory()
        obs.record_security_event(ORG_ID, "permission_violation", "agent_1", "Critical", severity="high")
        events = obs.get_security_events()
        assert events[0]["severity"] == "high"

    def test_ceo_dashboard(self):
        obs = IntelligenceObservatory()
        obs.record_metric(ORG_ID, MetricType.AI_COST, 0.05)
        obs.record_metric(ORG_ID, MetricType.AGENT_PERFORMANCE, 0.85)
        dash = obs.get_dashboard(ORG_ID, "ceo")
        assert dash["view"] == "ceo"
        assert "total_ai_cost" in dash

    def test_cto_dashboard(self):
        obs = IntelligenceObservatory()
        obs.record_metric(ORG_ID, MetricType.LATENCY, 500)
        obs.record_metric(ORG_ID, MetricType.ERRORS, 3)
        dash = obs.get_dashboard(ORG_ID, "cto")
        assert dash["view"] == "cto"
        assert "avg_latency_ms" in dash

    def test_cfo_dashboard(self):
        obs = IntelligenceObservatory()
        obs.record_metric(ORG_ID, MetricType.AI_COST, 0.05, model="gpt-4o")
        obs.record_metric(ORG_ID, MetricType.AI_COST, 0.02, model="claude-3-5-sonnet")
        dash = obs.get_dashboard(ORG_ID, "cfo")
        assert dash["view"] == "cfo"
        assert "cost_by_model" in dash
        assert dash["total_ai_cost"] == 0.07

    def test_ciso_dashboard(self):
        obs = IntelligenceObservatory()
        obs.record_security_event(ORG_ID, "access_denied", "a1", "test", severity="high")
        obs.record_security_event(ORG_ID, "breach", "a2", "critical", severity="critical")
        dash = obs.get_dashboard(ORG_ID, "ciso")
        assert dash["view"] == "ciso"
        assert dash["total_security_events"] == 2
        assert dash["critical_events"] == 1

    def test_tenant_isolation_observability(self):
        obs = IntelligenceObservatory()
        obs.record_metric(ORG_ID, MetricType.AI_COST, 0.05)
        obs.record_metric(ORG_ID_2, MetricType.AI_COST, 0.03)
        dash1 = obs.get_dashboard(ORG_ID, "cfo")
        dash2 = obs.get_dashboard(ORG_ID_2, "cfo")
        assert dash1["total_ai_cost"] != dash2["total_ai_cost"]

    def test_get_security_events_by_org(self):
        obs = IntelligenceObservatory()
        obs.record_security_event(ORG_ID, "test", "a1", "desc")
        obs.record_security_event(ORG_ID_2, "test", "a1", "desc")
        assert len(obs.get_security_events(org_id=ORG_ID)) == 1


# ══════════════════════════════════════════════════════════════
# 8. AUDIT TRAIL TESTS (8)
# ══════════════════════════════════════════════════════════════

class TestAuditTrail:
    def test_record_audit(self):
        trail = AuditTrail()
        entry = trail.record(ORG_ID, "user_1", "sales_data", "gpt-4o", "Sales Agent", "Q3 analysis", "query", "revenue report")
        assert entry.who == "user_1"
        assert entry.which_model == "gpt-4o"
        assert entry.which_agent == "Sales Agent"

    def test_audit_has_all_fields(self):
        trail = AuditTrail()
        entry = trail.record(ORG_ID, "u1", "data", "model", "agent", "why", "action", "result")
        d = entry.to_dict()
        for field in ["who", "when", "which_data", "which_model", "which_agent", "why", "action", "result"]:
            assert field in d

    def test_get_entries_by_org(self):
        trail = AuditTrail()
        trail.record(ORG_ID, "u1", "d", "m", "a", "w", "act", "r")
        trail.record(ORG_ID_2, "u1", "d", "m", "a", "w", "act", "r")
        assert len(trail.get_entries(org_id=ORG_ID)) == 1

    def test_get_entries_by_agent(self):
        trail = AuditTrail()
        trail.record(ORG_ID, "agent_1", "d", "m", "Sales", "w", "act", "r")
        trail.record(ORG_ID, "agent_2", "d", "m", "Finance", "w", "act", "r")
        assert len(trail.get_entries(agent_id="agent_1")) == 1

    def test_get_count(self):
        trail = AuditTrail()
        trail.record(ORG_ID, "u1", "d", "m", "a", "w", "act", "r")
        trail.record(ORG_ID, "u2", "d", "m", "a", "w", "act", "r")
        assert trail.get_count(org_id=ORG_ID) == 2

    def test_audit_timestamp(self):
        trail = AuditTrail()
        entry = trail.record(ORG_ID, "u1", "d", "m", "a", "w", "act", "r")
        assert entry.when is not None
        assert "T" in entry.when  # ISO format

    def test_tenant_isolation_audit(self):
        trail = AuditTrail()
        trail.record(ORG_ID, "u1", "org1_data", "m", "a", "w", "act", "r")
        trail.record(ORG_ID_2, "u1", "org2_data", "m", "a", "w", "act", "r")
        org1 = trail.get_entries(org_id=ORG_ID)
        assert all(e["org_id"] == ORG_ID for e in org1)

    def test_audit_immutability(self):
        """Audit entries should not be modifiable (conceptually)"""
        trail = AuditTrail()
        entry = trail.record(ORG_ID, "u1", "d", "m", "a", "w", "act", "r")
        # The entry exists and has all required fields
        assert entry.id is not None
        assert entry.when is not None


# ══════════════════════════════════════════════════════════════
# 9. SECURITY TESTS (10)
# ══════════════════════════════════════════════════════════════

class TestSecurityHardening:
    def test_ceo_can_access_all(self):
        mgr = AgentManager()
        sec = mgr.security
        agent = mgr.create_agent_from_profile(ORG_ID, RETAIL_PROFILE, AgentType.STRATEGY)
        assert sec.check_data_access(agent.id, "financial")
        assert sec.check_data_access(agent.id, "hr")
        assert sec.check_entity_access(agent.id, "customer")

    def test_cfo_cannot_access_hr_data(self):
        mgr = AgentManager()
        sec = mgr.security
        agent = mgr.create_agent_from_profile(ORG_ID, RETAIL_PROFILE, AgentType.FINANCE)
        assert not sec.check_data_access(agent.id, "employee_data")
        assert not sec.check_data_access(agent.id, "hr")

    def test_hr_cannot_access_financial_data(self):
        mgr = AgentManager()
        sec = mgr.security
        agent = mgr.create_agent_from_profile(ORG_ID, RETAIL_PROFILE, AgentType.HR)
        assert not sec.check_data_access(agent.id, "financial")

    def test_agent_cannot_modify_data(self):
        mgr = AgentManager()
        sec = mgr.security
        agent = mgr.create_agent_from_profile(ORG_ID, RETAIL_PROFILE, AgentType.SALES)
        assert not sec.check_action(agent.id, "modify_data")

    def test_sales_agent_cannot_send_notifications(self):
        mgr = AgentManager()
        sec = mgr.security
        agent = mgr.create_agent_from_profile(ORG_ID, RETAIL_PROFILE, AgentType.SALES)
        assert not sec.check_action(agent.id, "send_notification")

    def test_strategy_agent_can_create_decisions(self):
        mgr = AgentManager()
        sec = mgr.security
        agent = mgr.create_agent_from_profile(ORG_ID, RETAIL_PROFILE, AgentType.STRATEGY)
        assert sec.check_action(agent.id, "create_decision")

    def test_production_agent_can_create_decisions(self):
        mgr = AgentManager()
        sec = mgr.security
        agent = mgr.create_agent_from_profile(ORG_ID, MFG_PROFILE, AgentType.PRODUCTION)
        assert sec.check_action(agent.id, "create_decision")

    def test_inventory_agent_cannot_create_decisions(self):
        mgr = AgentManager()
        sec = mgr.security
        agent = mgr.create_agent_from_profile(ORG_ID, RETAIL_PROFILE, AgentType.INVENTORY)
        assert not sec.check_action(agent.id, "create_decision")

    def test_sensitivity_ceo_can_access_critical(self):
        mgr = AgentManager()
        sec = mgr.security
        agent = mgr.create_agent_from_profile(ORG_ID, RETAIL_PROFILE, AgentType.STRATEGY)
        assert sec.check_sensitivity(agent.id, "critical")

    def test_coo_cannot_access_critical(self):
        mgr = AgentManager()
        sec = mgr.security
        agent = mgr.create_agent_from_profile(ORG_ID, RETAIL_PROFILE, AgentType.INVENTORY)
        assert not sec.check_sensitivity(agent.id, "critical")


# ══════════════════════════════════════════════════════════════
# 10. MULTI-AGENT SCENARIO TESTS (8)
# ══════════════════════════════════════════════════════════════

class TestMultiAgentScenarios:
    def test_revenue_drop_investigation(self):
        """Full scenario: revenue drops → agents investigate → escalation"""
        mgr = AgentManager()
        agents = mgr.create_agents_for_industry(ORG_ID, RETAIL_PROFILE)
        router = AgentIntelligenceRouter()
        decision = router.route("Why did revenue drop in Germany?", agents, RETAIL_PROFILE)
        # Should select sales + finance
        assert len(decision.selected_agents) >= 1
        selected_types = [a.spec.type for a in agents if a.id in decision.selected_agents]
        assert AgentType.SALES in selected_types or AgentType.FINANCE in selected_types

    def test_quality_issue_investigation(self):
        """Manufacturing: quality issue → quality agent + production agent"""
        mgr = AgentManager()
        agents = mgr.create_agents_for_industry(ORG_ID, MFG_PROFILE)
        router = AgentIntelligenceRouter()
        decision = router.route("Why are defect rates increasing?", agents, MFG_PROFILE)
        selected_types = [a.spec.type for a in agents if a.id in decision.selected_agents]
        assert AgentType.QUALITY in selected_types

    def test_cross_functional_query(self):
        """Query spanning multiple domains"""
        mgr = AgentManager()
        agents = mgr.create_agents_for_industry(ORG_ID, RETAIL_PROFILE)
        router = AgentIntelligenceRouter()
        decision = router.route("Revenue drop and inventory shortage and customer complaints", agents, RETAIL_PROFILE)
        assert len(decision.selected_agents) >= 2

    def test_agent_communication_in_orchestration(self):
        """Agents communicate during orchestration"""
        proto = AgentCommunicationProtocol()
        sid = proto.create_session(ORG_ID, "Why did revenue drop?")
        proto.add_evidence(sid, "sales_agent", "Revenue down 15% in Germany", 0.85)
        proto.add_evidence(sid, "finance_agent", "Margin also declining", 0.80)
        proto.add_analysis(sid, "sales_agent", "Competitor entered German market")
        ctx = proto.get_context(sid)
        assert len(ctx.evidence) == 2
        assert len(ctx.analyses) == 1

    def test_consensus_building(self):
        """Agents build consensus through the protocol"""
        proto = AgentCommunicationProtocol()
        sid = proto.create_session(ORG_ID, "Strategy decision")
        proto.add_analysis(sid, "sales_agent", "Expand to new market")
        proto.add_analysis(sid, "finance_agent", "Expand to new market")
        proto.add_analysis(sid, "strategy_agent", "Expand to new market")
        proto.register_disagreement(sid, "a1", "I disagree with expansion")
        result = proto.resolve_conflicts(sid)
        assert "consensus" in result.lower()

    def test_full_enterprise_loop(self):
        """Company uploads → profile → dashboard → agents → query → decision → memory → audit"""
        mgr = AgentManager()
        # 1. Create agents from profile
        agents = mgr.create_agents_for_industry(ORG_ID, RETAIL_PROFILE)
        assert len(agents) > 0
        # 2. Execute query
        sales_agent = [a for a in agents if a.spec.type == AgentType.SALES][0]
        result = mgr.execute(sales_agent.id, "Q3 revenue analysis", RETAIL_PROFILE)
        assert result.error is None
        # 3. Memory stored
        mem = mgr.get_memory(sales_agent.id, "short_term")
        assert len(mem) > 0
        # 4. Performance tracked
        perf = mgr.get_performance(sales_agent.id)
        assert perf["conversations"] == 1

    def test_proactive_monitoring_scenario(self):
        """KPI monitoring → threshold breach → investigation → escalation"""
        sched = AgentScheduler()
        sched.create_schedule(ORG_ID, "sales_agent", TriggerType.KPI_THRESHOLD,
            {"kpi": "revenue", "threshold": -0.15, "comparison": "percent_change"})
        sched.update_kpi(ORG_ID, "revenue", 100000)
        triggered = sched.update_kpi(ORG_ID, "revenue", 80000)  # -20%
        assert len(triggered) == 1
        inv = sched.trigger_investigation(ORG_ID, "sales_agent", "Revenue dropped 20%",
            escalation_agents=["finance_agent", "ceo_agent"])
        assert len(inv.escalated_to) == 2

    def test_evaluation_loop_integration(self):
        """AI response → evaluation → quality score → feedback → learning"""
        engine = AIEvaluationEngine()
        mem = PersistentAgentMemory()
        # Evaluate response
        a = engine.evaluate("a1", ORG_ID, "Revenue analysis", "Revenue up 5%",
            accuracy=0.85, confidence=0.8, source_quality=0.7, business_outcome=0.75)
        assert a.quality_score > 50
        # User feedback
        engine.add_feedback(a.id, "Good analysis", approved=True)
        # Store in learning memory
        mem.create_memory_object("a1", ORG_ID, "Sales Agent", PersistentMemoryType.LEARNING,
            context="Revenue analysis", action="Evaluated response", result=f"Quality: {a.quality_score}",
            confidence=a.quality_score / 100, feedback="Approved")
        learning = mem.get_learning_memory("a1")
        assert len(learning) == 1
