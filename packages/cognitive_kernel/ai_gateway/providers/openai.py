import asyncio
import time
import logging
from typing import Any, AsyncGenerator, Dict, List, Optional
import openai
from openai import AsyncOpenAI

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

class OpenAIProvider(AIProvider):
    """
    OpenAI AI Provider implementation.
    """
    MODEL_PRICING = {
        "gpt-4o": {"input_rate": 2.50 / 1_000_000, "output_rate": 10.00 / 1_000_000},
        "gpt-4o-mini": {"input_rate": 0.15 / 1_000_000, "output_rate": 0.60 / 1_000_000},
        "gpt-4": {"input_rate": 30.00 / 1_000_000, "output_rate": 60.00 / 1_000_000},
        "gpt-3.5-turbo": {"input_rate": 0.50 / 1_000_000, "output_rate": 1.50 / 1_000_000},
        "text-embedding-3-small": {"input_rate": 0.02 / 1_000_000, "output_rate": 0.0},
        "text-embedding-3-large": {"input_rate": 0.13 / 1_000_000, "output_rate": 0.0},
    }

    def __init__(self, api_key: Optional[str] = None, max_retries: int = 3, timeout: float = 60.0):
        import os
        key = api_key or os.environ.get("OPENAI_API_KEY", "")
        self._client = AsyncOpenAI(api_key=key) if key else None
        self.max_retries = max_retries
        self.timeout = timeout

    @property
    def name(self) -> str:
        return "openai"

    @property
    def capabilities(self) -> List[ProviderCapability]:
        return [
            ProviderCapability.GENERATION,
            ProviderCapability.STREAMING,
            ProviderCapability.EMBEDDING,
            ProviderCapability.CLASSIFICATION,
            ProviderCapability.SUMMARIZATION,
        ]

    def _get_client(self) -> AsyncOpenAI:
        if not self._client:
            import os
            key = os.environ.get("OPENAI_API_KEY", "")
            if not key:
                raise ProviderUnavailableError("OpenAI API key not set")
            self._client = AsyncOpenAI(api_key=key)
        return self._client

    def _to_generate_request(self, request: GenerateRequest | str, model: Optional[str] = None, **kwargs) -> GenerateRequest:
        if isinstance(request, GenerateRequest):
            return request
        
        # Merge prompt, model and extra arguments
        prompt = request
        model_name = model or kwargs.pop("model", "gpt-4o")
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

    def _to_embed_request(self, request: EmbedRequest | List[str], model: Optional[str] = None, **kwargs) -> EmbedRequest:
        if isinstance(request, EmbedRequest):
            return request
        texts = request if isinstance(request, list) else [str(request)]
        model_name = model or kwargs.pop("model", "text-embedding-3-small")
        return EmbedRequest(texts=texts, model=model_name)

    def _calculate_cost(self, model: str, input_tokens: int, output_tokens: int) -> float:
        # Default pricing is gpt-4o
        pricing = self.MODEL_PRICING.get(model, self.MODEL_PRICING["gpt-4o"])
        return (input_tokens * pricing["input_rate"]) + (output_tokens * pricing["output_rate"])

    async def generate(self, request: GenerateRequest | str, model: Optional[str] = None, **kwargs) -> GenerateResponse:
        req = self._to_generate_request(request, model, **kwargs)
        client = self._get_client()
        start_time = time.perf_counter()

        messages = []
        if req.system_prompt:
            messages.append({"role": "system", "content": req.system_prompt})
        messages.append({"role": "user", "content": req.prompt})

        api_kwargs: Dict[str, Any] = {
            "model": req.model,
            "messages": messages,
            "temperature": req.temperature,
        }
        if req.max_tokens:
            api_kwargs["max_tokens"] = req.max_tokens
        if req.stop_sequences:
            api_kwargs["stop"] = req.stop_sequences
        if req.extra_params:
            api_kwargs.update(req.extra_params)

        for attempt in range(self.max_retries):
            try:
                response = await asyncio.wait_for(
                    client.chat.completions.create(**api_kwargs),
                    timeout=self.timeout
                )
                
                content = response.choices[0].message.content or ""
                latency_ms = (time.perf_counter() - start_time) * 1000

                usage = response.usage
                input_tokens = usage.prompt_tokens if usage else len(req.prompt) // 4 + 1
                output_tokens = usage.completion_tokens if usage else len(content) // 4 + 1
                total_tokens = usage.total_tokens if usage else (input_tokens + output_tokens)

                tokens_used = {
                    "input": input_tokens,
                    "output": output_tokens,
                    "total": total_tokens
                }

                cost = self._calculate_cost(req.model, input_tokens, output_tokens)

                return GenerateResponse(
                    content=content,
                    model=req.model,
                    tokens_used=tokens_used,
                    cost=cost,
                    latency_ms=latency_ms,
                    provider=self.name,
                    metadata={"finish_reason": response.choices[0].finish_reason if response.choices else None}
                )

            except openai.RateLimitError as e:
                logger.warning(f"OpenAI Rate Limit on attempt {attempt+1}: {e}")
                if attempt + 1 == self.max_retries:
                    raise RateLimitError(str(e), status_code=429)
                await asyncio.sleep(2 ** attempt)
            except (openai.APIConnectionError, openai.InternalServerError, asyncio.TimeoutError) as e:
                logger.warning(f"OpenAI connection error on attempt {attempt+1}: {e}")
                if attempt + 1 == self.max_retries:
                    raise ProviderUnavailableError(f"OpenAI provider unavailable: {str(e)}")
                await asyncio.sleep(2 ** attempt)
            except openai.APIError as e:
                raise ProviderError(f"OpenAI API Error: {str(e)}", status_code=e.status_code)
            except Exception as e:
                raise ProviderError(f"Unexpected OpenAI Error: {str(e)}")

    async def stream(self, request: GenerateRequest | str, model: Optional[str] = None, **kwargs) -> AsyncGenerator[StreamChunk, None]:
        req = self._to_generate_request(request, model, **kwargs)
        client = self._get_client()
        start_time = time.perf_counter()

        messages = []
        if req.system_prompt:
            messages.append({"role": "system", "content": req.system_prompt})
        messages.append({"role": "user", "content": req.prompt})

        api_kwargs: Dict[str, Any] = {
            "model": req.model,
            "messages": messages,
            "temperature": req.temperature,
            "stream": True,
            "stream_options": {"include_usage": True} if "gpt" in req.model else None
        }
        if req.max_tokens:
            api_kwargs["max_tokens"] = req.max_tokens
        if req.stop_sequences:
            api_kwargs["stop"] = req.stop_sequences
        if req.extra_params:
            api_kwargs.update(req.extra_params)

        try:
            stream = await asyncio.wait_for(
                client.chat.completions.create(**api_kwargs),
                timeout=self.timeout
            )
            
            accumulated_content = []
            async for chunk in stream:
                if not chunk.choices and hasattr(chunk, "usage") and chunk.usage:
                    # Final chunk with token usage
                    usage = chunk.usage
                    input_tokens = usage.prompt_tokens
                    output_tokens = usage.completion_tokens
                    total_tokens = usage.total_tokens
                    tokens_used = {"input": input_tokens, "output": output_tokens, "total": total_tokens}
                    cost = self._calculate_cost(req.model, input_tokens, output_tokens)
                    latency_ms = (time.perf_counter() - start_time) * 1000

                    yield StreamChunk(
                        content="",
                        model=req.model,
                        tokens_used=tokens_used,
                        cost=cost,
                        latency_ms=latency_ms,
                        provider=self.name,
                        is_final=True
                    )
                    break

                if chunk.choices:
                    delta = chunk.choices[0].delta.content or ""
                    accumulated_content.append(delta)
                    yield StreamChunk(
                        content=delta,
                        model=req.model,
                        provider=self.name,
                        is_final=False
                    )

            # Fallback if no usage chunk was returned
            else:
                full_content = "".join(accumulated_content)
                input_tokens = len(req.prompt) // 4 + 1
                output_tokens = len(full_content) // 4 + 1
                tokens_used = {"input": input_tokens, "output": output_tokens, "total": input_tokens + output_tokens}
                cost = self._calculate_cost(req.model, input_tokens, output_tokens)
                latency_ms = (time.perf_counter() - start_time) * 1000

                yield StreamChunk(
                    content="",
                    model=req.model,
                    tokens_used=tokens_used,
                    cost=cost,
                    latency_ms=latency_ms,
                    provider=self.name,
                    is_final=True
                )

        except openai.RateLimitError as e:
            raise RateLimitError(str(e), status_code=429)
        except (openai.APIConnectionError, openai.InternalServerError, asyncio.TimeoutError) as e:
            raise ProviderUnavailableError(f"OpenAI streaming unavailable: {str(e)}")
        except Exception as e:
            raise ProviderError(f"OpenAI streaming error: {str(e)}")

    async def embed(self, request: EmbedRequest | List[str], model: Optional[str] = None, **kwargs) -> EmbedResponse:
        req = self._to_embed_request(request, model, **kwargs)
        client = self._get_client()
        start_time = time.perf_counter()

        for attempt in range(self.max_retries):
            try:
                response = await asyncio.wait_for(
                    client.embeddings.create(
                        model=req.model,
                        input=req.texts,
                    ),
                    timeout=self.timeout
                )

                latency_ms = (time.perf_counter() - start_time) * 1000
                embeddings = [data.embedding for data in response.data]

                usage = response.usage
                input_tokens = usage.prompt_tokens if usage else sum(len(t) // 4 + 1 for t in req.texts)
                tokens_used = {
                    "input": input_tokens,
                    "output": 0,
                    "total": input_tokens
                }

                pricing = self.MODEL_PRICING.get(req.model, self.MODEL_PRICING["text-embedding-3-small"])
                cost = input_tokens * pricing["input_rate"]

                return EmbedResponse(
                    content="",
                    embeddings=embeddings,
                    model=req.model,
                    tokens_used=tokens_used,
                    cost=cost,
                    latency_ms=latency_ms,
                    provider=self.name
                )

            except openai.RateLimitError as e:
                if attempt + 1 == self.max_retries:
                    raise RateLimitError(str(e), status_code=429)
                await asyncio.sleep(2 ** attempt)
            except (openai.APIConnectionError, openai.InternalServerError, asyncio.TimeoutError) as e:
                if attempt + 1 == self.max_retries:
                    raise ProviderUnavailableError(f"OpenAI embed unavailable: {str(e)}")
                await asyncio.sleep(2 ** attempt)
            except Exception as e:
                raise ProviderError(f"OpenAI embed error: {str(e)}")

    async def evaluate(self, text: str, criteria: str, model: Optional[str] = None, **kwargs) -> GenerateResponse:
        prompt = f"Evaluate the following response based on this criteria: {criteria}. Return a rating/score from 0-10 and a clear, detailed justification.\n\nResponse to evaluate:\n{text}"
        return await self.generate(prompt, model=model or "gpt-4o", **kwargs)

    async def classify(self, text: str, categories: List[str], model: Optional[str] = None, **kwargs) -> GenerateResponse:
        prompt = f"Classify the following text into exactly one of these categories: {', '.join(categories)}.\nReturn ONLY the chosen category name and nothing else.\n\nText to classify:\n{text}"
        return await self.generate(prompt, model=model or "gpt-4o-mini", **kwargs)

    async def summarize(self, text: str, max_length: int = 500, model: Optional[str] = None, **kwargs) -> GenerateResponse:
        prompt = f"Summarize the following text in under {max_length} characters. Provide a highly concise summary.\n\nText to summarize:\n{text}"
        return await self.generate(prompt, model=model or "gpt-4o-mini", **kwargs)
