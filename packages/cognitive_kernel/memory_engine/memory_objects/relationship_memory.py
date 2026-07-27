from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict

@dataclass
class Relationship:
    id: str
    source_entity: str
    target_entity: str
    relationship_type: str

class RelationshipMemory:
    def __init__(self):
        self.storage: List[Relationship] = []

    def add(self, relationship: Relationship):
        self.storage.append(relationship)

    def search(self, query: str) -> List[Relationship]:
        return [r for r in self.storage if query in r.source_entity or query in r.target_entity]
