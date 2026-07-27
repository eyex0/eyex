from __future__ import annotations

import asyncio
import logging
import os
import shlex
import sys
import tempfile
from pathlib import Path

from langchain_core.tools import tool

logger = logging.getLogger("eyex.tools.code")

_SAFE_COMMANDS = frozenset({
    "python", "python3", "pip", "pip3", "npm", "npx", "node",
    "git", "ls", "cat", "pwd", "echo", "mkdir", "cp", "mv",
    "rm", "touch", "chmod", "head", "tail", "wc", "sort",
    "grep", "find", "diff", "which", "type",
})

_WINDOWS_SHELL_BUILTINS = frozenset({
    "echo", "dir", "type", "copy", "move", "del", "ren", "md", "rd",
    "cd", "cls", "date", "time", "ver", "vol", "title", "color",
    "prompt", "path", "set", "shift", "assoc", "ftype",
})


def _is_windows() -> bool:
    return sys.platform == "win32"


def _resolve_command(cmd_parts: list[str]) -> list[str]:
    if not _is_windows():
        return cmd_parts
    base = cmd_parts[0].lower()
    if base in _WINDOWS_SHELL_BUILTINS:
        return ["cmd.exe", "/c"] + cmd_parts
    return cmd_parts


@tool
async def execute_command(command: str, workdir: str | None = None, timeout: int = 30) -> str:
    """Execute a shell command in a restricted environment. Only safe commands are allowed. Returns stdout + stderr."""
    cmd_parts = shlex.split(command)
    if not cmd_parts:
        return "Error: Empty command"

    base = cmd_parts[0].lower()
    if base not in _SAFE_COMMANDS:
        return (
            f"Error: Command '{base}' is not allowed. "
            f"Allowed: {', '.join(sorted(_SAFE_COMMANDS))}"
        )

    dangerous = {"&&", "||", ";", "|", "$(", "`"}
    for part in cmd_parts:
        for sym in dangerous:
            if sym in part:
                return f"Error: Command contains shell metacharacter '{sym}'"

    resolved = _resolve_command(cmd_parts)

    try:
        cwd = str(Path(workdir).resolve()) if workdir else None
        proc = await asyncio.create_subprocess_exec(
            *resolved,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=cwd,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)

        result_parts = []
        if stdout:
            decoded = stdout.decode("utf-8", errors="replace").strip()
            if decoded:
                result_parts.append(decoded)
        if stderr:
            decoded = stderr.decode("utf-8", errors="replace").strip()
            if decoded:
                result_parts.append(f"[STDERR]\n{decoded}")

        output = "\n".join(result_parts) if result_parts else "(no output)"
        logger.info("Command '%s' exited with code %s", command, proc.returncode)
        return f"Exit code: {proc.returncode}\n{output}"
    except TimeoutError:
        return f"Error: Command timed out after {timeout} seconds"
    except FileNotFoundError:
        return f"Error: '{base}' not found or invalid command"
    except Exception as exc:
        logger.error("Command failed: %s", exc)
        return f"Error executing command: {exc}"


@tool
async def run_python_code(code: str, workdir: str | None = None) -> str:
    """Execute Python code in an isolated subprocess and return stdout + stderr. All imports must be in the code."""
    tmp = None
    try:
        tmp_dir = Path(tempfile.mkdtemp(prefix="eyex_code_"))
        tmp = tmp_dir / "_exec.py"
        tmp.write_text(code, encoding="utf-8")

        cwd = str(Path(workdir).resolve()) if workdir else str(tmp_dir)
        proc = await asyncio.create_subprocess_exec(
            sys.executable, str(tmp),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=cwd,
            env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=30)

        result_parts = []
        if stdout:
            decoded = stdout.decode("utf-8", errors="replace").strip()
            if decoded:
                result_parts.append(decoded)
        if stderr:
            decoded = stderr.decode("utf-8", errors="replace").strip()
            if decoded:
                result_parts.append(f"[STDERR]\n{decoded}")

        output = "\n".join(result_parts) if result_parts else "(no output)"
        return f"Exit code: {proc.returncode}\n{output}"
    except TimeoutError:
        return "Error: Python execution timed out after 30 seconds"
    except Exception as exc:
        logger.error("Python execution failed: %s", exc)
        return f"Error executing Python code: {exc}"
    finally:
        if tmp and tmp.exists():
            tmp.unlink()
        if tmp and tmp.parent.exists():
            import shutil
            shutil.rmtree(tmp.parent, ignore_errors=True)


@tool
async def run_javascript(code: str, workdir: str | None = None) -> str:
    """Execute JavaScript code using Node.js in an isolated subprocess. Returns stdout + stderr."""
    tmp = None
    try:
        tmp_dir = Path(tempfile.mkdtemp(prefix="eyex_js_"))
        tmp = tmp_dir / "_exec.mjs"
        tmp.write_text(code, encoding="utf-8")

        cwd = str(Path(workdir).resolve()) if workdir else str(tmp_dir)
        proc = await asyncio.create_subprocess_exec(
            "node", str(tmp),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=cwd,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=30)

        result_parts = []
        if stdout:
            decoded = stdout.decode("utf-8", errors="replace").strip()
            if decoded:
                result_parts.append(decoded)
        if stderr:
            decoded = stderr.decode("utf-8", errors="replace").strip()
            if decoded:
                result_parts.append(f"[STDERR]\n{decoded}")

        output = "\n".join(result_parts) if result_parts else "(no output)"
        return f"Exit code: {proc.returncode}\n{output}"
    except TimeoutError:
        return "Error: JavaScript execution timed out after 30 seconds"
    except FileNotFoundError:
        return "Error: Node.js not found. Ensure Node.js is installed and on PATH."
    except Exception as exc:
        logger.error("JavaScript execution failed: %s", exc)
        return f"Error executing JavaScript code: {exc}"
    finally:
        if tmp and tmp.exists():
            tmp.unlink()
        if tmp and tmp.parent.exists():
            import shutil
            shutil.rmtree(tmp.parent, ignore_errors=True)


@tool
async def list_running_processes() -> str:
    """List currently running processes (cross-platform). Returns PID, name, and memory usage."""
    import platform
    system = platform.system().lower()
    try:
        if system == "windows":
            proc = await asyncio.create_subprocess_exec(
                "tasklist", "/FO", "CSV", "/NH",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=10)
            if stdout:
                lines = stdout.decode("utf-8", errors="replace").strip().splitlines()
                processes = []
                for line in lines[:50]:
                    parts = [p.strip('" ') for p in line.split(",")]
                    if len(parts) >= 5:
                        processes.append(f"  {parts[0]} (PID: {parts[1]}, Mem: {parts[4]})")
                return f"Processes (top {len(processes)}):\n" + "\n".join(processes)
        else:
            proc = await asyncio.create_subprocess_exec(
                "ps", "aux", "--sort=-%mem",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=10)
            if stdout:
                lines = stdout.decode("utf-8", errors="replace").strip().splitlines()
                header = lines[0] if lines else ""
                data = lines[1:21] if len(lines) > 1 else []
                return f"Processes:\n{header}\n" + "\n".join(data)
        return "(no process information available)"
    except Exception as exc:
        logger.error("Failed to list processes: %s", exc)
        return f"Error listing processes: {exc}"


@tool
async def tail_file(file_path: str, lines: int = 20) -> str:
    """Read the last N lines of a file. Useful for checking recent logs or output."""
    try:
        path = Path(file_path).resolve()
        if not path.exists():
            return f"Error: File not found at {path}"
        if not path.is_file():
            return f"Error: {path} is not a file"

        content = path.read_text(encoding="utf-8", errors="replace")
        all_lines = content.splitlines()
        tail = all_lines[-min(lines, len(all_lines)):]
        result = "\n".join(tail)
        logger.info("Tailed %d lines from %s (total %d lines)", len(tail), path, len(all_lines))
        return f"Last {len(tail)} lines of {file_path} (total {len(all_lines)} lines):\n{result}"
    except PermissionError:
        return f"Error: Permission denied reading {file_path}"
    except Exception as exc:
        logger.error("Failed to tail file %s: %s", file_path, exc)
        return f"Error tailing file: {exc}"
