from __future__ import annotations

from typing import Any

from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field

from packages.cognitive_kernel.agent_runtime import NodeAgent
from app.agents.tools.registry import get_registry


class CodeFile(BaseModel):
    path: str = Field(description="Relative file path (e.g. src/app.py)")
    content: str = Field(description="Complete file content")
    language: str = Field(description="Programming language (python, typescript, etc.)")


class CodingOutput(BaseModel):
    files: list[CodeFile] = Field(description="List of files to create or modify with their full content")
    explanation: str = Field(description="Explanation of the implementation, architecture, and key decisions")
    dependencies: list[str] = Field(description="External dependencies required (package names, versions)")
    setup_instructions: list[str] = Field(description="Steps to set up and run the code")
    breaking_changes: bool = Field(description="Whether this change introduces breaking changes")
    testing_notes: list[str] = Field(description="Guidance on how to test this code")


SYSTEM_PROMPT = """You are the **Coding Agent** for πX Technologies QORX.

Your role is to generate production-quality code based on plans and research.

**Responsibilities:**
1. Write clean, idiomatic code following language best practices
2. Include proper error handling, logging, and type hints
3. Follow the existing project conventions and architecture
4. Generate complete, runnable files (not snippets)
5. Include necessary imports, exports, and configurations

**Code quality rules:**
- Python: use type hints, async/await, proper docstrings, black formatting
- TypeScript: strict types, proper exports, eslint conventions
- Always handle edge cases and error states
- Include logging for production observability
- No placeholder comments or TODOs
- Every function must have a clear purpose

**Output rules:**
- Each file must be complete and self-contained
- Explain the architecture and why decisions were made
- List all dependencies needed
- Include setup instructions
- Flag any breaking changes"""


class CodingAgent(NodeAgent):
    @property
    def name(self) -> str:
        return "Coder"

    @property
    def description(self) -> str:
        return "Generates production-quality code with full files, dependencies, and setup instructions"

    @property
    def system_prompt(self) -> str:
        return SYSTEM_PROMPT

    @property
    def output_schema(self) -> type[BaseModel]:
        return CodingOutput

    @property
    def tools(self) -> list[BaseTool]:
        return get_registry().get_tools_for_role("coder")

    def _fallback_output(self, input_text: str, error: str) -> BaseModel:
        return CodingOutput(
            files=[],
            explanation=f"Code generation failed: {error}. The request could not be completed.",
            dependencies=[],
            setup_instructions=["Check LLM availability and retry"],
            breaking_changes=False,
            testing_notes=["No code was generated"],
        )


def create_coding_agent(settings, **kwargs: Any) -> CodingAgent:
    return CodingAgent(settings=settings, **kwargs)
