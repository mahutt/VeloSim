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

from fastapi import APIRouter, Response
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST

# This router is intentionally mounted separately in `back.main` (not inside
# `api_router`) so the metrics endpoint remains public for Prometheus scrapes.
router = APIRouter(prefix="/metric", tags=["metrics"])


@router.get("/metrics")
def metrics() -> Response:
    """
    Expose Prometheus metrics for scraping.

    This endpoint returns metrics collected by the Prometheus client.
    Metrics are automatically populated via OpenTelemetry instrumentation
    and are scraped by Prometheus.

    Operational note:
        This endpoint is unauthenticated at the application level.
        Public access is blocked by nginx (returns 404).  Prometheus
        scrapes via the Docker internal network, bypassing nginx.
        See ``ansible/roles/nginx/templates/velosim.conf.j2``.

    Returns:
        Response: A plaintext HTTP response containing Prometheus metrics
        in the standard exposition format.
    """
    data = generate_latest()
    return Response(content=data, media_type=CONTENT_TYPE_LATEST)
