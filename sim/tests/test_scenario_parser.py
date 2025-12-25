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
from sim.utils.base_parse_strategy import BaseParseStrategy
from sim.utils.json_parser_strategy import JsonParseStrategy, ScenarioParseError
from sim.entities.inputParameters import InputParameter
from sim.entities.driver import Driver
from sim.entities.vehicle import Vehicle
from sim.utils.scenario_parser import ScenarioParser


def test_base_parse_strategy_is_abstract() -> None:
    class DummyStrategy(BaseParseStrategy):
        pass

    with pytest.raises(TypeError):
        DummyStrategy()  # type: ignore[abstract]


def test_json_parse_strategy_valid_input() -> None:
    scenario_json = {
        "id": 1,
        "name": "Test Scenario",
        "content": {
            "start_time": "day1:08:00",
            "end_time": "day1:12:00",
            "vehicle_battery_capacity": 999,
            "stations": [
                {
                    "name": "Station 1",
                    "initial_task_count": 2,
                    "scheduled_tasks": ["day1:09:30"],
                    "position": [45.5, -73.5],
                },
                {
                    "name": "Station 2",
                    "initial_task_count": 0,
                    "scheduled_tasks": ["day1:09:30"],
                    "position": [45.501, -73.55],
                },
                {
                    "name": "Station 3",
                    "initial_task_count": 0,
                    "scheduled_tasks": [],
                    "position": [45.511, -73.56],
                },
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
            "vehicles": [
                {
                    "name": "Vehicle 1",
                    "position": [-73.5610, 45.5070],
                    "battery_count": 999,
                }
            ],
        },
    }

    strategy = JsonParseStrategy(scenario_json=scenario_json)
    params: InputParameter = strategy.parse()

    assert isinstance(params, InputParameter)
    assert len(params.station_entities) == 3
    assert len(params.driver_entities) == 1
    assert len(params.vehicle_entities) == 1
    assert len(params.task_entities) == 4

    tasks = params.task_entities
    stations = params.station_entities
    drivers = params.driver_entities
    vehicles = params.vehicle_entities

    # With new schema, station IDs are auto-generated sequentially (1..n)
    # Scenario defines: Station 1 has 2 initial tasks and 1 scheduled at 09:30,
    # Station 2 has 1 scheduled at 09:30 -> total 4 tasks
    assert tasks[1].get_station() == stations[1]  # First task (initial, Station 1)
    assert tasks[2].get_station() == stations[1]  # Second task (initial, Station 1)
    assert tasks[3].get_station() == stations[1]  # Third task (scheduled, Station 1)
    assert tasks[4].get_station() == stations[2]  # Fourth task (scheduled, Station 2)

    # Check spawn delays
    assert tasks[1].spawn_delay == 0  # Initial task
    assert tasks[2].spawn_delay == 0  # Initial task
    # Scheduled at 09:30 with start at 08:00 => 1.5 hours (5400 seconds)
    assert tasks[3].spawn_delay == 90 * 60
    assert tasks[4].spawn_delay == 90 * 60

    for drv in drivers.values():
        assert isinstance(drv, Driver)
        assert isinstance(drv.task_list, list)
    for veh in vehicles.values():
        assert isinstance(veh, Vehicle)


def test_json_parse_strategy_invalid_json() -> None:
    # String instead of dict should fail
    strategy = JsonParseStrategy(
        scenario_json="string_instead_of_dict"  # type: ignore[arg-type]
    )
    with pytest.raises((AttributeError, ValueError)):
        strategy.parse()


def test_json_parse_strategy_with_invalid_time() -> None:
    """Test that invalid time formats now raise ScenarioParseError."""
    scenario_json_with_bad_time_format = {
        "id": 1,
        "name": "Test Scenario",
        "content": {
            "start_time": "day1:00:00",
            "end_time": "day2:01",  # invalid time format
            "vehicle_battery_capacity": 999,
            "stations": [
                {
                    "name": "Lionel-Groulx",
                    "position": [-74.0060, 40.7128],
                    "initial_task_count": 1,
                    "scheduled_tasks": [],
                },
                {
                    "name": "Guy-Concordia",
                    "position": [-118.2437, 34.0522],
                    "initial_task_count": 0,
                    "scheduled_tasks": ["day1:05:00"],
                },
                {
                    "name": "Peel",
                    "position": [-87.6298, 41.8781],
                    "initial_task_count": 0,
                    "scheduled_tasks": ["day1:08:00"],
                },
            ],
            "vehicles": [
                {
                    "name": "Vehicle 1",
                    "position": [-73.5610, 45.5070],
                    "battery_count": 999,
                },
                {
                    "name": "Vehicle 2",
                    "position": [-73.5670, 45.5090],
                    "battery_count": 999,
                },
            ],
            "drivers": [
                {
                    "name": "Driver 1",
                    "shift": {
                        "start_time": "day1:00:00",
                        "end_time": "day1:12:00",
                        "lunch_break": "day1:06:00",
                    },
                },
                {
                    "name": "Driver 2",
                    "shift": {
                        "start_time": "day1:00:00",
                        "end_time": "day1:12:00",
                        "lunch_break": "day1:06:00",
                    },
                },
            ],
        },
    }

    strategy = JsonParseStrategy(scenario_json=scenario_json_with_bad_time_format)
    # Now validation catches the invalid time format and raises an exception
    with pytest.raises(ScenarioParseError) as exc_info:
        strategy.parse()

    # Verify the error contains information about the invalid time
    assert "end_time" in str(exc_info.value) or "time" in str(exc_info.value).lower()


def test_json_parse_strategy_validate_without_parsing() -> None:
    """Test that validate method can check scenarios without parsing."""
    valid_scenario = {
        "start_time": "day1:00:00",
        "end_time": "day1:01:00",
        "vehicle_battery_capacity": 999,
        "stations": [
            {
                "name": "Test Station",
                "position": [-74.0060, 40.7128],
                "initial_task_count": 1,
                "scheduled_tasks": [],
            }
        ],
        "vehicles": [
            {"name": "Vehicle 1", "position": [-73.5610, 45.5070], "battery_count": 2}
        ],
        "drivers": [
            {
                "name": "Driver 1",
                "shift": {
                    "start_time": "day1:00:00",
                    "end_time": "day1:01:00",
                    "lunch_break": "day1:00:30",
                },
            }
        ],
    }

    invalid_scenario = {
        "start_time": "day1:00:00",
        "end_time": "invalid_time",  # Invalid format
        "vehicle_battery_capacity": 999,
        "stations": [],
        "vehicles": [],
        "drivers": [],
    }

    strategy = JsonParseStrategy(scenario_json=valid_scenario)

    # Valid scenario should return no errors
    errors = strategy.validate()
    assert len(errors) == 0

    # Invalid scenario should return errors
    strategy_invalid = JsonParseStrategy(scenario_json=invalid_scenario)
    errors = strategy_invalid.validate()
    assert len(errors) > 0
    assert any("time" in str(err).lower() for err in errors)


def test_scenario_parser_delegates_to_strategy() -> None:
    fake_input_param = InputParameter({}, {}, {})

    class MockStrategy(BaseParseStrategy):
        def __init__(self) -> None:
            self.called: bool = False

        def parse(self, scenario_json: dict) -> InputParameter:
            self.called = True
            assert scenario_json == "input"  # type: ignore[comparison-overlap]
            return fake_input_param

    mock_strategy = MockStrategy()
    parser = ScenarioParser(mock_strategy)
    result = parser.parse("input")  # type: ignore[arg-type]

    assert mock_strategy.called
    assert result is fake_input_param
