"""
Google Gemini AI Provider
"""
from .base import AIProvider
from google.generativeai import GenerativeModel
import google.generativeai as genai
import os

class GoogleGeminiProvider(AIProvider):
    """
    An AI Provider for Google Gemini models.
    """
    def __init__(self):
        self.client = genai.configure(api_key=os.environ["GOOGLE_API_KEY"])

    @property
    def name(self) -> str:
        return "google"

    async def generate(self, model: str, prompt: str, **kwargs):
        model = GenerativeModel(model)
        response = await model.generate_content_async(prompt, **kwargs)
        return response.text

    async def stream(self, model: str, prompt: str, **kwargs):
        model = GenerativeModel(model)
        response = await model.generate_content_async(prompt, stream=True, **kwargs)
        async for chunk in response:
            yield chunk.text

    async def embed(self, model: str, texts: list[str], **kwargs):
        return await genai.embed_content_async(
            model=model,
            content=texts,
            **kwargs,
        )
    
    async def health_check(self):
        try:
            # A lightweight check, like listing models
            genai.list_models()
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
