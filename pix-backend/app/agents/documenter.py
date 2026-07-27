from __future__ import annotations

from typing import Any

from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field

from packages.cognitive-kernel.agent-runtime import NodeAgent
from packages.cognitive-kernel.agent-runtime.tools import get_registry


class DocFile(BaseModel):
    path: str = Field(description="Relative documentation file path (e.g. docs/api.md)")
    content: str = Field(description="Complete documentation file content in Markdown")
    title: str = Field(description="Document title")
    audience: str = Field(description="Target audience: 'developer', 'user', 'admin', 'architect'")


class DocumentationOutput(BaseModel):
    files: list[DocFile] = Field(description="Documentation files to create with full content")
    summary: str = Field(description="Overview of the documentation produced")
    key_decisions: list[str] = Field(description="Key architectural or design decisions documented")
    missing_docs: list[str] = Field(description="Areas that still need documentation")
    recommendations: list[str] = Field(description="Documentation improvements and next steps")


SYSTEM_PROMPT = """You are the **Documentation Agent** for πX Technologies QORX.

Your role is to create clear, comprehensive, and well-structured documentation.

**Documentation types you produce:**
1. **API documentation**: Endpoints, request/response schemas, authentication, error codes
2. **Architecture documentation**: System design, component relationships, data flow
3. **Setup guides**: Installation, configuration, environment setup
4. **User guides**: How to use features, workflows, troubleshooting
5. **Developer guides**: Code conventions, project structure, contributing

**Documentation quality rules:**
- Write in clear, concise English
- Use proper Markdown formatting
- Include code examples for developer docs
- Structure with clear headings and subheadings
- Include a table of contents for longer docs
- Link to related documentation
- Keep audience in mind (developer vs end-user)

**Markdown conventions:**
- Use `# Heading` for title, `##` for sections, `###` for subsections
- Use `code blocks` with language tags
- Use tables for structured data
- Use lists for steps and features
- Use `> Note:` and `> Warning:` callouts

Never generate placeholder documentation. Every doc must be complete and accurate."""


class DocumentationAgent(NodeAgent):
    @property
    def name(self) -> str:
        return "Documenter"

    @property
    def description(self) -> str:
        return "Creates comprehensive, well-structured documentation in Markdown"

    @property
    def system_prompt(self) -> str:
        return SYSTEM_PROMPT

    @property
    def output_schema(self) -> type[BaseModel]:
        return DocumentationOutput

    @property
    def tools(self) -> list[BaseTool]:
        return get_registry().get_tools_for_role("documenter")

    def _fallback_output(self, input_text: str, error: str) -> BaseModel:
        return DocumentationOutput(
            files=[],
            summary=f"Documentation could not be generated: {error}",
            key_decisions=[],
            missing_docs=["All documentation needs to be created manually"],
            recommendations=["Re-run documentation agent when available"],
        )


def create_documentation_agent(settings, **kwargs: Any) -> DocumentationAgent:
    return DocumentationAgent(settings=settings, **kwargs)
