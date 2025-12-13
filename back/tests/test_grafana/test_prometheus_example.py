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

import re
import time
import pytest
from back.grafana_logging import prometheus_example as prom


# Reset _demo_metrics before each test
@pytest.fixture(autouse=True)
def reset_demo_metrics() -> None:
    prom._demo_metrics["counters"].clear()
    prom._demo_metrics["histograms"].clear()


def test_example_simulation_start_counter() -> None:
    prom.example_simulation_start_counter()
    assert len(prom._demo_metrics["counters"]) == 1
    labels, value = prom._demo_metrics["counters"][0]
    assert value == 1


def test_example_simulation_start_timing() -> None:
    start = time.time()
    prom.example_simulation_start_timing()
    elapsed = (time.time() - start) * 1000

    assert len(prom._demo_metrics["histograms"]) == 1
    labels, value = prom._demo_metrics["histograms"][0]
    # value recorded should be roughly sleep time
    assert 150 <= value <= 300
    assert elapsed >= 180


def test_example_full_simulation_metrics() -> None:
    result = prom.example_full_simulation_metrics()
    assert "startup_time_ms" in result
    assert result["startup_time_ms"] > 0
    # check metrics were recorded
    assert len(prom._demo_metrics["counters"]) == 1
    assert len(prom._demo_metrics["histograms"]) == 1


def test_example_metrics_endpoint() -> None:
    # Add some metrics first
    prom.example_simulation_start_counter()
    prom.example_simulation_start_timing()
    output = prom.example_metrics_endpoint()
    assert isinstance(output, str)
    assert "simulation_start_total" in output
    assert "simulation_start_duration_ms" in output

    # Simple regex check for Prometheus-style labels
    assert re.search(r"simulation_start_total\{.*\} 1", output)
