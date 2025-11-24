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
from typing import Any, Dict, List
from sim.validation import ScenarioValidator


@pytest.fixture
def validator() -> ScenarioValidator:
    """Fixture to provide a ScenarioValidator instance."""
    return ScenarioValidator()


@pytest.fixture
def simulator_format_scenario() -> Dict[str, Any]:
    """Fixture providing a scenario in the format expected by the simulator.

    The simulator expects:
    - scheduled_tasks.time as simple time format with relative day (e.g. 'day1:08:00')
    - initial_tasks.time as optional (can be omitted or set to 'day1:00:00')
    """
    return {
        "start_time": "day1:08:00",
        "end_time": "day1:17:00",
        "scenario_title": "Simulator Format Test",
        "stations": [
            {
                "station_id": 8074,
                "station_name": "Station A",
                "task_count": 3,
                "station_position": [45.5, -73.5],
            },
            {
                "station_id": 2105,
                "station_name": "Station B",
                "task_count": 2,
                "station_position": [40.7, -74.0],
            },
        ],
        "resources": [
            {
                "resource_id": 1,
                "task_count": 3,
                "resource_position": [45.5, -73.5],
            },
            {
                "resource_id": 2,
                "task_count": 2,
                "resource_position": [40.7, -74.0],
            },
        ],
        "initial_tasks": [
            {"station_id": "8074"},  # No time field, no ID
        ],
        "scheduled_tasks": [
            {"station_id": "2105", "time": "day1:08:02"},
            {"station_id": "2508", "time": "day1:08:30"},
            {"station_id": "8074", "time": "day1:09:00"},
        ],
    }


def test_simulator_format_compatibility(
    validator: ScenarioValidator, simulator_format_scenario: Dict[str, Any]
) -> None:
    """Test that validator accepts the exact format required by the simulator."""
    # Add missing station that scheduled_tasks reference
    simulator_format_scenario["stations"].append(
        {
            "station_id": 2508,
            "station_name": "Station C",
            "task_count": 1,
            "station_position": [45.5, -73.5],
        }
    )

    errors: List[Dict[str, str]] = validator.validate_all(simulator_format_scenario)

    # Should have no validation errors
    assert len(errors) == 0, f"Expected no errors but got: {errors}"


def test_valid_time_formats_only(validator: ScenarioValidator) -> None:
    """Test validator only accepts str time formats
    with simple time and relative days."""
    scenario: Dict[str, Any] = {
        "start_time": "day1:08:00",
        "end_time": "day1:17:00",
        "scenario_title": "Numeric Format Test",
        "stations": [
            {
                "station_id": 1,
                "station_name": "Station 1",
                "task_count": 5,
                "station_position": [45.5, -73.5],
            }
        ],
        "resources": [
            {
                "resource_id": 1,
                "task_count": 5,
                "resource_position": [45.5, -73.5],
            }
        ],
        "initial_tasks": [
            {"station_id": "1"},  # No time, no ID (correct)
            {"station_id": "1", "time": "day1:08:00"},
        ],
        "scheduled_tasks": [
            {"station_id": "1", "time": "day1:08:30"},
            {"station_id": "1", "time": "day1:08:45"},
        ],
    }

    errors: List[Dict[str, str]] = validator.validate_all(scenario)
    assert len(errors) == 0, f"Expected no errors but got: {errors}"


def test_integer_time_formats_rejected(validator: ScenarioValidator) -> None:
    """Test that integer time formats are rejected."""
    scenario: Dict[str, Any] = {
        "start_time": "day1:08:00",
        "end_time": "day1:17:00",
        "stations": [
            {
                "station_id": 1,
                "station_name": "Station 1",
                "task_count": 1,
                "station_position": [45.5, -73.5],
            }
        ],
        "resources": [
            {
                "resource_id": 1,
                "task_count": 1,
                "resource_position": [45.5, -73.5],
            }
        ],
        "scheduled_tasks": [
            {
                "station_id": "1",
                "time": 3600,
            },  # integer format - should be rejected
        ],
    }

    errors: List[Dict[str, str]] = validator.validate_all(scenario)
    assert len(errors) > 0
    assert any("Time must be a string" in err["message"] for err in errors)

    # Test RFC 3339 format is rejected
    scenario["scheduled_tasks"] = [
        {"station_id": "1", "time": "2025-11-06T14:30:00Z"},
    ]
    errors = validator.validate_all(scenario)
    assert len(errors) > 0
    assert any("Invalid time format" in err["message"] for err in errors)


def test_zero_time_is_valid(validator: ScenarioValidator) -> None:
    """Test that time=start_time is valid for tasks (means spawn immediately)."""
    scenario: Dict[str, Any] = {
        "start_time": "day1:08:00",
        "end_time": "day1:17:00",
        "stations": [
            {
                "station_id": 1,
                "station_name": "Station 1",
                "task_count": 2,
                "station_position": [45.5, -73.5],
            }
        ],
        "resources": [
            {
                "resource_id": 1,
                "task_count": 2,
                "resource_position": [45.5, -73.5],
            }
        ],
        "initial_tasks": [
            {"station_id": "1", "time": "day1:08:00"},  # means immediate
        ],
        "scheduled_tasks": [
            {"station_id": "1", "time": "day1:08:00"},  # means immediate
        ],
    }

    errors: List[Dict[str, str]] = validator.validate_all(scenario)
    assert len(errors) == 0, f"Expected no errors but got: {errors}"


def test_large_time_values_are_valid(validator: ScenarioValidator) -> None:
    """Test that large time values in seconds are accepted."""
    scenario: Dict[str, Any] = {
        "start_time": "day1:08:00",
        "end_time": "day1:17:00",
        "stations": [
            {
                "station_id": 1,
                "station_name": "Station 1",
                "task_count": 1,
                "station_position": [45.5, -73.5],
            }
        ],
        "resources": [
            {
                "resource_id": 1,
                "task_count": 1,
                "resource_position": [45.5, -73.5],
            }
        ],
        "scheduled_tasks": [
            {"station_id": "1", "time": "day1:16:00"},  # 8 hours
        ],
    }

    errors: List[Dict[str, str]] = validator.validate_all(scenario)
    assert len(errors) == 0, f"Expected no errors but got: {errors}"
