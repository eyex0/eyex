from .ai_gateway import AI_GATEWAY
from .ai_gateway.router import MODEL_ROUTER

class AIControlPlane:
    def __init__(self):
        self.fallback_providers = ["google", "openai"] # This should be configurable

    async def generate(self, task: str, context: dict, goal: str, budget: str, privacy: str):
        complexity = "low" # This would be determined by a more sophisticated method.
        model_name = MODEL_ROUTER.select_model(task, complexity, budget, privacy)
        
        provider_name, model = model_name.split(":")
        
        provider_preference = [provider_name] + [p for p in self.fallback_providers if p != provider_name]

        for provider_name in provider_preference:
            try:
                provider = AI_GATEWAY.get_provider(provider_name)
                # This is a simplified call to the provider.
                return await provider.generate(model=model, prompt=f"{goal}: {context}")
            except Exception as e:
                print(f"Provider {provider_name} failed with error: {e}. Trying next provider.")
        
        raise Exception("All AI providers failed.")

    async def collaborate(self, models: list[str], prompt: str):
        current_input = prompt
        for model_name in models:
            provider_name, model = model_name.split(":")
            provider = AI_GATEWAY.get_provider(provider_name)
            current_input = await provider.generate(model=model, prompt=current_input)
        return current_input

PX_AI = AIControlPlane()
