"""Auto-generate tool documentation from the ToolRegistry.

Usage:
    python scripts/generate_tool_docs.py [output_path]

Defaults to docs/tools.md if no output path given.
"""
from __future__ import annotations

import sys
from pathlib import Path


def generate_tool_docs(output_path: str | None = None) -> str:
    """Generate Markdown documentation for all registered tools."""
    # Import must happen after path is set up
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    
    from app.agents.tools.registry import get_registry
    
    registry = get_registry()
    all_tools = registry.list_all_tools()
    roles = registry.list_roles()
    
    # Tools by category
    categories: dict[str, list[str]] = {
        "File Tools": ["read_file", "write_file", "list_directory", "search_files", 
                       "grep_files", "edit_file", "delete_file", "move_file"],
        "GitHub Tools": ["github_search_repos", "github_get_repo", "github_list_issues",
                        "github_create_issue", "github_list_pull_requests", 
                        "github_get_pull_request", "github_create_pull_request",
                        "github_get_file_contents", "github_list_branches"],
        "Web Tools": ["web_search", "web_fetch"],
        "Code Tools": ["execute_command", "run_python_code", "run_javascript",
                      "list_running_processes", "tail_file"],
        "Database Tools": ["db_query", "db_execute", "db_list_tables", "db_describe_table"],
    }
    
    lines = [
        "# πX Tools Reference",
        "",
        f"*Auto-generated from ToolRegistry — {len(all_tools)} tools across {len(roles)} agent roles*",
        "",
        "## Overview",
        "",
        f"The ToolRegistry singleton manages {len(all_tools)} tools across {len(categories)} categories. "
        "Each agent role has a curated subset of tools available during execution.",
        "",
    ]
    
    for category, tool_names in categories.items():
        lines.append(f"## {category}")
        lines.append("")
        for name in tool_names:
            desc = all_tools.get(name, "No description available")
            lines.append(f"### `{name}`")
            lines.append("")
            lines.append(f"{desc}")
            lines.append("")
    
    # Agent role tool assignments
    lines.append("## Agent Tool Assignments")
    lines.append("")
    lines.append("| Agent Role | Tools | Count |")
    lines.append("|------------|-------|-------|")
    for role in sorted(roles):
        tool_names = registry.get_tool_names_for_role(role)
        count = len(tool_names)
        names_str = ", ".join(f"`{n}`" for n in tool_names) if tool_names else "*None*"
        lines.append(f"| {role} | {names_str} | {count} |")
    
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append(f"*Generated on {__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*")
    
    content = "\n".join(lines)
    
    if output_path:
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        Path(output_path).write_text(content, encoding="utf-8")
        print(f"Documentation written to {output_path}")
    
    return content


if __name__ == "__main__":
    output = sys.argv[1] if len(sys.argv) > 1 else "docs/tools.md"
    generate_tool_docs(output)
