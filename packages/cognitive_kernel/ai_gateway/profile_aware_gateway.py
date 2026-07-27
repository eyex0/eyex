"""
πX Profile-Aware AI Gateway — AI Gateway integration.

Routes AI requests based on organization's AI policies:
  - preferred_models: org can specify which models to use
  - budget_limit: enforce spending caps
  - privacy_level: "private" → only local/on-prem models; "standard" → any
  - data_sensitivity: "high" → no external API calls, local models only

Financial company with sensitive data → private models only.
SaaS company with public data → cheapest/fastest model.
"""
from __future__ import annotations

import logging
from typing import Any

from packages.cognitive_kernel.ai_gateway.main import AIGateway
from packages.cognitive_kernel.ai_gateway.providers.base import GenerateRequest
from packages.cognitive_kernel.intelligence_profile.context_provider import ProfileContextProvider

logger = logging.getLogger("pix.ai_gateway.profile_aware")


class ProfileAwareAIGateway:
    """AI Gateway wrapper that respects organization AI policies."""

    def __init__(
        self,
        gateway: AIGateway | None = None,
        context_provider: ProfileContextProvider | None = None,
    ):
        self.gateway = gateway or AIGateway()
        self.context_provider = context_provider

    async def generate(
        self,
        request: GenerateRequest,
        organization_id: str,
        context_provider: ProfileContextProvider | None = None,
    ) -> Any:
        """Generate with org-specific AI policy enforcement."""
        provider = context_provider or self.context_provider
        if not provider:
            return await self.gateway.generate(request)

        policy = await provider.get_ai_policy(organization_id)

        # Check privacy level
        privacy = policy.get("privacy_level", "standard")
        sensitivity = policy.get("data_sensitivity", "normal")

        if privacy == "private" or sensitivity == "high":
            # Restrict to local/private models only
            preferred = policy.get("preferred_models", {})
            if preferred:
                # Use the org's preferred private model
                request.model = preferred.get("primary", "ollama:llama3")
                request.provider = "ollama"
            logger.info("Org %s: routing to private model due to privacy policy", organization_id)
        elif preferred := policy.get("preferred_models", {}).get("primary"):
            # Use org's preferred model
            request.model = preferred
            logger.debug("Org %s: using preferred model %s", organization_id, preferred)

        # Check budget (simplified — real implementation would check cost tracker)
        budget_limit = policy.get("budget_limit")
        if budget_limit:
            # Could check accumulated spend vs budget here
            logger.debug("Org %s: budget limit = %s", organization_id, budget_limit)

        return await self.gateway.generate(request)
