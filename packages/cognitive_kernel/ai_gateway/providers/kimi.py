"""
Kimi AI Provider
"""
from .base import AIProvider
import openai

class KimiProvider(AIProvider):
    """
    An AI Provider for Kimi models.
    """
    def __init__(self, api_key: str):
        self.client = openai.AsyncOpenAI(api_key=api_key, base_url="https://api.kimi.ai/v1")

    @property
    def name(self) -> str:
        return "kimi"

    async def generate(self, model: str, prompt: str, **kwargs):
        response = await self.client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            **kwargs,
        )
        return response.choices[0].message.content

    async def stream(self, model: str, prompt: str, **kwargs):
        stream = await self.client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            stream=True,
            **kwargs,
        )
        async for chunk in stream:
            yield chunk.choices[0].delta.content or ""

    async def embed(self, *args, **kwargs):
        pass

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
