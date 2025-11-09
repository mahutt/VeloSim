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
from back.services.scenario_validation_service import ScenarioValidator


@pytest.fixture
def validator() -> ScenarioValidator:
    """Fixture to provide a ScenarioValidator instance."""
    return ScenarioValidator()


@pytest.fixture
def simulator_format_scenario() -> Dict[str, Any]:
    """Fixture providing a scenario in the format expected by the simulator.

    The simulator expects:
    - scheduled_tasks.time as integer/float seconds
    - initial_tasks.time as optional (can be omitted or set to 0)
    """
    return {
        "start_time": "08:00",
        "end_time": "17:00",
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
            {"id": "t3", "station_id": "8074"},  # No time field
        ],
        "scheduled_tasks": [
            {"id": "t4", "station_id": "2105", "time": 30},  # 30 seconds
            {"id": "t5", "station_id": "2508", "time": 120},  # 2 minutes
            {"id": "t6", "station_id": "8074", "time": 1800.5},  # 30.5 minutes
        ],
    }


def test_simulator_format_compatibility(
    validator: ScenarioValidator, simulator_format_scenario: Dict[str, Any]
) -> None:
    """Test that validator accepts the exact format used by the simulator.

    This ensures backward compatibility and that scenarios from the simulator
    can pass validation without modification.
    """
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


def test_numeric_time_formats_only(validator: ScenarioValidator) -> None:
    """Test validator only accepts numeric time formats.

    This is the simulator's source of truth:
    - initial_tasks: no time field (spawns immediately)
    - scheduled_tasks: numeric seconds (int or float)
    """
    scenario: Dict[str, Any] = {
        "start_time": "08:00",
        "end_time": "17:00",
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
            {"id": "t1", "station_id": "1"},  # No time (correct)
            {"id": "t2", "station_id": "1", "time": 0},  # Zero seconds (correct)
        ],
        "scheduled_tasks": [
            {"id": "t4", "station_id": "1", "time": 600},  # Integer seconds
            {"id": "t5", "station_id": "1", "time": 1800.5},  # Float seconds
        ],
    }

    errors: List[Dict[str, str]] = validator.validate_all(scenario)
    assert len(errors) == 0, f"Expected no errors but got: {errors}"


def test_string_time_formats_rejected(validator: ScenarioValidator) -> None:
    """Test that string time formats are rejected (simulator doesn't accept them)."""
    # Test HH:MM format is rejected
    scenario: Dict[str, Any] = {
        "start_time": "08:00",
        "end_time": "17:00",
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
                "id": "t1",
                "station_id": "1",
                "time": "10:30",
            },  # String format - should be rejected
        ],
    }

    errors: List[Dict[str, str]] = validator.validate_all(scenario)
    assert len(errors) > 0
    assert any("numeric seconds" in err["message"] for err in errors)

    # Test RFC 3339 format is rejected
    scenario["scheduled_tasks"] = [
        {"id": "t1", "station_id": "1", "time": "2025-11-06T14:30:00Z"},
    ]
    errors = validator.validate_all(scenario)
    assert len(errors) > 0
    assert any("numeric seconds" in err["message"] for err in errors)


def test_zero_time_is_valid(validator: ScenarioValidator) -> None:
    """Test that time=0 is valid for tasks (means spawn immediately)."""
    scenario: Dict[str, Any] = {
        "start_time": "08:00",
        "end_time": "17:00",
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
            {"id": "t1", "station_id": "1", "time": 0},  # Zero means immediate
        ],
        "scheduled_tasks": [
            {"id": "t2", "station_id": "1", "time": 0},  # Zero means immediate
        ],
    }

    errors: List[Dict[str, str]] = validator.validate_all(scenario)
    assert len(errors) == 0, f"Expected no errors but got: {errors}"


def test_large_time_values_are_valid(validator: ScenarioValidator) -> None:
    """Test that large time values in seconds are accepted."""
    scenario: Dict[str, Any] = {
        "start_time": "08:00",
        "end_time": "17:00",
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
            {"id": "t1", "station_id": "1", "time": 32400},  # 9 hours in seconds
        ],
    }

    errors: List[Dict[str, str]] = validator.validate_all(scenario)
    assert len(errors) == 0, f"Expected no errors but got: {errors}"
