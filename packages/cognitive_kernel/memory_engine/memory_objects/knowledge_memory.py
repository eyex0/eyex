from __future__ import annotations
from dataclasses import dataclass, field
from typing import List

@dataclass
class Knowledge:
    id: str
    content: str
    source: str
    tags: List[str] = field(default_factory=list)
    confidence: float = 0.0

class KnowledgeMemory:
    def __init__(self):
        self.storage: List[Knowledge] = []

    def add(self, knowledge: Knowledge):
        self.storage.append(knowledge)

    def search(self, query: str) -> List[Knowledge]:
        # Simplified search
        return [k for k in self.storage if query in k.content]
