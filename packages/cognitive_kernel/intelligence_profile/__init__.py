"""
πX Intelligence Profile System — Adaptive enterprise intelligence identity.

Every organization has a dynamic intelligence profile that defines:
  - Who they are (industry, business model, structure)
  - How they operate (departments, workflows, processes)
  - How they speak (terminology, glossary, synonyms)
  - What matters (KPIs, metrics, objectives)
  - What data they have (connected sources, schemas, mappings)
  - What AI they need (agents, policies, preferred models)

The profile is NOT predefined. It is discovered from data, suggested by AI,
confirmed by users, and continuously refined through learning.
"""
from .profile_core import IntelligenceProfile, ProfileManager, ProfileVersionManager
from .profile_ontology import OntologyManager
from .profile_kpis import KPIManager
from .profile_glossary import GlossaryManager
from .profile_data_sources import DataSourceManager
from .profile_events import EventManager
from .semantic_history import SemanticHistoryManager
from .confidence_scorer import ProfileConfidenceScorer
from .industry_templates import IndustryTemplateRegistry
from .profile_intelligence_agent import ProfileIntelligenceAgent
from .tenant_security import ProfileTenantGuard

__all__ = [
    "IntelligenceProfile",
    "ProfileManager",
    "ProfileVersionManager",
    "OntologyManager",
    "KPIManager",
    "GlossaryManager",
    "DataSourceManager",
    "EventManager",
    "SemanticHistoryManager",
    "ProfileConfidenceScorer",
    "IndustryTemplateRegistry",
    "ProfileIntelligenceAgent",
    "ProfileTenantGuard",
]
