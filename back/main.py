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

from typing import Annotated, AsyncIterator, Dict
from fastapi.middleware.cors import CORSMiddleware
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware
from contextlib import asynccontextmanager
from fastapi import Depends, FastAPI, HTTPException
from fastapi.security import OAuth2PasswordRequestForm

from back.auth.dependency import get_user_id
from back.core.telemetry import initialize_global_telemetry
from back.middleware.metrics_middleware import MetricsMiddleware
from back.core.config import settings
from back.api.v1 import api_router
from back.exception_handlers import (
    bad_request_error_handler,
    item_not_found_error_handler,
    unexpected_error_handler,
    velosim_permission_error_handler,
)
from back.exceptions import (
    BadRequestError,
    ItemNotFoundError,
    UnexpectedError,
    VelosimPermissionError,
)
from back.api.v1.metrics import router as metrics_router
from back.services.simulation_service import simulation_service
from back.auth import Token, authenticate_user
from back.database.session import get_db
from grafana_logging.logger import get_logger

logger = get_logger(__name__)

# Configure OpenTelemetry for Prometheus metrics
initialize_global_telemetry()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Application lifespan management.

    Args:
        app: The FastAPI application instance.

    Returns:
        AsyncIterator[None]: Async context manager for startup and shutdown.
    """
    # Startup
    yield
    # Shutdown - cleanup simulations
    try:
        db = next(get_db())
        try:
            simulation_service.stop_all_simulations_system(db)
        finally:
            db.close()
    except Exception as e:
        # In test environments or if database is unavailable,
        # gracefully skip cleanup
        logger.warning(f"Could not cleanup simulations during shutdown: {e}")


# Create FastAPI application
app = FastAPI(
    title="VeloSim Backend API",
    description="Backend API for VeloSim bike sharing simulation platform",
    version="1.0.0",
    docs_url="/api/docs" if settings.ENVIRONMENT != "production" else None,
    redoc_url="/api/redoc" if settings.ENVIRONMENT != "production" else None,
    lifespan=lifespan,
)

# Add metrics middleware to track all endpoint calls
app.add_middleware(MetricsMiddleware)

# Register domain exception handlers to centralize error-to-HTTP mapping
app.add_exception_handler(BadRequestError, bad_request_error_handler)
app.add_exception_handler(ItemNotFoundError, item_not_found_error_handler)
app.add_exception_handler(VelosimPermissionError, velosim_permission_error_handler)
app.add_exception_handler(UnexpectedError, unexpected_error_handler)


@app.post("/api/token")
async def login_for_access_token(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
) -> Token:
    """This implements the OAuth2 token endpoint. Per the OAuth2 spec this must be
    multipart form data and not JSON. Doing it this way means it is compatible with many
    existing OAuth2 libraries and the built-in authentication features of Swagger.
    However, nothing stops us from also implementing a JSON endpoint for this if it is
    neccesary.

    We only use usernames/passwords for authentication, however, we support passing
    these in either the username or client id field, and password or client secret field
    again for maximum compatibility with differenc scenarios.

    Args:
        form_data: OAuth2 password request form containing
            username/password or client_id/client_secret.

    Returns:
        Token: Access token and token type for authenticated user.
    """
    access_token = authenticate_user(
        form_data.username or form_data.client_id,
        form_data.password or form_data.client_secret,
    )
    if access_token is None:
        raise HTTPException(status_code=400, detail="Invalid credentials")
    return Token(access_token=access_token, token_type="bearer")


# Add ProxyHeaders middleware to trust X-Forwarded-* headers from nginx
app.add_middleware(ProxyHeadersMiddleware, trusted_hosts=["127.0.0.1", "localhost"])

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routing strategy note:
# - `api_router` is wrapped with `Depends(get_user_id)` to protect v1 business APIs.
# - `metrics_router` is intentionally mounted separately and BEFORE `api_router`
#   so `/api/v1/metric/metrics` remains publicly scrapeable by Prometheus.
# - If metrics are re-included inside `api_router`, scrapes will return 401.
#
# Keep auth-free operational endpoints (token, health, metrics) outside the
# authenticated router to avoid coupling observability/availability checks to
# end-user authentication.
#
# Security note: the metrics endpoint is unauthenticated at the application level,
# but nginx blocks public access to /api/v1/metric/metrics (returns 404).
# Prometheus scrapes internally via the Docker bridge network (backend:8000),
# bypassing nginx entirely.  See ansible/roles/nginx/templates/velosim.conf.j2.
app.include_router(metrics_router, prefix="/api/v1")
app.include_router(api_router, prefix="/api/v1", dependencies=[Depends(get_user_id)])


@app.get("/")
async def root() -> Dict[str, str]:
    """Root endpoint.

    Returns:
        Dict[str, str]: API information including name and version.
    """
    return {"message": "VeloSim Backend API", "version": "1.0.0"}


@app.get("/health")
async def health_check() -> Dict[str, str]:
    """Basic health check endpoint.

    Returns:
        Dict[str, str]: Health status of the service.
    """
    return {"status": "healthy", "service": "VeloSim Backend API"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "back.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True if settings.ENVIRONMENT == "development" else False,
    )
