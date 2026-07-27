from __future__ import annotations

import asyncio
import json
import logging
import time
from abc import ABC, abstractmethod
from enum import StrEnum
from typing import Any

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.tools import BaseTool
from langchain_openai import ChatOpenAI
from pydantic import BaseModel

from packages.cognitive-kernel.memory-engine import PersistentMemory

logger = logging.getLogger("pix.agents.base")

_MAX_TOOL_ITERATIONS = 10


class AgentRole(StrEnum):
    SUPERVISOR = "supervisor"
    PLANNER = "planner"
    RESEARCHER = "researcher"
    CODER = "coder"
    REVIEWER = "reviewer"
    TESTER = "tester"
    DOCUMENTER = "documenter"
    DEVOPS = "devops"


def default_llm(settings: Any) -> ChatOpenAI:
    kwargs = {
        "model": settings.openai_model,
        "temperature": settings.openai_temperature,
        "max_tokens": settings.openai_max_tokens,
        "api_key": settings.openai_api_key,
    }
    if settings.openai_base_url:
        kwargs["base_url"] = settings.openai_base_url

    # Add reasoning support for DeepSeek v4 flash
    if "deepseek-v4" in settings.openai_model.lower():
        kwargs["model_kwargs"] = {
            "extra_body": {
                "chat_template_kwargs": {
                    "thinking": True, 
                    "reasoning_effort": "high"
                }
            }
        }
        
    # Add reasoning support for DiffusionGemma
    if "diffusiongemma" in settings.openai_model.lower():
        kwargs.setdefault("model_kwargs", {})
        kwargs["model_kwargs"]["chat_template_kwargs"] = {
            "enable_thinking": True
        }
        
    return ChatOpenAI(**kwargs)


class AgentMemory:
    """In-memory conversation store for agent sessions (fallback when no DB)."""

    def __init__(self) -> None:
        self._store: dict[str, list[dict[str, str]]] = {}

    def get(self, session_id: str, default: list | None = None) -> list[dict[str, str]]:
        return self._store.get(session_id, default or [])

    def add(self, session_id: str, role: str, content: str) -> None:
        if session_id not in self._store:
            self._store[session_id] = []
        self._store[session_id].append({"role": role, "content": content})

    def clear(self, session_id: str) -> None:
        self._store.pop(session_id, None)


_MEMORY = AgentMemory()


def get_global_memory() -> AgentMemory:
    return _MEMORY


class NodeAgent(ABC):
    """Base class for all LangGraph-compatible agents.

    Supports both in-memory (AgentMemory) and persistent (PersistentMemory) backends.
    When a PersistentMemory instance is provided via `memory_service`, the agent
    stores all conversations and long-term facts in PostgreSQL + Redis.
    """

    def __init__(
        self,
        llm: BaseChatModel | None = None,
        memory: AgentMemory | None = None,
        memory_service: PersistentMemory | None = None,
        settings: Any | None = None,
        **kwargs: Any,
    ) -> None:
        self.settings = settings
        self.llm = llm or default_llm(self.settings)
        self.memory = memory or _MEMORY
        self.memory_service = memory_service or _get_global_persistent_memory()
        self._extra_kwargs = kwargs

    @property
    @abstractmethod
    def name(self) -> str: ...

    @property
    @abstractmethod
    def description(self) -> str: ...

    @property
    @abstractmethod
    def system_prompt(self) -> str: ...

    @property
    @abstractmethod
    def output_schema(self) -> type[BaseModel]: ...

    @property
    def tools(self) -> list[BaseTool]:
        return []

    def build_prompt(self) -> ChatPromptTemplate:
        return ChatPromptTemplate.from_messages([
            SystemMessage(content=self.system_prompt),
            MessagesPlaceholder(variable_name="history", optional=True),
            MessagesPlaceholder(variable_name="input_messages"),
        ])

    async def execute(self, input_text: str, session_id: str | None = None) -> BaseModel:
        history_msgs = await self._load_history(session_id)
        start = time.perf_counter()

        # Cap input size to reduce token cost and latency
        max_input_chars = 12000
        if len(input_text) > max_input_chars:
            input_text = input_text[:max_input_chars] + "\n...[truncated]"
            logger.debug("%s input truncated to %d chars", self.name, max_input_chars)

        try:
            if self.tools:
                tool_context = await self._run_tool_loop(input_text, history_msgs)
                augmented_input = (
                    f"{input_text}\n\n[Tool Results]\n{tool_context}"
                    if tool_context else input_text
                )
                final_input = [HumanMessage(content=augmented_input)]
            else:
                final_input = [HumanMessage(content=input_text)]

            # Some agents have no structured output — just use the LLM directly
            timeout = self.settings.agent_timeout_seconds or 60
            if not hasattr(self.output_schema, "model_fields"):
                chain = self.build_prompt() | self.llm
                result_raw = await asyncio.wait_for(
                    chain.ainvoke({
                        "input_messages": final_input,
                        "history": history_msgs,
                    }),
                    timeout=timeout,
                )
                result = result_raw
            else:
                chain = self.build_prompt() | self.llm.with_structured_output(self.output_schema)
                result = await asyncio.wait_for(
                    chain.ainvoke({
                        "input_messages": final_input,
                        "history": history_msgs,
                    }),
                    timeout=timeout,
                )

            elapsed = time.perf_counter() - start
            logger.info(
                "%s agent completed in %.0fms — input: %d chars",
                self.name, elapsed * 1000, len(input_text),
            )

            await self._store_interaction(session_id, input_text, result)

            return result
        except Exception as exc:
            elapsed = time.perf_counter() - start
            logger.error("%s agent failed after %.0fms: %s", self.name, elapsed * 1000, exc)
            return self._fallback_output(input_text, str(exc))

    async def _run_tool_loop(self, input_text: str, history_msgs: list) -> str:
        """Run a tool-calling loop: LLM may call tools, results are fed back. Returns accumulated tool context."""
        messages: list = [
            SystemMessage(content=(
                f"{self.system_prompt}\n\n"
                "You have access to tools. Use them when you need information. "
                "After gathering enough context, respond with your final structured output."
            )),
            *history_msgs,
            HumanMessage(content=input_text),
        ]

        tool_map = {t.name: t for t in self.tools}

        for iteration in range(_MAX_TOOL_ITERATIONS):
            with_llm = self.llm.bind_tools(self.tools)
            response = await with_llm.ainvoke(messages)
            messages.append(response)

            if not hasattr(response, "tool_calls") or not response.tool_calls:
                break

            for tc in response.tool_calls:
                tool_name = tc.get("name", "")
                tool_args = tc.get("args", {})
                tool_call_id = tc.get("id", f"call_{iteration}_{tool_name}")

                tool_fn = tool_map.get(tool_name)
                if not tool_fn:
                    result_text = f"Error: Unknown tool '{tool_name}'"
                else:
                    try:
                        result_text = await tool_fn.ainvoke(tool_args)
                    except Exception as exc:
                        result_text = f"Error executing {tool_name}: {exc}"

                messages.append(ToolMessage(content=str(result_text)[:3000], tool_call_id=tool_call_id))
                logger.debug(
                    "Tool call %s/%s: %s(args=%s) -> %d chars",
                    self.name, iteration, tool_name,
                    json.dumps(tool_args)[:120], len(result_text),
                )
        else:
            logger.warning(
                "%s agent reached max tool iterations (%d) — proceeding with collected context",
                self.name, _MAX_TOOL_ITERATIONS,
            )

        # Extract tool results from the conversation for structured output context
        tool_parts = []
        for msg in messages:
            if isinstance(msg, ToolMessage):
                tool_parts.append(msg.content[:2000])
        return "\n\n".join(tool_parts) if tool_parts else ""

    @abstractmethod
    def _fallback_output(self, input_text: str, error: str) -> BaseModel:
        ...

    async def _load_history(self, session_id: str | None) -> list:
        if not session_id:
            return []

        history_msgs: list = []

        if self.memory_service and self.memory_service.session_factory:
            try:
                conv = await self.memory_service.get_conversation(session_id, limit=50)
                for msg in conv:
                    if msg["role"] == "user":
                        history_msgs.append(HumanMessage(content=msg["content"]))
                    else:
                        history_msgs.append(AIMessage(content=msg["content"]))
                if history_msgs:
                    logger.debug("Loaded %d history messages for session %s", len(history_msgs), session_id)
                return history_msgs
            except Exception as exc:
                logger.warning("Failed to load persistent history, falling back to in-memory: %s", exc)

        fallback = self.memory.get(session_id)
        for msg in fallback:
            if msg.get("role") == "user":
                history_msgs.append(HumanMessage(content=msg.get("content", "")))
            else:
                history_msgs.append(AIMessage(content=msg.get("content", "")))
        return history_msgs

    async def _store_interaction(self, session_id: str | None, input_text: str, result: BaseModel) -> None:
        if not session_id:
            return

        result_json = result.model_dump_json()
        agent_name = self.name.lower()

        if self.memory_service and self.memory_service.session_factory:
            try:
                facts = self._extract_facts(result)
                await self.memory_service.store_interaction(
                    session_id=session_id,
                    user_message=input_text,
                    assistant_message=result_json,
                    agent_name=agent_name,
                    facts=facts,
                )
                summary = result.model_dump().get("summary", "")[:200] or result.model_dump().get("plan", "")[:200]
                if summary:
                    await self.memory_service.set_agent_memory(
                        session_id, agent_name,
                        f"last_{agent_name}_summary", summary,
                        memory_type="summary",
                    )
                return
            except Exception as exc:
                logger.warning("Failed to store in persistent memory, falling back to in-memory: %s", exc)

        self.memory.add(session_id, "user", input_text)
        self.memory.add(session_id, "assistant", result_json)

    def _extract_facts(self, result: BaseModel) -> list[tuple[str, str, float]]:
        facts: list[tuple[str, str, float]] = []
        dumped = result.model_dump()
        summary = dumped.get("summary") or dumped.get("plan") or dumped.get("findings")
        if summary and isinstance(summary, str):
            facts.append((f"{self.name.lower()}_last_summary", summary[:500], 0.6))
        explanation = dumped.get("explanation")
        if explanation and isinstance(explanation, str):
            facts.append((f"{self.name.lower()}_last_explanation", explanation[:500], 0.5))
        return facts

    def create_node(self) -> Any:
        agent = self

        async def node_fn(state: dict) -> dict:
            request = state.get("request", "") or state.get("input", "")
            session_id = state.get("session_id") or state.get("thread_id")
            try:
                output = await agent.execute(request, session_id=session_id)
                return {
                    **state,
                    f"{agent.name.lower()}_result": output.model_dump(),
                    "status": "running",
                }
            except Exception as exc:
                return {
                    **state,
                    "error": str(exc),
                    "status": "failed",
                }

        node_fn.__name__ = f"{agent.name.lower()}_node"
        node_fn.__doc__ = f"LangGraph node for {agent.name}"
        return node_fn


_PERSISTENT_MEMORY: PersistentMemory | None = None


def set_global_persistent_memory(memory: PersistentMemory) -> None:
    global _PERSISTENT_MEMORY
    _PERSISTENT_MEMORY = memory


def _get_global_persistent_memory() -> PersistentMemory | None:
    return _PERSISTENT_MEMORY
