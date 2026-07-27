"""πX Multi-Agent System — Mission Runner.

Executes a multi-agent workflow mission through the LangGraph AgentGraph.
Supports both real LLM execution (with OPENAI_API_KEY) and dry-run simulation.

Usage:
    python scripts/run_mission.py "Build a simple AI-powered application"
    python scripts/run_mission.py "Research vector databases" --dry-run
    python scripts/run_mission.py "Plan a microservices architecture" --verbose
"""
from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.agents.graph import AgentGraph
from app.schemas.agent import AgentRequest
from app.services.agent_service import AgentOrchestratorService

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("pix.mission")


def print_banner():
    print()
    print("+" + "-"*54 + "+")
    print("|        πX Multi-Agent System - Mission Runner     |")
    print("+" + "-"*54 + "+")
    print()


def print_agent_step(step: dict, index: int) -> None:
    node = step.get("node", "unknown")
    status = step.get("status", "unknown")
    duration = step.get("duration_ms", 0)
    icon = "[OK]" if status == "completed" else "[FAIL]" if status == "failed" else "[...]"
    print(f"  {icon} Step {index}: {node:<15} {status:<12} {duration:>8.0f}ms")


def print_result(result: dict) -> None:
    status = result.get("status", "unknown")
    print()
    print(f"  Status: {'[OK] COMPLETED' if status == 'completed' else '[FAIL] FAILED'}")
    print(f"  Request ID: {result.get('request_id', 'N/A')}")
    
    nodes = result.get("nodes_executed", [])
    print(f"\n  -- Execution Steps ({len(nodes)}) --")
    for i, step in enumerate(nodes, 1):
        print_agent_step(step, i)
    
    classification = result.get("classification")
    if classification:
        print(f"\n  -- Classification --")
        print(f"  Category: {classification.get('category', 'N/A')}")
        print(f"  Confidence: {classification.get('confidence', 0):.1%}")
        print(f"  Reasoning: {classification.get('reasoning', 'N/A')}")
    
    final = result.get("final_response")
    if final:
        print(f"\n  -- Final Response --")
        print(f"  {final[:2000]}")
        if len(final) > 2000:
            print(f"  ... (truncated, {len(final)} total chars)")
    
    if result.get("error"):
        print(f"\n  -- Error --")
        print(f"  {result['error']}")


async def run_mission(request: str, dry_run: bool = False, verbose: bool = False) -> dict:
    if verbose:
        logging.getLogger("pix").setLevel(logging.DEBUG)
    
    logger.info("Mission: %s", request)
    logger.info("Mode: %s", "DRY RUN (simulated)" if dry_run else "LIVE (LLM required)")
    
    if dry_run:
        logger.info("Building simulated mission pipeline...")
        graph = AgentGraph()
        graph.build()
        
        # Simulated result matching a full coding pipeline
        result = {
            "request": request,
            "request_id": f"mission-{int(time.time())}",
            "classification": {
                "category": "coding",
                "confidence": 0.92,
                "reasoning": "Request involves building an application, which requires code generation, review, testing, documentation, and DevOps setup.",
                "suggested_agents": ["planner", "coder", "reviewer", "tester", "documenter", "devops"],
                "requires_decomposition": True,
            },
            "planner_result": {
                "plan": "Build an AI-powered application with a FastAPI backend and React frontend",
                "steps": [
                    "Set up project structure and dependencies",
                    "Implement AI service layer",
                    "Build REST API endpoints",
                    "Create React frontend components",
                    "Add testing",
                    "Containerize with Docker",
                ],
                "step_details": [
                    {"index": 0, "description": "Project setup", "agent": "coder", "effort": "30 min", "dependencies": []},
                    {"index": 1, "description": "AI service layer", "agent": "coder", "effort": "2 hours", "dependencies": [0]},
                    {"index": 2, "description": "REST API", "agent": "coder", "effort": "1 hour", "dependencies": [1]},
                    {"index": 3, "description": "Frontend", "agent": "coder", "effort": "3 hours", "dependencies": [2]},
                    {"index": 4, "description": "Testing", "agent": "tester", "effort": "1 hour", "dependencies": [3]},
                    {"index": 5, "description": "Docker setup", "agent": "devops", "effort": "30 min", "dependencies": [4]},
                ],
                "estimated_effort": "8-10 hours",
                "risks": ["OpenAI API key required for AI features", "Frontend expertise needed for React components"],
                "recommendations": ["Use GPT-4o-mini for cost-effective AI", "Start with backend API first, then frontend"],
            },
            "coder_result": {
                "files": [
                    {"path": "app/main.py", "content": "from fastapi import FastAPI\napp = FastAPI()\n\n@app.get('/')\ndef root():\n    return {'message': 'AI App'}\n", "language": "python"},
                    {"path": "app/ai_service.py", "content": "from openai import OpenAI\nclient = OpenAI()\n\ndef generate_text(prompt: str) -> str:\n    response = client.chat.completions.create(\n        model='gpt-4o-mini',\n        messages=[{'role': 'user', 'content': prompt}]\n    )\n    return response.choices[0].message.content\n", "language": "python"},
                ],
                "explanation": "Created a FastAPI application with an AI service layer using OpenAI. The main app has a health-check endpoint, and the AI service provides text generation capabilities.",
                "dependencies": ["fastapi>=0.115.0", "openai>=1.55.0", "uvicorn[standard]>=0.32.0"],
                "setup_instructions": ["pip install -r requirements.txt", "export OPENAI_API_KEY=your-key", "uvicorn app.main:app --reload"],
                "breaking_changes": False,
                "testing_notes": ["Mock OpenAI client in tests", "Test both success and error paths"],
            },
            "reviewer_result": {
                "summary": "Code is well-structured and follows best practices. Minor improvements suggested.",
                "issues": [
                    {"severity": "minor", "category": "error_handling", "location": "app/ai_service.py:5", "description": "No error handling for API failures", "suggestion": "Wrap OpenAI calls in try/except and return meaningful error messages"},
                    {"severity": "minor", "category": "security", "location": "app/ai_service.py:2", "description": "API key should use environment variable", "suggestion": "Use pydantic-settings or python-dotenv for configuration"},
                ],
                "strengths": ["Clean FastAPI setup", "Good separation of concerns", "Proper async support ready"],
                "recommendations": ["Add input validation with Pydantic", "Add rate limiting", "Add structured logging"],
                "score": 82,
                "approved": True,
            },
            "tester_result": {
                "test_files": [
                    {"path": "tests/test_main.py", "content": "from fastapi.testclient import TestClient\nfrom app.main import app\nclient = TestClient(app)\n\ndef test_root():\n    response = client.get('/')\n    assert response.status_code == 200\n", "framework": "pytest"},
                    {"path": "tests/test_ai_service.py", "content": "from unittest.mock import patch\nfrom app.ai_service import generate_text\n\n@patch('app.ai_service.client.chat.completions.create')\ndef test_generate_text(mock_create):\n    mock_create.return_value.choices[0].message.content = 'Hello'\n    result = generate_text('Hi')\n    assert result == 'Hello'\n", "framework": "pytest"},
                ],
                "coverage_analysis": "Core paths covered: API health check, AI service generation. Need integration tests.",
                "test_strategy": "Unit tests for AI service with mocked OpenAI, integration tests for API endpoints",
                "missing_tests": ["Integration test with real API", "Error path tests", "Load test"],
                "setup_instructions": ["pip install pytest pytest-asyncio httpx", "pytest tests/ -v"],
                "recommendations": ["Add CI pipeline to run tests on every PR", "Aim for 80%+ coverage"],
            },
            "documenter_result": {
                "files": [
                    {"path": "docs/api.md", "content": "# API Documentation\n\n## Endpoints\n- GET / - Health check\n", "title": "API Reference", "audience": "developer"},
                    {"path": "docs/setup.md", "content": "# Setup Guide\n\n1. Clone the repository\n2. Install dependencies\n3. Configure environment\n4. Run the application\n", "title": "Setup Guide", "audience": "developer"},
                ],
                "summary": "Created API documentation and setup guide for developers",
                "key_decisions": ["FastAPI for REST API", "OpenAI for AI features", "Pytest for testing"],
                "missing_docs": ["Deployment guide", "Architecture overview", "Contributing guidelines"],
                "recommendations": ["Add OpenAPI/Swagger docs via FastAPI built-in", "Create user-facing documentation"],
            },
            "devops_result": {
                "config_files": [
                    {"path": "Dockerfile", "content": "FROM python:3.12-slim\nWORKDIR /app\nCOPY requirements.txt .\nRUN pip install -r requirements.txt\nCOPY . .\nCMD ['uvicorn', 'app.main:app', '--host', '0.0.0.0', '--port', '8000']\n", "type": "docker"},
                ],
                "deployment_steps": ["Build Docker image", "Push to container registry", "Deploy to cloud platform"],
                "infrastructure_requirements": ["Cloud provider account", "Container registry", "PostgreSQL database", "Redis instance"],
                "cicd_pipeline": "GitHub Actions: lint → test → build → deploy",
                "monitoring_setup": ["Application health check endpoint", "Structured logging", "OpenTelemetry traces"],
                "security_notes": ["Use secrets manager for API keys", "Enable HTTPS", "Implement authentication"],
                "estimated_resources": "1 CPU, 512MB RAM, $20-50/month",
            },
            "final_response": "## Plan\nBuild an AI-powered application with a FastAPI backend and React frontend\n...",
            "error": None,
            "nodes_executed": [
                {"node": "supervisor", "status": "completed", "duration_ms": 150.0},
                {"node": "planner", "status": "completed", "duration_ms": 2500.0},
                {"node": "coder", "status": "completed", "duration_ms": 8000.0},
                {"node": "reviewer", "status": "completed", "duration_ms": 1500.0},
                {"node": "tester", "status": "completed", "duration_ms": 2000.0},
                {"node": "quality_gate", "status": "completed", "duration_ms": 5.0},
                {"node": "documenter", "status": "completed", "duration_ms": 1200.0},
                {"node": "devops", "status": "completed", "duration_ms": 1800.0},
                {"node": "responder", "status": "completed", "duration_ms": 50.0},
            ],
            "status": "completed",
            "iteration_count": 1,
        }
        return result
    
    # Live mode — use actual AgentGraph with LLM
    logger.info("Running live mission through AgentGraph...")
    service = AgentOrchestratorService(memory_service=None)
    result = await service.execute(AgentRequest(input=request))
    
    return {
        "request": request,
        "request_id": result.thread_id or "N/A",
        "nodes_executed": [s.model_dump() for s in result.steps],
        "final_response": result.output,
        "error": result.error,
        "status": "completed" if result.success else "failed",
    }


def main():
    print_banner()
    
    parser = argparse.ArgumentParser(description="Run an πX multi-agent mission")
    parser.add_argument("request", nargs="?", default="Build a simple AI-powered application",
                       help="The mission request for the multi-agent system")
    parser.add_argument("--dry-run", action="store_true",
                       help="Run in simulation mode (no LLM required)")
    parser.add_argument("--verbose", "-v", action="store_true",
                       help="Show detailed debug logging")
    parser.add_argument("--output", "-o", type=str, default=None,
                       help="Save results to JSON file")
    
    args = parser.parse_args()
    
    print(f"  Request: {args.request}")
    print(f"  Mode: {'DRY RUN' if args.dry_run else 'LIVE'}")
    print()
    
    result = asyncio.run(run_mission(args.request, args.dry_run, args.verbose))
    print_result(result)
    
    if args.output:
        output_path = Path(args.output)
        output_path.write_text(json.dumps(result, indent=2, default=str), encoding="utf-8")
        print(f"\n  Results saved to {output_path}")
    
    status = result.get("status", "failed")
    print(f"\n  {'='*54}")
    print(f"  Mission {'COMPLETED' if status == 'completed' else 'FAILED'}")
    print(f"  {'='*54}")
    print()
    
    return 0 if status == "completed" else 1


if __name__ == "__main__":
    sys.exit(main())
