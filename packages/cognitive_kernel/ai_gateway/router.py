from typing import Dict, Any

class ModelRouter:
    def __init__(self):
        self.model_scores: Dict[str, Dict[str, float]] = {
            "google:gemini-flash": {"quality": 0.7, "speed": 0.9, "cost": 0.9, "reliability": 0.8, "privacy": 0.8},
            "openai:gpt-4": {"quality": 0.9, "speed": 0.7, "cost": 0.6, "reliability": 0.9, "privacy": 0.7},
            "google:gemini-pro": {"quality": 0.8, "speed": 0.8, "cost": 0.8, "reliability": 0.8, "privacy": 0.8},
            "anthropic:claude-3-opus": {"quality": 0.95, "speed": 0.6, "cost": 0.5, "reliability": 0.9, "privacy": 0.8},
            "mistral:mistral-large-latest": {"quality": 0.85, "speed": 0.8, "cost": 0.7, "reliability": 0.8, "privacy": 0.7},
        }

    def select_model(self, task_type: str, complexity: str, budget: str, privacy: str, accuracy: str, latency: str) -> str:
        scores: Dict[str, float] = {}
        for model, model_scores in self.model_scores.items():
            score = 0
            # Task Type
            if task_type == "complex_reasoning":
                score += model_scores["quality"] * 0.4
                score += model_scores["reliability"] * 0.2
            else: # simple_task
                score += model_scores["speed"] * 0.4
                score += model_scores["cost"] * 0.2
            
            # Complexity
            if complexity == "high":
                score += model_scores["quality"] * 0.2
            else: # low
                score += model_scores["speed"] * 0.2

            # Budget
            if budget == "high":
                score += model_scores["cost"] * -0.2 # Higher budget means cost is less of a concern
            else: # low
                score += model_scores["cost"] * 0.2

            # Privacy
            if privacy == "enterprise":
                score += model_scores["privacy"] * 0.3
            
            # Accuracy
            if accuracy == "high":
                score += model_scores["quality"] * 0.3
            
            # Latency
            if latency == "low":
                score += model_scores["speed"] * 0.3
            
            scores[model] = score

        return max(scores, key=scores.get)

MODEL_ROUTER = ModelRouter()
