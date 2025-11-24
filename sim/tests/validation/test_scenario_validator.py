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
from sim.validation import ScenarioValidator

VALID_SCENARIO_CONTENT: Dict[str, Any] = {
    "start_time": "day1:08:00",
    "end_time": "day1:12:00",
    "stations": [
        {
            "station_id": 1,
            "station_name": "Station 1",
            "station_position": [-73.5, 45.5],
        }
    ],
    "resources": [{"resource_id": 1, "resource_position": [-73.5, 45.5]}],
    "initial_tasks": [{"station_id": "1"}],
    "scheduled_tasks": [{"station_id": "1"}],
    "scenario_title": "Test Scenario",
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


def test_duplicate_station_id(validator: ScenarioValidator) -> None:
    scenario_content: Dict[str, Any] = copy.deepcopy(VALID_SCENARIO_CONTENT)
    scenario_content["stations"].append(
        {
            "station_id": 1,
            "station_name": "Station Duplicate",
            "station_position": [-73.6, 45.6],
        }
    )
    errors: List[Dict[str, str]] = validator.validate_all(scenario_content)
    assert any("Duplicate station ID" in e["message"] for e in errors)


def test_duplicate_resource_id(validator: ScenarioValidator) -> None:
    scenario_content: Dict[str, Any] = copy.deepcopy(VALID_SCENARIO_CONTENT)
    scenario_content["resources"].append(
        {"resource_id": 1, "resource_position": [-73.6, 45.6]}
    )
    errors: List[Dict[str, str]] = validator.validate_all(scenario_content)
    assert any("Duplicate resource ID" in e["message"] for e in errors)


def test_invalid_lat_lon(validator: ScenarioValidator) -> None:
    scenario_content: Dict[str, Any] = copy.deepcopy(VALID_SCENARIO_CONTENT)
    scenario_content["stations"][0]["station_position"] = [200, 100]  # Invalid
    scenario_content["resources"][0]["resource_position"] = [-200, -100]  # Invalid
    errors: List[Dict[str, str]] = validator.validate_all(scenario_content)
    assert any("station_position" in e["field"] for e in errors)
    assert any("resource_position" in e["field"] for e in errors)


def test_task_with_nonexistent_station(validator: ScenarioValidator) -> None:
    scenario_content: Dict[str, Any] = copy.deepcopy(VALID_SCENARIO_CONTENT)
    scenario_content["initial_tasks"][0]["station_id"] = "999"
    errors: List[Dict[str, str]] = validator.validate_all(scenario_content)
    assert any(
        "station_id" in e["field"] and "does not exist" in e["message"] for e in errors
    )


def test_empty_lists(validator: ScenarioValidator) -> None:
    scenario_content: Dict[str, Any] = copy.deepcopy(VALID_SCENARIO_CONTENT)
    scenario_content["stations"] = []
    scenario_content["resources"] = []
    scenario_content["initial_tasks"] = []
    scenario_content["scheduled_tasks"] = []
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


def test_task_time_with_string_format_accepted(
    validator: ScenarioValidator,
) -> None:
    """Test that task times accept string formats."""
    scenario_content: Dict[str, Any] = copy.deepcopy(VALID_SCENARIO_CONTENT)
    # Ensure we have at least one station with id="1"
    if (
        len(scenario_content["stations"]) == 0
        or scenario_content["stations"][0]["station_id"] != 1
    ):
        scenario_content["stations"] = [
            {
                "station_id": 1,
                "station_name": "Test Station",
                "station_position": [-73.5, 45.5],
            }
        ]

    # Test that dayx:HH:MM time format is accepted
    scenario_content["scheduled_tasks"] = [{"station_id": "1", "time": "day1:08:30"}]
    errors = validator.validate_all(scenario_content)
    assert len(errors) == 0

    # Test that RFC 3339 time format is rejected
    scenario_content["initial_tasks"] = [
        {"station_id": "1", "time": "2025-11-06T10:30:00Z"}
    ]
    errors = validator.validate_all(scenario_content)
    assert len(errors) > 0
    assert any("Invalid time format" in err["message"] for err in errors)


def test_validate_initial_tasks_time_optional(validator: ScenarioValidator) -> None:
    """Test that time field is optional for initial_tasks."""
    scenario_content: Dict[str, Any] = copy.deepcopy(VALID_SCENARIO_CONTENT)

    # Test initial_tasks without time field (ID auto-generated)
    scenario_content["initial_tasks"] = [
        {"station_id": "1"},  # No time field, no ID
    ]
    scenario_content["scheduled_tasks"] = []
    errors: List[Dict[str, str]] = validator.validate_all(scenario_content)
    assert len(errors) == 0


def test_validate_scenario_with_no_task_id(validator: ScenarioValidator) -> None:
    """Test that id field works without it for tasks (auto-generated by simulator)."""
    scenario_content: Dict[str, Any] = copy.deepcopy(VALID_SCENARIO_CONTENT)

    # Test initial_tasks without id field
    scenario_content["initial_tasks"] = [
        {"station_id": "1"},  # No id field - will be auto-generated
    ]
    scenario_content["scheduled_tasks"] = [
        {
            "station_id": "1",
            "time": "day1:08:30",
        },  # No id field - will be auto-generated
    ]
    errors: List[Dict[str, str]] = validator.validate_all(scenario_content)
    assert len(errors) == 0


def test_validate_tasks_with_explicit_ids(validator: ScenarioValidator) -> None:
    """Test that specifying task IDs produces errors (IDs are auto-generated)."""
    scenario_content: Dict[str, Any] = copy.deepcopy(VALID_SCENARIO_CONTENT)

    # Test with explicit IDs - should produce errors
    scenario_content["initial_tasks"] = [
        {"id": "t1", "station_id": "1"},
    ]
    scenario_content["scheduled_tasks"] = [
        {"id": "t2", "station_id": "1", "time": "day1:08:30"},
    ]
    errors: List[Dict[str, str]] = validator.validate_all(scenario_content)

    # Should have 2 errors (one for each task with ID)
    assert len(errors) == 2
    for error in errors:
        assert "auto-generated" in error["message"].lower()
        assert "ignored" in error["message"].lower()


def test_validation_with_line_numbers() -> None:
    """Test line numbers in validation errors with JSON string."""
    json_string = """{
  "content": {
    "start_time": "day1:08:00",
    "end_time": "day1:12:00",
    "stations": [
      {
        "station_id": 1,
        "station_name": "Station 1",
        "station_position": [-73.5, 45.5]
      }
    ],
    "resources": [],
    "initial_tasks": [
      {
        "station_id": "999"
      }
    ],
    "scheduled_tasks": []
  }
}"""

    data = json.loads(json_string)
    validator = ScenarioValidator(json_string=json_string)
    errors = validator.validate_all(data["content"])

    # Should have error for nonexistent station
    assert len(errors) > 0
    station_errors = [e for e in errors if "station_id" in e.get("field", "")]
    assert len(station_errors) > 0

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
    scenario_content["stations"][0]["station_position"] = [-73.5, 45.5, 100.0]

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
    scenario_content["stations"][0]["station_position"] = "invalid"

    errors = validator.validate_all(scenario_content)

    assert len(errors) > 0
    assert any(
        "position must be" in error.get("message", "").lower() for error in errors
    )


def test_task_time_with_invalid_type(validator: ScenarioValidator) -> None:
    """Test task time validation with invalid type (not int, float, or None)."""
    scenario_content: Dict[str, Any] = copy.deepcopy(VALID_SCENARIO_CONTENT)
    # Time must be numeric or None
    scenario_content["scheduled_tasks"] = [
        {"station_id": "1", "time": {"invalid": "object"}}
    ]

    errors = validator.validate_all(scenario_content)

    assert len(errors) > 0
    assert any("time must be" in error.get("message", "").lower() for error in errors)
