"""πX Risk Analyzer — Assess risks for decisions."""
from __future__ import annotations

import json
import logging

from packages.cognitive_kernel.ai_gateway import AI_GATEWAY
from packages.cognitive_kernel.ai_gateway.providers.base import GenerateRequest

logger = logging.getLogger("pix.decision.risk")


class RiskAnalyzer:
    def __init__(self, gateway=None):
        self.gateway = gateway or AI_GATEWAY

    async def analyze_risks(self, decision_context: str, evidence: list[dict]) -> dict:
        evidence_text = "\n".join(f"- {e.get('content', '')}" for e in evidence)
        prompt = f"""Identify risks in the following decision context. Return a JSON array.
Each risk: {{"description": "...", "probability": 0.0-1.0, "impact": 0.0-1.0, "category": "...", "mitigation": "..."}}

Context:
{decision_context[:4000]}

Evidence:
{evidence_text[:2000]}

Return ONLY the JSON array."""

        try:
            response = await self.gateway.generate(
                GenerateRequest(prompt=prompt, temperature=0.4, max_tokens=1500)
            )
            content = response.content.strip()
            if content.startswith("```"):
                content = content.split("\n", 1)[1].rsplit("```", 1)[0]
            risks = json.loads(content)
        except Exception as exc:
            logger.error("Risk analysis failed: %s", exc)
            risks = []

        # Calculate risk scores
        for i, risk in enumerate(risks):
            risk["id"] = f"risk_{i}"
            risk["risk_score"] = risk.get("probability", 0.5) * risk.get("impact", 0.5)

        max_score = max((r["risk_score"] for r in risks), default=0)
        if max_score < 0.3:
            overall_level = "LOW"
        elif max_score < 0.6:
            overall_level = "MEDIUM"
        else:
            overall_level = "HIGH"

        return {
            "risks": risks,
            "overall_risk_level": overall_level,
            "risk_score": max_score,
            "mitigations": [r.get("mitigation", "") for r in risks if r.get("mitigation")],
        }
