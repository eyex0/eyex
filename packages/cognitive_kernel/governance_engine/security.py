from typing import Dict, Any

class AISecurityLayer:
    def detect_prompt_injection(self, prompt: str) -> bool:
        # Simplified implementation
        return "ignore previous instructions" in prompt.lower()

    def filter_sensitive_data(self, data: str) -> str:
        # Simplified implementation
        return "[REDACTED]"

AI_SECURITY_LAYER = AISecurityLayer()
