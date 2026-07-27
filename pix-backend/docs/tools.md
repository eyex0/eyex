# πX Tools Reference

_Auto-generated from ToolRegistry — 28 tools across 8 agent roles_

## Overview

The ToolRegistry singleton manages 28 tools across 5 categories. Each agent role has a curated subset of tools available during execution.

## File Tools

### `read_file`

Read the contents of a file at the given path. Returns the file content as a str

### `write_file`

Write content to a file at the given path. Creates parent directories if needed.

### `list_directory`

List all files and directories in the given directory path with sizes.

### `search_files`

Search for files matching a glob pattern. Uses ** for recursive matching. Exampl

### `grep_files`

Search file contents using a regex pattern. Optionally filter by file glob (e.g.

### `edit_file`

Perform an exact string replacement in a file. Replaces the first occurrence of

### `delete_file`

Delete a file or directory. Set recursive=True to delete non-empty directories.

### `move_file`

Rename or move a file or directory from source to destination.

## GitHub Tools

### `github_search_repos`

Search GitHub repositories by query. Returns repo name, description, stars, lang

### `github_get_repo`

Get details about a GitHub repository. Format: 'owner/repo' (e.g. 'tensorflow/te

### `github_list_issues`

List issues for a GitHub repository. State: 'open', 'closed', 'all'.

### `github_create_issue`

Create a new issue on a GitHub repository.

### `github_list_pull_requests`

List pull requests for a GitHub repository. State: 'open', 'closed', 'merged', '

### `github_get_pull_request`

Get detailed information about a specific pull request.

### `github_create_pull_request`

Create a pull request on a GitHub repository.

### `github_get_file_contents`

Get the contents of a file from a GitHub repository at a specific branch/ref.

### `github_list_branches`

List branches for a GitHub repository.

## Web Tools

### `web_search`

Search the web for information. Returns title, URL, and snippet for each result.

### `web_fetch`

Fetch and extract content from a URL. Format options: 'markdown' (default), 'tex

## Code Tools

### `execute_command`

Execute a shell command in a restricted environment. Only safe commands are allo

### `run_python_code`

Execute Python code in an isolated subprocess and return stdout + stderr. All im

### `run_javascript`

Execute JavaScript code using Node.js in an isolated subprocess. Returns stdout

### `list_running_processes`

List currently running processes (cross-platform). Returns PID, name, and memory

### `tail_file`

Read the last N lines of a file. Useful for checking recent logs or output.

## Database Tools

### `db_query`

Execute a SELECT SQL query against the database and return results as a formatte

### `db_execute`

Execute an INSERT, UPDATE, or DELETE SQL statement. Returns number of affected r

### `db_list_tables`

List all tables in the database with their schema information.

### `db_describe_table`

Describe the schema of a specific database table: columns, types, nullability, d

## Agent Tool Assignments

| Agent Role | Tools                                                                                                                                                                                                                                                                                                                     | Count |
| ---------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----- |
| coder      | `read_file`, `write_file`, `edit_file`, `delete_file`, `move_file`, `list_directory`, `search_files`, `grep_files`, `execute_command`, `run_python_code`, `run_javascript`, `github_get_file_contents`, `github_list_branches`, `github_search_repos`                                                                     | 14    |
| devops     | `read_file`, `write_file`, `edit_file`, `list_directory`, `search_files`, `grep_files`, `execute_command`, `run_python_code`, `tail_file`, `list_running_processes`, `db_query`, `db_list_tables`, `db_describe_table`, `github_list_branches`, `github_list_pull_requests`, `github_get_pull_request`, `github_get_repo` | 17    |
| documenter | `read_file`, `write_file`, `list_directory`, `search_files`, `grep_files`                                                                                                                                                                                                                                                 | 5     |
| planner    | `read_file`, `search_files`, `grep_files`, `list_directory`                                                                                                                                                                                                                                                               | 4     |
| researcher | `read_file`, `search_files`, `grep_files`, `web_search`, `web_fetch`, `github_search_repos`, `github_get_repo`, `github_get_file_contents`                                                                                                                                                                                | 8     |
| reviewer   | `read_file`, `search_files`, `grep_files`, `list_directory`, `tail_file`                                                                                                                                                                                                                                                  | 5     |
| supervisor | _None_                                                                                                                                                                                                                                                                                                                    | 0     |
| tester     | `read_file`, `write_file`, `edit_file`, `list_directory`, `search_files`, `grep_files`, `execute_command`, `run_python_code`, `run_javascript`                                                                                                                                                                            | 9     |

---

_Generated on 2026-07-19 13:12:45_
