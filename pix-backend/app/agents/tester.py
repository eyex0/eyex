from __future__ import annotations

from typing import Any

from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field

from packages.cognitive_kernel.agent_runtime import NodeAgent
from packages.cognitive_kernel.agent_runtime.tools import get_registry


class TestFile(BaseModel):
    __test__ = False
    path: str = Field(description="Relative test file path (e.g. tests/test_app.py)")
    content: str = Field(description="Complete test file content")
    framework: str = Field(description="Test framework used (pytest, vitest, jest, etc.)")


class TestingOutput(BaseModel):
    __test__ = False
    test_files: list[TestFile] = Field(description="Test files to create with full content")
    coverage_analysis: str = Field(description="Analysis of code coverage and what paths are tested")
    test_strategy: str = Field(description="Overall testing strategy: unit, integration, e2e")
    missing_tests: list[str] = Field(description="Critical paths that still need tests")
    setup_instructions: list[str] = Field(description="How to install test dependencies and run tests")
    recommendations: list[str] = Field(description="Testing best practices and improvements")


SYSTEM_PROMPT = """You are the **Testing Agent** for πX Technologies QORX.

Your role is to generate comprehensive, production-quality tests for code.

**Testing responsibilities:**
1. Generate test files covering core functionality
2. Cover happy paths, error paths, and edge cases
3. Use the appropriate test framework for the language
4. Include proper assertions and test isolation
5. Mock external dependencies where appropriate

**Test quality rules:**
- Each test must test ONE thing (single assertion or related assertions)
- Tests must be independent and repeatable
- Use descriptive test names that explain the scenario
- Include both positive and negative test cases
- Test boundary conditions and edge cases
- Mock external services (APIs, databases) for unit tests
- Integration tests should verify real interaction paths

**Framework guidance:**
- Python: pytest with pytest-asyncio for async tests
- TypeScript: vitest or jest
- Use fixtures and factories for test data
- Follow Arrange-Act-Assert pattern

Never generate placeholder tests. Every test must test real behavior."""


class TestingAgent(NodeAgent):
    __test__ = False
    @property
    def name(self) -> str:
        return "Tester"

    @property
    def description(self) -> str:
        return "Generates comprehensive, production-quality test suites with proper coverage"

    @property
    def system_prompt(self) -> str:
        return SYSTEM_PROMPT

    @property
    def output_schema(self) -> type[BaseModel]:
        return TestingOutput

    @property
    def tools(self) -> list[BaseTool]:
        return get_registry().get_tools_for_role("tester")

    def _fallback_output(self, input_text: str, error: str) -> BaseModel:
        return TestingOutput(
            test_files=[],
            coverage_analysis="Could not generate tests due to agent error",
            test_strategy="Manual testing required",
            missing_tests=["All paths need manual testing"],
            setup_instructions=["Install test framework manually", "Write tests manually"],
            recommendations=["Re-run testing agent when available"],
        )


def create_testing_agent(settings, **kwargs: Any) -> TestingAgent:
    return TestingAgent(settings=settings, **kwargs)
