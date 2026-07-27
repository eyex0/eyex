from fastapi import APIRouter

from app.api.v1.activity import activity_router
from app.api.v1.admin import admin_router
from app.api.v1.agents import agents_router as agents_v1_router
from app.api.v1.agents_v2 import agents_router as agents_v2_router
from app.api.v1.auth import auth_router
from app.api.v1.billing import billing_router, dashboard_router
from app.api.v1.chat import chat_router
from app.api.v1.cognitive_data import cognitive_data_router
from app.api.v1.enterprise import enterprise_router
from app.api.v1.gtm import gtm_router
from app.api.v1.health import health_router
from app.api.v1.intelligence import intelligence_router
from app.api.v1.memory import memory_router
from app.api.v1.status import status_router
from app.api.v1.trust import trust_router
from app.api.v1.workspaces import workspaces_router
from app.api.v1.ingestion import ingestion_router
from app.api.v1.knowledge_graph import knowledge_router
from app.api.v1.decisions import decisions_router

api_v1_router = APIRouter(prefix="/api/v1")
api_v1_router.include_router(health_router)
api_v1_router.include_router(auth_router)
api_v1_router.include_router(agents_v1_router)
api_v1_router.include_router(agents_v2_router)
api_v1_router.include_router(chat_router)
api_v1_router.include_router(memory_router)
api_v1_router.include_router(status_router)
api_v1_router.include_router(admin_router)
api_v1_router.include_router(workspaces_router)
api_v1_router.include_router(billing_router)
api_v1_router.include_router(dashboard_router)
api_v1_router.include_router(activity_router)
api_v1_router.include_router(intelligence_router)
api_v1_router.include_router(enterprise_router)
api_v1_router.include_router(gtm_router)
api_v1_router.include_router(trust_router)
api_v1_router.include_router(cognitive_data_router)
api_v1_router.include_router(ingestion_router)
api_v1_router.include_router(knowledge_router)
api_v1_router.include_router(decisions_router)
