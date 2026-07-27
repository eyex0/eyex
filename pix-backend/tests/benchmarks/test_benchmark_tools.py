"""Benchmark tool execution speed for file operations, search/grep, and registry lookups."""
from __future__ import annotations

import tempfile
import time
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.agents.tools.file_tools import grep_files, read_file, search_files, write_file
from app.agents.tools.registry import ToolRegistry, get_registry


class TestFileToolBenchmarks:
    @pytest.fixture
    def tmp_dir(self):
        with tempfile.TemporaryDirectory() as d:
            yield Path(d)

    async def test_read_file_speed(self, tmp_dir):
        f = tmp_dir / "test.txt"
        f.write_text("x" * 10000, encoding="utf-8")
        times = []
        for _ in range(50):
            start = time.perf_counter()
            await read_file.ainvoke({"file_path": str(f)})
            elapsed = (time.perf_counter() - start) * 1000
            times.append(elapsed)
        avg = sum(times) / len(times)
        assert avg < 50, f"read_file avg {avg:.2f}ms exceeded 50ms"

    async def test_write_file_speed(self, tmp_path):
        f = tmp_path / "bench_write.txt"
        times = []
        for _ in range(20):
            start = time.perf_counter()
            await write_file.ainvoke({"file_path": str(f), "content": "x" * 1000})
            elapsed = (time.perf_counter() - start) * 1000
            times.append(elapsed)
        avg = sum(times) / len(times)
        assert avg < 50, f"write_file avg {avg:.2f}ms exceeded 50ms"


class TestSearchGrepBenchmark:
    @pytest.fixture
    def tmp_dir_with_files(self):
        with tempfile.TemporaryDirectory() as d:
            base = Path(d)
            for i in range(20):
                (base / f"file_{i}.py").write_text(f"def func_{i}():\n    return {i}\n")
            (base / "sub").mkdir()
            for i in range(10):
                (base / "sub" / f"util_{i}.py").write_text(f"def util_{i}():\n    return {i}\n")
            yield base

    async def test_search_files_speed(self, tmp_path):
        for i in range(50):
            (tmp_path / f"file_{i}.py").write_text(f"def func_{i}():\n    return {i}\n")
        times = []
        for _ in range(20):
            start = time.perf_counter()
            await search_files.ainvoke({"pattern": "**/*.py", "path": str(tmp_path)})
            elapsed = (time.perf_counter() - start) * 1000
            times.append(elapsed)
        avg = sum(times) / len(times)
        assert avg < 100, f"search_files avg {avg:.2f}ms exceeded 100ms"

    async def test_grep_small_pattern(self, tmp_path):
        for i in range(20):
            (tmp_path / f"file_{i}.py").write_text(f"def func_{i}():\n    return {i}\n")
        times = []
        for _ in range(20):
            start = time.perf_counter()
            await grep_files.ainvoke({"pattern": "def func_1", "path": str(tmp_path), "include": "*.py"})
            elapsed = (time.perf_counter() - start) * 1000
            times.append(elapsed)
        avg = sum(times) / len(times)
        assert avg < 100, f"grep_files avg {avg:.2f}ms exceeded 100ms"

    async def test_grep_large_pattern(self, tmp_path):
        for i in range(50):
            (tmp_path / f"file_{i}.py").write_text(f"def func_{i}():\n    return {i}\n")
        times = []
        for _ in range(20):
            start = time.perf_counter()
            await grep_files.ainvoke({"pattern": "def func_", "path": str(tmp_path), "include": "*.py"})
            elapsed = (time.perf_counter() - start) * 1000
            times.append(elapsed)
        avg = sum(times) / len(times)
        assert avg < 200, f"grep large pattern avg {avg:.2f}ms exceeded 200ms"


class TestRegistryLookupBenchmark:
    def test_registry_lookup_speed(self):
        from app.agents.tools.registry import get_registry

        reg = get_registry()
        times = []
        for _ in range(1000):
            start = time.perf_counter()
            _ = reg.get_tool("read_file")
            _ = reg.get_tool("write_file")
            _ = reg.get_tool("web_search")
            _ = reg.get_tool("grep_files")
            _ = reg.get_tool("execute_command")
            elapsed = (time.perf_counter() - start) * 1000
            times.append(elapsed)
        avg = sum(times) / len(times)
        assert avg < 1, f"Registry lookup avg {avg:.4f}ms exceeded 1ms"

    def test_registry_list_all_tools_speed(self):
        from app.agents.tools.registry import get_registry

        reg = get_registry()
        times = []
        for _ in range(1000):
            start = time.perf_counter()
            _ = reg.list_all_tools()
            elapsed = (time.perf_counter() - start) * 1000
            times.append(elapsed)
        avg = sum(times) / len(times)
        assert avg < 1, f"Registry list_all_tools avg {avg:.4f}ms exceeded 1ms"
