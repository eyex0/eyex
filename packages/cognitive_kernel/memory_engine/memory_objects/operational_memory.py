from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict

@dataclass
class Process:
    id: str
    name: str
    steps: List[str] = field(default_factory=list)
    owner: str = ""

class OperationalMemory:
    def __init__(self):
        self.storage: List[Process] = []

    def add(self, process: Process):
        self.storage.append(process)

    def search(self, query: str) -> List[Process]:
        return [p for p in self.storage if query in p.name]
