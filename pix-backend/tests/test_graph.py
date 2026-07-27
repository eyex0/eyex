from __future__ import annotations

from unittest.mock import patch

import pytest

from app.agents.graph import (
    AgentGraph,
    route_from_supervisor,
    route_from_planner,
    route_from_coder,
    route_from_quality_gate,
    route_from_ceo,
    route_from_cfo,
    route_from_coo,
    route_from_risk,
)


def _make_state(overrides: dict | None = None) -> dict:
    base = {
        "request": "Build a login API",
        "request_id": "test-id",
        "classification": None,
        "planner_result": None,
        "researcher_result": None,
        "coder_result": None,
        "reviewer_result": None,
        "tester_result": None,
        "documenter_result": None,
        "devops_result": None,
        "final_response": None,
        "error": None,
        "nodes_executed": [],
        "status": "running",
        "iteration_count": 0,
        **(overrides or {}),
    }
    return base


class TestRouting:
    def test_supervisor_routes_planning_to_planner(self):
        state = _make_state({"classification": {"category": "planning", "confidence": 0.9}})
        assert route_from_supervisor(state) == "planner"

    def test_supervisor_routes_research_to_researcher(self):
        state = _make_state({"classification": {"category": "research", "confidence": 0.85}})
        assert route_from_supervisor(state) == "researcher"

    def test_supervisor_routes_coding_to_coder(self):
        state = _make_state({"classification": {"category": "coding", "confidence": 0.95}})
        assert route_from_supervisor(state) == "coder"

    def test_supervisor_routes_general_to_responder(self):
        state = _make_state({"classification": {"category": "general", "confidence": 0.9}})
        assert route_from_supervisor(state) == "responder"

    def test_supervisor_routes_to_responder_on_error(self):
        state = _make_state({"error": "Something broke"})
        assert route_from_supervisor(state) == "__end__"

    def test_coder_fans_out_to_reviewer_and_tester(self):
        state = _make_state({"coder_result": {"files": [], "explanation": "test"}})
        result = route_from_coder(state)
        assert isinstance(result, list)
        assert "reviewer" in result
        assert "tester" in result

    def test_quality_gate_passes_to_documenter_when_approved(self):
        state = _make_state({"reviewer_result": {"approved": True, "score": 90}})
        assert route_from_quality_gate(state) == "documenter"

    def test_quality_gate_rejects_back_to_coder(self):
        state = _make_state({
            "reviewer_result": {"approved": False, "score": 40},
            "iteration_count": 1,
        })
        assert route_from_quality_gate(state) == "coder"

    def test_quality_gate_limits_iterations(self):
        state = _make_state({
            "reviewer_result": {"approved": False, "score": 30},
            "iteration_count": 5,
        })
        assert route_from_quality_gate(state) == "documenter"

    def test_planner_routes_to_researcher_when_agent_assigned(self):
        state = _make_state({
            "planner_result": {
                "step_details": [
                    {"index": 0, "description": "Research DB options", "agent": "researcher", "effort": "1h", "dependencies": []},
                    {"index": 1, "description": "Implement schema", "agent": "coder", "effort": "2h", "dependencies": [0]},
                ],
            },
        })
        assert route_from_planner(state) == "researcher"

    def test_planner_routes_to_responder_when_no_plan(self):
        state = _make_state({"planner_result": None})
        assert route_from_planner(state) == "responder"

    def test_supervisor_routes_executive_to_ceo(self):
        state = _make_state({"classification": {"category": "executive", "confidence": 0.9}})
        assert route_from_supervisor(state) == "ceo"

    def test_intelligence_routes_to_analyst(self):
        state = _make_state({"classification": {"category": "intelligence", "confidence": 0.9}})
        assert route_from_supervisor(state) == "analyst"

    def test_ceo_routes_to_cfo(self):
        state = _make_state({"ceo_result": {"strategic_vision": "Grow market share", "key_priorities": [], "confidence_score": 0.8}})
        assert route_from_ceo(state) == "cfo"

    def test_cfo_routes_to_coo(self):
        state = _make_state({"cfo_result": {"financial_health_assessment": "Stable", "key_metrics": {}}})
        assert route_from_cfo(state) == "coo"

    def test_coo_routes_to_risk(self):
        state = _make_state({"coo_result": {"operational_efficiency": "Good", "process_improvements": []}})
        assert route_from_coo(state) == "risk"

    def test_risk_routes_to_responder(self):
        state = _make_state({"risk_result": {"overall_risk_score": 0.3, "identified_risks": []}})
        assert route_from_risk(state) == "responder"


@pytest.mark.asyncio
class TestGraphExecution:
    @pytest.mark.asyncio
    async def test_graph_builds_successfully(self):
        graph = AgentGraph()
        built = graph.build()
        assert built is not None
        assert graph.graph is not None

    @pytest.mark.asyncio
    async def test_general_request_goes_straight_to_responder(self):
        graph = AgentGraph()
        graph.build()

        with patch.object(graph.graph, "ainvoke") as mock_invoke:
            mock_invoke.return_value = {
                "request": "Hello",
                "request_id": "test-1",
                "classification": {"category": "general", "confidence": 0.95},
                "planner_result": None,
                "researcher_result": None,
                "coder_result": None,
                "reviewer_result": None,
                "tester_result": None,
                "documenter_result": None,
                "devops_result": None,
                "final_response": "**Analysis:** Simple greeting",
                "error": None,
                "nodes_executed": [
                    {"node": "supervisor", "status": "completed", "duration_ms": 200},
                    {"node": "responder", "status": "completed", "duration_ms": 50},
                ],
                "status": "completed",
                "iteration_count": 1,
            }
            result = await graph.run("Hello")
            assert result["status"] == "completed"
            assert result["final_response"] is not None
            assert len(result["nodes_executed"]) == 2

    @pytest.mark.asyncio
    async def test_graph_handles_full_coding_pipeline(self):
        graph = AgentGraph()
        graph.build()

        with patch.object(graph.graph, "ainvoke") as mock_invoke:
            mock_invoke.return_value = {
                "request": "Build an API",
                "request_id": "test-2",
                "classification": {"category": "coding", "confidence": 0.9},
                "planner_result": None,
                "researcher_result": None,
                "coder_result": {"files": [{"path": "main.py", "content": "...", "language": "python"}], "explanation": "Created API"},
                "reviewer_result": {"approved": True, "score": 85, "issues": [], "summary": "Good"},
                "tester_result": {"test_files": [{"path": "test_main.py", "content": "...", "framework": "pytest"}], "test_strategy": "Unit"},
                "documenter_result": {"files": [{"path": "docs/api.md", "content": "...", "title": "API Docs", "audience": "developer"}], "summary": "Created docs"},
                "devops_result": {"config_files": [{"path": "Dockerfile", "content": "...", "type": "docker"}], "cicd_pipeline": "GitHub Actions"},
                "final_response": "## Code Generated\nCreated API\n- `main.py` (python)",
                "error": None,
                "nodes_executed": [
                    {"node": "supervisor", "status": "completed", "duration_ms": 150},
                    {"node": "coder", "status": "completed", "duration_ms": 3000},
                    {"node": "reviewer", "status": "completed", "duration_ms": 1000},
                    {"node": "tester", "status": "completed", "duration_ms": 1200},
                    {"node": "quality_gate", "status": "completed", "duration_ms": 10},
                    {"node": "documenter", "status": "completed", "duration_ms": 800},
                    {"node": "devops", "status": "completed", "duration_ms": 600},
                    {"node": "responder", "status": "completed", "duration_ms": 100},
                ],
                "status": "completed",
                "iteration_count": 1,
            }
            result = await graph.run("Build an API")
            assert result["status"] == "completed"
            assert result["coder_result"] is not None
            assert result["reviewer_result"] is not None
            assert result["tester_result"] is not None
            assert result["documenter_result"] is not None
            assert result["devops_result"] is not None
            assert len(result["nodes_executed"]) == 8
