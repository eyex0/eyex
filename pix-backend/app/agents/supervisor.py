from __future__ import annotations

import logging
import time
from typing import Any

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

logger = logging.getLogger("pix.agents.supervisor")


class SupervisorClassification(BaseModel):
    category: str = Field(
        description="Classification: 'executive', 'intelligence', 'planning', 'research', 'coding', 'general'"
    )
    confidence: float = Field(description="Confidence score between 0.0 and 1.0", ge=0.0, le=1.0)
    reasoning: str = Field(description="Brief justification for the classification")
    suggested_agents: list[str] = Field(
        description="Ordered list of agents, e.g. ['analyst', 'strategist', 'decision'] or ['ceo', 'cfo', 'coo', 'risk']"
    )
    requires_decomposition: bool = Field(
        description="Whether this request needs multi-step decomposition"
    )


SYSTEM_PROMPT = """You are the Supervisor Agent of the πX Technologies intelligence platform.

Your responsibilities:
1. Analyze every incoming request thoroughly
2. Classify it into one of six categories:
   - **executive**: C-suite level requests requiring strategic decisions, company-wide analysis, executive reports, board presentations, comprehensive business review — routes to CEO → CFO → COO → Risk pipeline
   - **intelligence**: Business analysis, data-driven decisions, strategy, recommendations, financial review, performance analysis — routes to Analyst → Strategist → Decision pipeline
   - **planning**: Project breakdown, architecture, task decomposition
   - **research**: Information gathering, investigation, data collection
   - **coding**: Code generation, implementation, debugging, technical writing
   - **general**: Simple conversation, greetings, help, platform questions
3. Determine which agents should handle the request and in what order
4. Decide if the request requires multi-step decomposition

Classification rules:
- "What's our strategic direction?", "Executive summary of the company", "Board presentation", "Company-wide review", "Full enterprise analysis" → "executive"
- Business questions like "Analyze our revenue", "Review company performance", "What should we improve?" → "intelligence"
- Build or implement something → "coding"
- Analyze, investigate, find information → "research"
- Plan, design, architect → "planning"
- Simple chat → "general"

For executive requests, suggest agents: ["ceo", "cfo", "coo", "risk"]
For intelligence requests, suggest agents: ["analyst", "strategist", "decision"]
For complex projects: ["planner", "researcher", "coder"]
For simple chat: []

Be concise but precise. Your classifications drive the entire agent workflow."""


class SupervisorAgent:
    def __init__(self, llm: BaseChatModel | None = None, settings: Any | None = None):
        self.settings = settings
        self.llm = llm or self._default_llm(self.settings)
        self.parser = PydanticOutputParser(pydantic_object=SupervisorClassification)
        self.prompt = ChatPromptTemplate.from_messages([
            SystemMessage(content=SYSTEM_PROMPT),
            MessagesPlaceholder(variable_name="history"),
            HumanMessage(content="{input}"),
        ])

    @staticmethod
    def _default_llm(settings: Any) -> "ChatOpenAI | None":
        try:
            s = settings or type("S", (), {
                "openai_model": "gpt-4o-mini",
                "openai_temperature": 0.1,
                "openai_max_tokens": 2000,
                "openai_api_key": "",
            })()
            return ChatOpenAI(
                model=getattr(s, "openai_model", "gpt-4o-mini"),
                temperature=getattr(s, "openai_temperature", 0.1),
                max_tokens=getattr(s, "openai_max_tokens", 2000),
                api_key=getattr(s, "openai_api_key", ""),
            )
        except Exception:
            return None

    async def classify(self, input_text: str, history: list[dict[str, str]] | None = None) -> SupervisorClassification:
        if self.llm is None:
            return SupervisorClassification(
                category="general",
                confidence=0.5,
                reasoning=f"No LLM available — default classification for: {input_text[:100]}",
                suggested_agents=["sales_intelligence"],
                requires_decomposition=False,
            )
        messages = []
        if history:
            for msg in history:
                role = msg.get("role", "user")
                content = msg.get("content", "")
                if role == "user":
                    messages.append(HumanMessage(content=content))
                else:
                    messages.append(AIMessage(content=content))

        chain = self.prompt | self.llm.with_structured_output(SupervisorClassification)

        start = time.perf_counter()
        try:
            result: SupervisorClassification = await chain.ainvoke({
                "input": input_text,
                "history": messages,
            })
            elapsed = time.perf_counter() - start
            logger.info(
                "Supervisor classified request as '%s' (confidence=%.2f) in %.0fms",
                result.category, result.confidence, elapsed * 1000,
            )
            return result
        except Exception as exc:
            elapsed = time.perf_counter() - start
            logger.error("Supervisor classification failed after %.0fms: %s", elapsed * 1000, exc)
            return SupervisorClassification(
                category="general",
                confidence=0.5,
                reasoning=f"Fallback classification due to error: {exc}",
                suggested_agents=[],
                requires_decomposition=False,
            )

    async def analyze(self, input_text: str, history: list[dict[str, str]] | None = None) -> dict[str, Any]:
        try:
            classification = await self.classify(input_text, history)
        except Exception as e:
            logger.warning(f"LLM classify failed, using default: {e}")
            classification = SupervisorClassification(
                category="general",
                confidence=0.5,
                reasoning=f"Default classification (LLM unavailable): {input_text[:100]}",
                suggested_agents=["sales_intelligence"],
                requires_decomposition=False,
            )

        return {
            "classification": classification.model_dump(),
            "analysis": {
                "input_length": len(input_text),
                "has_history": bool(history),
                "history_length": len(history) if history else 0,
            },
        }
