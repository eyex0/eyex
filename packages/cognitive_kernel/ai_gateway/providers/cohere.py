"""
Cohere AI Provider
"""
from .base import AIProvider
import cohere

class CohereProvider(AIProvider):
    """
    An AI Provider for Cohere models.
    """
    def __init__(self, api_key: str):
        self.client = cohere.AsyncClient(api_key=api_key)

    @property
    def name(self) -> str:
        return "cohere"

    async def generate(self, model: str, prompt: str, **kwargs):
        response = await self.client.chat(
            model=model,
            message=prompt,
            **kwargs,
        )
        return response.text

    async def stream(self, model: str, prompt: str, **kwargs):
        stream = await self.client.chat(
            model=model,
            message=prompt,
            stream=True,
            **kwargs,
        )
        async for event in stream:
            if event.event_type == "text-generation":
                yield event.text

    async def embed(self, model: str, texts: list[str], **kwargs):
        response = await self.client.embed(
            model=model,
            texts=texts,
            **kwargs,
        )
        return response.embeddings
    
    async def health_check(self):
        try:
            await self.client.check_api_key()
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
