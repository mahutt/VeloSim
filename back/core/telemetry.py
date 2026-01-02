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

from opentelemetry import metrics
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.exporter.prometheus import PrometheusMetricReader


def initialize_global_telemetry() -> None:
    """
    Configures the global OpenTelemetry meter provider for the application.

    This initializes OpenTelemetry metrics with a Prometheus exporter and sets
    process-wide state used by the rest of the application. On the first call, it:

    1. Sets up the Prometheus integration responsible for collecting metrics
    from OpenTelemetry and exposing them on the Prometheus /metrics endpoint.
    2. Creates the central MeterProvider that all metrics flow through and
    connects it to the Prometheus integration.
    3. Registers this MeterProvider as the global provider used by
    opentelemetry.metrics.

    Once this has run, metrics can be created anywhere in the application using
    metrics.get_meter(), and they will be collected and exposed via Prometheus.

    Initialization is process-wide and idempotent. If a global
    MeterProvider has already been registered with OpenTelemetry, this function
    is a no-op. Idempotency is derived from OpenTelemetry's existing global state
    rather than from a separate local guard.

    Example usage elsewhere in the application:

        from opentelemetry import metrics
        meter = metrics.get_meter(__name__)
        counter = meter.create_counter("example_counter")

    Returns:
        None
    """

    # If a provider is already set, assume global telemetry has been initialized
    if isinstance(metrics.get_meter_provider(), MeterProvider):
        return

    resource = Resource(attributes={SERVICE_NAME: "velosim-backend"})
    reader = PrometheusMetricReader()
    provider = MeterProvider(resource=resource, metric_readers=[reader])

    metrics.set_meter_provider(provider)
