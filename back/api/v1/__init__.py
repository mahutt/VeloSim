from fastapi import APIRouter
from .stations import router as stations_router

# Create the main v1 API router
api_router = APIRouter()

# Include all endpoint routers
api_router.include_router(stations_router)

__all__ = ["api_router"]
