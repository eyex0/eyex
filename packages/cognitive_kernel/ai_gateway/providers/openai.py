"""
OpenAI AI Provider
"""
from .base import AIProvider
import openai
import asyncio
import logging

logger = logging.getLogger(__name__)

class OpenAIProvider(AIProvider):
    """
    An AI Provider for OpenAI models.
    """
    def __init__(self, api_key: str, max_retries: int = 3, timeout: int = 60):
        self.client = openai.AsyncOpenAI(api_key=api_key)
        self.max_retries = max_retries
        self.timeout = timeout

    @property
    def name(self) -> str:
        return "openai"

    async def generate(self, model: str, prompt: str, **kwargs):
        for attempt in range(self.max_retries):
            try:
                response = await asyncio.wait_for(
                    self.client.chat.completions.create(
                        model=model,
                        messages=[{"role": "user", "content": prompt}],
                        **kwargs,
                    ),
                    timeout=self.timeout
                )
                return response.choices[0].message.content
            except (openai.APIError, asyncio.TimeoutError) as e:
                logger.warning(f"OpenAI generate failed on attempt {attempt + 1}: {e}")
                if attempt + 1 == self.max_retries:
                    raise
        return None

    async def stream(self, model: str, prompt: str, **kwargs):
        for attempt in range(self.max_retries):
            try:
                stream = await asyncio.wait_for(
                    self.client.chat.completions.create(
                        model=model,
                        messages=[{"role": "user", "content": prompt}],
                        stream=True,
                        **kwargs,
                    ),
                    timeout=self.timeout
                )
                async for chunk in stream:
                    yield chunk.choices[0].delta.content or ""
                return
            except (openai.APIError, asyncio.TimeoutError) as e:
                logger.warning(f"OpenAI stream failed on attempt {attempt + 1}: {e}")
                if attempt + 1 == self.max_retries:
                    raise

    async def embed(self, model: str, texts: list[str], **kwargs):
        for attempt in range(self.max_retries):
            try:
                response = await asyncio.wait_for(
                    self.client.embeddings.create(
                        model=model,
                        input=texts,
                        **kwargs,
                    ),
                    timeout=self.timeout
                )
                return response.data
            except (openai.APIError, asyncio.TimeoutError) as e:
                logger.warning(f"OpenAI embed failed on attempt {attempt + 1}: {e}")
                if attempt + 1 == self.max_retries:
                    raise
        return None

    async def health_check(self):
        try:
            await self.client.models.list()
            return True
        except Exception:
            return False
            
    async def rerank(self, *args, **kwargs):
        pass
    async def evaluate(self, *args, **kwargs):
        pass
    async def classify(self, *args, **kwargs):
        pass
    async def summarize(self, *args, **kwargs):
        pass
    async def extract(self, *args, **kwargs):
        pass
    async def translate(self, *args, **kwargs):
        pass
    async def moderate(self, *args, **kwargs):
        pass
