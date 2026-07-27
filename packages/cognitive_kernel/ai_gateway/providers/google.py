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

class GoogleGeminiProvider(AIProvider):
    """
    Google Gemini AI Provider implementation using httpx.
    """
    MODEL_PRICING = {
        "gemini-1.5-flash": {"input_rate": 0.075 / 1_000_000, "output_rate": 0.30 / 1_000_000},
        "gemini-1.5-pro": {"input_rate": 1.25 / 1_000_000, "output_rate": 5.00 / 1_000_000},
        "text-embedding-004": {"input_rate": 0.025 / 1_000_000, "output_rate": 0.0},
    }

    def __init__(self, api_key: Optional[str] = None, max_retries: int = 3, timeout: float = 60.0):
        import os
        self.api_key = api_key or os.environ.get("GOOGLE_API_KEY", "")
        self.max_retries = max_retries
        self.timeout = timeout

    @property
    def name(self) -> str:
        return "google"

    @property
    def capabilities(self) -> List[ProviderCapability]:
        return [
            ProviderCapability.GENERATION,
            ProviderCapability.STREAMING,
            ProviderCapability.EMBEDDING,
            ProviderCapability.CLASSIFICATION,
            ProviderCapability.SUMMARIZATION,
        ]

    def _get_api_key(self) -> str:
        if not self.api_key:
            import os
            self.api_key = os.environ.get("GOOGLE_API_KEY", "")
            if not self.api_key:
                raise ProviderUnavailableError("Google API key not set")
        return self.api_key

    def _to_generate_request(self, request: GenerateRequest | str, model: Optional[str] = None, **kwargs) -> GenerateRequest:
        if isinstance(request, GenerateRequest):
            return request
        
        prompt = request
        model_name = model or kwargs.pop("model", "gemini-1.5-flash")
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
        model_name = model or kwargs.pop("model", "text-embedding-004")
        return EmbedRequest(texts=texts, model=model_name)

    def _calculate_cost(self, model: str, input_tokens: int, output_tokens: int) -> float:
        pricing = self.MODEL_PRICING.get(model)
        if not pricing:
            for k, v in self.MODEL_PRICING.items():
                if k in model:
                    pricing = v
                    break
            else:
                pricing = self.MODEL_PRICING["gemini-1.5-flash"]
        return (input_tokens * pricing["input_rate"]) + (output_tokens * pricing["output_rate"])

    async def generate(self, request: GenerateRequest | str, model: Optional[str] = None, **kwargs) -> GenerateResponse:
        req = self._to_generate_request(request, model, **kwargs)
        api_key = self._get_api_key()
        start_time = time.perf_counter()

        # Format model name (prefixed with models/ if not already)
        model_id = req.model
        if not model_id.startswith("models/"):
            model_id = f"models/{model_id}"

        body: Dict[str, Any] = {
            "contents": [
                {
                    "parts": [{"text": req.prompt}]
                }
            ],
            "generationConfig": {
                "temperature": req.temperature,
            }
        }
        if req.system_prompt:
            body["systemInstruction"] = {
                "parts": [{"text": req.system_prompt}]
            }
        if req.max_tokens:
            body["generationConfig"]["maxOutputTokens"] = req.max_tokens
        if req.stop_sequences:
            body["generationConfig"]["stopSequences"] = req.stop_sequences
        if req.extra_params:
            body.update(req.extra_params)

        url = f"https://generativelanguage.googleapis.com/v1beta/{model_id}:generateContent?key={api_key}"

        for attempt in range(self.max_retries):
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.post(
                        url,
                        json=body,
                        headers={"content-type": "application/json"},
                        timeout=self.timeout
                    )
                
                latency_ms = (time.perf_counter() - start_time) * 1000

                if response.status_code == 429:
                    raise RateLimitError(response.text, status_code=429)
                elif response.status_code >= 500:
                    raise ProviderUnavailableError(f"Google Gemini internal error: {response.text}", status_code=response.status_code)
                elif response.status_code != 200:
                    raise ProviderError(f"Google Gemini Error: {response.text}", status_code=response.status_code)

                data = response.json()
                
                candidates = data.get("candidates") or []
                content = ""
                if candidates:
                    parts = candidates[0].get("content", {}).get("parts") or []
                    content = "".join(p.get("text", "") for p in parts)

                usage = data.get("usageMetadata") or {}
                input_tokens = usage.get("promptTokenCount", len(req.prompt) // 4 + 1)
                output_tokens = usage.get("candidatesTokenCount", len(content) // 4 + 1)
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
                    metadata={"finish_reason": candidates[0].get("finishReason") if candidates else None}
                )

            except RateLimitError as e:
                logger.warning(f"Google Rate Limit on attempt {attempt+1}: {e}")
                if attempt + 1 == self.max_retries:
                    raise
                await asyncio.sleep(2 ** attempt)
            except (httpx.RequestError, asyncio.TimeoutError, ProviderUnavailableError) as e:
                logger.warning(f"Google connection error on attempt {attempt+1}: {e}")
                if attempt + 1 == self.max_retries:
                    raise ProviderUnavailableError(f"Google provider unavailable: {str(e)}")
                await asyncio.sleep(2 ** attempt)
            except Exception as e:
                if isinstance(e, ProviderError):
                    raise
                raise ProviderError(f"Unexpected Google Gemini Error: {str(e)}")

    async def stream(self, request: GenerateRequest | str, model: Optional[str] = None, **kwargs) -> AsyncGenerator[StreamChunk, None]:
        req = self._to_generate_request(request, model, **kwargs)
        api_key = self._get_api_key()
        start_time = time.perf_counter()

        model_id = req.model
        if not model_id.startswith("models/"):
            model_id = f"models/{model_id}"

        body = {
            "contents": [
                {
                    "parts": [{"text": req.prompt}]
                }
            ],
            "generationConfig": {
                "temperature": req.temperature,
            }
        }
        if req.system_prompt:
            body["systemInstruction"] = {
                "parts": [{"text": req.system_prompt}]
            }
        if req.max_tokens:
            body["generationConfig"]["maxOutputTokens"] = req.max_tokens
        if req.stop_sequences:
            body["generationConfig"]["stopSequences"] = req.stop_sequences
        if req.extra_params:
            body.update(req.extra_params)

        url = f"https://generativelanguage.googleapis.com/v1beta/{model_id}:streamGenerateContent?alt=sse&key={api_key}"

        try:
            async with httpx.AsyncClient() as client:
                async with client.stream(
                    "POST",
                    url,
                    headers={"content-type": "application/json"},
                    json=body,
                    timeout=self.timeout
                ) as response:
                    
                    if response.status_code == 429:
                        raise RateLimitError(response.read().decode(), status_code=429)
                    elif response.status_code != 200:
                        raise ProviderError(f"Google Gemini stream error: {response.read().decode()}", status_code=response.status_code)

                    input_tokens = 0
                    output_tokens = 0
                    accumulated_content = []

                    async for line in response.aiter_lines():
                        if not line:
                            continue
                        if line.startswith("data:"):
                            raw_data = line[5:].strip()
                            try:
                                data = json.loads(raw_data)
                            except json.JSONDecodeError:
                                continue

                            candidates = data.get("candidates") or []
                            text = ""
                            if candidates:
                                parts = candidates[0].get("content", {}).get("parts") or []
                                text = "".join(p.get("text", "") for p in parts)
                                accumulated_content.append(text)
                                yield StreamChunk(
                                    content=text,
                                    model=req.model,
                                    provider=self.name,
                                    is_final=False
                                )

                            usage = data.get("usageMetadata") or {}
                            if usage:
                                input_tokens = usage.get("promptTokenCount", 0)
                                output_tokens = usage.get("candidatesTokenCount", 0)

                    # Finished stream
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
            raise ProviderError(f"Google Gemini streaming error: {str(e)}")

    async def embed(self, request: EmbedRequest | List[str], model: Optional[str] = None, **kwargs) -> EmbedResponse:
        req = self._to_embed_request(request, model, **kwargs)
        api_key = self._get_api_key()
        start_time = time.perf_counter()

        model_id = req.model
        if not model_id.startswith("models/"):
            model_id = f"models/{model_id}"

        # Gemini supports batch embedding
        requests_list = []
        for text in req.texts:
            requests_list.append({
                "model": model_id,
                "content": {
                    "parts": [{"text": text}]
                }
            })

        body = {"requests": requests_list}
        url = f"https://generativelanguage.googleapis.com/v1beta/{model_id}:batchEmbedContents?key={api_key}"

        for attempt in range(self.max_retries):
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.post(
                        url,
                        headers={"content-type": "application/json"},
                        json=body,
                        timeout=self.timeout
                    )
                
                latency_ms = (time.perf_counter() - start_time) * 1000

                if response.status_code == 429:
                    raise RateLimitError(response.text, status_code=429)
                elif response.status_code != 200:
                    raise ProviderError(f"Google Gemini embed error: {response.text}", status_code=response.status_code)

                data = response.json()
                embeddings_data = data.get("embeddings") or []
                embeddings = [item.get("values", []) for item in embeddings_data]

                input_tokens = sum(len(text) // 4 + 1 for text in req.texts)
                tokens_used = {
                    "input": input_tokens,
                    "output": 0,
                    "total": input_tokens
                }

                pricing = self.MODEL_PRICING.get(req.model, self.MODEL_PRICING["text-embedding-004"])
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

            except RateLimitError as e:
                if attempt + 1 == self.max_retries:
                    raise
                await asyncio.sleep(2 ** attempt)
            except Exception as e:
                if isinstance(e, ProviderError):
                    raise
                raise ProviderError(f"Google Gemini embed error: {str(e)}")

    async def evaluate(self, text: str, criteria: str, model: Optional[str] = None, **kwargs) -> GenerateResponse:
        prompt = f"Evaluate the following response based on this criteria: {criteria}. Return a rating/score from 0-10 and a clear, detailed justification.\n\nResponse to evaluate:\n{text}"
        return await self.generate(prompt, model=model or "gemini-1.5-flash", **kwargs)

    async def classify(self, text: str, categories: List[str], model: Optional[str] = None, **kwargs) -> GenerateResponse:
        prompt = f"Classify the following text into exactly one of these categories: {', '.join(categories)}.\nReturn ONLY the chosen category name and nothing else.\n\nText to classify:\n{text}"
        return await self.generate(prompt, model=model or "gemini-1.5-flash", **kwargs)

    async def summarize(self, text: str, max_length: int = 500, model: Optional[str] = None, **kwargs) -> GenerateResponse:
        prompt = f"Summarize the following text in under {max_length} characters. Provide a highly concise summary.\n\nText to summarize:\n{text}"
        return await self.generate(prompt, model=model or "gemini-1.5-flash", **kwargs)
