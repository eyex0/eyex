import os
from typing import Optional, List
from openai import AsyncOpenAI

from .base import ProviderCapability
from .openai import OpenAIProvider

class OpenRouterProvider(OpenAIProvider):
    """
    OpenRouter AI Provider (inherits from OpenAIProvider due to protocol compatibility).
    """
    MODEL_PRICING = {
        "meta-llama/llama-3-8b-instruct": {"input_rate": 0.05 / 1_000_000, "output_rate": 0.05 / 1_000_000},
        "mistralai/mixtral-8x7b-instruct": {"input_rate": 0.24 / 1_000_000, "output_rate": 0.24 / 1_000_000},
        "anthropic/claude-3.5-sonnet": {"input_rate": 3.00 / 1_000_000, "output_rate": 15.00 / 1_000_000},
        "google/gemini-flash-1.5": {"input_rate": 0.075 / 1_000_000, "output_rate": 0.30 / 1_000_000},
    }

    def __init__(self, api_key: Optional[str] = None, max_retries: int = 3, timeout: float = 60.0):
        key = api_key or os.environ.get("OPENROUTER_API_KEY", "")
        self._client = AsyncOpenAI(
            api_key=key,
            base_url="https://openrouter.ai/api/v1",
            default_headers={
                "HTTP-Referer": "https://github.com/eyex-audit",
                "X-Title": "eyex-audit AI Control Plane"
            }
        ) if key else None
        self.max_retries = max_retries
        self.timeout = timeout

    @property
    def name(self) -> str:
        return "openrouter"

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
            key = os.environ.get("OPENROUTER_API_KEY", "")
            if not key:
                raise ValueError("OpenRouter API key not set")
            self._client = AsyncOpenAI(
                api_key=key,
                base_url="https://openrouter.ai/api/v1",
                default_headers={
                    "HTTP-Referer": "https://github.com/eyex-audit",
                    "X-Title": "eyex-audit AI Control Plane"
                }
            )
        return self._client

    def _to_generate_request(self, request, model=None, **kwargs):
        req = super()._to_generate_request(request, model, **kwargs)
        if req.model in ["gpt-4o", "gemini-1.5-flash", "claude-3-5-sonnet"]:
            # Route to a generic openrouter model if the caller uses default keys
            req.model = "meta-llama/llama-3-8b-instruct"
        return req

    def _calculate_cost(self, model: str, input_tokens: int, output_tokens: int) -> float:
        pricing = self.MODEL_PRICING.get(model, {"input_rate": 1.00 / 1_000_000, "output_rate": 2.00 / 1_000_000})
        return (input_tokens * pricing["input_rate"]) + (output_tokens * pricing["output_rate"])
