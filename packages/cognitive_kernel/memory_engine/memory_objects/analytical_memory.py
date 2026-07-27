from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Any

@dataclass
class Metric:
    id: str
    name: str
    value: Any
    timestamp: str

class AnalyticalMemory:
    def __init__(self):
        self.storage: List[Metric] = []

    def add(self, metric: Metric):
        self.storage.append(metric)

    def search(self, query: str) -> List[Metric]:
        return [m for m in self.storage if query in m.name]
