"""
Anthropic AI Provider
"""
from .base import AIProvider
import anthropic

class AnthropicProvider(AIProvider):
    """
    An AI Provider for Anthropic models.
    """
    def __init__(self, api_key: str):
        self.client = anthropic.AsyncAnthropic(api_key=api_key)

    @property
    def name(self) -> str:
        return "anthropic"

    async def generate(self, model: str, prompt: str, **kwargs):
        response = await self.client.messages.create(
            model=model,
            max_tokens=4096,
            messages=[
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
            **kwargs,
        )
        return response.content

    async def stream(self, model: str, prompt: str, **kwargs):
        async with self.client.messages.stream(
            model=model,
            max_tokens=4096,
            messages=[
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
            **kwargs,
        ) as stream:
            async for text in stream.text_stream:
                yield text

    async def embed(self, *args, **kwargs):
        pass
    
    async def health_check(self):
        try:
            await self.client.count_tokens("health check")
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
