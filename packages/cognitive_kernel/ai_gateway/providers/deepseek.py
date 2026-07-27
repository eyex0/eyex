import os
from typing import Optional, List
from openai import AsyncOpenAI

from .base import ProviderCapability
from .openai import OpenAIProvider

class DeepSeekProvider(OpenAIProvider):
    """
    DeepSeek AI Provider (inherits from OpenAIProvider due to protocol compatibility).
    """
    MODEL_PRICING = {
        "deepseek-chat": {"input_rate": 0.14 / 1_000_000, "output_rate": 0.28 / 1_000_000},
        "deepseek-reasoner": {"input_rate": 0.55 / 1_000_000, "output_rate": 2.19 / 1_000_000},
    }

    def __init__(self, api_key: Optional[str] = None, max_retries: int = 3, timeout: float = 60.0):
        key = api_key or os.environ.get("DEEPSEEK_API_KEY", "")
        # Set base_url to deepseek API
        self._client = AsyncOpenAI(api_key=key, base_url="https://api.deepseek.com/v1") if key else None
        self.max_retries = max_retries
        self.timeout = timeout

    @property
    def name(self) -> str:
        return "deepseek"

    @property
    def capabilities(self) -> List[ProviderCapability]:
        return [
            ProviderCapability.GENERATION,
            ProviderCapability.STREAMING,
            ProviderCapability.CLASSIFICATION,
            ProviderCapability.SUMMARIZATION,
        ]

    def _get_client(self) -> AsyncOpenAI:
        if not self._client:
            key = os.environ.get("DEEPSEEK_API_KEY", "")
            if not key:
                raise ValueError("DeepSeek API key not set")
            self._client = AsyncOpenAI(api_key=key, base_url="https://api.deepseek.com/v1")
        return self._client

    def _to_generate_request(self, request, model=None, **kwargs):
        req = super()._to_generate_request(request, model, **kwargs)
        if req.model == "gpt-4o" or req.model == "gemini-1.5-flash":
            req.model = "deepseek-chat"  # fallback default
        return req

    def _calculate_cost(self, model: str, input_tokens: int, output_tokens: int) -> float:
        pricing = self.MODEL_PRICING.get(model, self.MODEL_PRICING["deepseek-chat"])
        return (input_tokens * pricing["input_rate"]) + (output_tokens * pricing["output_rate"])
