from __future__ import annotations

import asyncio
import logging
import re
from pathlib import Path

from langchain_core.tools import tool

logger = logging.getLogger("pix.tools.file")

_BASE_DIR = Path.cwd().resolve()
_ALLOWED_DIRS = frozenset({_BASE_DIR, _BASE_DIR / "data", _BASE_DIR / "uploads"})


def _resolve_path(file_path: str) -> Path:
    return Path(file_path).resolve()


def _assert_safe_path(path: Path) -> None:
    if not path.exists():
        return
    try:
        path.relative_to(_BASE_DIR)
    except ValueError:
        for allowed in _ALLOWED_DIRS:
            try:
                path.relative_to(allowed)
                return
            except ValueError:
                continue
        raise PermissionError(f"Path '{path}' is outside the allowed working directory '{_BASE_DIR}'")


@tool
async def read_file(file_path: str) -> str:
    """Read the contents of a file at the given path. Returns the file content as a string."""
    try:
        path = _resolve_path(file_path)
        if not path.exists():
            return f"Error: File not found at {path}"
        if not path.is_file():
            return f"Error: {path} is not a file"
        content = await asyncio.to_thread(path.read_text, encoding="utf-8")
        logger.info("Read file %s (%d bytes)", path, len(content))
        return content
    except PermissionError:
        return f"Error: Permission denied reading {file_path}"
    except Exception as exc:
        logger.error("Failed to read file %s: %s", file_path, exc)
        return f"Error reading file: {exc}"


@tool
async def write_file(file_path: str, content: str) -> str:
    """Write content to a file at the given path. Creates parent directories if needed. Overwrites existing files."""
    try:
        path = _resolve_path(file_path)
        await asyncio.to_thread(path.parent.mkdir, parents=True, exist_ok=True)
        await asyncio.to_thread(path.write_text, content, encoding="utf-8")
        logger.info("Wrote file %s (%d bytes)", path, len(content))
        return f"Successfully wrote {len(content)} bytes to {path}"
    except PermissionError:
        return f"Error: Permission denied writing to {file_path}"
    except Exception as exc:
        logger.error("Failed to write file %s: %s", file_path, exc)
        return f"Error writing file: {exc}"


@tool
async def list_directory(dir_path: str) -> str:
    """List all files and directories in the given directory path with sizes."""
    try:
        path = _resolve_path(dir_path)
        if not path.exists():
            return f"Error: Directory not found at {path}"
        if not path.is_dir():
            return f"Error: {path} is not a directory"
        entries = []
        for entry in sorted(path.iterdir()):
            suffix = "/" if entry.is_dir() else ""
            if entry.is_file():
                size = entry.stat().st_size
                entries.append(f"{entry.name}{suffix}  ({size} bytes)")
            else:
                entries.append(f"{entry.name}{suffix}")
        result = "\n".join(entries) if entries else "(empty directory)"
        logger.info("Listed directory %s (%d entries)", path, len(entries))
        return result
    except PermissionError:
        return f"Error: Permission denied listing {dir_path}"
    except Exception as exc:
        logger.error("Failed to list directory %s: %s", dir_path, exc)
        return f"Error listing directory: {exc}"


@tool
async def search_files(pattern: str, path: str | None = None) -> str:
    """Search for files matching a glob pattern. Uses ** for recursive matching. Example: '**/*.py' or 'src/**/*.ts'."""
    try:
        search_root = _resolve_path(path) if path else _BASE_DIR
        if not search_root.exists():
            return f"Error: Search path not found at {search_root}"
        if not search_root.is_dir():
            return f"Error: {search_root} is not a directory"

        matches = list(sorted(search_root.rglob(pattern)))
        if not matches:
            return f"No files matching '{pattern}' found in {search_root}"

        lines = [f"Found {len(matches)} file(s) matching '{pattern}':"]
        for m in matches[:200]:
            try:
                rel = m.relative_to(_BASE_DIR)
            except ValueError:
                rel = m
            size = m.stat().st_size if m.is_file() else 0
            lines.append(f"  {rel}  ({size} bytes)" if m.is_file() else f"  {rel}/")

        if len(matches) > 200:
            lines.append(f"  ... and {len(matches) - 200} more")

        logger.info("Searched for '%s' in %s — %d matches", pattern, search_root, len(matches))
        return "\n".join(lines)
    except Exception as exc:
        logger.error("Failed to search files: %s", exc)
        return f"Error searching files: {exc}"


@tool
async def grep_files(pattern: str, path: str | None = None, include: str | None = None) -> str:
    """Search file contents using a regex pattern. Optionally filter by file glob (e.g. '*.py'). Returns matching lines."""
    try:
        search_root = _resolve_path(path) if path else _BASE_DIR
        if not search_root.exists():
            return f"Error: Search path not found at {search_root}"
        if not search_root.is_dir():
            return f"Error: {search_root} is not a directory"

        matches = []
        files_to_check = list(search_root.rglob(include)) if include else list(search_root.rglob("*"))
        regex = re.compile(pattern)

        for fpath in files_to_check:
            if not fpath.is_file():
                continue
            try:
                text = fpath.read_text(encoding="utf-8", errors="replace")
                for lineno, line in enumerate(text.splitlines(), 1):
                    if regex.search(line):
                        try:
                            rel = fpath.relative_to(_BASE_DIR)
                        except ValueError:
                            rel = fpath
                        matches.append(f"{rel}:{lineno}: {line.strip()[:200]}")
                        if len(matches) >= 200:
                            break
            except Exception:
                continue
            if len(matches) >= 200:
                break

        if not matches:
            return f"No matches for '{pattern}' in {search_root}"

        result = f"Found {len(matches)} match(es) for '{pattern}':\n" + "\n".join(matches)
        if len(matches) >= 200:
            result += "\n... (results truncated at 200 matches)"

        logger.info("Grep for '%s' in %s — %d matches", pattern, search_root, len(matches))
        return result
    except re.error as exc:
        return f"Error: Invalid regex pattern '{pattern}': {exc}"
    except Exception as exc:
        logger.error("Failed to grep files: %s", exc)
        return f"Error searching file contents: {exc}"


@tool
async def edit_file(file_path: str, old_string: str, new_string: str) -> str:
    """Perform an exact string replacement in a file. Replaces the first occurrence of old_string with new_string."""
    try:
        path = _resolve_path(file_path)
        if not path.exists():
            return f"Error: File not found at {path}"
        if not path.is_file():
            return f"Error: {path} is not a file"

        content = path.read_text(encoding="utf-8")
        if old_string not in content:
            return f"Error: old_string not found in {file_path}"
        if content.count(old_string) > 1:
            return f"Error: Found {content.count(old_string)} occurrences — provide more context to make old_string unique"

        new_content = content.replace(old_string, new_string, 1)
        path.write_text(new_content, encoding="utf-8")
        logger.info("Edited file %s — replaced %d chars with %d chars", path, len(old_string), len(new_string))
        return f"Successfully edited {path}"
    except PermissionError:
        return f"Error: Permission denied editing {file_path}"
    except Exception as exc:
        logger.error("Failed to edit file %s: %s", file_path, exc)
        return f"Error editing file: {exc}"


@tool
async def delete_file(file_path: str, recursive: bool = False) -> str:
    """Delete a file or directory. Set recursive=True to delete non-empty directories."""
    try:
        path = _resolve_path(file_path)
        if not path.exists():
            return f"Error: Path not found at {path}"

        if path.is_file():
            path.unlink()
            logger.info("Deleted file %s", path)
            return f"Successfully deleted file {path}"
        elif path.is_dir():
            if recursive:
                import shutil
                shutil.rmtree(path)
                logger.info("Deleted directory %s (recursive)", path)
                return f"Successfully deleted directory {path} and all contents"
            else:
                path.rmdir()
                logger.info("Deleted empty directory %s", path)
                return f"Successfully deleted empty directory {path}"
        return f"Error: Unknown path type for {path}"
    except OSError as exc:
        return f"Error deleting {file_path}: {exc}. Use recursive=True for non-empty directories."
    except Exception as exc:
        logger.error("Failed to delete %s: %s", file_path, exc)
        return f"Error deleting: {exc}"


@tool
async def move_file(source: str, destination: str) -> str:
    """Rename or move a file or directory from source to destination."""
    try:
        src = _resolve_path(source)
        dst = _resolve_path(destination)
        if not src.exists():
            return f"Error: Source not found at {src}"

        dst.parent.mkdir(parents=True, exist_ok=True)
        src.rename(dst)
        logger.info("Moved %s -> %s", src, dst)
        return f"Successfully moved {src} to {dst}"
    except PermissionError:
        return f"Error: Permission denied moving {source} to {destination}"
    except Exception as exc:
        logger.error("Failed to move %s -> %s: %s", source, destination, exc)
        return f"Error moving file: {exc}"
