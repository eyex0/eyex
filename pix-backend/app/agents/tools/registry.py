from __future__ import annotations

from typing import Any

from langchain_core.tools import BaseTool

from app.agents.tools.code_tools import (
    execute_command,
    list_running_processes,
    run_javascript,
    run_python_code,
    tail_file,
)
from app.agents.tools.db_tools import db_describe_table, db_execute, db_list_tables, db_query
from app.agents.tools.file_tools import (
    delete_file,
    edit_file,
    grep_files,
    list_directory,
    move_file,
    read_file,
    search_files,
    write_file,
)
from app.agents.tools.github_tools import (
    github_create_issue,
    github_create_pull_request,
    github_get_file_contents,
    github_get_pull_request,
    github_get_repo,
    github_list_branches,
    github_list_issues,
    github_list_pull_requests,
    github_search_repos,
)
from app.agents.tools.web_tools import web_fetch, web_search

_ALL_TOOLS: dict[str, BaseTool] = {}


def _register(t: BaseTool) -> BaseTool:
    _ALL_TOOLS[t.name] = t
    return t


_read_file = _register(read_file)
_write_file = _register(write_file)
_list_directory = _register(list_directory)
_search_files = _register(search_files)
_grep_files = _register(grep_files)
_edit_file = _register(edit_file)
_delete_file = _register(delete_file)
_move_file = _register(move_file)

_github_search_repos = _register(github_search_repos)
_github_get_repo = _register(github_get_repo)
_github_list_issues = _register(github_list_issues)
_github_create_issue = _register(github_create_issue)
_github_list_pull_requests = _register(github_list_pull_requests)
_github_get_pull_request = _register(github_get_pull_request)
_github_create_pull_request = _register(github_create_pull_request)
_github_get_file_contents = _register(github_get_file_contents)
_github_list_branches = _register(github_list_branches)

_web_search = _register(web_search)
_web_fetch = _register(web_fetch)

_execute_command = _register(execute_command)
_run_python_code = _register(run_python_code)
_run_javascript = _register(run_javascript)
_list_running_processes = _register(list_running_processes)
_tail_file = _register(tail_file)

_db_query = _register(db_query)
_db_execute = _register(db_execute)
_db_list_tables = _register(db_list_tables)
_db_describe_table = _register(db_describe_table)

_AGENT_TOOLS: dict[str, list[str]] = {
    "supervisor": [],
    "planner": [
        "read_file",
        "search_files",
        "grep_files",
        "list_directory",
    ],
    "researcher": [
        "read_file",
        "search_files",
        "grep_files",
        "web_search",
        "web_fetch",
        "github_search_repos",
        "github_get_repo",
        "github_get_file_contents",
    ],
    "coder": [
        "read_file",
        "write_file",
        "edit_file",
        "delete_file",
        "move_file",
        "list_directory",
        "search_files",
        "grep_files",
        "execute_command",
        "run_python_code",
        "run_javascript",
        "github_get_file_contents",
        "github_list_branches",
        "github_search_repos",
    ],
    "reviewer": [
        "read_file",
        "search_files",
        "grep_files",
        "list_directory",
        "tail_file",
    ],
    "tester": [
        "read_file",
        "write_file",
        "edit_file",
        "list_directory",
        "search_files",
        "grep_files",
        "execute_command",
        "run_python_code",
        "run_javascript",
    ],
    "documenter": [
        "read_file",
        "write_file",
        "list_directory",
        "search_files",
        "grep_files",
    ],
    "devops": [
        "read_file",
        "write_file",
        "edit_file",
        "list_directory",
        "search_files",
        "grep_files",
        "execute_command",
        "run_python_code",
        "tail_file",
        "list_running_processes",
        "db_query",
        "db_list_tables",
        "db_describe_table",
        "github_list_branches",
        "github_list_pull_requests",
        "github_get_pull_request",
        "github_get_repo",
    ],
}


class ToolRegistry:
    """Central registry for all agent tools. Maps agent roles to their authorized tool sets."""

    def __init__(self) -> None:
        self._all_tools = dict(_ALL_TOOLS)
        self._agent_tool_map = dict(_AGENT_TOOLS)

    def get_tool(self, name: str) -> BaseTool | None:
        return self._all_tools.get(name)

    def get_tools_for_role(self, role: str) -> list[BaseTool]:
        names = self._agent_tool_map.get(role, [])
        return [self._all_tools[n] for n in names if n in self._all_tools]

    def get_tool_names_for_role(self, role: str) -> list[str]:
        return list(self._agent_tool_map.get(role, []))

    def list_all_tools(self) -> dict[str, str]:
        return {name: tool.description[:80] for name, tool in sorted(self._all_tools.items())}

    def list_roles(self) -> list[str]:
        return list(self._agent_tool_map.keys())

    def bind_tools_to_llm(self, role: str, llm: Any) -> Any:
        tools = self.get_tools_for_role(role)
        if not tools:
            return llm
        return llm.bind_tools(tools)


_REGISTRY: ToolRegistry | None = None


def get_registry() -> ToolRegistry:
    global _REGISTRY
    if _REGISTRY is None:
        _REGISTRY = ToolRegistry()
    return _REGISTRY
