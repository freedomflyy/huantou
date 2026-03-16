from fastapi import APIRouter

from app.api.routes.admin import router as admin_router
from app.api.routes.assets import router as assets_router
from app.api.routes.auth import router as auth_router
from app.api.routes.health import router as health_router
from app.api.routes.moderation import router as moderation_router
from app.api.routes.points import router as points_router
from app.api.routes.tasks import router as tasks_router

api_router = APIRouter()
api_router.include_router(admin_router)
api_router.include_router(assets_router)
api_router.include_router(auth_router)
api_router.include_router(health_router)
api_router.include_router(moderation_router)
api_router.include_router(points_router)
api_router.include_router(tasks_router)
