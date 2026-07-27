from fastapi import APIRouter

from app.api.v1.activity import activity_router
from app.api.v1.admin import admin_router
from app.api.v1.agents import agents_router as agents_v1_router
from app.api.v1.agents_v2 import agents_router as agents_v2_router
from app.api.v1.auth import auth_router
from app.api.v1.enterprise import enterprise_router
from app.api.v1.gtm import gtm_router
from app.api.v1.intelligence_profile import ip_router as intelligence_profile_router
from app.api.v1.dashboard import dashboard_router
from app.api.v1.agent_os import agent_os_router

api_router = APIRouter()
api_router.include_router(auth_router)
api_router.include_router(enterprise_router)
api_router.include_router(admin_router)
api_router.include_router(gtm_router)
api_router.include_router(activity_router)
api_router.include_router(agents_v1_router)
api_router.include_router(agents_v2_router)
api_router.include_router(intelligence_profile_router)
api_router.include_router(dashboard_router)
api_router.include_router(agent_os_router)
