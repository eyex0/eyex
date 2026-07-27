"""πX Alternatives Generator — Generate decision alternatives."""
from __future__ import annotations

import json
import logging

from packages.cognitive_kernel.ai_gateway import AI_GATEWAY
from packages.cognitive_kernel.ai_gateway.providers.base import GenerateRequest

logger = logging.getLogger("pix.decision.alternatives")


class AlternativesGenerator:
    def __init__(self, gateway=None):
        self.gateway = gateway or AI_GATEWAY

    async def generate(
        self, question: str, context: dict, constraints: list[str] | None = None
    ) -> list[dict]:
        constraints_text = "\n".join(f"- {c}" for c in (constraints or []))
        prompt = f"""Generate 3-5 alternative approaches to the following question. Return a JSON array.
Each alternative: {{"title": "...", "description": "...", "pros": [], "cons": [], "estimated_cost": "...", "estimated_impact": "...", "feasibility": 0.0-1.0}}

Question: {question}

Constraints:
{constraints_text or 'None specified'}

Return ONLY the JSON array."""

        try:
            response = await self.gateway.generate(
                GenerateRequest(prompt=prompt, temperature=0.6, max_tokens=1500)
            )
            content = response.content.strip()
            if content.startswith("```"):
                content = content.split("\n", 1)[1].rsplit("```", 1)[0]
            alternatives = json.loads(content)
            for i, alt in enumerate(alternatives):
                alt["id"] = f"alt_{i}"
            return alternatives
        except Exception as exc:
            logger.error("Alternatives generation failed: %s", exc)
            return [{
                "id": "default",
                "title": "Proceed with current approach",
                "description": question,
                "pros": [],
                "cons": [],
                "estimated_cost": "unknown",
                "estimated_impact": "unknown",
                "feasibility": 0.5,
            }]
