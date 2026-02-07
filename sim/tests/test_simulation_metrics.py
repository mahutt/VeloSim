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

import pytest

from sim.core.simulation_report import SimulationReport


def test_initial_state() -> None:
    """
    SimulationMetrics should initialize with zero driving and servicing time.
    """
    metrics = SimulationReport()

    assert metrics.total_driving_time == 0
    assert metrics.total_servicing_time == 0


def test_increment_driving_time() -> None:
    """
    increment_driving_time should increase total_driving_time by one.
    """
    metrics = SimulationReport()

    metrics.increment_driving_time()
    metrics.increment_driving_time()

    assert metrics.total_driving_time == 2
    assert metrics.total_servicing_time == 0


def test_increment_servicing_time() -> None:
    """
    increment_servicing_time should increase total_servicing_time by one.
    """
    metrics = SimulationReport()

    metrics.increment_servicing_time()
    metrics.increment_servicing_time()
    metrics.increment_servicing_time()

    assert metrics.total_servicing_time == 3
    assert metrics.total_driving_time == 0


def test_driving_to_servicing_ratio_normal_case() -> None:
    """
    get_driving_to_servicing_ratio should return servicing / driving.
    """
    metrics = SimulationReport()

    for _ in range(4):
        metrics.increment_driving_time()

    for _ in range(2):
        metrics.increment_servicing_time()

    ratio = metrics.get_driving_to_servicing_ratio()

    assert ratio == pytest.approx(0.5)


def test_driving_to_servicing_ratio_zero_driving_time() -> None:
    """
    get_driving_to_servicing_ratio should return 0 when driving time is zero.
    """
    metrics = SimulationReport()

    metrics.increment_servicing_time()
    metrics.increment_servicing_time()

    assert metrics.get_driving_to_servicing_ratio() == 0
