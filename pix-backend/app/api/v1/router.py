from fastapi import APIRouter

from app.api.v1.activity import activity_router
from app.api.v1.admin import admin_router
from app.api.v1.agents import agents_router as agents_v1_router
from app.api.v1.agents_v2 import agents_v2_router
from app.api.v1.auth import auth_router
from app.api.v1.enterprise import enterprise_router
from app.api.v1.gtm import gtm_router
from app.api.v1.intelligence_profile import intelligence_profile_router
from app.api.v1.dashboard import dashboard_router

api_router = APIRouter()
api_router.include_router(auth_router, prefix="/auth", tags=["Auth"])
api_router.include_router(enterprise_router, prefix="/enterprise", tags=["Enterprise"])
api_router.include_router(admin_router, prefix="/admin", tags=["Admin"])
api_router.include_router(gtm_router, prefix="/gtm", tags=["GTM"])
api_router.include_router(activity_router, prefix="/activity", tags=["Activity"])
api_router.include_router(agents_v1_router, prefix="/agents", tags=["Agents V1"])
api_router.include_router(agents_v2_router, prefix="/agents/v2", tags=["Agents V2"])
api_router.include_router(intelligence_profile_router, prefix="/intelligence-profile", tags=["Intelligence Profile"])
api_router.include_router(dashboard_router, prefix="/dashboard", tags=["Dashboard"])
