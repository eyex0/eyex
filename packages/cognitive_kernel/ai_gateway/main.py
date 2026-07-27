import os
import time
import asyncio
import hashlib
import json
import logging
from typing import Any, AsyncGenerator, Dict, List, Optional

import httpx

from .providers.base import AIProvider, GenerateRequest, GenerateResponse, StreamChunk, EmbedRequest, EmbedResponse
from .providers.google import GoogleGeminiProvider
from .providers.openai import OpenAIProvider
from .providers.anthropic import AnthropicProvider
from .providers.openrouter import OpenRouterProvider
from .providers.deepseek import DeepSeekProvider
from .providers.kimi import KimiProvider
from .providers.mistral import MistralProvider
from .providers.cohere import CohereProvider
from .providers.ollama import OllamaProvider
from .providers.vllm import VLLMProvider
from .providers.lmstudio import LMStudioProvider

from .router import MODEL_ROUTER, ModelRouter
from .cost_tracker import CostTracker
from .cache import SemanticCache, get_redis_client

logger = logging.getLogger(__name__)

class AIGateway:
    def __init__(self):
        self.providers: dict[str, AIProvider] = {}
        self.cost_tracker = CostTracker()
        self.cache = SemanticCache()
        self.redis = get_redis_client()
        self._register_default_providers()

    def _register_default_providers(self):
        # We fetch credentials from environment variables.
        if os.environ.get("GOOGLE_API_KEY"):
            self.register_provider("google", GoogleGeminiProvider())
        if os.environ.get("OPENAI_API_KEY"):
            self.register_provider("openai", OpenAIProvider(api_key=os.environ.get("OPENAI_API_KEY")))
        if os.environ.get("ANTHROPIC_API_KEY"):
            self.register_provider("anthropic", AnthropicProvider(api_key=os.environ.get("ANTHROPIC_API_KEY")))
        if os.environ.get("OPENROUTER_API_KEY"):
            self.register_provider("openrouter", OpenRouterProvider(api_key=os.environ.get("OPENROUTER_API_KEY")))
        if os.environ.get("DEEPSEEK_API_KEY"):
            self.register_provider("deepseek", DeepSeekProvider(api_key=os.environ.get("DEEPSEEK_API_KEY")))
        if os.environ.get("KIMI_API_KEY"):
            self.register_provider("kimi", KimiProvider(api_key=os.environ.get("KIMI_API_KEY")))
        if os.environ.get("MISTRAL_API_KEY"):
            self.register_provider("mistral", MistralProvider(api_key=os.environ.get("MISTRAL_API_KEY")))
        if os.environ.get("COHERE_API_KEY"):
            self.register_provider("cohere", CohereProvider(api_key=os.environ.get("COHERE_API_KEY")))
        
        # Local providers — register only if available (lazy init for tests)
        try:
            self.register_provider("ollama", OllamaProvider())
        except Exception:
            pass
        try:
            self.register_provider("vllm", VLLMProvider(base_url=os.environ.get("VLLM_BASE_URL", "")))
        except Exception:
            pass
        try:
            self.register_provider("lmstudio", LMStudioProvider(base_url=os.environ.get("LMSTUDIO_BASE_URL", "")))
        except Exception:
            pass

    def register_provider(self, name: str, provider: AIProvider):
        self.providers[name] = provider

    def get_provider(self, name: str) -> AIProvider:
        if name not in self.providers:
            raise ValueError(f"Provider {name} not registered")
        return self.providers[name]

    def list_providers(self) -> list:
        return list(self.providers.keys())

    async def generate(self, request, provider=None, model=None, fallback=None) -> GenerateResponse:
        # Extract prompt
        if isinstance(request, str):
            prompt = request
        elif hasattr(request, "prompt"):
            prompt = request.prompt
        else:
            prompt = str(request)

        prompt_hash = hashlib.sha256(prompt.encode("utf-8")).hexdigest()

        # Check semantic cache first
        cached = await self.cache.get(prompt_hash=prompt_hash, prompt=prompt)
        if cached:
            return GenerateResponse(
                content=cached.get("content", ""),
                model=cached.get("model", model or "cached"),
                tokens_used=cached.get("tokens_used", {"input": 0, "output": 0, "total": 0}),
                cost=cached.get("cost", 0.0),
                latency_ms=cached.get("latency_ms", 0.0),
                provider=cached.get("provider", provider or "cached"),
                metadata=cached.get("metadata")
            )

        # Route model/provider if not specified
        if not provider or not model:
            task_type = "generation"
            complexity = "low"
            budget = "high"
            privacy = "standard"
            accuracy = "medium"
            latency = "medium"
            if isinstance(request, dict):
                task_type = request.get("task_type", task_type)
                complexity = request.get("complexity", complexity)
                budget = request.get("budget", budget)
                privacy = request.get("privacy", privacy)
                accuracy = request.get("accuracy", accuracy)
                latency = request.get("latency", latency)
            elif hasattr(request, "extra_params") and request.extra_params:
                task_type = request.extra_params.get("task_type", task_type)
                complexity = request.extra_params.get("complexity", complexity)
                budget = request.extra_params.get("budget", budget)
                privacy = request.extra_params.get("privacy", privacy)
                accuracy = request.extra_params.get("accuracy", accuracy)
                latency = request.extra_params.get("latency", latency)
            
            selected = MODEL_ROUTER.select_model(
                task_type=task_type,
                complexity=complexity,
                budget=budget,
                privacy=privacy,
                accuracy=accuracy,
                latency=latency
            )
            r_provider, r_model = selected.split(":", 1)
            provider = provider or r_provider
            model = model or r_model

        # Build GenerateRequest
        if isinstance(request, str):
            request_obj = GenerateRequest(prompt=request, model=model)
        else:
            request_obj = request
            if hasattr(request_obj, "model"):
                request_obj.model = model

        # Retry logic with exponential backoff (1s, 2s, 4s)
        backoffs = [1, 2, 4]
        last_err = None
        
        for attempt, delay in enumerate(backoffs):
            try:
                start_time = time.perf_counter()
                provider_instance = self.get_provider(provider)
                response = await provider_instance.generate(request_obj, model=model)
                latency_ms = (time.perf_counter() - start_time) * 1000
                response.latency_ms = latency_ms
                response.provider = provider
                
                # Record cost
                await self.cost_tracker.record_usage(
                    org_id=request_obj.extra_params.get("org_id", "default_org") if (hasattr(request_obj, "extra_params") and request_obj.extra_params) else "default_org",
                    provider=provider,
                    model=model,
                    input_tokens=response.tokens_used.get("input", 0),
                    output_tokens=response.tokens_used.get("output", 0),
                    cost=response.cost
                )
                
                # Save to cache
                await self.cache.set(prompt_hash=prompt_hash, response=response, prompt=prompt)
                return response
            except Exception as e:
                last_err = e
                logger.warning(f"Generate attempt {attempt + 1} failed for {provider}:{model}: {e}")
                if attempt < len(backoffs) - 1:
                    await asyncio.sleep(delay)

        # Fallback logic
        fallbacks = []
        if fallback:
            fallbacks = [fallback] if isinstance(fallback, str) else fallback
        else:
            fallbacks = MODEL_ROUTER.get_fallback(provider)

        for fb_prov in fallbacks:
            fb_model = None
            for score_model in MODEL_ROUTER.model_scores.keys():
                if score_model.startswith(f"{fb_prov}:"):
                    fb_model = score_model.split(":", 1)[1]
                    break
            if not fb_model:
                defaults = {"openai": "gpt-4o-mini", "anthropic": "claude-3-5-sonnet", "google": "gemini-flash"}
                fb_model = defaults.get(fb_prov, "gpt-4")

            logger.info(f"Trying fallback provider {fb_prov} with model {fb_model}")
            for attempt, delay in enumerate(backoffs):
                try:
                    start_time = time.perf_counter()
                    provider_instance = self.get_provider(fb_prov)
                    
                    # Update model
                    if isinstance(request_obj, GenerateRequest):
                        request_obj.model = fb_model
                    response = await provider_instance.generate(request_obj, model=fb_model)
                    
                    latency_ms = (time.perf_counter() - start_time) * 1000
                    response.latency_ms = latency_ms
                    response.provider = fb_prov
                    
                    # Record cost
                    await self.cost_tracker.record_usage(
                        org_id=request_obj.extra_params.get("org_id", "default_org") if (hasattr(request_obj, "extra_params") and request_obj.extra_params) else "default_org",
                        provider=fb_prov,
                        model=fb_model,
                        input_tokens=response.tokens_used.get("input", 0),
                        output_tokens=response.tokens_used.get("output", 0),
                        cost=response.cost
                    )
                    
                    # Save to cache
                    await self.cache.set(prompt_hash=prompt_hash, response=response, prompt=prompt)
                    return response
                except Exception as fb_e:
                    last_err = fb_e
                    logger.warning(f"Fallback generate attempt {attempt + 1} failed for {fb_prov}:{fb_model}: {fb_e}")
                    if attempt < len(backoffs) - 1:
                        await asyncio.sleep(delay)

        raise last_err

    async def stream(self, request, provider=None) -> AsyncGenerator[StreamChunk, None]:
        if not provider:
            task_type = "generation"
            complexity = "low"
            budget = "high"
            privacy = "standard"
            accuracy = "medium"
            latency = "medium"
            if isinstance(request, dict):
                task_type = request.get("task_type", task_type)
                complexity = request.get("complexity", complexity)
                budget = request.get("budget", budget)
                privacy = request.get("privacy", privacy)
                accuracy = request.get("accuracy", accuracy)
                latency = request.get("latency", latency)
            elif hasattr(request, "extra_params") and request.extra_params:
                task_type = request.extra_params.get("task_type", task_type)
                complexity = request.extra_params.get("complexity", complexity)
                budget = request.extra_params.get("budget", budget)
                privacy = request.extra_params.get("privacy", privacy)
                accuracy = request.extra_params.get("accuracy", accuracy)
                latency = request.extra_params.get("latency", latency)
            
            selected = MODEL_ROUTER.select_model(
                task_type=task_type,
                complexity=complexity,
                budget=budget,
                privacy=privacy,
                accuracy=accuracy,
                latency=latency
            )
            r_provider, r_model = selected.split(":", 1)
            provider = r_provider
            model = r_model
        else:
            model = None
            for score_model in MODEL_ROUTER.model_scores.keys():
                if score_model.startswith(f"{provider}:"):
                    model = score_model.split(":", 1)[1]
                    break
            if not model:
                model = "gpt-4"

        if isinstance(request, str):
            request_obj = GenerateRequest(prompt=request, model=model)
        else:
            request_obj = request
            if hasattr(request_obj, "model"):
                request_obj.model = model

        provider_instance = self.get_provider(provider)
        async for chunk in provider_instance.stream(request_obj, model=model):
            yield chunk

    async def embed(self, texts, provider='openai', model=None) -> list[list[float]]:
        is_single = isinstance(texts, str)
        if is_single:
            texts = [texts]

        if not model:
            model = "text-embedding-3-small" if provider == "openai" else "models/text-embedding-004"

        results = [None] * len(texts)
        uncached_indices = []
        uncached_texts = []

        for i, t in enumerate(texts):
            t_hash = hashlib.sha256(t.encode("utf-8")).hexdigest()
            cache_key = f"embedding_cache:{provider}:{model}:{t_hash}"
            cached_val = await self.redis.get(cache_key)
            if cached_val:
                results[i] = json.loads(cached_val)
            else:
                uncached_indices.append(i)
                uncached_texts.append(t)

        if uncached_texts:
            provider_instance = self.get_provider(provider)
            req = EmbedRequest(texts=uncached_texts, model=model)
            embed_response = await provider_instance.embed(req, model=model)
            
            for text_idx, emb in zip(uncached_indices, embed_response.embeddings):
                results[text_idx] = emb
                t = texts[text_idx]
                t_hash = hashlib.sha256(t.encode("utf-8")).hexdigest()
                cache_key = f"embedding_cache:{provider}:{model}:{t_hash}"
                await self.redis.setex(cache_key, 86400, json.dumps(emb))

        return results

    async def classify(self, text, labels, provider=None) -> dict:
        if not provider:
            provider = "openai"
        model = None
        for score_model in MODEL_ROUTER.model_scores.keys():
            if score_model.startswith(f"{provider}:"):
                model = score_model.split(":", 1)[1]
                break
        if not model:
            model = "gpt-4o-mini" if provider == "openai" else "gpt-4"

        provider_instance = self.get_provider(provider)
        response = await provider_instance.classify(text, categories=labels, model=model)
        try:
            return json.loads(response.content)
        except Exception:
            return {"category": response.content.strip()}

    async def summarize(self, text, max_length=200, provider=None) -> str:
        if not provider:
            provider = "openai"
        model = None
        for score_model in MODEL_ROUTER.model_scores.keys():
            if score_model.startswith(f"{provider}:"):
                model = score_model.split(":", 1)[1]
                break
        if not model:
            model = "gpt-4o-mini" if provider == "openai" else "gpt-4"

        provider_instance = self.get_provider(provider)
        response = await provider_instance.summarize(text, max_length=max_length, model=model)
        return response.content

AI_GATEWAY = AIGateway()
