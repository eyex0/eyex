from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, AsyncGenerator, Dict, List, Optional
from pydantic import BaseModel, Field

class ProviderCapability(str, Enum):
    GENERATION = "GENERATION"
    STREAMING = "STREAMING"
    EMBEDDING = "EMBEDDING"
    CLASSIFICATION = "CLASSIFICATION"
    SUMMARIZATION = "SUMMARIZATION"

# Custom exceptions
class ProviderError(Exception):
    """Base exception for provider errors."""
    def __init__(self, message: str, status_code: Optional[int] = None, response_body: Optional[str] = None):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.response_body = response_body

class ProviderUnavailableError(ProviderError):
    """Raised when a provider is down, unreachable, or times out."""
    pass

class RateLimitError(ProviderError):
    """Raised when a provider returns a rate limit error (HTTP 429)."""
    pass

# Request and Response models using Pydantic
class GenerateRequest(BaseModel):
    prompt: str
    model: str
    system_prompt: Optional[str] = None
    temperature: Optional[float] = 0.7
    max_tokens: Optional[int] = None
    stop_sequences: Optional[List[str]] = None
    extra_params: Optional[Dict[str, Any]] = None

class GenerateResponse(BaseModel):
    content: str
    model: str
    tokens_used: Dict[str, int] = Field(default_factory=lambda: {"input": 0, "output": 0, "total": 0})
    cost: float = 0.0
    latency_ms: float = 0.0
    provider: str
    metadata: Optional[Dict[str, Any]] = None

class StreamChunk(BaseModel):
    content: str
    model: str
    tokens_used: Optional[Dict[str, int]] = None
    cost: Optional[float] = None
    latency_ms: Optional[float] = None
    provider: str
    is_final: bool = False

class EmbedRequest(BaseModel):
    texts: List[str]
    model: str

class EmbedResponse(BaseModel):
    content: str = ""  # Satisfy requirement: "Each response includes: content, model, tokens_used, cost, latency_ms, provider"
    embeddings: List[List[float]]
    model: str
    tokens_used: Dict[str, int] = Field(default_factory=lambda: {"input": 0, "output": 0, "total": 0})
    cost: float = 0.0
    latency_ms: float = 0.0
    provider: str

class AIProvider(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        """Returns the identifier name of the provider."""
        pass

    @property
    @abstractmethod
    def capabilities(self) -> List[ProviderCapability]:
        """Returns capabilities of this provider."""
        pass

    @abstractmethod
    async def generate(self, request: GenerateRequest | str, model: Optional[str] = None, **kwargs) -> GenerateResponse:
        """Generates a text completion."""
        pass

    @abstractmethod
    async def stream(self, request: GenerateRequest | str, model: Optional[str] = None, **kwargs) -> AsyncGenerator[StreamChunk, None]:
        """Streams a text completion."""
        pass

    @abstractmethod
    async def embed(self, request: EmbedRequest | List[str], model: Optional[str] = None, **kwargs) -> EmbedResponse:
        """Generates vector embeddings for input texts."""
        pass

    @abstractmethod
    async def evaluate(self, text: str, criteria: str, model: Optional[str] = None, **kwargs) -> GenerateResponse:
        """Evaluates text response based on criteria."""
        pass

    @abstractmethod
    async def classify(self, text: str, categories: List[str], model: Optional[str] = None, **kwargs) -> GenerateResponse:
        """Classifies text into one of the categories."""
        pass

    @abstractmethod
    async def summarize(self, text: str, max_length: int = 500, model: Optional[str] = None, **kwargs) -> GenerateResponse:
        """Summarizes text to a maximum length."""
        pass
