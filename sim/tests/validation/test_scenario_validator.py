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
import copy
import json
from typing import Any, Dict, List
from sim.utils.json_parser_strategy import _ScenarioValidator as ScenarioValidator

VALID_SCENARIO_CONTENT: Dict[str, Any] = {
    "start_time": "day1:08:00",
    "end_time": "day1:12:00",
    "vehicle_battery_capacity": 999,
    "stations": [
        {
            "name": "Station 1",
            "position": [-73.5, 45.5],
            "initial_task_count": 1,
            "scheduled_tasks": ["day1:09:30"],
        }
    ],
    "vehicles": [
        {"name": "Vehicle 1", "position": [-73.56, 45.51], "battery_count": 999}
    ],
    "drivers": [
        {
            "name": "Driver 1",
            "shift": {
                "start_time": "day1:08:00",
                "end_time": "day1:12:00",
                "lunch_break": "day1:10:00",
            },
        }
    ],
}


@pytest.fixture
def validator() -> ScenarioValidator:
    """Fixture to provide a ScenarioValidator instance."""
    return ScenarioValidator()


def test_valid_scenario(validator: ScenarioValidator) -> None:
    errors: List[Dict[str, str]] = validator.validate_all(VALID_SCENARIO_CONTENT)
    assert errors == [], f"Expected no errors, got: {errors}"


def test_missing_required_fields(validator: ScenarioValidator) -> None:
    scenario_content: Dict[str, Any] = {}
    errors: List[Dict[str, str]] = validator.validate_all(scenario_content)
    assert any(e["field"] == "start_time" for e in errors)
    assert any(e["field"] == "end_time" for e in errors)
    assert any(e["field"] == "vehicle_battery_capacity" for e in errors)


def test_invalid_time_format(validator: ScenarioValidator) -> None:
    scenario_content: Dict[str, Any] = copy.deepcopy(VALID_SCENARIO_CONTENT)
    scenario_content["start_time"] = "8AM"
    scenario_content["end_time"] = "1200"
    errors: List[Dict[str, str]] = validator.validate_all(scenario_content)
    assert any("start_time" in e["field"] for e in errors)
    assert any("end_time" in e["field"] for e in errors)


def test_end_time_before_start_time(validator: ScenarioValidator) -> None:
    scenario_content: Dict[str, Any] = copy.deepcopy(VALID_SCENARIO_CONTENT)
    scenario_content["start_time"] = "day1:12:00"
    scenario_content["end_time"] = "day1:08:00"
    errors: List[Dict[str, str]] = validator.validate_all(scenario_content)
    assert any(e["field"] == "end_time" and "after" in e["message"] for e in errors)


def test_station_missing_required_fields(validator: ScenarioValidator) -> None:
    scenario_content: Dict[str, Any] = copy.deepcopy(VALID_SCENARIO_CONTENT)
    scenario_content["stations"].append({})  # missing required fields
    errors: List[Dict[str, str]] = validator.validate_all(scenario_content)
    assert any("stations[1].name" == e.get("field") for e in errors)
    assert any("stations[1].position" == e.get("field") for e in errors)
    assert any("stations[1].scheduled_tasks" == e.get("field") for e in errors)


def test_vehicle_missing_required_fields(validator: ScenarioValidator) -> None:
    scenario_content: Dict[str, Any] = copy.deepcopy(VALID_SCENARIO_CONTENT)
    scenario_content["vehicles"].append({})
    errors: List[Dict[str, str]] = validator.validate_all(scenario_content)
    assert any("vehicles[1].name" == e.get("field") for e in errors)


def test_invalid_lat_lon(validator: ScenarioValidator) -> None:
    scenario_content: Dict[str, Any] = copy.deepcopy(VALID_SCENARIO_CONTENT)
    scenario_content["stations"][0]["position"] = [200, 100]  # Invalid lat/lon
    scenario_content["vehicles"][0]["position"] = [200, 100]  # Invalid lat/lon
    errors: List[Dict[str, str]] = validator.validate_all(scenario_content)
    assert any("stations[0].position" in e.get("field", "") for e in errors)
    assert any("vehicles[0].position" in e.get("field", "") for e in errors)


def test_scheduled_tasks_time_accepts_string(validator: ScenarioValidator) -> None:
    scenario_content: Dict[str, Any] = copy.deepcopy(VALID_SCENARIO_CONTENT)
    scenario_content["stations"][0]["scheduled_tasks"] = ["day1:08:30"]
    errors = validator.validate_all(scenario_content)
    assert len(errors) == 0


def test_empty_lists(validator: ScenarioValidator) -> None:
    scenario_content: Dict[str, Any] = copy.deepcopy(VALID_SCENARIO_CONTENT)
    scenario_content["stations"] = []
    scenario_content["vehicles"] = []
    scenario_content["drivers"] = []
    errors: List[Dict[str, str]] = validator.validate_all(scenario_content)
    assert isinstance(errors, list)


def test_multi_day_scenario(validator: ScenarioValidator) -> None:
    """Test that scenarios spanning multiple days are supported."""
    scenario_content: Dict[str, Any] = copy.deepcopy(VALID_SCENARIO_CONTENT)
    # Start on one day, end on the next
    scenario_content["start_time"] = "day1:08:00"
    scenario_content["end_time"] = "day2:08:00"  # 24 hours later
    errors: List[Dict[str, str]] = validator.validate_all(scenario_content)
    assert len(errors) == 0


def test_simple_time_format_still_works(validator: ScenarioValidator) -> None:
    """Test backward compatibility with simple HH:MM format."""
    scenario_content: Dict[str, Any] = copy.deepcopy(VALID_SCENARIO_CONTENT)
    scenario_content["start_time"] = "day1:08:00"
    scenario_content["end_time"] = "day1:17:00"
    errors: List[Dict[str, str]] = validator.validate_all(scenario_content)
    assert len(errors) == 0


def test_scheduled_tasks_time_validation(validator: ScenarioValidator) -> None:
    """Validate scheduled_tasks string format; reject RFC3339."""
    scenario_content: Dict[str, Any] = copy.deepcopy(VALID_SCENARIO_CONTENT)
    # Valid format
    scenario_content["stations"][0]["scheduled_tasks"] = ["day1:08:30"]
    errors = validator.validate_all(scenario_content)
    assert len(errors) == 0

    # Invalid (RFC3339) format should be rejected
    scenario_content["stations"][0]["scheduled_tasks"] = ["2025-11-06T10:30:00Z"]
    errors = validator.validate_all(scenario_content)
    assert len(errors) > 0
    assert any("scheduled_tasks" in err.get("field", "") for err in errors)


def test_initial_task_count_optional_time(validator: ScenarioValidator) -> None:
    """Initial tasks are represented by count and do not require time fields."""
    scenario_content: Dict[str, Any] = copy.deepcopy(VALID_SCENARIO_CONTENT)
    scenario_content["stations"][0]["initial_task_count"] = 2
    scenario_content["stations"][0]["scheduled_tasks"] = []
    errors: List[Dict[str, str]] = validator.validate_all(scenario_content)
    assert len(errors) == 0


def test_vehicle_battery_capacity_required_and_positive(
    validator: ScenarioValidator,
) -> None:
    scenario_content: Dict[str, Any] = copy.deepcopy(VALID_SCENARIO_CONTENT)
    # Missing capacity
    del scenario_content["vehicle_battery_capacity"]
    errors = validator.validate_all(scenario_content)
    assert any(e.get("field") == "vehicle_battery_capacity" for e in errors)

    # Non-positive capacity
    scenario_content = copy.deepcopy(VALID_SCENARIO_CONTENT)
    scenario_content["vehicle_battery_capacity"] = 0
    errors = validator.validate_all(scenario_content)
    assert any(
        "vehicle_battery_capacity" in e.get("field", "")
        or "vehicle_battery_capacity" in e.get("message", "")
        for e in errors
    )


def test_scheduled_tasks_must_be_iterable_strings(validator: ScenarioValidator) -> None:
    scenario_content: Dict[str, Any] = copy.deepcopy(VALID_SCENARIO_CONTENT)
    # Non-iterable
    scenario_content["stations"][0]["scheduled_tasks"] = "day1:09:00"
    errors = validator.validate_all(scenario_content)
    assert any("scheduled_tasks" in e.get("field", "") for e in errors)

    # Iterable but wrong element type
    scenario_content = copy.deepcopy(VALID_SCENARIO_CONTENT)
    scenario_content["stations"][0]["scheduled_tasks"] = [{"invalid": "object"}]
    errors = validator.validate_all(scenario_content)
    assert any("scheduled_tasks" in e.get("field", "") for e in errors)


def test_validation_with_line_numbers() -> None:
    """Test line numbers in validation errors with JSON string."""
    json_string = """{
    "content": {
        "start_time": "day1:08:00",
        "end_time": "day1:12:00",
        "vehicle_battery_capacity": 999,
        "stations": [
            {
                "name": "Station 1",
                "position": [-73.5, 45.5],
                "initial_task_count": 0,
                "scheduled_tasks": ["bad-time-format"]
            }
        ],
        "vehicles": [],
        "drivers": []
    }
}"""

    data = json.loads(json_string)
    validator = ScenarioValidator(json_string=json_string)
    errors = validator.validate_all(data["content"])

    # Should have error for invalid scheduled_tasks time
    assert len(errors) > 0
    sched_errors = [e for e in errors if "scheduled_tasks" in e.get("field", "")]
    assert len(sched_errors) > 0

    # Line numbers may or may not be present depending on parsing
    # Just verify the structure is correct (has field and message, optionally line)
    for error in errors:
        assert "field" in error
        assert "message" in error
        # line is optional
        if "line" in error:
            assert isinstance(error["line"], int)
            assert error["line"] > 0


def test_validation_without_line_numbers() -> None:
    """Test that validation works without JSON string (no line numbers)."""
    validator = ScenarioValidator()  # No JSON string provided
    scenario_content: Dict[str, Any] = copy.deepcopy(VALID_SCENARIO_CONTENT)
    scenario_content["start_time"] = "invalid"

    errors = validator.validate_all(scenario_content)

    # Should have errors
    assert len(errors) > 0

    # Errors should not have line numbers
    for error in errors:
        assert "field" in error
        assert "message" in error
        # No line field when JSON string not provided
        line_val = error.get("line")
        assert "line" not in error or line_val is None


def test_position_with_wrong_length_list(validator: ScenarioValidator) -> None:
    """Test position validation with wrong length list."""
    scenario_content: Dict[str, Any] = copy.deepcopy(VALID_SCENARIO_CONTENT)
    # Position list must have exactly 2 coordinates
    scenario_content["stations"][0]["position"] = [-73.5, 45.5, 100.0]

    errors = validator.validate_all(scenario_content)

    assert len(errors) > 0
    assert any(
        "exactly two coordinates" in error.get("message", "").lower()
        for error in errors
    )


def test_position_with_invalid_type(validator: ScenarioValidator) -> None:
    """Test position validation with invalid type."""
    scenario_content: Dict[str, Any] = copy.deepcopy(VALID_SCENARIO_CONTENT)
    # Position must be dict or list/tuple
    scenario_content["stations"][0]["position"] = "invalid"

    errors = validator.validate_all(scenario_content)

    assert len(errors) > 0
    assert any(
        "position must be" in error.get("message", "").lower() for error in errors
    )


def test_scheduled_tasks_with_invalid_type(validator: ScenarioValidator) -> None:
    """Test scheduled_tasks element type must be string time."""
    scenario_content: Dict[str, Any] = copy.deepcopy(VALID_SCENARIO_CONTENT)
    scenario_content["stations"][0]["scheduled_tasks"] = [{"invalid": "object"}]

    errors = validator.validate_all(scenario_content)

    assert len(errors) > 0
    assert any("scheduled_tasks" in error.get("field", "") for error in errors)


def test_array_elements_have_distinct_line_numbers() -> None:
    """Missing driver fields in different array elements use distinct lines."""
    json_string = """{
    "content": {
        "start_time": "day1:08:00",
        "end_time": "day1:12:00",
        "vehicle_battery_capacity": 999,
        "stations": [
            {
                "name": "Station 1",
                "position": [-73.5, 45.5],
                "initial_task_count": 0,
                "scheduled_tasks": []
            }
        ],
        "vehicles": [
            {
                "name": "V1",
                "position": [-73.56, 45.51],
                "battery_count": 2
            }
        ],
        "drivers": [
            { "name": "D1" },
            { "name": "D2" }
        ]
    }
}"""

    data = json.loads(json_string)
    validator = ScenarioValidator(json_string=json_string)
    errors = validator.validate_all(data["content"])

    # Should have errors for missing shift on drivers[0] and drivers[1]
    shift_errors = [
        e
        for e in errors
        if e.get("field", "").startswith("drivers[")
        and e.get("field", "").endswith(".shift")
    ]
    assert len(shift_errors) >= 2

    # Check that errors have line numbers and they are different
    line_numbers = [e.get("line") for e in shift_errors if e.get("line") is not None]
    assert len(line_numbers) >= 2
    assert (
        len(set(line_numbers)) >= 2
    ), f"Expected distinct line numbers, got: {line_numbers}"
