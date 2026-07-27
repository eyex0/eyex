"""πX Knowledge Graph Entities."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, UTC
from typing import Any


@dataclass
class Entity:
    id: str
    name: str
    entity_type: str
    properties: dict[str, Any] = field(default_factory=dict)
    org_id: str = "default"
    created_at: str | None = None
    updated_at: str | None = None


@dataclass
class Company(Entity):
    entity_type: str = "Company"
    industry: str = ""
    region: str = ""
    strategy: str = ""
    goals: list[str] = field(default_factory=list)


@dataclass
class Customer(Entity):
    entity_type: str = "Customer"
    company: str = ""
    contact: str = ""
    value: float = 0.0
    status: str = "active"


@dataclass
class Product(Entity):
    entity_type: str = "Product"
    price: float = 0.0
    category: str = ""
    status: str = "active"


@dataclass
class Project(Entity):
    entity_type: str = "Project"
    status: str = "planning"
    start_date: str = ""
    end_date: str = ""
    budget: float = 0.0


@dataclass
class Employee(Entity):
    entity_type: str = "Employee"
    role: str = ""
    skills: list[str] = field(default_factory=list)
    department: str = ""
    responsibilities: list[str] = field(default_factory=list)


@dataclass
class Document(Entity):
    entity_type: str = "Document"
    doc_type: str = ""
    source: str = ""


@dataclass
class Decision(Entity):
    entity_type: str = "Decision"
    status: str = "pending"
    confidence: float = 0.0


@dataclass
class Metric(Entity):
    entity_type: str = "Metric"
    value: float = 0.0
    unit: str = ""
    period: str = ""


@dataclass
class Vendor(Entity):
    entity_type: str = "Vendor"
    service_type: str = ""
    contract_value: float = 0.0


@dataclass
class Market(Entity):
    entity_type: str = "Market"
    region: str = ""
    size: float = 0.0


@dataclass
class Technology(Entity):
    entity_type: str = "Technology"
    category: str = ""
    maturity: str = ""


ENTITY_TYPES = {
    "Company": Company, "Customer": Customer, "Product": Product,
    "Project": Project, "Employee": Employee, "Document": Document,
    "Decision": Decision, "Metric": Metric, "Vendor": Vendor,
    "Market": Market, "Technology": Technology,
}


class EntityFactory:
    @staticmethod
    def create_entity(entity_type: str, **kwargs) -> Entity:
        cls = ENTITY_TYPES.get(entity_type, Entity)
        return cls(**kwargs)
