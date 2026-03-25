"""
MIT License

Copyright (c) 2025 VeloSim Contributors

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""

from fastapi import APIRouter
from .simulation import router as simulation_router
from .users import router as users_router
from .logs import router as logs_router
from .scenarios import router as scenarios_router
from .traffic_templates import router as traffic_templates_router

# Note: the Prometheus metrics router is excluded out of `api_router`.
# `api_router` is mounted in `back.main` with auth dependencies, and including
# metrics here would require authentication for `/api/v1/metric/metrics`,
# breaking Prometheus scraping.

# Create the main v1 API router
api_router = APIRouter()

# Include all endpoint routers
api_router.include_router(simulation_router)
api_router.include_router(users_router)
api_router.include_router(logs_router)
api_router.include_router(scenarios_router)
api_router.include_router(traffic_templates_router)

__all__ = ["api_router"]
