from typing import Any

from typing_extensions import TypedDict


class GraphState(TypedDict, total=False):
    messages: list[dict[str, Any]]
    next_node: str
    context: dict[str, Any]
    error: str | None
