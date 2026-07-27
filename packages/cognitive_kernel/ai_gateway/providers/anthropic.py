import asyncio
import json
import time
import logging
from typing import Any, AsyncGenerator, Dict, List, Optional
import httpx

from .base import (
    AIProvider,
    ProviderCapability,
    GenerateRequest,
    GenerateResponse,
    StreamChunk,
    EmbedRequest,
    EmbedResponse,
    ProviderError,
    ProviderUnavailableError,
    RateLimitError,
)

logger = logging.getLogger(__name__)

class AnthropicProvider(AIProvider):
    """
    Anthropic AI Provider implementation using httpx.
    """
    MODEL_PRICING = {
        "claude-3-opus": {"input_rate": 15.00 / 1_000_000, "output_rate": 75.00 / 1_000_000},
        "claude-3-opus-20240229": {"input_rate": 15.00 / 1_000_000, "output_rate": 75.00 / 1_000_000},
        "claude-3-5-sonnet": {"input_rate": 3.00 / 1_000_000, "output_rate": 15.00 / 1_000_000},
        "claude-3-5-sonnet-20240620": {"input_rate": 3.00 / 1_000_000, "output_rate": 15.00 / 1_000_000},
        "claude-3-haiku": {"input_rate": 0.25 / 1_000_000, "output_rate": 1.25 / 1_000_000},
        "claude-3-haiku-20240307": {"input_rate": 0.25 / 1_000_000, "output_rate": 1.25 / 1_000_000},
    }

    def __init__(self, api_key: Optional[str] = None, max_retries: int = 3, timeout: float = 60.0):
        import os
        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY", "")
        self.max_retries = max_retries
        self.timeout = timeout

    @property
    def name(self) -> str:
        return "anthropic"

    @property
    def capabilities(self) -> List[ProviderCapability]:
        return [
            ProviderCapability.GENERATION,
            ProviderCapability.STREAMING,
            ProviderCapability.CLASSIFICATION,
            ProviderCapability.SUMMARIZATION,
        ]

    def _get_headers(self) -> Dict[str, str]:
        if not self.api_key:
            import os
            self.api_key = os.environ.get("ANTHROPIC_API_KEY", "")
            if not self.api_key:
                raise ProviderUnavailableError("Anthropic API key not set")
        return {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }

    def _to_generate_request(self, request: GenerateRequest | str, model: Optional[str] = None, **kwargs) -> GenerateRequest:
        if isinstance(request, GenerateRequest):
            return request
        
        prompt = request
        model_name = model or kwargs.pop("model", "claude-3-5-sonnet")
        system_prompt = kwargs.pop("system_prompt", None)
        temperature = kwargs.pop("temperature", 0.7)
        max_tokens = kwargs.pop("max_tokens", None)
        stop_sequences = kwargs.pop("stop_sequences", None)
        
        return GenerateRequest(
            prompt=prompt,
            model=model_name,
            system_prompt=system_prompt,
            temperature=temperature,
            max_tokens=max_tokens,
            stop_sequences=stop_sequences,
            extra_params=kwargs
        )

    def _calculate_cost(self, model: str, input_tokens: int, output_tokens: int) -> float:
        # Default pricing matches Claude 3.5 Sonnet
        pricing = self.MODEL_PRICING.get(model)
        if not pricing:
            # Check prefix matches
            for k, v in self.MODEL_PRICING.items():
                if model.startswith(k):
                    pricing = v
                    break
            else:
                pricing = self.MODEL_PRICING["claude-3-5-sonnet"]
        return (input_tokens * pricing["input_rate"]) + (output_tokens * pricing["output_rate"])

    async def generate(self, request: GenerateRequest | str, model: Optional[str] = None, **kwargs) -> GenerateResponse:
        req = self._to_generate_request(request, model, **kwargs)
        headers = self._get_headers()
        start_time = time.perf_counter()

        body = {
            "model": req.model,
            "messages": [{"role": "user", "content": req.prompt}],
            "max_tokens": req.max_tokens or 4096,
            "temperature": req.temperature,
        }
        if req.system_prompt:
            body["system"] = req.system_prompt
        if req.stop_sequences:
            body["stop_sequences"] = req.stop_sequences
        if req.extra_params:
            body.update(req.extra_params)

        for attempt in range(self.max_retries):
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.post(
                        "https://api.anthropic.com/v1/messages",
                        headers=headers,
                        json=body,
                        timeout=self.timeout
                    )
                
                latency_ms = (time.perf_counter() - start_time) * 1000

                if response.status_code == 429:
                    raise RateLimitError(response.text, status_code=429)
                elif response.status_code >= 500:
                    raise ProviderUnavailableError(f"Anthropic API internal error: {response.text}", status_code=response.status_code)
                elif response.status_code != 200:
                    raise ProviderError(f"Anthropic API Error: {response.text}", status_code=response.status_code)

                data = response.json()
                content = data["content"][0]["text"] if data.get("content") else ""
                
                usage = data.get("usage") or {}
                input_tokens = usage.get("input_tokens", len(req.prompt) // 4 + 1)
                output_tokens = usage.get("output_tokens", len(content) // 4 + 1)
                
                tokens_used = {
                    "input": input_tokens,
                    "output": output_tokens,
                    "total": input_tokens + output_tokens
                }

                cost = self._calculate_cost(req.model, input_tokens, output_tokens)

                return GenerateResponse(
                    content=content,
                    model=req.model,
                    tokens_used=tokens_used,
                    cost=cost,
                    latency_ms=latency_ms,
                    provider=self.name,
                    metadata={"stop_reason": data.get("stop_reason")}
                )

            except RateLimitError as e:
                logger.warning(f"Anthropic Rate Limit on attempt {attempt+1}: {e}")
                if attempt + 1 == self.max_retries:
                    raise
                await asyncio.sleep(2 ** attempt)
            except (httpx.RequestError, asyncio.TimeoutError, ProviderUnavailableError) as e:
                logger.warning(f"Anthropic connection error on attempt {attempt+1}: {e}")
                if attempt + 1 == self.max_retries:
                    raise ProviderUnavailableError(f"Anthropic provider unavailable: {str(e)}")
                await asyncio.sleep(2 ** attempt)
            except Exception as e:
                if isinstance(e, ProviderError):
                    raise
                raise ProviderError(f"Unexpected Anthropic Error: {str(e)}")

    async def stream(self, request: GenerateRequest | str, model: Optional[str] = None, **kwargs) -> AsyncGenerator[StreamChunk, None]:
        req = self._to_generate_request(request, model, **kwargs)
        headers = self._get_headers()
        start_time = time.perf_counter()

        body = {
            "model": req.model,
            "messages": [{"role": "user", "content": req.prompt}],
            "max_tokens": req.max_tokens or 4096,
            "temperature": req.temperature,
            "stream": True
        }
        if req.system_prompt:
            body["system"] = req.system_prompt
        if req.stop_sequences:
            body["stop_sequences"] = req.stop_sequences
        if req.extra_params:
            body.update(req.extra_params)

        try:
            async with httpx.AsyncClient() as client:
                async with client.stream(
                    "POST",
                    "https://api.anthropic.com/v1/messages",
                    headers=headers,
                    json=body,
                    timeout=self.timeout
                ) as response:
                    
                    if response.status_code == 429:
                        raise RateLimitError(response.read().decode(), status_code=429)
                    elif response.status_code != 200:
                        raise ProviderError(f"Anthropic API stream error: {response.read().decode()}", status_code=response.status_code)

                    input_tokens = 0
                    output_tokens = 0
                    accumulated_content = []

                    async for line in response.aiter_lines():
                        if not line:
                            continue
                        if line.startswith("event:"):
                            event_type = line[6:].strip()
                            continue
                        if line.startswith("data:"):
                            raw_data = line[5:].strip()
                            try:
                                data = json.loads(raw_data)
                            except json.JSONDecodeError:
                                continue

                            t_type = data.get("type")
                            if t_type == "message_start":
                                msg = data.get("message") or {}
                                usage = msg.get("usage") or {}
                                input_tokens = usage.get("input_tokens", 0)
                            elif t_type == "content_block_delta":
                                delta = data.get("delta") or {}
                                text = delta.get("text", "")
                                accumulated_content.append(text)
                                yield StreamChunk(
                                    content=text,
                                    model=req.model,
                                    provider=self.name,
                                    is_final=False
                                )
                            elif t_type == "message_delta":
                                usage = data.get("usage") or {}
                                output_tokens = usage.get("output_tokens", 0)
                            elif t_type == "message_stop":
                                # Stream complete
                                latency_ms = (time.perf_counter() - start_time) * 1000
                                if not input_tokens:
                                    input_tokens = len(req.prompt) // 4 + 1
                                if not output_tokens:
                                    output_tokens = len("".join(accumulated_content)) // 4 + 1
                                
                                tokens_used = {
                                    "input": input_tokens,
                                    "output": output_tokens,
                                    "total": input_tokens + output_tokens
                                }
                                cost = self._calculate_cost(req.model, input_tokens, output_tokens)

                                yield StreamChunk(
                                    content="",
                                    model=req.model,
                                    tokens_used=tokens_used,
                                    cost=cost,
                                    latency_ms=latency_ms,
                                    provider=self.name,
                                    is_final=True
                                )

        except RateLimitError as e:
            raise RateLimitError(str(e), status_code=429)
        except Exception as e:
            if isinstance(e, ProviderError):
                raise
            raise ProviderError(f"Anthropic streaming error: {str(e)}")

    async def embed(self, request: EmbedRequest | List[str], model: Optional[str] = None, **kwargs) -> EmbedResponse:
        raise ProviderError("Anthropic does not support vector embedding generation directly.")

    async def evaluate(self, text: str, criteria: str, model: Optional[str] = None, **kwargs) -> GenerateResponse:
        prompt = f"Evaluate the following response based on this criteria: {criteria}. Return a rating/score from 0-10 and a clear, detailed justification.\n\nResponse to evaluate:\n{text}"
        return await self.generate(prompt, model=model or "claude-3-5-sonnet", **kwargs)

    async def classify(self, text: str, categories: List[str], model: Optional[str] = None, **kwargs) -> GenerateResponse:
        prompt = f"Classify the following text into exactly one of these categories: {', '.join(categories)}.\nReturn ONLY the chosen category name and nothing else.\n\nText to classify:\n{text}"
        return await self.generate(prompt, model=model or "claude-3-5-sonnet", **kwargs)

    async def summarize(self, text: str, max_length: int = 500, model: Optional[str] = None, **kwargs) -> GenerateResponse:
        prompt = f"Summarize the following text in under {max_length} characters. Provide a highly concise summary.\n\nText to summarize:\n{text}"
        return await self.generate(prompt, model=model or "claude-3-5-sonnet", **kwargs)
