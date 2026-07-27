"""
πX Intelligence Profile API — Full CRUD for profiles, ontology, KPIs, glossary, data sources, events.

All endpoints require authentication and enforce tenant isolation (organization_id).
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from app.dependencies import get_current_user
from app.models.user import User
from app.database import async_session_factory

logger = logging.getLogger("pix.api.intelligence_profile")

ip_router = APIRouter(prefix="/intelligence-profile", tags=["Intelligence Profile"])


def _get_org_id(user: User) -> str:
    """Extract organization_id from authenticated user."""
    if hasattr(user, "organization_id") and user.organization_id:
        return str(user.organization_id)
    if hasattr(user, "id"):
        return str(user.id)
    return "default"


# ── Profile ───────────────────────────────────────────────────────────

class ProfileCreate(BaseModel):
    industry: str | None = None
    business_model: str | None = None
    company_size: str | None = None
    region: str | None = None
    locations: list[dict] = []
    profile_config: dict = {}


class ProfileUpdate(BaseModel):
    industry: str | None = None
    business_model: str | None = None
    company_size: str | None = None
    region: str | None = None
    locations: list[dict] | None = None
    profile_config: dict | None = None
    status: str | None = None


@ip_router.get("/")
async def get_profile(user: User = Depends(get_current_user)):
    """Get the active intelligence profile for the current organization."""
    from packages.cognitive_kernel.intelligence_profile.profile_core import ProfileManager
    mgr = ProfileManager(async_session_factory)
    org_id = _get_org_id(user)
    profile = await mgr.get_by_org(org_id)
    if not profile:
        return {"profile": None, "message": "No profile found. Create one first."}
    return {"profile": profile.to_dict()}


@ip_router.post("/")
async def create_profile(body: ProfileCreate, user: User = Depends(get_current_user)):
    from packages.cognitive_kernel.intelligence_profile.profile_core import ProfileManager
    mgr = ProfileManager(async_session_factory)
    org_id = _get_org_id(user)
    profile = await mgr.create(
        organization_id=org_id,
        industry=body.industry,
        business_model=body.business_model,
        company_size=body.company_size,
        region=body.region,
        locations=body.locations,
        profile_config=body.profile_config,
    )
    return {"profile": profile.to_dict()}


@ip_router.patch("/{profile_id}")
async def update_profile(profile_id: str, body: ProfileUpdate, user: User = Depends(get_current_user)):
    from packages.cognitive_kernel.intelligence_profile.profile_core import ProfileManager
    mgr = ProfileManager(async_session_factory)
    org_id = _get_org_id(user)
    updates = {k: v for k, v in body.model_dump().items() if v is not None}
    profile = await mgr.update(org_id, profile_id, updates, changed_by=str(user.id))
    if not profile:
        return {"error": "Profile not found"}, 404
    return {"profile": profile.to_dict()}


@ip_router.post("/{profile_id}/activate")
async def activate_profile(profile_id: str, user: User = Depends(get_current_user)):
    from packages.cognitive_kernel.intelligence_profile.profile_core import ProfileManager
    mgr = ProfileManager(async_session_factory)
    org_id = _get_org_id(user)
    profile = await mgr.activate(org_id, profile_id)
    if not profile:
        return {"error": "Profile not found"}, 404
    return {"profile": profile.to_dict()}


# ── Versioning ────────────────────────────────────────────────────────

@ip_router.get("/{profile_id}/versions")
async def list_versions(profile_id: str, user: User = Depends(get_current_user)):
    from packages.cognitive_kernel.intelligence_profile.profile_core import ProfileManager
    mgr = ProfileManager(async_session_factory)
    org_id = _get_org_id(user)
    versions = await mgr.list_versions(org_id, profile_id)
    return {"versions": versions}


@ip_router.get("/{profile_id}/versions/{version_number}")
async def get_version(profile_id: str, version_number: int, user: User = Depends(get_current_user)):
    from packages.cognitive_kernel.intelligence_profile.profile_core import ProfileVersionManager
    vm = ProfileVersionManager(async_session_factory)
    org_id = _get_org_id(user)
    version = await vm.get_version(org_id, profile_id, version_number)
    if not version:
        return {"error": "Version not found"}, 404
    return version


@ip_router.post("/{profile_id}/rollback/{version_number}")
async def rollback_profile(profile_id: str, version_number: int, user: User = Depends(get_current_user)):
    from packages.cognitive_kernel.intelligence_profile.profile_core import ProfileVersionManager
    vm = ProfileVersionManager(async_session_factory)
    org_id = _get_org_id(user)
    profile = await vm.rollback(org_id, profile_id, version_number, changed_by=str(user.id))
    if not profile:
        return {"error": "Rollback failed"}, 400
    return {"profile": profile.to_dict()}


# ── Ontology ──────────────────────────────────────────────────────────

class EntityCreate(BaseModel):
    entity_type: str
    entity_label: str | None = None
    properties_schema: dict = {}
    relationships: list = []
    aliases: list = []
    confidence: float = 0.5
    source: str = "inferred"


@ip_router.get("/{profile_id}/ontology")
async def get_ontology(profile_id: str, entity_type: str | None = None, user: User = Depends(get_current_user)):
    from packages.cognitive_kernel.intelligence_profile.profile_ontology import OntologyManager
    mgr = OntologyManager(async_session_factory)
    org_id = _get_org_id(user)
    entities = await mgr.get_entities(org_id, profile_id, entity_type)
    return {"entities": entities, "total": len(entities)}


@ip_router.post("/{profile_id}/ontology")
async def add_entity(profile_id: str, body: EntityCreate, user: User = Depends(get_current_user)):
    from packages.cognitive_kernel.intelligence_profile.profile_ontology import OntologyManager
    from packages.cognitive_kernel.intelligence_profile.profile_events import EventManager, ProfileEventType
    mgr = OntologyManager(async_session_factory)
    events = EventManager(async_session_factory)
    org_id = _get_org_id(user)
    result = await mgr.add_entity(
        org_id, profile_id, body.entity_type, body.entity_label,
        body.properties_schema, body.relationships, body.aliases,
        body.confidence, body.source,
    )
    await events.emit(org_id, ProfileEventType.ONTOLOGY_ADDED, profile_id,
                      event_data=result, entity_type="ontology", entity_id=result["id"],
                      triggered_by="user", user_id=str(user.id))
    return result


@ip_router.delete("/{profile_id}/ontology/{entity_id}")
async def delete_entity(profile_id: str, entity_id: str, user: User = Depends(get_current_user)):
    from packages.cognitive_kernel.intelligence_profile.profile_ontology import OntologyManager
    mgr = OntologyManager(async_session_factory)
    org_id = _get_org_id(user)
    deleted = await mgr.delete_entity(org_id, entity_id)
    return {"deleted": deleted}


# ── KPIs ──────────────────────────────────────────────────────────────

class KPICreate(BaseModel):
    name: str
    label: str | None = None
    category: str | None = None
    definition: str | None = None
    formula: dict = {}
    target: dict = {}
    unit: str | None = None
    aliases: list = []
    confidence: float = 0.5
    source: str = "inferred"


@ip_router.get("/{profile_id}/kpis")
async def get_kpis(profile_id: str, category: str | None = None, user: User = Depends(get_current_user)):
    from packages.cognitive_kernel.intelligence_profile.profile_kpis import KPIManager
    mgr = KPIManager(async_session_factory)
    org_id = _get_org_id(user)
    kpis = await mgr.get_kpis(org_id, profile_id, category)
    return {"kpis": kpis, "total": len(kpis)}


@ip_router.post("/{profile_id}/kpis")
async def add_kpi(profile_id: str, body: KPICreate, user: User = Depends(get_current_user)):
    from packages.cognitive_kernel.intelligence_profile.profile_kpis import KPIManager
    mgr = KPIManager(async_session_factory)
    org_id = _get_org_id(user)
    return await mgr.add_kpi(
        org_id, profile_id, body.name, body.label, body.category, body.definition,
        body.formula, body.target, body.unit, body.aliases, body.confidence, body.source,
    )


@ip_router.delete("/{profile_id}/kpis/{kpi_id}")
async def delete_kpi(profile_id: str, kpi_id: str, user: User = Depends(get_current_user)):
    from packages.cognitive_kernel.intelligence_profile.profile_kpis import KPIManager
    mgr = KPIManager(async_session_factory)
    org_id = _get_org_id(user)
    return {"deleted": await mgr.delete_kpi(org_id, kpi_id)}


# ── Glossary ──────────────────────────────────────────────────────────

class TermCreate(BaseModel):
    term: str
    definition: str | None = None
    aliases: list = []
    synonyms: list = []
    category: str | None = None
    maps_to_entity: str | None = None
    confidence: float = 0.5
    source: str = "inferred"


@ip_router.get("/{profile_id}/glossary")
async def get_glossary(profile_id: str, user: User = Depends(get_current_user)):
    from packages.cognitive_kernel.intelligence_profile.profile_glossary import GlossaryManager
    mgr = GlossaryManager(async_session_factory)
    org_id = _get_org_id(user)
    terms = await mgr.get_terms(org_id, profile_id)
    return {"terms": terms, "total": len(terms)}


@ip_router.post("/{profile_id}/glossary")
async def add_term(profile_id: str, body: TermCreate, user: User = Depends(get_current_user)):
    from packages.cognitive_kernel.intelligence_profile.profile_glossary import GlossaryManager
    mgr = GlossaryManager(async_session_factory)
    org_id = _get_org_id(user)
    return await mgr.add_term(
        org_id, profile_id, body.term, body.definition, body.aliases,
        body.synonyms, body.category, body.maps_to_entity, body.confidence, body.source,
    )


@ip_router.post("/{profile_id}/glossary/resolve")
async def resolve_term(profile_id: str, body: dict, user: User = Depends(get_current_user)):
    from packages.cognitive_kernel.intelligence_profile.profile_glossary import GlossaryManager
    mgr = GlossaryManager(async_session_factory)
    org_id = _get_org_id(user)
    result = await mgr.resolve_term(org_id, profile_id, body.get("term", ""))
    return {"resolved": result}


# ── Data Sources ──────────────────────────────────────────────────────

@ip_router.get("/{profile_id}/data-sources")
async def get_data_sources(profile_id: str, user: User = Depends(get_current_user)):
    from packages.cognitive_kernel.intelligence_profile.profile_data_sources import DataSourceManager
    mgr = DataSourceManager(async_session_factory)
    org_id = _get_org_id(user)
    sources = await mgr.get_sources(org_id, profile_id)
    return {"data_sources": sources, "total": len(sources)}


# ── Events ────────────────────────────────────────────────────────────

@ip_router.get("/{profile_id}/events")
async def get_events(
    profile_id: str,
    event_type: str | None = None,
    limit: int = Query(50, ge=1, le=200),
    user: User = Depends(get_current_user),
):
    from packages.cognitive_kernel.intelligence_profile.profile_events import EventManager
    mgr = EventManager(async_session_factory)
    org_id = _get_org_id(user)
    events = await mgr.get_events(org_id, profile_id, event_type, limit)
    return {"events": events, "total": len(events)}


# ── Semantic History ──────────────────────────────────────────────────

@ip_router.get("/{profile_id}/semantic-history")
async def get_semantic_history(
    profile_id: str,
    column_name: str | None = None,
    limit: int = Query(50, ge=1, le=200),
    user: User = Depends(get_current_user),
):
    from packages.cognitive_kernel.intelligence_profile.semantic_history import SemanticHistoryManager
    mgr = SemanticHistoryManager(async_session_factory)
    org_id = _get_org_id(user)
    history = await mgr.get_history(org_id, column_name, profile_id, limit)
    return {"history": history, "total": len(history)}


@ip_router.get("/{profile_id}/semantic-history/stats")
async def get_semantic_stats(profile_id: str, user: User = Depends(get_current_user)):
    from packages.cognitive_kernel.intelligence_profile.semantic_history import SemanticHistoryManager
    mgr = SemanticHistoryManager(async_session_factory)
    org_id = _get_org_id(user)
    return await mgr.get_learning_stats(org_id)


# ── Industry Templates ────────────────────────────────────────────────

@ip_router.get("/templates/list")
async def list_templates(user: User = Depends(get_current_user)):
    from packages.cognitive_kernel.intelligence_profile.industry_templates import IndustryTemplateRegistry
    registry = IndustryTemplateRegistry()
    return {"templates": registry.list_all_templates()}


@ip_router.get("/templates/{industry}")
async def get_template(industry: str, user: User = Depends(get_current_user)):
    from packages.cognitive_kernel.intelligence_profile.industry_templates import IndustryTemplateRegistry
    registry = IndustryTemplateRegistry()
    template = registry.get_template_dict(industry)
    if not template:
        return {"error": "Template not found"}, 404
    return template


# ── Analyze & Create Flow ─────────────────────────────────────────────

class AnalyzeRequest(BaseModel):
    file_name: str
    file_type: str
    columns: list[dict]


class CreateFromSuggestionsRequest(BaseModel):
    suggestions: dict
    user_confirmed: bool = False


@ip_router.post("/analyze")
async def analyze_dataset(body: AnalyzeRequest, user: User = Depends(get_current_user)):
    """Analyze uploaded data and get profile suggestions."""
    from packages.cognitive_kernel.intelligence_profile.profile_intelligence_agent import ProfileIntelligenceAgent
    agent = ProfileIntelligenceAgent(async_session_factory)
    org_id = _get_org_id(user)
    return await agent.analyze_dataset(org_id, body.file_name, body.file_type, body.columns)


@ip_router.post("/create-from-suggestions")
async def create_from_suggestions(body: CreateFromSuggestionsRequest, user: User = Depends(get_current_user)):
    """Create a profile from confirmed suggestions."""
    from packages.cognitive_kernel.intelligence_profile.profile_intelligence_agent import ProfileIntelligenceAgent
    agent = ProfileIntelligenceAgent(async_session_factory)
    org_id = _get_org_id(user)
    profile = await agent.create_profile_from_suggestions(
        org_id, body.suggestions, body.user_confirmed, user_id=str(user.id)
    )
    return {"profile": profile.to_dict()}


@ip_router.post("/{profile_id}/refine")
async def refine_profile(
    profile_id: str,
    body: AnalyzeRequest,
    user: User = Depends(get_current_user),
):
    """Refine an existing profile with new data."""
    from packages.cognitive_kernel.intelligence_profile.profile_intelligence_agent import ProfileIntelligenceAgent
    agent = ProfileIntelligenceAgent(async_session_factory)
    org_id = _get_org_id(user)
    return await agent.refine_profile(org_id, profile_id, body.columns, body.file_name, body.file_type)


# ── Confidence ───────────────────────────────────────────────────────

@ip_router.get("/{profile_id}/confidence")
async def get_confidence(profile_id: str, user: User = Depends(get_current_user)):
    """Get confidence score breakdown for a profile."""
    from packages.cognitive_kernel.intelligence_profile.profile_intelligence_agent import ProfileIntelligenceAgent
    agent = ProfileIntelligenceAgent(async_session_factory)
    org_id = _get_org_id(user)
    return await agent._recalculate_confidence(org_id, profile_id)


# ── Tenant Security ──────────────────────────────────────────────────

@ip_router.get("/tenant/stats")
async def get_tenant_stats(user: User = Depends(get_current_user)):
    """Get data isolation statistics for the current tenant."""
    from packages.cognitive_kernel.intelligence_profile.tenant_security import ProfileTenantGuard
    guard = ProfileTenantGuard(async_session_factory)
    org_id = _get_org_id(user)
    return await guard.get_tenant_stats(org_id)
