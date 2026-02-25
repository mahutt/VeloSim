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
from sim.entities.input_parameter import InputParameter
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
        "start_time": "day1:08:00",
        "end_time": "day1:12:00",
        "vehicle_battery_capacity": 999,
        "stations": [
            {
                "name": "Station 1",
                "initial_task_count": 2,
                "scheduled_tasks": ["day1:09:30"],
                "position": [-73.5, 45.5],
            },
            {
                "name": "Station 2",
                "initial_task_count": 0,
                "scheduled_tasks": ["day1:09:30"],
                "position": [-73.55, 45.501],
            },
            {
                "name": "Station 3",
                "initial_task_count": 0,
                "scheduled_tasks": [],
                "position": [-73.56, 45.511],
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
    }

    strategy = JsonParseStrategy(scenario_json=scenario_json)
    params: InputParameter = strategy.parse()

    assert isinstance(params, InputParameter)
    assert len(params.station_entities) == 3
    assert len(params.driver_entities) == 1
    assert len(params.vehicle_entities) == 1
    assert len(params.task_entities) == 2

    tasks = params.task_entities
    stations = params.station_entities
    drivers = params.driver_entities
    vehicles = params.vehicle_entities

    # With new refactored approach:
    # - Initial tasks (2 from Station 1) are created immediately with IDs 1, 2
    # - Scheduled tasks are NOT in task_entities until they pop up during simulation
    assert tasks[1].get_station() == stations[1]  # First task (initial, Station 1)
    assert tasks[2].get_station() == stations[1]  # Second task (initial, Station 1)

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
    with pytest.raises((AttributeError, ValueError, TypeError)):
        strategy.parse()


def test_json_parse_strategy_with_invalid_time() -> None:
    """Test that invalid time formats now raise ScenarioParseError."""
    scenario_json_with_bad_time_format = {
        "start_time": "day1:00:00",
        "end_time": "day2:01",  # invalid time format
        "vehicle_battery_capacity": 999,
        "stations": [
            {
                "name": "Lionel-Groulx",
                "position": [-73.58, 45.48],
                "initial_task_count": 1,
                "scheduled_tasks": [],
            },
            {
                "name": "Guy-Concordia",
                "position": [-73.57, 45.49],
                "initial_task_count": 0,
                "scheduled_tasks": ["day1:05:00"],
            },
            {
                "name": "Peel",
                "position": [-73.57, 45.50],
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
    }

    strategy = JsonParseStrategy(scenario_json=scenario_json_with_bad_time_format)
    # Now validation catches the invalid time format and raises an exception
    with pytest.raises(ScenarioParseError) as exc_info:
        strategy.parse()

    # Verify the error contains information about the invalid time
    assert "end_time" in str(exc_info.value) or "time" in str(exc_info.value).lower()


def test_json_parse_with_no_lunch_break_and_long_shift() -> None:
    scenario_json = {
        "start_time": "day1:08:00",
        "end_time": "day1:12:00",
        "vehicle_battery_capacity": 50,
        "stations": [
            {
                "name": "Station 1",
                "initial_task_count": 2,
                "scheduled_tasks": ["day1:09:30"],
                "position": [-73.5, 45.5],
            },
            {
                "name": "Station 2",
                "initial_task_count": 0,
                "scheduled_tasks": ["day1:09:30"],
                "position": [-73.55, 45.501],
            },
            {
                "name": "Station 3",
                "initial_task_count": 0,
                "scheduled_tasks": [],
                "position": [-73.56, 45.511],
            },
        ],
        "drivers": [
            {
                "name": "Driver 1",
                "shift": {"start_time": "day1:07:00", "end_time": "day1:15:00"},
            }
        ],
        "vehicles": [
            {
                "name": "Vehicle 1",
                "position": [-73.5610, 45.5070],
                "battery_count": 20,
            }
        ],
    }

    strategy = JsonParseStrategy(scenario_json=scenario_json)
    sim_start = strategy._time_to_seconds("day1:08:00")
    st_sec = strategy._time_to_seconds("day1:07:00")
    et_sec = strategy._time_to_seconds("day1:15:00")
    params: InputParameter = strategy.parse()

    assert isinstance(params, InputParameter)
    drivers = params.get_driver_entities()
    first_driver_key = next(iter(drivers))
    driver = drivers[first_driver_key]

    lunch_break = driver.get_driver_shift().get_lunch_break()
    sim_lunch_break = driver.get_driver_shift().get_sim_lunch_break()
    calculated_lunch = round((st_sec + et_sec) / 2)
    assert lunch_break == calculated_lunch
    assert sim_lunch_break == calculated_lunch - sim_start


def test_json_parse_with_lunch_break_assigned_before_sim_time() -> None:
    scenario_json = {
        "start_time": "day1:12:00",
        "end_time": "day1:16:00",
        "vehicle_battery_capacity": 50,
        "stations": [
            {
                "name": "Station 1",
                "initial_task_count": 2,
                "scheduled_tasks": ["day1:09:30"],
                "position": [-73.5, 45.5],
            },
            {
                "name": "Station 2",
                "initial_task_count": 0,
                "scheduled_tasks": ["day1:09:30"],
                "position": [-73.55, 45.501],
            },
            {
                "name": "Station 3",
                "initial_task_count": 0,
                "scheduled_tasks": [],
                "position": [-73.56, 45.511],
            },
        ],
        "drivers": [
            {
                "name": "Driver 1",
                "shift": {"start_time": "day1:08:00", "end_time": "day1:14:00"},
            }
        ],
        "vehicles": [
            {
                "name": "Vehicle 1",
                "position": [-73.5610, 45.5070],
                "battery_count": 20,
            }
        ],
    }

    strategy = JsonParseStrategy(scenario_json=scenario_json)
    sim_start = strategy._time_to_seconds("day1:12:00")
    st_sec = strategy._time_to_seconds("day1:08:00")
    et_sec = strategy._time_to_seconds("day1:14:00")
    params: InputParameter = strategy.parse()

    assert isinstance(params, InputParameter)
    drivers = params.get_driver_entities()
    first_driver_key = next(iter(drivers))
    driver = drivers[first_driver_key]

    lunch_break = driver.get_driver_shift().get_lunch_break()
    calculated_lunch = round((st_sec + et_sec) / 2)
    assert lunch_break == calculated_lunch
    assert calculated_lunch < sim_start


def test_json_parse_with_no_lunch_break_and_short_shift() -> None:
    scenario_json = {
        "start_time": "day1:08:00",
        "end_time": "day1:12:00",
        "vehicle_battery_capacity": 50,
        "stations": [
            {
                "name": "Station 1",
                "initial_task_count": 2,
                "scheduled_tasks": ["day1:09:30"],
                "position": [-73.5, 45.5],
            },
            {
                "name": "Station 2",
                "initial_task_count": 0,
                "scheduled_tasks": ["day1:09:30"],
                "position": [-73.55, 45.501],
            },
            {
                "name": "Station 3",
                "initial_task_count": 0,
                "scheduled_tasks": [],
                "position": [-73.56, 45.511],
            },
        ],
        "drivers": [
            {
                "name": "Driver 1",
                "shift": {"start_time": "day1:08:00", "end_time": "day1:11:00"},
            }
        ],
        "vehicles": [
            {
                "name": "Vehicle 1",
                "position": [-73.5610, 45.5070],
                "battery_count": 20,
            }
        ],
    }

    strategy = JsonParseStrategy(scenario_json=scenario_json)
    params: InputParameter = strategy.parse()

    assert isinstance(params, InputParameter)
    drivers = params.get_driver_entities()
    first_driver_key = next(iter(drivers))
    driver = drivers[first_driver_key]

    lunch_break = driver.get_driver_shift().get_lunch_break()
    assert lunch_break is None


def test_json_parse_with_no_lunch_break_and_short_sim_duration() -> None:
    scenario_json = {
        "start_time": "day1:08:00",
        "end_time": "day1:08:30",
        "vehicle_battery_capacity": 50,
        "stations": [
            {
                "name": "Station 1",
                "initial_task_count": 2,
                "scheduled_tasks": ["day1:08:05"],
                "position": [-73.5, 45.5],
            },
            {
                "name": "Station 2",
                "initial_task_count": 0,
                "scheduled_tasks": ["day1:08:10"],
                "position": [-73.55, 45.501],
            },
            {
                "name": "Station 3",
                "initial_task_count": 0,
                "scheduled_tasks": [],
                "position": [-73.56, 45.511],
            },
        ],
        "drivers": [
            {
                "name": "Driver 1",
                "shift": {"start_time": "day1:08:00", "end_time": "day1:11:00"},
            }
        ],
        "vehicles": [
            {
                "name": "Vehicle 1",
                "position": [-73.5610, 45.5070],
                "battery_count": 20,
            }
        ],
    }

    strategy = JsonParseStrategy(scenario_json=scenario_json)
    params: InputParameter = strategy.parse()

    assert isinstance(params, InputParameter)
    drivers = params.get_driver_entities()
    first_driver_key = next(iter(drivers))
    driver = drivers[first_driver_key]

    lunch_break = driver.get_driver_shift().get_lunch_break()
    assert lunch_break is None


def test_json_parse_strategy_validate_without_parsing() -> None:
    """Test that validate method can check scenarios without parsing."""
    valid_scenario = {
        "start_time": "day1:00:00",
        "end_time": "day1:01:00",
        "vehicle_battery_capacity": 999,
        "stations": [
            {
                "name": "Test Station",
                "position": [-73.58, 45.48],
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
