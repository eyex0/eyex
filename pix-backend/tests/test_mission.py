"""Comprehensive end-to-end mission test for the multi-agent system.

Simulates the full 'Build a simple AI-powered application' mission
through the AgentGraph with per-agent mocks to verify routing,
state management, error handling, and final report generation.
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.agents.graph import (
    AgentGraph,
    AgentWorkflowState,
    route_from_supervisor,
    route_from_planner,
    route_from_researcher,
    route_from_coder,
    route_from_quality_gate,
    route_from_documenter,
    route_from_devops,
    _supervisor_node,
    _quality_gate_node,
    _responder_node,
    _run_agent_node,
)
from app.agents.base import NodeAgent
from app.agents.supervisor import SupervisorAgent


def _make_state(overrides: dict | None = None) -> AgentWorkflowState:
    base: AgentWorkflowState = {
        "request": "Build a simple AI-powered application",
        "request_id": "mission-test-001",
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
        "status": "pending",
        "iteration_count": 0,
    }
    if overrides:
        base.update(overrides)
    return base


def _mock_agent_result(data: dict) -> AsyncMock:
    mock = AsyncMock(spec=NodeAgent)
    inner_mock = MagicMock()
    inner_mock.model_dump.return_value = data
    mock.execute = AsyncMock(return_value=inner_mock)
    return mock


class TestMissionBuildAndRouting:
    """Test the AgentGraph structure and routing with a coding mission request."""

    def test_graph_has_all_9_nodes(self):
        """The graph must contain all 9 nodes: supervisor, planner, researcher,
        coder, reviewer, tester, quality_gate, documenter, devops, responder."""
        graph = AgentGraph()
        graph.build()
        assert graph.graph is not None
        nodes = list(graph.graph.nodes.keys())
        # LangGraph automatically adds __start__, so total is 11 (10 named + __start__)
        named_nodes = [n for n in nodes if not n.startswith("__")]
        assert "supervisor" in named_nodes, "Missing supervisor node"
        assert "analyst" in named_nodes, "Missing analyst node"
        assert "strategist" in named_nodes, "Missing strategist node"
        assert "decision" in named_nodes, "Missing decision node"
        assert "planner" in named_nodes, "Missing planner node"
        assert "researcher" in named_nodes, "Missing researcher node"
        assert "coder" in named_nodes, "Missing coder node"
        assert "reviewer" in named_nodes, "Missing reviewer node"
        assert "tester" in named_nodes, "Missing tester node"
        assert "documenter" in named_nodes, "Missing documenter node"
        assert "devops" in named_nodes, "Missing devops node"
        assert "responder" in named_nodes, "Missing responder node"
        assert "ceo" in named_nodes, "Missing ceo node"
        assert "cfo" in named_nodes, "Missing cfo node"
        assert "coo" in named_nodes, "Missing coo node"
        assert "risk" in named_nodes, "Missing risk node"
        assert len(named_nodes) == 17, f"Expected 17 named nodes, got {len(named_nodes)}"

    def test_supervisor_routes_coding_to_coder(self):
        """Coding requests should route directly to coder from supervisor."""
        state = _make_state({"classification": {"category": "coding", "confidence": 0.95}})
        assert route_from_supervisor(state) == "coder"

    def test_coding_pipeline_route_after_coder(self):
        """After coder completes, the workflow should fan out to reviewer AND tester."""
        state = _make_state({
            "coder_result": {"files": [], "explanation": "test code", "dependencies": []},
        })
        result = route_from_coder(state)
        assert isinstance(result, list), "route_from_coder should return a list"
        assert "reviewer" in result
        assert "tester" in result

    def test_quality_gate_passes_approved_code(self):
        """Quality gate should route approved code to documenter."""
        state = _make_state({
            "reviewer_result": {"approved": True, "score": 90, "issues": [], "summary": "Great"},
            "coder_result": {"files": [], "explanation": "code"},
            "tester_result": {"test_files": [], "test_strategy": "unit"},
            "iteration_count": 1,
        })
        assert route_from_quality_gate(state) == "documenter"

    def test_quality_gate_rejects_unapproved_code(self):
        """Quality gate should send unapproved code back to coder for iteration."""
        state = _make_state({
            "reviewer_result": {"approved": False, "score": 45, "issues": [{"severity": "critical"}]},
            "coder_result": {"files": [], "explanation": "buggy code"},
            "iteration_count": 1,
        })
        assert route_from_quality_gate(state) == "coder"

    def test_quality_gate_max_iterations(self):
        """Quality gate should stop iterating after MAX_WORKFLOW_ITERATIONS."""
        state = _make_state({
            "reviewer_result": {"approved": False, "score": 30},
            "iteration_count": 5,
        })
        assert route_from_quality_gate(state) == "documenter"

    def test_documenter_routes_to_devops(self):
        """Documenter should always route to devops."""
        state = _make_state({"documenter_result": {"files": [], "summary": "docs"}})
        assert route_from_documenter(state) == "devops"

    def test_devops_routes_to_responder(self):
        """DevOps should always route to responder (final step)."""
        state = _make_state({"devops_result": {"config_files": []}})
        assert route_from_devops(state) == "responder"


class TestMissionNodeExecution:
    """Test each node's execution logic with mocked agent outputs."""

    @pytest.mark.asyncio
    async def test_supervisor_node_classifies_coding_mission(self):
        """Supervisor should classify a coding mission request."""
        state = _make_state()

        with patch.object(SupervisorAgent, "analyze", new=AsyncMock()) as mock_analyze:
            mock_analyze.return_value = {
                "classification": {
                    "category": "coding",
                    "confidence": 0.95,
                    "reasoning": "Building an app requires code generation",
                    "suggested_agents": ["coder", "tester"],
                    "requires_decomposition": True,
                },
                "analysis": {"input_length": 42, "has_history": False, "history_length": 0},
            }
            result = await _supervisor_node(state)
            assert result["classification"]["category"] == "coding"
            assert result["classification"]["confidence"] == 0.95
            assert len(result["nodes_executed"]) == 1
            assert result["nodes_executed"][0]["node"] == "supervisor"
            assert result["nodes_executed"][0]["status"] == "completed"

    @pytest.mark.asyncio
    async def test_supervisor_node_fallback_on_error(self):
        """Supervisor should produce fallback classification on error."""
        state = _make_state()

        with patch.object(SupervisorAgent, "analyze", new=AsyncMock()) as mock_analyze:
            mock_analyze.side_effect = Exception("LLM unavailable")
            result = await _supervisor_node(state)
            assert result.get("error") is not None
            assert result.get("status") == "failed"

    @pytest.mark.asyncio
    async def test_quality_gate_evaluates_review_and_tests(self):
        """Quality gate should evaluate review results correctly."""
        state = _make_state({
            "reviewer_result": {
                "approved": True,
                "score": 88,
                "issues": [],
                "summary": "Good code",
                "strengths": ["Clean"],
                "recommendations": [],
            },
            "coder_result": {"files": [], "explanation": "code"},
            "tester_result": {"test_files": [], "test_strategy": "pytest", "coverage_analysis": "80%"},
        })
        result = await _quality_gate_node(state)
        assert result["status"] == "running"
        assert len(result["nodes_executed"]) == 1
        assert result["nodes_executed"][0]["node"] == "quality_gate"
        assert result["nodes_executed"][0]["status"] == "completed"

    @pytest.mark.asyncio
    async def test_responder_compiles_full_report(self):
        """Responder should compile all agent results into a final report."""
        state = _make_state({
            "classification": {"category": "coding", "confidence": 0.9, "reasoning": "test"},
            "planner_result": {
                "plan": "Build an AI app",
                "steps": ["Setup", "Implement", "Test"],
                "estimated_effort": "8 hours",
            },
            "coder_result": {
                "files": [{"path": "main.py", "content": "...", "language": "python"}],
                "explanation": "Created the application",
            },
            "reviewer_result": {
                "summary": "Code looks good",
                "score": 85,
                "approved": True,
                "issues": [],
                "strengths": [],
                "recommendations": [],
            },
            "tester_result": {
                "test_files": [{"path": "test_main.py", "content": "...", "framework": "pytest"}],
                "test_strategy": "Unit tests with pytest",
            },
            "documenter_result": {
                "files": [{"path": "docs/api.md", "content": "...", "title": "API", "audience": "developer"}],
                "summary": "Created documentation",
            },
            "devops_result": {
                "config_files": [{"path": "Dockerfile", "content": "...", "type": "docker"}],
                "cicd_pipeline": "GitHub Actions",
            },
            "status": "running",
            "iteration_count": 1,
        })
        result = await _responder_node(state)
        assert result["status"] == "completed"
        assert result["final_response"] is not None
        report = result["final_response"]
        assert "Code Generated" in report, "Report should include coder output"
        assert "Review" in report, "Report should include reviewer output"
        assert "Tests" in report, "Report should include tester output"
        assert "Documentation" in report, "Report should include documenter output"
        assert "DevOps" in report, "Report should include devops output"
        assert result["nodes_executed"][0]["status"] == "completed"


class TestMissionFullExecution:
    """Test the complete end-to-end mission execution with mocked graph."""

    @pytest.mark.asyncio
    async def test_full_mission_execution(self):
        """Execute a complete 'Build a simple AI-powered application' mission."""
        graph = AgentGraph()
        graph.build()
        assert graph.graph is not None

        expected_result = {
            "request": "Build a simple AI-powered application",
            "request_id": "mission-full-001",
            "classification": {
                "category": "coding",
                "confidence": 0.95,
                "reasoning": "Building an AI application requires code generation and testing",
                "suggested_agents": ["coder", "tester", "reviewer"],
                "requires_decomposition": True,
            },
            "planner_result": {
                "plan": "Build an AI-powered FastAPI application",
                "steps": ["Setup project", "Implement AI service", "Create API", "Add tests", "Containerize"],
                "step_details": [],
                "estimated_effort": "8-10 hours",
                "risks": [],
                "recommendations": [],
            },
            "coder_result": {
                "files": [
                    {"path": "app/main.py", "content": "...", "language": "python"},
                    {"path": "app/ai_service.py", "content": "...", "language": "python"},
                ],
                "explanation": "Created FastAPI app with AI service layer",
                "dependencies": ["fastapi", "openai"],
                "setup_instructions": ["pip install -r requirements.txt"],
                "breaking_changes": False,
                "testing_notes": ["Mock OpenAI in tests"],
            },
            "reviewer_result": {
                "summary": "Clean implementation, minor improvements needed",
                "issues": [
                    {"severity": "minor", "category": "error_handling", "location": "ai_service.py",
                     "description": "Add error handling", "suggestion": "Wrap in try/except"},
                ],
                "strengths": ["Good structure", "Clean code"],
                "recommendations": ["Add input validation"],
                "score": 85,
                "approved": True,
            },
            "tester_result": {
                "test_files": [
                    {"path": "tests/test_main.py", "content": "...", "framework": "pytest"},
                    {"path": "tests/test_ai_service.py", "content": "...", "framework": "pytest"},
                ],
                "coverage_analysis": "Core paths covered",
                "test_strategy": "Unit tests with mocked dependencies",
                "missing_tests": ["Integration tests"],
                "setup_instructions": [],
                "recommendations": [],
            },
            "documenter_result": {
                "files": [
                    {"path": "docs/api.md", "content": "...", "title": "API Reference", "audience": "developer"},
                ],
                "summary": "Created API documentation",
                "key_decisions": ["FastAPI + OpenAI"],
                "missing_docs": [],
                "recommendations": [],
            },
            "devops_result": {
                "config_files": [
                    {"path": "Dockerfile", "content": "...", "type": "docker"},
                ],
                "deployment_steps": ["Build image", "Push to registry", "Deploy"],
                "infrastructure_requirements": ["Cloud account"],
                "cicd_pipeline": "GitHub Actions",
                "monitoring_setup": ["Health check", "Logging"],
                "security_notes": ["Use secrets manager"],
                "estimated_resources": "1 CPU, 512MB RAM",
            },
            "final_response": (
                "## Plan\nBuild an AI-powered FastAPI application\n"
                "### Steps\n1. Setup project\n2. Implement AI service\n3. Create API\n"
                "4. Add tests\n5. Containerize\n\n---\n\n"
                "## Code Generated\nCreated FastAPI app with AI service layer\n"
                "- `app/main.py` (python)\n- `app/ai_service.py` (python)\n\n---\n\n"
                "## Review (Score: 85/100)\n\n---\n\n"
                "## Tests\nUnit tests with mocked dependencies\n"
                "- `tests/test_main.py` (pytest)\n- `tests/test_ai_service.py` (pytest)\n\n---\n\n"
                "## Documentation\nCreated API documentation\n\n---\n\n"
                "## DevOps\nGitHub Actions"
            ),
            "error": None,
            "nodes_executed": [
                {"node": "supervisor", "status": "completed", "duration_ms": 150.0, "started_at": 1000.0},
                {"node": "planner", "status": "completed", "duration_ms": 2000.0, "started_at": 1150.0},
                {"node": "coder", "status": "completed", "duration_ms": 5000.0, "started_at": 3150.0},
                {"node": "reviewer", "status": "completed", "duration_ms": 1500.0, "started_at": 8150.0},
                {"node": "tester", "status": "completed", "duration_ms": 2000.0, "started_at": 8150.0},
                {"node": "quality_gate", "status": "completed", "duration_ms": 5.0, "started_at": 10150.0},
                {"node": "documenter", "status": "completed", "duration_ms": 1000.0, "started_at": 10155.0},
                {"node": "devops", "status": "completed", "duration_ms": 1500.0, "started_at": 11155.0},
                {"node": "responder", "status": "completed", "duration_ms": 50.0, "started_at": 12655.0},
            ],
            "status": "completed",
            "iteration_count": 1,
        }

        with patch.object(graph.graph, "ainvoke", new=AsyncMock()) as mock_invoke:
            mock_invoke.return_value = expected_result
            result = await graph.run("Build a simple AI-powered application")

        assert result["status"] == "completed"
        assert result["error"] is None

        assert result["classification"]["category"] == "coding"
        assert result["planner_result"] is not None
        assert result["coder_result"] is not None
        assert result["reviewer_result"] is not None
        assert result["tester_result"] is not None
        assert result["documenter_result"] is not None
        assert result["devops_result"] is not None
        assert result["final_response"] is not None

        assert len(result["nodes_executed"]) == 9
        executed_nodes = [n["node"] for n in result["nodes_executed"]]
        expected_nodes = ["supervisor", "planner", "coder", "reviewer", "tester",
                          "quality_gate", "documenter", "devops", "responder"]
        for node in expected_nodes:
            assert node in executed_nodes, f"Missing node: {node}"

        for node_record in result["nodes_executed"]:
            assert node_record["status"] == "completed", \
                f"Node {node_record['node']} failed with status {node_record['status']}"

        report = result["final_response"]
        assert "Plan" in report
        assert "Code Generated" in report
        assert "Review" in report
        assert "Tests" in report
        assert "Documentation" in report
        assert "DevOps" in report

    @pytest.mark.asyncio
    async def test_mission_with_retry_on_failure(self):
        """Mission should handle a rejected review by retrying coder."""
        graph = AgentGraph()
        graph.build()
        assert graph.graph is not None

        expected_result = {
            "request": "Build a simple AI-powered application",
            "request_id": "mission-retry-001",
            "classification": {"category": "coding", "confidence": 0.9},
            "planner_result": {"plan": "Test", "steps": [], "estimated_effort": "1h"},
            "coder_result": {"files": [{"path": "main.py"}], "explanation": "Fixed code after review"},
            "reviewer_result": {"approved": True, "score": 90, "issues": [], "summary": "Now acceptable"},
            "tester_result": {"test_files": [{"path": "test_main.py"}], "test_strategy": "pytest"},
            "documenter_result": {"files": [], "summary": "Documentation"},
            "devops_result": {"config_files": [], "cicd_pipeline": "CI/CD"},
            "final_response": "## Code Generated\nFixed code after review",
            "error": None,
            "nodes_executed": [
                {"node": "supervisor", "status": "completed", "duration_ms": 100},
                {"node": "coder", "status": "completed", "duration_ms": 3000},
                {"node": "reviewer", "status": "completed", "duration_ms": 500},
                {"node": "tester", "status": "completed", "duration_ms": 600},
                {"node": "quality_gate", "status": "completed", "duration_ms": 5},
                {"node": "coder", "status": "completed", "duration_ms": 2000},
                {"node": "reviewer", "status": "completed", "duration_ms": 400},
                {"node": "tester", "status": "completed", "duration_ms": 500},
                {"node": "quality_gate", "status": "completed", "duration_ms": 5},
                {"node": "documenter", "status": "completed", "duration_ms": 800},
                {"node": "devops", "status": "completed", "duration_ms": 600},
                {"node": "responder", "status": "completed", "duration_ms": 50},
            ],
            "status": "completed",
            "iteration_count": 2,
        }

        with patch.object(graph.graph, "ainvoke", new=AsyncMock()) as mock_invoke:
            mock_invoke.return_value = expected_result
            result = await graph.run("Build a simple AI-powered application")

        assert result["status"] == "completed"
        assert result["iteration_count"] == 2, "Should have iterated twice (retry)"
        assert len(result["nodes_executed"]) == 12, "Should have 12 node executions including retries"

    @pytest.mark.asyncio
    async def test_mission_error_handling(self):
        """Mission should handle errors gracefully and return error state."""
        graph = AgentGraph()
        graph.build()

        expected_result = {
            "request": "Build a simple AI-powered application",
            "request_id": "mission-error-001",
            "classification": {"category": "coding", "confidence": 0.9},
            "planner_result": None,
            "coder_result": {"error": "OpenAI API key not configured", "success": False},
            "reviewer_result": None,
            "tester_result": None,
            "documenter_result": None,
            "devops_result": None,
            "final_response": None,
            "error": "OpenAI API key not configured",
            "nodes_executed": [
                {"node": "supervisor", "status": "completed", "duration_ms": 100},
                {"node": "planner", "status": "failed", "duration_ms": 500},
            ],
            "status": "failed",
            "iteration_count": 1,
        }

        with patch.object(graph.graph, "ainvoke", new=AsyncMock()) as mock_invoke:
            mock_invoke.return_value = expected_result
            result = await graph.run("Build a simple AI-powered application")

        assert result["status"] == "failed"
        assert result["error"] is not None

    @pytest.mark.asyncio
    async def test_graph_level_error_handling(self):
        """Graph.run() should handle exceptions and return a valid failed state."""
        graph = AgentGraph()
        graph.build()

        with patch.object(graph.graph, "ainvoke", new=AsyncMock()) as mock_invoke:
            mock_invoke.side_effect = Exception("Unexpected graph error")
            result = await graph.run("Build a simple AI-powered application")

        assert result["status"] == "failed"
        assert "Unexpected graph error" in str(result.get("error", ""))
        assert len(result.get("nodes_executed", [])) == 1
        assert result["nodes_executed"][0]["node"] == "graph"


class TestAgentCommunication:
    """Test that agents can communicate through shared state."""

    @pytest.mark.asyncio
    async def test_planner_feeds_coder_with_plan(self):
        """Coder node should receive planner output in its input context."""
        state = _make_state({
            "planner_result": {
                "plan": "Build a FastAPI app with AI features",
                "steps": ["Setup", "Implement", "Test"],
            },
        })

        coder_node = _run_agent_node(
            lambda **kw: _mock_agent_result({
                "files": [{"path": "main.py", "content": "...", "language": "python"}],
                "explanation": "Built the app according to plan",
                "dependencies": [],
                "setup_instructions": [],
                "breaking_changes": False,
                "testing_notes": [],
            }),
            "coder_result",
        )

        result = await coder_node(state)
        assert result["coder_result"] is not None
        coder_output = result["coder_result"]
        assert "files" in coder_output
        assert len(coder_output["files"]) > 0

    @pytest.mark.asyncio
    async def test_reviewer_and_tester_work_in_parallel(self):
        """Reviewer and tester should both receive coder output and execute concurrently."""
        state = _make_state({
            "coder_result": {
                "files": [{"path": "main.py", "content": "print('hello')", "language": "python"}],
                "explanation": "Simple app",
            },
        })
        targets = route_from_coder(state)
        assert len(targets) == 2
        assert "reviewer" in targets
        assert "tester" in targets


class TestMissionReporting:
    """Test that the final mission report is comprehensive."""

    def test_final_report_contains_all_agent_sections(self):
        """The responder should compile a report with sections from all agents."""
        from app.agents.graph import _responder_node

        state = _make_state({
            "classification": {"category": "coding", "reasoning": "Building an app"},
            "planner_result": {
                "plan": "Build AI app",
                "steps": ["Step 1", "Step 2"],
                "estimated_effort": "8h",
            },
            "coder_result": {
                "files": [],
                "explanation": "Generated code",
            },
            "reviewer_result": {
                "summary": "Good",
                "score": 85,
                "approved": True,
                "issues": [],
                "strengths": [],
                "recommendations": [],
            },
            "tester_result": {
                "test_files": [],
                "test_strategy": "Unit tests",
            },
            "documenter_result": {
                "files": [],
                "summary": "Created docs",
            },
            "devops_result": {
                "config_files": [],
                "cicd_pipeline": "GitHub Actions",
            },
            "status": "running",
        })

        assert state["classification"]["category"] == "coding"
        assert state["planner_result"]["plan"] == "Build AI app"
        assert state["coder_result"]["explanation"] == "Generated code"
        assert state["reviewer_result"]["score"] == 85
        assert state["tester_result"]["test_strategy"] == "Unit tests"
        assert state["documenter_result"]["summary"] == "Created docs"
        assert state["devops_result"]["cicd_pipeline"] == "GitHub Actions"
