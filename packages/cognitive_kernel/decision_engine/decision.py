from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, List, Dict

@dataclass
class Decision:
    id: str
    organization_id: str
    title: str
    category: str
    created_by: str
    timestamp: str
    problem_definition: str
    business_context: Dict[str, Any] = field(default_factory=dict)
    available_information: List[str] = field(default_factory=list)
    constraints: List[str] = field(default_factory=list)
    alternatives: List[Dict[str, Any]] = field(default_factory=list)
    chosen_option: Dict[str, Any] | None = None
    reasoning: List[str] = field(default_factory=list)
    evidence: List[str] = field(default_factory=list)
    risk_analysis: Dict[str, Any] = field(default_factory=dict)
    expected_outcome: str = ""
    actual_outcome: str = ""
    success_score: float = 0.0
    lessons_learned: List[str] = field(default_factory=list)
    confidence_score: float = 0.0
