from fastapi import APIRouter
from app.api import companies, competitors, health, interviews, profiles, research, sources

api_router = APIRouter()

# Mount health & system routes
api_router.include_router(health.router)

# Mount company intelligence routes
api_router.include_router(companies.router)
api_router.include_router(research.router)
api_router.include_router(profiles.router)
api_router.include_router(interviews.router)
api_router.include_router(competitors.router)
api_router.include_router(sources.router)
