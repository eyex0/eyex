"""
Ollama AI Provider
"""
from .base import AIProvider
import ollama

class OllamaProvider(AIProvider):
    """
    An AI Provider for Ollama models.
    """
    def __init__(self):
        self.client = ollama.AsyncClient()

    @property
    def name(self) -> str:
        return "ollama"

    async def generate(self, model: str, prompt: str, **kwargs):
        response = await self.client.chat(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            **kwargs,
        )
        return response['message']['content']

    async def stream(self, model: str, prompt: str, **kwargs):
        async for part in await self.client.chat(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            stream=True,
            **kwargs,
        ):
            yield part['message']['content']

    async def embed(self, model: str, texts: list[str], **kwargs):
        results = []
        for text in texts:
            response = await self.client.embeddings(
                model=model,
                prompt=text,
                **kwargs,
            )
            results.append(response["embedding"])
        return results
    
    async def health_check(self):
        try:
            await self.client.list()
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
