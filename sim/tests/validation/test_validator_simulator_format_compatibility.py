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
from sim.utils.json_parser_strategy import _ScenarioValidator as ScenarioValidator


@pytest.fixture
def validator() -> ScenarioValidator:
    """Fixture to provide a ScenarioValidator instance."""
    return ScenarioValidator()


@pytest.fixture
def simulator_format_scenario() -> Dict[str, Any]:
    """Fixture providing a scenario in the format expected by the simulator.

    New schema expects:
    - `vehicle_battery_capacity` as positive integer
    - `stations`: name, position [lon, lat], initial_task_count,
        scheduled_tasks ["dayX:HH:MM"]
    - `vehicles`: name, position [lon, lat], battery_count
    - `drivers`: name, shift with start_time/end_time/lunch_break
        as "dayX:HH:MM"
    """
    return {
        "start_time": "day1:08:00",
        "end_time": "day1:17:00",
        "vehicle_battery_capacity": 999,
        "stations": [
            {
                "name": "Station A",
                "position": [-73.5, 45.5],
                "initial_task_count": 3,
                "scheduled_tasks": ["day1:08:02", "day1:09:00"],
            },
            {
                "name": "Station B",
                "position": [-73.58, 45.48],
                "initial_task_count": 2,
                "scheduled_tasks": ["day1:08:30"],
            },
        ],
        "vehicles": [
            {"name": "Vehicle 1", "position": [-73.5, 45.5], "battery_count": 3},
            {"name": "Vehicle 2", "position": [-73.58, 45.48], "battery_count": 2},
        ],
        "drivers": [
            {
                "name": "Driver 1",
                "shift": {
                    "start_time": "day1:08:00",
                    "end_time": "day1:17:00",
                    "lunch_break": "day1:12:00",
                },
            },
            {
                "name": "Driver 2",
                "shift": {
                    "start_time": "day1:08:00",
                    "end_time": "day1:17:00",
                    "lunch_break": "day1:12:00",
                },
            },
        ],
    }


def test_simulator_format_compatibility(
    validator: ScenarioValidator, simulator_format_scenario: Dict[str, Any]
) -> None:
    """Test that validator accepts the exact format required by the simulator."""
    # Add missing station that scheduled_tasks reference
    simulator_format_scenario["stations"].append(
        {
            "name": "Station C",
            "position": [-73.5, 45.5],
            "initial_task_count": 1,
            "scheduled_tasks": [],
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
        "vehicle_battery_capacity": 999,
        "stations": [
            {
                "name": "Station 1",
                "position": [-73.5, 45.5],
                "initial_task_count": 1,
                "scheduled_tasks": ["day1:08:30", "day1:08:45"],
            }
        ],
        "vehicles": [
            {"name": "Vehicle 1", "position": [-73.5, 45.5], "battery_count": 5}
        ],
        "drivers": [
            {
                "name": "Driver 1",
                "shift": {
                    "start_time": "day1:08:00",
                    "end_time": "day1:17:00",
                    "lunch_break": "day1:12:00",
                },
            }
        ],
    }

    errors: List[Dict[str, str]] = validator.validate_all(scenario)
    assert len(errors) == 0, f"Expected no errors but got: {errors}"


def test_integer_time_formats_rejected(validator: ScenarioValidator) -> None:
    """Test that integer time formats are rejected."""
    scenario: Dict[str, Any] = {
        "start_time": "day1:08:00",
        "end_time": "day1:17:00",
        "vehicle_battery_capacity": 999,
        "stations": [
            {
                "name": "Station 1",
                "position": [-73.5, 45.5],
                "initial_task_count": 0,
                # Integer element should be rejected
                "scheduled_tasks": [3600],
            }
        ],
    }

    errors: List[Dict[str, str]] = validator.validate_all(scenario)
    assert len(errors) > 0
    assert any("Time must be a string" in err["message"] for err in errors)

    # Test RFC 3339 format is rejected (as station scheduled task string)
    scenario["stations"][0]["scheduled_tasks"] = [
        "2025-11-06T14:30:00Z",
    ]
    errors = validator.validate_all(scenario)
    assert len(errors) > 0
    assert any("Invalid time format" in err["message"] for err in errors)


def test_zero_time_is_valid(validator: ScenarioValidator) -> None:
    """Test that time=start_time is valid for tasks (means spawn immediately)."""
    scenario: Dict[str, Any] = {
        "start_time": "day1:08:00",
        "end_time": "day1:17:00",
        "vehicle_battery_capacity": 999,
        "stations": [
            {
                "name": "Station 1",
                "position": [-73.5, 45.5],
                "initial_task_count": 2,
                "scheduled_tasks": ["day1:08:00"],
            }
        ],
        "vehicles": [
            {"name": "Vehicle 1", "position": [-73.5, 45.5], "battery_count": 2}
        ],
        "drivers": [
            {
                "name": "Driver 1",
                "shift": {
                    "start_time": "day1:08:00",
                    "end_time": "day1:17:00",
                    "lunch_break": "day1:12:00",
                },
            }
        ],
    }

    errors: List[Dict[str, str]] = validator.validate_all(scenario)
    assert len(errors) == 0, f"Expected no errors but got: {errors}"


def test_large_time_values_are_valid(validator: ScenarioValidator) -> None:
    """Test that large time values in seconds are accepted."""
    scenario: Dict[str, Any] = {
        "start_time": "day1:08:00",
        "end_time": "day1:17:00",
        "vehicle_battery_capacity": 999,
        "stations": [
            {
                "name": "Station 1",
                "position": [-73.5, 45.5],
                "initial_task_count": 0,
                "scheduled_tasks": ["day1:16:00"],
            }
        ],
        "vehicles": [
            {"name": "Vehicle 1", "position": [-73.5, 45.5], "battery_count": 2}
        ],
        "drivers": [
            {
                "name": "Driver 1",
                "shift": {
                    "start_time": "day1:08:00",
                    "end_time": "day1:17:00",
                    "lunch_break": "day1:12:00",
                },
            }
        ],
    }

    errors: List[Dict[str, str]] = validator.validate_all(scenario)
    assert len(errors) == 0, f"Expected no errors but got: {errors}"
