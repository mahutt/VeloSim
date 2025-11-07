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
from datetime import datetime
from typing import Any, Dict, List
from back.services.scenario_validation_service import ScenarioValidator

VALID_SCENARIO: Dict[str, Any] = {
    "id": 1,
    "name": "Test Scenario",
    "content": {
        "start_time": "08:00",
        "end_time": "12:00",
        "stations": [
            {
                "station_id": 1,
                "station_name": "Station 1",
                "task_count": 2,
                "station_position": [45.5, -73.5],
            }
        ],
        "resources": [
            {"resource_id": 1, "task_count": 2, "resource_position": [45.5, -73.5]}
        ],
        "initial_tasks": [{"id": "t1", "station_id": "1"}],
        "scheduled_tasks": [{"id": "t2", "station_id": "1"}],
        "scenario_title": "Test Scenario",
    },
    "description": "A valid scenario",
    "user_id": 1,
    "date_created": datetime.now(),
    "date_updated": datetime.now(),
}


@pytest.fixture
def validator() -> ScenarioValidator:
    """Fixture to provide a ScenarioValidator instance."""
    return ScenarioValidator()


def test_valid_scenario(validator: ScenarioValidator) -> None:
    errors: List[Dict[str, str]] = validator.validate_all(VALID_SCENARIO)
    assert errors == [], f"Expected no errors, got: {errors}"


def test_missing_required_fields(validator: ScenarioValidator) -> None:
    scenario: Dict[str, Any] = {}
    errors: List[Dict[str, str]] = validator.validate_all(scenario)
    assert any(e["field"] == "id" for e in errors)
    assert any(e["field"] == "name" for e in errors)
    assert any(e["field"] == "content" for e in errors)


def test_invalid_time_format(validator: ScenarioValidator) -> None:
    scenario: Dict[str, Any] = VALID_SCENARIO.copy()
    scenario["content"]["start_time"] = "8AM"
    scenario["content"]["end_time"] = "1200"
    errors: List[Dict[str, str]] = validator.validate_all(scenario)
    assert any("start_time" in e["field"] for e in errors)
    assert any("end_time" in e["field"] for e in errors)


def test_end_time_before_start_time(validator: ScenarioValidator) -> None:
    scenario: Dict[str, Any] = VALID_SCENARIO.copy()
    scenario["content"]["start_time"] = "12:00"
    scenario["content"]["end_time"] = "08:00"
    errors: List[Dict[str, str]] = validator.validate_all(scenario)
    assert any(e["field"] == "end_time" and "after" in e["message"] for e in errors)


def test_duplicate_station_id(validator: ScenarioValidator) -> None:
    scenario: Dict[str, Any] = VALID_SCENARIO.copy()
    scenario["content"]["stations"].append(
        {
            "station_id": 1,
            "station_name": "Station Duplicate",
            "task_count": 1,
            "station_position": [45.6, -73.6],
        }
    )
    errors: List[Dict[str, str]] = validator.validate_all(scenario)
    assert any("Duplicate station ID" in e["message"] for e in errors)


def test_duplicate_resource_id(validator: ScenarioValidator) -> None:
    scenario: Dict[str, Any] = VALID_SCENARIO.copy()
    scenario["content"]["resources"].append(
        {"resource_id": 1, "task_count": 1, "resource_position": [45.6, -73.6]}
    )
    errors: List[Dict[str, str]] = validator.validate_all(scenario)
    assert any("Duplicate resource ID" in e["message"] for e in errors)


def test_invalid_lat_lon(validator: ScenarioValidator) -> None:
    scenario: Dict[str, Any] = VALID_SCENARIO.copy()
    scenario["content"]["stations"][0]["station_position"] = [100, 200]  # Invalid
    scenario["content"]["resources"][0]["resource_position"] = [-100, -200]  # Invalid
    errors: List[Dict[str, str]] = validator.validate_all(scenario)
    assert any("station_position" in e["field"] for e in errors)
    assert any("resource_position" in e["field"] for e in errors)


def test_task_with_nonexistent_station(validator: ScenarioValidator) -> None:
    scenario: Dict[str, Any] = VALID_SCENARIO.copy()
    scenario["content"]["initial_tasks"][0]["station_id"] = "999"
    errors: List[Dict[str, str]] = validator.validate_all(scenario)
    assert any(
        "station_id" in e["field"] and "does not exist" in e["message"] for e in errors
    )


def test_empty_lists(validator: ScenarioValidator) -> None:
    scenario: Dict[str, Any] = VALID_SCENARIO.copy()
    scenario["content"]["stations"] = []
    scenario["content"]["resources"] = []
    scenario["content"]["initial_tasks"] = []
    scenario["content"]["scheduled_tasks"] = []
    errors: List[Dict[str, str]] = validator.validate_all(scenario)
    assert isinstance(errors, list)


def test_missing_content_key(validator: ScenarioValidator) -> None:
    scenario: Dict[str, Any] = VALID_SCENARIO.copy()
    scenario.pop("content")
    errors: List[Dict[str, str]] = validator.validate_all(scenario)
    assert any(e["field"] == "content" for e in errors)


def test_rfc3339_datetime_format(validator: ScenarioValidator) -> None:
    """Test that RFC 3339 / ISO 8601 datetime strings are accepted."""
    scenario: Dict[str, Any] = VALID_SCENARIO.copy()
    # Use RFC 3339 format with timezone
    scenario["content"]["start_time"] = "2025-11-06T08:00:00Z"
    scenario["content"]["end_time"] = "2025-11-06T17:00:00Z"
    errors: List[Dict[str, str]] = validator.validate_all(scenario)
    assert len(errors) == 0


def test_multi_day_scenario(validator: ScenarioValidator) -> None:
    """Test that scenarios exceeding 24 hours are rejected."""
    scenario: Dict[str, Any] = VALID_SCENARIO.copy()
    # Start on one day, end on the next (more than 24 hours)
    scenario["content"]["start_time"] = "2025-11-06T08:00:00Z"
    scenario["content"]["end_time"] = "2025-11-07T08:00:01Z"  # 24 hours and 1 second
    errors: List[Dict[str, str]] = validator.validate_all(scenario)
    assert any("cannot exceed 24 hours" in e["message"] for e in errors)


def test_exactly_24_hours_allowed(validator: ScenarioValidator) -> None:
    """Test that scenarios of exactly 24 hours are allowed."""
    scenario: Dict[str, Any] = VALID_SCENARIO.copy()
    scenario["content"]["start_time"] = "2025-11-06T08:00:00Z"
    scenario["content"]["end_time"] = "2025-11-07T08:00:00Z"  # Exactly 24 hours
    errors: List[Dict[str, str]] = validator.validate_all(scenario)
    assert len(errors) == 0


def test_datetime_with_seconds(validator: ScenarioValidator) -> None:
    """Test that datetime strings with seconds precision are accepted."""
    scenario: Dict[str, Any] = VALID_SCENARIO.copy()
    scenario["content"]["start_time"] = "2025-11-06T08:00:00Z"
    scenario["content"]["end_time"] = "2025-11-06T17:30:45Z"
    errors: List[Dict[str, str]] = validator.validate_all(scenario)
    assert len(errors) == 0


def test_simple_time_format_still_works(validator: ScenarioValidator) -> None:
    """Test backward compatibility with simple HH:MM format."""
    scenario: Dict[str, Any] = VALID_SCENARIO.copy()
    scenario["content"]["start_time"] = "08:00"
    scenario["content"]["end_time"] = "17:00"
    errors: List[Dict[str, str]] = validator.validate_all(scenario)
    assert len(errors) == 0


def test_task_time_with_rfc3339(validator: ScenarioValidator) -> None:
    """Test that task times support RFC 3339 format."""
    import copy

    scenario: Dict[str, Any] = copy.deepcopy(VALID_SCENARIO)
    # Ensure we have at least one station with id="1"
    if (
        len(scenario["content"]["stations"]) == 0
        or scenario["content"]["stations"][0]["station_id"] != 1
    ):
        scenario["content"]["stations"] = [
            {
                "station_id": 1,
                "station_name": "Test Station",
                "task_count": 2,
                "station_position": [45.5, -73.5],
            }
        ]

    # Add task with RFC 3339 time format
    scenario["content"]["initial_tasks"] = [
        {"id": "t1", "station_id": "1", "time": "2025-11-06T10:30:00Z"}
    ]
    errors: List[Dict[str, str]] = validator.validate_all(scenario)
    assert len(errors) == 0
