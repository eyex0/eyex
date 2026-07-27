from __future__ import annotations

import json
import logging
import os
from typing import Any

from langchain_core.tools import tool

logger = logging.getLogger("pix.tools.github")

_GITHUB_TOKEN: str | None = None
_GITHUB_API = "https://api.github.com"


def _configure_github() -> None:
    global _GITHUB_TOKEN
    if _GITHUB_TOKEN is None:
        _GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")


def _headers() -> dict[str, str]:
    _configure_github()
    h = {
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "πX-Agents/1.0",
    }
    if _GITHUB_TOKEN:
        h["Authorization"] = f"Bearer {_GITHUB_TOKEN}"
    return h


async def _gh_get(path: str, params: dict[str, Any] | None = None) -> dict[str, Any] | list[Any]:
    import httpx
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{_GITHUB_API}{path}",
            headers=_headers(),
            params=params,
            timeout=15,
        )
        resp.raise_for_status()
        return resp.json()


async def _gh_post(path: str, data: dict[str, Any]) -> dict[str, Any]:
    import httpx
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{_GITHUB_API}{path}",
            headers={**_headers(), "Content-Type": "application/json"},
            json=data,
            timeout=15,
        )
        resp.raise_for_status()
        return resp.json()


@tool
async def github_search_repos(query: str, limit: int = 10) -> str:
    """Search GitHub repositories by query. Returns repo name, description, stars, language, and URL."""
    try:
        data = await _gh_get("/search/repositories", {"q": query, "per_page": min(limit, 50), "sort": "stars"})
        items = data.get("items", [])[:limit]
        if not items:
            return f"No repositories found matching '{query}'"

        lines = [f"Found {data.get('total_count', 0)} repositories for '{query}' (showing top {len(items)}):\n"]
        for repo in items:
            lines.append(
                f"  {repo['full_name']}"
                f"  ⭐ {repo['stargazers_count']}"
                f"  [{repo.get('language', 'N/A')}]"
                f"  {repo.get('description', 'No description')[:120] or 'No description'}"
            )
        return "\n".join(lines)
    except Exception as exc:
        logger.error("GitHub search failed: %s", exc)
        return f"Error searching GitHub: {exc}"


@tool
async def github_get_repo(repo: str) -> str:
    """Get details about a GitHub repository. Format: 'owner/repo' (e.g. 'tensorflow/tensorflow')."""
    try:
        data = await _gh_get(f"/repos/{repo}")
        return (
            f"Repository: {data['full_name']}\n"
            f"Description: {data.get('description', 'N/A')}\n"
            f"Stars: {data.get('stargazers_count', 0)}\n"
            f"Forks: {data.get('forks_count', 0)}\n"
            f"Language: {data.get('language', 'N/A')}\n"
            f"License: {data.get('license', {}).get('spdx_id', 'N/A') if data.get('license') else 'N/A'}\n"
            f"Topics: {', '.join(data.get('topics', [])) or 'None'}\n"
            f"Default branch: {data.get('default_branch', 'main')}\n"
            f"Created: {data.get('created_at', 'N/A')}\n"
            f"Updated: {data.get('updated_at', 'N/A')}\n"
            f"URL: {data['html_url']}"
        )
    except Exception as exc:
        logger.error("GitHub get_repo failed: %s", exc)
        return f"Error getting repository: {exc}"


@tool
async def github_list_issues(repo: str, state: str = "open", limit: int = 20) -> str:
    """List issues for a GitHub repository. State: 'open', 'closed', 'all'."""
    try:
        data = await _gh_get(f"/repos/{repo}/issues", {"state": state, "per_page": min(limit, 100), "sort": "updated"})
        issues = [i for i in data if "pull_request" not in i][:limit]
        if not issues:
            return f"No {state} issues found for {repo}"

        lines = [f"{len(issues)} {state} issue(s) in {repo}:\n"]
        for issue in issues:
            labels = ", ".join(label["name"] for label in issue.get("labels", []))
            label_str = f" [{labels}]" if labels else ""
            lines.append(f"  #{issue['number']} {issue['title']}{label_str}")
        return "\n".join(lines)
    except Exception as exc:
        logger.error("GitHub list_issues failed: %s", exc)
        return f"Error listing issues: {exc}"


@tool
async def github_create_issue(repo: str, title: str, body: str, labels: list[str] | None = None) -> str:
    """Create a new issue on a GitHub repository."""
    try:
        data: dict[str, Any] = {"title": title, "body": body}
        if labels:
            data["labels"] = labels
        result = await _gh_post(f"/repos/{repo}/issues", data)
        return f"Issue created: #{result['number']} {result['title']}\nURL: {result['html_url']}"
    except Exception as exc:
        logger.error("GitHub create_issue failed: %s", exc)
        return f"Error creating issue: {exc}"


@tool
async def github_list_pull_requests(repo: str, state: str = "open", limit: int = 20) -> str:
    """List pull requests for a GitHub repository. State: 'open', 'closed', 'merged', 'all'."""
    try:
        params: dict[str, Any] = {"per_page": min(limit, 100), "sort": "updated"}
        if state != "all":
            params["state"] = state
        data = await _gh_get(f"/repos/{repo}/pulls", params)
        prs = data[:limit]
        if not prs:
            return f"No {state} pull requests found for {repo}"

        lines = [f"{len(prs)} {state} pull request(s) in {repo}:\n"]
        for pr in prs:
            lines.append(f"  #{pr['number']} {pr['title']} by {pr['user']['login']}")
        return "\n".join(lines)
    except Exception as exc:
        logger.error("GitHub list_prs failed: %s", exc)
        return f"Error listing pull requests: {exc}"


@tool
async def github_get_pull_request(repo: str, pr_number: int) -> str:
    """Get detailed information about a specific pull request."""
    try:
        data = await _gh_get(f"/repos/{repo}/pulls/{pr_number}")
        return (
            f"PR #{data['number']}: {data['title']}\n"
            f"State: {data.get('state', 'N/A')}\n"
            f"Author: {data['user']['login']}\n"
            f"Created: {data.get('created_at', 'N/A')}\n"
            f"Updated: {data.get('updated_at', 'N/A')}\n"
            f"Merged: {data.get('merged', False)}\n"
            f"Additions: {data.get('additions', 0)}\n"
            f"Deletions: {data.get('deletions', 0)}\n"
            f"Changed files: {data.get('changed_files', 0)}\n"
            f"Body: {data.get('body', 'No description')[:500] or 'No description'}\n"
            f"URL: {data['html_url']}"
        )
    except Exception as exc:
        logger.error("GitHub get_pr failed: %s", exc)
        return f"Error getting pull request: {exc}"


@tool
async def github_create_pull_request(repo: str, title: str, head: str, base: str, body: str = "", draft: bool = False) -> str:
    """Create a pull request on a GitHub repository."""
    try:
        result = await _gh_post(f"/repos/{repo}/pulls", {
            "title": title,
            "head": head,
            "base": base,
            "body": body,
            "draft": draft,
        })
        return f"PR created: #{result['number']} {result['title']}\nURL: {result['html_url']}"
    except Exception as exc:
        logger.error("GitHub create_pr failed: %s", exc)
        return f"Error creating pull request: {exc}"


@tool
async def github_get_file_contents(repo: str, path: str, ref: str = "main") -> str:
    """Get the contents of a file from a GitHub repository at a specific branch/ref."""
    try:
        data = await _gh_get(f"/repos/{repo}/contents/{path}", {"ref": ref})
        if isinstance(data, dict) and data.get("content"):
            import base64
            content = base64.b64decode(data["content"]).decode("utf-8")
            size = data.get("size", len(content))
            return f"File: {path} @ {repo}:{ref} ({size} bytes)\n\n{content}"
        return json.dumps(data, indent=2)[:2000]
    except Exception as exc:
        logger.error("GitHub get_file_contents failed: %s", exc)
        return f"Error getting file contents: {exc}"


@tool
async def github_list_branches(repo: str, limit: int = 30) -> str:
    """List branches for a GitHub repository."""
    try:
        data = await _gh_get(f"/repos/{repo}/branches", {"per_page": min(limit, 100)})
        if not data:
            return f"No branches found for {repo}"
        lines = [f"Branches in {repo} ({len(data)}):"]
        for branch in data:
            lines.append(f"  {branch['name']}")
        return "\n".join(lines)
    except Exception as exc:
        logger.error("GitHub list_branches failed: %s", exc)
        return f"Error listing branches: {exc}"
