"""
πX Universal Data Intelligence Engine — Understands ANY enterprise data.

Any company. Any industry. Any schema. Any column names.
πX understands the business meaning automatically.

Components:
  - UniversalDataProfiler: Profiles any data source (XLSX, CSV, PDF, DOCX, DB, API)
  - SemanticMappingEngineV2: Profile + ontology + glossary + history + LLM fallback
  - RelationshipDiscoveryEngine: Discovers entity relationships from data patterns
  - DataQualityIntelligence: Quality scoring before ingestion
  - SemanticMemory: Learns from corrections, remembers company-specific mappings
  - PIIProtector: Detects and masks PII before AI processing
"""
from .universal_profiler import UniversalDataProfiler
from .semantic_mapping_v2 import SemanticMappingEngineV2
from .relationship_discovery import RelationshipDiscoveryEngine
from .data_quality import DataQualityIntelligence
from .semantic_memory import SemanticMemory
from .pii_protection import PIIProtector

__all__ = [
    "UniversalDataProfiler",
    "SemanticMappingEngineV2",
    "RelationshipDiscoveryEngine",
    "DataQualityIntelligence",
    "SemanticMemory",
    "PIIProtector",
]
