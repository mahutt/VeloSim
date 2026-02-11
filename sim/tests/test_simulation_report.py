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
    SimulationReport should initialize with zero metrics and empty task list.

    Returns:
        None
    """
    metrics = SimulationReport()

    assert metrics.total_driving_time == 0
    assert metrics.total_servicing_time == 0
    assert metrics.tasks_completed_per_shift == []


def test_increment_driving_time() -> None:
    """
    increment_driving_time should increase total_driving_time.

    Returns:
        None
    """
    metrics = SimulationReport()

    metrics.increment_driving_time()
    metrics.increment_driving_time()

    assert metrics.total_driving_time == 2
    assert metrics.total_servicing_time == 0


def test_increment_servicing_time() -> None:
    """
    increment_servicing_time should increase total_servicing_time.

    Returns:
        None
    """
    metrics = SimulationReport()

    metrics.increment_servicing_time()
    metrics.increment_servicing_time()
    metrics.increment_servicing_time()

    assert metrics.total_servicing_time == 3
    assert metrics.total_driving_time == 0


def test_add_task_count_for_shift_single_entry() -> None:
    """
    add_task_count_for_shift should store a single task count.

    Returns:
        None
    """
    metrics = SimulationReport()

    metrics.add_task_count_for_shift(5)

    assert metrics.tasks_completed_per_shift == [5]


def test_add_task_count_for_shift_multiple_entries() -> None:
    """
    add_task_count_for_shift should store multiple task counts in order.

    Returns:
        None
    """
    metrics = SimulationReport()

    metrics.add_task_count_for_shift(3)
    metrics.add_task_count_for_shift(7)
    metrics.add_task_count_for_shift(2)

    assert metrics.tasks_completed_per_shift == [3, 7, 2]


def test_get_average_tasks_per_shift_normal_case() -> None:
    """
    get_average_tasks_per_shift should return correct average.

    Returns:
        None
    """
    metrics = SimulationReport()

    metrics.add_task_count_for_shift(4)
    metrics.add_task_count_for_shift(6)
    metrics.add_task_count_for_shift(10)

    assert metrics.get_average_tasks_per_shift() == pytest.approx(20 / 3)


def test_get_average_tasks_per_shift_empty() -> None:
    """
    get_average_tasks_per_shift should return 0.0 when list is empty.

    Returns:
        None
    """
    metrics = SimulationReport()

    assert metrics.get_average_tasks_per_shift() == 0.0


def test_get_servicing_to_driving_ratio_normal_case() -> None:
    """
    get_servicing_to_driving_ratio should return servicing / driving.

    Returns:
        None
    """
    metrics = SimulationReport()

    for _ in range(4):
        metrics.increment_driving_time()

    for _ in range(2):
        metrics.increment_servicing_time()

    assert metrics.get_servicing_to_driving_ratio() == pytest.approx(0.5)


def test_get_servicing_to_driving_ratio_zero_driving_time() -> None:
    """
    get_servicing_to_driving_ratio should return 0.0 when driving time is zero.

    Returns:
        None
    """
    metrics = SimulationReport()

    metrics.increment_servicing_time()
    metrics.increment_servicing_time()

    assert metrics.get_servicing_to_driving_ratio() == 0.0


def test_reset_clears_all_metrics() -> None:
    """
    reset should clear driving time, servicing time, and task list.

    Returns:
        None
    """
    metrics = SimulationReport()

    metrics.increment_driving_time()
    metrics.increment_servicing_time()
    metrics.add_task_count_for_shift(5)
    metrics.add_task_count_for_shift(8)

    metrics.reset()

    assert metrics.total_driving_time == 0
    assert metrics.total_servicing_time == 0
    assert metrics.tasks_completed_per_shift == []


def test_reset_on_fresh_instance() -> None:
    """
    reset should be safe on a fresh instance with no prior data.

    Returns:
        None
    """
    metrics = SimulationReport()

    metrics.reset()

    assert metrics.total_driving_time == 0
    assert metrics.total_servicing_time == 0
    assert metrics.tasks_completed_per_shift == []


def test_get_average_service_time_for_tasks_normal_case() -> None:
    """
    get_average_service_time_for_tasks should return correct average
    when service_times contains values.

    Returns:
        None
    """
    metrics = SimulationReport()

    metrics.response_times = [5, 10, 15]

    assert metrics.get_average_service_time_for_tasks() == pytest.approx(10.0)


def test_get_average_service_time_for_tasks_single_entry() -> None:
    """
    get_average_service_time_for_tasks should return the value itself
    when only one service time exists.

    Returns:
        None
    """
    metrics = SimulationReport()

    metrics.response_times = [8]

    assert metrics.get_average_service_time_for_tasks() == 8.0


def test_get_average_service_time_for_tasks_empty() -> None:
    """
    get_average_service_time_for_tasks should return 0.0
    when there are no recorded service times.

    Returns:
        None
    """
    metrics = SimulationReport()

    assert metrics.get_average_service_time_for_tasks() == 0.0


def test_add_task_count_for_shift_allows_zero() -> None:
    """
    add_task_count_for_shift should correctly store zero
    as a valid shift task count.

    Returns:
        None
    """
    metrics = SimulationReport()

    metrics.add_task_count_for_shift(0)

    assert metrics.tasks_completed_per_shift == [0]


def test_add_task_count_for_shift_large_value() -> None:
    """
    add_task_count_for_shift should handle large task counts.

    Returns:
        None
    """
    metrics = SimulationReport()

    metrics.add_task_count_for_shift(1000)

    assert metrics.tasks_completed_per_shift == [1000]
