from __future__ import annotations
from dataclasses import dataclass, field
from typing import List

@dataclass
class Company:
    id: str
    name: str
    industry: str
    region: str
    strategy: str
    goals: List[str] = field(default_factory=list)

@dataclass
class Department:
    id: str
    name: str
    function: str
    owner: str
    budget: float

@dataclass
class Employee:
    id: str
    role: str
    skills: List[str] = field(default_factory=list)
    department: str
    responsibilities: List[str] = field(default_factory=list)
