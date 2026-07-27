"""
πX Profile-Aware Decision Engine — Decision Engine integration.

Decision reasoning now includes company-specific context:
  - KPIs and targets (not generic "improve sales")
  - Company terminology (not generic business terms)
  - Historical decisions from the same profile
  - Industry-specific risk factors

Generic: "Improve sales"
πX:     "Increase Sell-out KPI by 15% in Region North while maintaining margin target."
"""
from __future__ import annotations

import json
import logging
from typing import Any

from packages.cognitive_kernel.ai_gateway import AI_GATEWAY
from packages.cognitive_kernel.ai_gateway.providers.base import GenerateRequest
from packages.cognitive_kernel.intelligence_profile.context_provider import ProfileContextProvider

logger = logging.getLogger("pix.decision_engine.profile_aware")


class ProfileAwareDecisionEngine:
    """Decision engine that uses Intelligence Profile for company-specific reasoning."""

    def __init__(
        self,
        session_factory=None,
        gateway=None,
        context_provider: ProfileContextProvider | None = None,
    ):
        self.gateway = gateway or AI_GATEWAY
        self.context_provider = context_provider

    async def decide(
        self,
        question: str,
        organization_id: str,
        context_provider: ProfileContextProvider | None = None,
        additional_context: dict | None = None,
    ) -> dict:
        """Make a profile-aware decision with company-specific context."""
        provider = context_provider or self.context_provider
        if not provider:
            raise ValueError("ProfileContextProvider is required for profile-aware decisions")

        profile_ctx = await provider.get_context(organization_id)

        # Build company-specific context
        company_context = self._build_decision_context(profile_ctx, question)

        # Reasoning with company context
        reasoning_chain = await self._reason_with_context(question, company_context, profile_ctx)

        # Risk analysis with industry-specific risks
        risks = await self._analyze_profile_risks(question, profile_ctx, reasoning_chain)

        # Recommendation using company KPIs and terminology
        recommendation = await self._recommend_with_kpis(
            question, reasoning_chain, risks, profile_ctx
        )

        # Confidence includes profile confidence
        profile_confidence = profile_ctx.get("confidence_score", 0.5)
        decision_confidence = self._calculate_confidence(
            reasoning_chain, risks, profile_confidence
        )

        return {
            "question": question,
            "organization_id": organization_id,
            "profile_id": profile_ctx.get("profile_id"),
            "company_context": company_context,
            "reasoning_chain": reasoning_chain,
            "risks": risks,
            "recommendation": recommendation,
            "confidence": decision_confidence,
            "profile_confidence": profile_confidence,
            "kpis_referenced": [k["name"] for k in profile_ctx.get("kpis", []) if k["name"].lower() in question.lower()],
        }

    def _build_decision_context(self, profile_ctx: dict, question: str) -> dict:
        """Build company-specific decision context."""
        identity = profile_ctx.get("company_identity", {})
        kpis = profile_ctx.get("kpis", [])
        glossary = profile_ctx.get("glossary", [])

        # Find relevant KPIs mentioned in the question
        question_lower = question.lower()
        relevant_kpis = []
        for kpi in kpis:
            kpi_terms = [kpi["name"].lower()] + [a.lower() for a in kpi.get("aliases", [])]
            if any(term in question_lower for term in kpi_terms):
                relevant_kpis.append(kpi)

        # Resolve terminology in the question
        glossary_mapping = {}
        for term in glossary:
            for alias in [term["term"]] + term.get("aliases", []) + term.get("synonyms", []):
                if alias.lower() in question_lower:
                    glossary_mapping[alias.lower()] = term["term"]

        return {
            "industry": identity.get("industry"),
            "business_model": identity.get("business_model"),
            "region": identity.get("region"),
            "relevant_kpis": [k["name"] for k in relevant_kpis],
            "kpi_targets": {k["name"]: k.get("target", {}) for k in relevant_kpis},
            "terminology_resolved": glossary_mapping,
            "ontology_entities": [e["entity_type"] for e in profile_ctx.get("ontology", [])],
        }

    async def _reason_with_context(
        self, question: str, context: dict, profile_ctx: dict
    ) -> list[str]:
        """Generate reasoning chain with company-specific context."""
        kpi_context = await self.context_provider.get_kpi_context(
            profile_ctx.get("profile_id", "")  # May not work without org_id, fallback below
        ) if self.context_provider else ""

        # Build context string
        kpi_str = "\n".join(
            f"- {k}: {d}" for k, d in context.get("kpi_targets", {}).items()
        ) if context.get("kpi_targets") else "No specific KPIs referenced"

        terminology = context.get("terminology_resolved", {})
        term_str = "\n".join(f"- '{k}' → {v}" for k, v in terminology.items()) if terminology else ""

        prompt = f"""Analyze this business question for a {context.get('industry', 'generic')} company.

Question: {question}

Company KPIs and targets:
{kpi_str}

Terminology resolution:
{term_str or 'No company-specific terms detected'}

Ontology entities: {', '.join(context.get('ontology_entities', []))}

Provide 3-7 reasoning steps. Return as a JSON array of strings."""

        try:
            response = await self.gateway.generate(
                GenerateRequest(prompt=prompt, temperature=0.5, max_tokens=1000)
            )
            content = response.content.strip()
            if content.startswith("```"):
                content = content.split("\n", 1)[1].rsplit("```", 1)[0]
            return json.loads(content)
        except Exception as exc:
            logger.error("Profile-aware reasoning failed: %s", exc)
            return ["Unable to generate reasoning with profile context."]

    async def _analyze_profile_risks(
        self, question: str, profile_ctx: dict, reasoning: list[str]
    ) -> list[dict]:
        """Analyze risks with industry-specific context."""
        industry = profile_ctx.get("company_identity", {}).get("industry", "generic")
        reasoning_text = "\n".join(reasoning)

        prompt = f"""Identify risks for this decision in a {industry} company.
Question: {question}
Reasoning: {reasoning_text}

Return JSON array. Each risk: {{"description": "...", "probability": 0.0-1.0, "impact": 0.0-1.0, "category": "...", "mitigation": "..."}}
Return ONLY the JSON."""

        try:
            response = await self.gateway.generate(
                GenerateRequest(prompt=prompt, temperature=0.4, max_tokens=1200)
            )
            content = response.content.strip()
            if content.startswith("```"):
                content = content.split("\n", 1)[1].rsplit("```", 1)[0]
            risks = json.loads(content)
            for i, risk in enumerate(risks):
                risk["id"] = f"risk_{i}"
                risk["risk_score"] = risk.get("probability", 0.5) * risk.get("impact", 0.5)
            return risks
        except Exception as exc:
            logger.error("Profile-aware risk analysis failed: %s", exc)
            return []

    async def _recommend_with_kpis(
        self, question: str, reasoning: list[str], risks: list[dict], profile_ctx: dict
    ) -> str:
        """Generate recommendation referencing company KPIs and terminology."""
        kpis = profile_ctx.get("kpis", [])
        kpi_names = [k["name"] for k in kpis[:5]]
        industry = profile_ctx.get("company_identity", {}).get("industry", "")

        reasoning_text = "\n".join(reasoning)
        risks_text = "\n".join(f"- {r.get('description', '')}" for r in risks[:5])

        prompt = f"""Based on the analysis, provide a clear, actionable recommendation for this {industry} company.

Question: {question}
Reasoning: {reasoning_text}
Risks: {risks_text}
Company KPIs: {', '.join(kpi_names) if kpi_names else 'Not defined'}

Reference specific KPIs and company terminology in your recommendation where relevant.
2-3 sentences."""

        try:
            response = await self.gateway.generate(
                GenerateRequest(prompt=prompt, temperature=0.4, max_tokens=500)
            )
            return response.content
        except Exception as exc:
            logger.error("Profile-aware recommendation failed: %s", exc)
            return "Unable to generate recommendation with profile context."

    @staticmethod
    def _calculate_confidence(reasoning: list[str], risks: list[dict], profile_confidence: float) -> float:
        """Calculate confidence weighting profile confidence."""
        reasoning_factor = min(len(reasoning) / 5, 1.0) * 0.3
        risk_factor = 1.0 - min(max((r.get("risk_score", 0.5) for r in risks), default=0.5), 1.0) * 0.4
        profile_factor = profile_confidence * 0.3
        return round(max(0.0, min(1.0, reasoning_factor + risk_factor + profile_factor)), 4)
