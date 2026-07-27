from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, List, Dict

@dataclass
class Decision:
    id: str
    problem_definition: str
    business_context: Dict[str, Any] = field(default_factory=dict)
    alternatives: List[Dict[str, Any]] = field(default_factory=list)
    chosen_option: Dict[str, Any] | None = None
    reasoning: List[str] = field(default_factory=list)
    evidence: List[str] = field(default_factory=list)
    expected_outcome: str = ""
    actual_outcome: str = ""
    success_score: float = 0.0

class DecisionMemory:
    def __init__(self):
        self.storage: List[Decision] = []

    def add(self, decision: Decision):
        self.storage.append(decision)

    def search(self, query: str) -> List[Decision]:
        return [d for d in self.storage if query in d.problem_definition]
