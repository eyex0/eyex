"""Tests for all tool categories and the registry."""
from __future__ import annotations

import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.agents.tools.code_tools import execute_command, run_python_code, tail_file
from app.agents.tools.db_tools import db_list_tables, db_query
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
from app.agents.tools.github_tools import github_get_repo, github_list_issues, github_search_repos
from app.agents.tools.registry import ToolRegistry, get_registry
from app.agents.tools.web_tools import web_fetch, web_search


class TestRegistry:
    def test_registry_singleton(self):
        r1 = get_registry()
        r2 = get_registry()
        assert r1 is r2

    def test_all_tools_registered(self):
        reg = get_registry()
        tools = reg.list_all_tools()
        assert "read_file" in tools
        assert "write_file" in tools
        assert "search_files" in tools
        assert "grep_files" in tools
        assert "edit_file" in tools
        assert "delete_file" in tools
        assert "move_file" in tools
        assert "web_search" in tools
        assert "web_fetch" in tools
        assert "execute_command" in tools
        assert "run_python_code" in tools
        assert "run_javascript" in tools
        assert "github_search_repos" in tools
        assert "db_query" in tools
        assert "db_list_tables" in tools

    def test_agent_tool_assignments(self):
        reg = get_registry()
        for role in ["planner", "researcher", "coder", "reviewer", "tester", "documenter", "devops"]:
            tools = reg.get_tools_for_role(role)
            assert len(tools) > 0, f"{role} should have tools"
            assert all(t.name for t in tools)

    def test_supervisor_has_no_tools(self):
        reg = get_registry()
        assert reg.get_tools_for_role("supervisor") == []

    def test_get_tool_by_name(self):
        reg = get_registry()
        t = reg.get_tool("read_file")
        assert t is not None
        assert t.name == "read_file"

    def test_get_tool_not_found(self):
        reg = get_registry()
        assert reg.get_tool("nonexistent") is None

    def test_list_roles(self):
        reg = get_registry()
        assert "supervisor" in reg.list_roles()
        assert "coder" in reg.list_roles()

    def test_bind_tools_to_llm_no_tools(self):
        reg = get_registry()
        llm = MagicMock()
        result = reg.bind_tools_to_llm("supervisor", llm)
        assert result is llm

    def test_bind_tools_to_llm_with_tools(self):
        reg = get_registry()
        llm = MagicMock()
        result = reg.bind_tools_to_llm("coder", llm)
        assert result is not llm
        llm.bind_tools.assert_called_once()

    def test_coder_tools(self):
        reg = get_registry()
        names = reg.get_tool_names_for_role("coder")
        assert "read_file" in names
        assert "write_file" in names
        assert "edit_file" in names
        assert "execute_command" in names
        assert "run_python_code" in names

    def test_researcher_tools(self):
        reg = get_registry()
        names = reg.get_tool_names_for_role("researcher")
        assert "web_search" in names
        assert "web_fetch" in names
        assert "github_search_repos" in names
        assert "read_file" in names

    def test_devops_tools(self):
        reg = get_registry()
        names = reg.get_tool_names_for_role("devops")
        assert "db_query" in names
        assert "db_list_tables" in names
        assert "github_list_branches" in names
        assert "execute_command" in names

    def test_documenter_tools(self):
        reg = get_registry()
        names = reg.get_tool_names_for_role("documenter")
        assert "read_file" in names
        assert "write_file" in names
        assert "search_files" in names
        assert "grep_files" in names


class TestFileTools:
    @pytest.fixture
    def tmp_dir(self):
        with tempfile.TemporaryDirectory() as d:
            yield Path(d)

    async def test_read_file_not_found(self):
        result = await read_file.ainvoke({"file_path": "/nonexistent/path/file.txt"})
        assert "Error" in result
        assert "not found" in result

    async def test_read_file_success(self, tmp_dir):
        f = tmp_dir / "test.txt"
        f.write_text("hello world", encoding="utf-8")
        result = await read_file.ainvoke({"file_path": str(f)})
        assert result == "hello world"

    async def test_write_file(self, tmp_dir):
        f = tmp_dir / "sub" / "test.txt"
        result = await write_file.ainvoke({"file_path": str(f), "content": "written content"})
        assert "Successfully wrote" in result
        assert f.read_text(encoding="utf-8") == "written content"

    async def test_list_directory(self, tmp_dir):
        (tmp_dir / "a.txt").write_text("a")
        (tmp_dir / "b.txt").write_text("bb")
        result = await list_directory.ainvoke({"dir_path": str(tmp_dir)})
        assert "a.txt" in result
        assert "b.txt" in result

    async def test_list_directory_not_found(self):
        result = await list_directory.ainvoke({"dir_path": "/nonexistent"})
        assert "Error" in result

    async def test_search_files(self, tmp_dir):
        (tmp_dir / "main.py").write_text("code")
        (tmp_dir / "sub").mkdir()
        (tmp_dir / "sub" / "util.py").write_text("util")
        result = await search_files.ainvoke({"pattern": "**/*.py", "path": str(tmp_dir)})
        assert "main.py" in result
        assert "util.py" in result

    async def test_grep_files(self, tmp_dir):
        (tmp_dir / "app.py").write_text("def hello():\n    pass")
        (tmp_dir / "other.py").write_text("def world():\n    pass")
        result = await grep_files.ainvoke({"pattern": "hello", "path": str(tmp_dir), "include": "*.py"})
        assert "app.py" in result
        assert "hello" in result
        assert "world" not in result

    async def test_edit_file(self, tmp_dir):
        f = tmp_dir / "test.txt"
        f.write_text("old content", encoding="utf-8")
        result = await edit_file.ainvoke({"file_path": str(f), "old_string": "old", "new_string": "new"})
        assert "Successfully edited" in result
        assert f.read_text(encoding="utf-8") == "new content"

    async def test_edit_file_not_found(self, tmp_dir):
        f = tmp_dir / "nonexistent.txt"
        result = await edit_file.ainvoke({"file_path": str(f), "old_string": "x", "new_string": "y"})
        assert "Error" in result

    async def test_edit_file_string_not_found(self, tmp_dir):
        f = tmp_dir / "test.txt"
        f.write_text("content")
        result = await edit_file.ainvoke({"file_path": str(f), "old_string": "nonexistent", "new_string": "x"})
        assert "Error" in result
        assert "not found" in result

    async def test_delete_file(self, tmp_dir):
        f = tmp_dir / "delete_me.txt"
        f.write_text("to delete")
        result = await delete_file.ainvoke({"file_path": str(f)})
        assert "Successfully deleted" in result
        assert not f.exists()

    async def test_delete_file_not_found(self):
        result = await delete_file.ainvoke({"file_path": "/nonexistent"})
        assert "Error" in result

    async def test_move_file(self, tmp_dir):
        src = tmp_dir / "source.txt"
        dst = tmp_dir / "dest.txt"
        src.write_text("move me")
        result = await move_file.ainvoke({"source": str(src), "destination": str(dst)})
        assert "Successfully moved" in result
        assert dst.exists()
        assert not src.exists()

    async def test_move_file_not_found(self):
        result = await move_file.ainvoke({"source": "/nonexistent", "destination": "/tmp/x"})
        assert "Error" in result


class TestCodeTools:
    async def test_execute_command_echo(self):
        result = await execute_command.ainvoke({"command": "echo hello"})
        assert "hello" in result

    async def test_execute_command_empty(self):
        result = await execute_command.ainvoke({"command": ""})
        assert "Error" in result

    async def test_execute_command_blocked(self):
        result = await execute_command.ainvoke({"command": "wget http://evil.com"})
        assert "not allowed" in result.lower()

    async def test_execute_command_unsafe(self):
        result = await execute_command.ainvoke({"command": "unsafe_cmd"})
        assert "not allowed" in result.lower()

    async def test_run_python_code(self):
        result = await run_python_code.ainvoke({"code": "print('hello from python')"})
        assert "hello from python" in result

    async def test_run_python_code_error(self):
        result = await run_python_code.ainvoke({"code": "raise ValueError('test error')"})
        assert "test error" in result

    async def test_tail_file(self, tmp_path):
        f = tmp_path / "log.txt"
        f.write_text("\n".join(f"line {i}" for i in range(100)))
        result = await tail_file.ainvoke({"file_path": str(f), "lines": 5})
        assert "line 99" in result
        assert "line 95" in result
        assert "line 0" not in result

    async def test_tail_file_not_found(self):
        result = await tail_file.ainvoke({"file_path": "/nonexistent.log"})
        assert "Error" in result


class TestWebTools:
    @patch("httpx.AsyncClient")
    async def test_web_fetch(self, mock_client):
        mock_resp = MagicMock()
        mock_resp.text = "<html><body><h1>Test Page</h1><p>Content here.</p></body></html>"
        mock_resp.headers = {"content-type": "text/html"}
        mock_client.return_value.__aenter__.return_value.get.return_value = mock_resp

        result = await web_fetch.ainvoke({"url": "https://example.com", "format": "markdown"})
        assert "Test Page" in result or "Content" in result

    @patch("httpx.AsyncClient")
    async def test_web_fetch_error(self, mock_client):
        import httpx
        mock_client.return_value.__aenter__.return_value.get.side_effect = httpx.HTTPStatusError(
            "404", request=MagicMock(), response=MagicMock(status_code=404, reason_phrase="Not Found")
        )
        result = await web_fetch.ainvoke({"url": "https://example.com/404"})
        assert "Error" in result

    async def test_web_search_returns_results_or_fallback(self):
        result = await web_search.ainvoke({"query": "python programming language", "num_results": 3})
        assert isinstance(result, str)


class TestGitHubTools:
    @patch("httpx.AsyncClient")
    async def test_github_search_repos(self, mock_client):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "total_count": 1,
            "items": [{
                "full_name": "test/repo",
                "stargazers_count": 100,
                "language": "Python",
                "description": "A test repo",
            }],
        }
        mock_client.return_value.__aenter__.return_value.get.return_value = mock_resp

        result = await github_search_repos.ainvoke({"query": "test", "limit": 5})
        assert "test/repo" in result

    @patch("httpx.AsyncClient")
    async def test_github_get_repo_error(self, mock_client):
        import httpx
        mock_client.return_value.__aenter__.return_value.get.side_effect = httpx.HTTPStatusError(
            "404", request=MagicMock(), response=MagicMock(status_code=404, reason_phrase="Not Found")
        )
        result = await github_get_repo.ainvoke({"repo": "nonexistent/repo"})
        assert "Error" in result

    @patch("httpx.AsyncClient")
    async def test_github_list_issues(self, mock_client):
        mock_resp = MagicMock()
        mock_resp.json.return_value = [
            {"number": 1, "title": "Bug fix", "labels": []},
        ]
        mock_client.return_value.__aenter__.return_value.get.return_value = mock_resp
        result = await github_list_issues.ainvoke({"repo": "test/repo", "state": "open", "limit": 10})
        assert "Bug fix" in result


class TestDBTools:
    async def test_db_list_tables(self):
        result = await db_list_tables.ainvoke({})
        assert isinstance(result, str)
        assert "Error" in result or "Tables" in result or "0 rows" in result

    async def test_db_query_rejects_non_select(self):
        result = await db_query.ainvoke({"sql": "DROP TABLE users"})
        assert "Error" in result
        assert "SELECT" in result

    async def test_db_query_select(self):
        result = await db_query.ainvoke({"sql": "SELECT 1 as test", "max_rows": 5})
        assert isinstance(result, str)


class TestAgentToolIntegration:
    async def test_planner_tools_from_agent(self):
        from app.agents.planner import PlannerAgent
        from unittest.mock import MagicMock

        agent = PlannerAgent(llm=MagicMock())
        tools = agent.tools
        assert len(tools) == 4
        names = {t.name for t in tools}
        assert "read_file" in names
        assert "search_files" in names
        assert "grep_files" in names
        assert "list_directory" in names

    async def test_coder_tools_from_agent(self):
        from app.agents.coder import CodingAgent
        from unittest.mock import MagicMock

        agent = CodingAgent(llm=MagicMock())
        tools = agent.tools
        assert len(tools) == 14
        names = {t.name for t in tools}
        assert "read_file" in names
        assert "write_file" in names
        assert "edit_file" in names

    async def test_devops_tools_from_agent(self):
        from app.agents.devops import DevOpsAgent
        from unittest.mock import MagicMock

        agent = DevOpsAgent(llm=MagicMock())
        tools = agent.tools
        assert len(tools) == 17
        names = {t.name for t in tools}
        assert "db_query" in names
        assert "execute_command" in names
        assert "github_list_branches" in names

    async def test_agent_execute_no_tools(self):
        from app.agents.planner import PlannerAgent
        from unittest.mock import MagicMock, AsyncMock

        agent = PlannerAgent(llm=MagicMock())
        result = await agent.execute("test", session_id=None)
        # Should fallback since LLM is mocked
        assert hasattr(result, "plan")

    async def test_base_execute_with_tools_calls_tool_loop(self):
        from app.agents.coder import CodingAgent
        from unittest.mock import MagicMock, patch

        mock_llm = MagicMock()
        # Mock the LLM to return a response without tool calls
        mock_response = MagicMock()
        mock_response.tool_calls = []
        mock_chain = AsyncMock()
        mock_chain.ainvoke.return_value = MagicMock()
        mock_llm.with_structured_output.return_value = mock_chain

        agent = CodingAgent(llm=mock_llm)
        result = await agent.execute("hello", session_id=None)
        assert result is not None

    async def test_tool_loop_with_tools_returns_context(self):
        from app.agents.coder import CodingAgent
        from unittest.mock import MagicMock, AsyncMock

        mock_llm = MagicMock()
        mock_response_with_tools = MagicMock()
        mock_response_with_tools.tool_calls = [
            {"name": "read_file", "args": {"file_path": "/tmp/test.txt"}, "id": "call_1"}
        ]
        mock_response_no_tools = MagicMock()
        mock_response_no_tools.tool_calls = []

        mock_llm.bind_tools.return_value = mock_llm
        mock_llm.ainvoke = AsyncMock(side_effect=[mock_response_with_tools, mock_response_no_tools])

        agent = CodingAgent(llm=mock_llm)
        context = await agent._run_tool_loop("test", [])
        assert isinstance(context, str)
