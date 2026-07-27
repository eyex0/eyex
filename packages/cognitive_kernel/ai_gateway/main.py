from .providers.base import AIProvider
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
from .router import MODEL_ROUTER
import os

class AIGateway:
    def __init__(self):
        self.providers: dict[str, AIProvider] = {}
        self._register_default_providers()

    def _register_default_providers(self):
        # This is a simplified registration. In a real implementation,
        # we would fetch credentials from a secure store.
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
        
        self.register_provider("ollama", OllamaProvider())
        self.register_provider("vllm", VLLMProvider(base_url=os.environ.get("VLLM_BASE_URL", "")))
        self.register_provider("lmstudio", LMStudioProvider(base_url=os.environ.get("LMSTUDIO_BASE_URL", "")))

    def register_provider(self, name: str, provider: AIProvider):
        self.providers[name] = provider

    def get_provider(self, name: str) -> AIProvider:
        if name not in self.providers:
            raise ValueError(f"Provider {name} not registered")
        return self.providers[name]

    async def generate(self, task: str, context: dict, goal: str, budget: str, privacy: str):
        model_name = MODEL_ROUTER.select_model(task, "low", budget, privacy)
        provider_name, model = model_name.split(":")
        provider = self.get_provider(provider_name)
        return await provider.generate(model=model, prompt=f"{goal}: {context}")

AI_GATEWAY = AIGateway()
