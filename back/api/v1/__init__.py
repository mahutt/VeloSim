from fastapi import APIRouter
from .stations import router as stations_router
from .station_tasks import router as station_tasks_router
from .simulation import router as simulation_router

# Create the main v1 API router
api_router = APIRouter()

# Include all endpoint routers
api_router.include_router(stations_router)
api_router.include_router(station_tasks_router)
api_router.include_router(simulation_router)

__all__ = ["api_router"]
