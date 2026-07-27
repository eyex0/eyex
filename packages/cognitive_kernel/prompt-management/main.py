from typing import Dict, Any

class PromptRegistry:
    def __init__(self):
        self._prompts: Dict[str, Dict[str, Any]] = {}

    def register(self, name: str, version: str, template: str, owner: str):
        if name not in self._prompts:
            self._prompts[name] = {}
        self._prompts[name][version] = {
            "template": template,
            "owner": owner,
            "performance": [],
            "history": [],
        }

    def get_prompt(self, name: str, version: str = "latest") -> str | None:
        if name not in self._prompts:
            return None
        if version == "latest":
            latest_version = max(self._prompts[name].keys())
            return self._prompts[name][latest_version]["template"]
        return self._prompts.get(name, {}).get(version, {}).get("template")

    def track_performance(self, name: str, version: str, performance_metrics: Dict[str, Any]):
        if name in self._prompts and version in self._prompts[name]:
            self._prompts[name][version]["performance"].append(performance_metrics)

PROMPT_REGISTRY = PromptRegistry()
