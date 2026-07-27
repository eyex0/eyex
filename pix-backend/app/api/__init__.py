from app.api.v1.auth import auth_router
from app.api.v1.health import health_router
from app.api.v1.router import api_v1_router

__all__ = ["api_v1_router", "health_router", "auth_router"]
