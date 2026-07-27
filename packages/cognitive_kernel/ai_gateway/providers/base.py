"""πX AI Provider Base — Abstract interface for all AI providers."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, AsyncGenerator


class ProviderCapability(Enum):
    GENERATION = "generation"
    STREAMING = "streaming"
    EMBEDDING = "embedding"
    CLASSIFICATION = "classification"
    SUMMARIZATION = "summarization"


@dataclass
class GenerateRequest:
    prompt: str
    system_prompt: str | None = None
    temperature: float = 0.7
    max_tokens: int | None = None
    top_p: float = 1.0
    stop: list[str] | None = None

    def to_dict(self) -> dict:
        d = {"prompt": self.prompt, "temperature": self.temperature, "top_p": self.top_p}
        if self.system_prompt:
            d["system_prompt"] = self.system_prompt
        if self.max_tokens:
            d["max_tokens"] = self.max_tokens
        if self.stop:
            d["stop"] = self.stop
        return d


@dataclass
class GenerateResponse:
    content: str
    model: str = ""
    tokens_used: int = 0
    cost: float = 0.0
    latency_ms: float = 0.0
    provider: str = ""
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "content": self.content,
            "model": self.model,
            "tokens_used": self.tokens_used,
            "cost": self.cost,
            "latency_ms": self.latency_ms,
            "provider": self.provider,
            "metadata": self.metadata,
        }


@dataclass
class StreamChunk:
    content: str
    done: bool = False
    metadata: dict = field(default_factory=dict)


@dataclass
class EmbedRequest:
    texts: list[str]
    model: str = "text-embedding-3-small"
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class EmbedResponse:
    embeddings: list[list[float]]
    model: str
    token_count: int = 0
    cached: bool = False


class AIProvider(ABC):
    """Abstract base class for all AI providers."""

    @property
    @abstractmethod
    def name(self) -> str:
        ...

    @abstractmethod
    async def generate(self, model: str | None = None, **kwargs) -> GenerateResponse:
        ...

    @abstractmethod
    async def stream(self, model: str | None = None, **kwargs) -> AsyncGenerator[StreamChunk, None]:
        ...

    @abstractmethod
    async def embed(self, model: str | None = None, **kwargs) -> list[float]:
        ...

    async def classify(self, model: str | None = None, **kwargs) -> dict:
        raise NotImplementedError(f"{self.name} does not support classification")

    async def summarize(self, model: str | None = None, **kwargs) -> str:
        raise NotImplementedError(f"{self.name} does not support summarization")

    def capabilities(self) -> set[ProviderCapability]:
        return {ProviderCapability.GENERATION, ProviderCapability.STREAMING}


class ProviderError(Exception):
    """Base error for AI provider failures."""
    def __init__(self, message: str, status_code: int | None = None):
        super().__init__(message)
        self.status_code = status_code


class ProviderUnavailableError(ProviderError):
    """Provider is unavailable (network, auth, or service issue)."""
    def __init__(self, message: str, status_code: int | None = None):
        super().__init__(message, status_code=status_code)


class RateLimitError(ProviderError):
    """Provider rate limit exceeded."""
    def __init__(self, message: str, status_code: int = 429):
        super().__init__(message, status_code=status_code)
