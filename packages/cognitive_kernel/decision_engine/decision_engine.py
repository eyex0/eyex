"""πX Decision Engine — Full decision intelligence pipeline."""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, UTC
from typing import Any

from packages.cognitive_kernel.ai_gateway import AI_GATEWAY
from packages.cognitive_kernel.ai_gateway.providers.base import GenerateRequest
from .risk_analyzer import RiskAnalyzer
from .confidence_scorer import ConfidenceScorer
from .alternatives_generator import AlternativesGenerator

logger = logging.getLogger("pix.decision_engine")


class DecisionEngine:
    """Orchestrates: Question → Context → Evidence → Reasoning → Risk → Recommendation."""

    def __init__(self, gateway=None, memory=None, graph_store=None):
        self.gateway = gateway or AI_GATEWAY
        self.memory = memory
        self.graph_store = graph_store
        self.risk_analyzer = RiskAnalyzer(gateway=self.gateway)
        self.confidence_scorer = ConfidenceScorer()
        self.alternatives_gen = AlternativesGenerator(gateway=self.gateway)

    async def decide(self, question: str, org_id: str, context: dict | None = None) -> dict:
        decision_id = str(uuid.uuid4())
        context = context or {}

        # Step 1: Context retrieval
        retrieved_context = await self._retrieve_context(question, org_id)

        # Step 2: Evidence collection
        evidence = await self._collect_evidence(question, retrieved_context, org_id)

        # Step 3: Reasoning
        reasoning_chain = await self._reason(question, retrieved_context, evidence)

        # Step 4: Risk analysis
        risk_assessment = await self.risk_analyzer.analyze_risks(
            f"{question}\nContext: {retrieved_context}", evidence
        )

        # Step 5: Recommendation
        recommendation = await self._generate_recommendation(
            question, evidence, reasoning_chain, risk_assessment
        )

        # Step 6: Confidence scoring
        confidence = self.confidence_scorer.score_decision(
            evidence, reasoning_chain, risk_assessment.get("risks", [])
        )

        # Step 7: Alternatives
        alternatives = await self.alternatives_gen.generate(
            question, retrieved_context, context.get("constraints", [])
        )

        return {
            "decision_id": decision_id,
            "question": question,
            "context_summary": str(retrieved_context)[:500],
            "evidence": evidence,
            "reasoning_chain": reasoning_chain,
            "risks": risk_assessment.get("risks", []),
            "overall_risk_level": risk_assessment.get("overall_risk_level", "unknown"),
            "recommendation": recommendation,
            "confidence": confidence,
            "alternatives": alternatives,
            "created_at": datetime.now(UTC).isoformat(),
        }

    async def _retrieve_context(self, question: str, org_id: str) -> dict:
        """Retrieve relevant context from memory and knowledge graph."""
        context: dict[str, Any] = {}
        if self.memory:
            try:
                memories = await self.memory.recall_all(
                    session_id=org_id, min_importance=0.3, limit=20
                )
                context["memory"] = memories
            except Exception as exc:
                logger.warning("Context retrieval from memory failed: %s", exc)
        if self.graph_store:
            try:
                stats = await self.graph_store.get_graph_stats(org_id)
                context["graph_stats"] = stats
            except Exception as exc:
                logger.warning("Graph context retrieval failed: %s", exc)
        return context

    async def _collect_evidence(self, question: str, context: dict, org_id: str) -> list[dict]:
        """Collect evidence from memory and knowledge graph."""
        evidence: list[dict] = []
        # From memory
        if context.get("memory"):
            for key, value in context["memory"].items():
                evidence.append({
                    "source": "memory",
                    "key": key,
                    "content": value[:200],
                    "confidence": 0.7,
                })
        # From graph (if available)
        if self.graph_store:
            try:
                nodes = await self.graph_store.search_nodes(question, org_id=org_id, limit=10)
                for node in nodes:
                    evidence.append({
                        "source": "knowledge_graph",
                        "key": node.get("label", ""),
                        "content": f"{node.get('label')} ({node.get('type')})",
                        "confidence": 0.6,
                    })
            except Exception as exc:
                logger.warning("Evidence from graph failed: %s", exc)
        # If no evidence, add a default
        if not evidence:
            evidence.append({
                "source": "default",
                "key": "no_context",
                "content": "No specific evidence found. Decision based on general reasoning.",
                "confidence": 0.3,
            })
        return evidence

    async def _reason(self, question: str, context: dict, evidence: list[dict]) -> list[str]:
        """Generate reasoning chain using AI."""
        evidence_text = "\n".join(f"- [{e['source']}] {e['content']}" for e in evidence)
        prompt = f"""Analyze the following business question and provide a step-by-step reasoning chain.

Question: {question}

Evidence:
{evidence_text}

Provide 3-7 reasoning steps. Return as a JSON array of strings."""

        try:
            response = await self.gateway.generate(
                GenerateRequest(prompt=prompt, temperature=0.5, max_tokens=1000)
            )
            import json
            content = response.content.strip()
            if content.startswith("```"):
                content = content.split("\n", 1)[1].rsplit("```", 1)[0]
            return json.loads(content)
        except Exception as exc:
            logger.error("Reasoning generation failed: %s", exc)
            return ["Unable to generate reasoning chain due to an error."]

    async def _generate_recommendation(
        self, question: str, evidence: list[dict], reasoning: list[str], risks: dict
    ) -> str:
        """Generate a final recommendation."""
        evidence_text = "\n".join(f"- {e['content']}" for e in evidence)
        reasoning_text = "\n".join(f"{i+1}. {r}" for i, r in enumerate(reasoning))
        risks_text = "\n".join(f"- {r.get('description', '')}" for r in risks.get("risks", []))

        prompt = f"""Based on the following analysis, provide a clear, actionable recommendation.

Question: {question}

Evidence:
{evidence_text}

Reasoning:
{reasoning_text}

Risks:
{risks_text}

Provide a single, concise recommendation (2-3 sentences)."""

        try:
            response = await self.gateway.generate(
                GenerateRequest(prompt=prompt, temperature=0.4, max_tokens=500)
            )
            return response.content
        except Exception as exc:
            logger.error("Recommendation generation failed: %s", exc)
            return "Unable to generate recommendation."
