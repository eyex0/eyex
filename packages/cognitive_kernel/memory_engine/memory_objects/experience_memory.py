from __future__ import annotations
from dataclasses import dataclass, field
from typing import List

@dataclass
class Experience:
    id: str
    event: str
    outcome: str
    lessons_learned: List[str] = field(default_factory=list)

class ExperienceMemory:
    def __init__(self):
        self.storage: List[Experience] = []

    def add(self, experience: Experience):
        self.storage.append(experience)

    def search(self, query: str) -> List[Experience]:
        return [e for e in self.storage if query in e.event]
