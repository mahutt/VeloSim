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

from unittest.mock import Mock
import pytest
from sim.utils.replay_parser import ReplayParser


def test_replay_parser_parse_minimal_valid_replay() -> None:
    from sim.utils.replay_parser import ReplayParser
    from sim.entities.input_parameter import InputParameter
    from sim.entities.task_state import State
    from sim.entities.driver import DriverState

    scenario_json = {
        "start_time": "08:00",
        "end_time": "10:00",
    }

    keyframe_json = {
        "clock": {
            "simSecondsPassed": 1800,
            "startTime": 0,
        },
        "stations": [{"id": 1, "name": "Station A", "position": [0.0, 0.0]}],
        "vehicles": [{"id": 100, "batteryCount": 5}],
        "drivers": [
            {
                "id": 10,
                "name": "alfa",
                "position": [1.0, 1.0],
                "state": "idle",
                "vehicleId": 100,
                "taskIds": [],
                "route": None,
                "shift": {
                    "startTime": 0,
                    "endTime": 7200,
                    "lunchBreak": None,
                },
            }
        ],
        "tasks": [{"id": 500, "stationId": 1, "state": "open"}],
    }

    state = ReplayParser.parse(
        scenario_json=scenario_json,
        keyframe_json=keyframe_json,
    )

    # --- core assertions ---
    assert isinstance(state.input_parameters, InputParameter)
    assert state.current_time_seconds == 1800

    input_param = state.input_parameters

    station = next(iter(input_param.station_entities.values()))
    task = station.tasks[0]
    assert task.state == State.OPEN

    driver = next(iter(input_param.driver_entities.values()))
    assert driver.state == DriverState.IDLE


def test_replay_parser_extracts_playback_state_fields() -> None:
    """Test that ReplayParser extracts was_running, real_time_factor, and paused_by_user
    from keyframe."""
    from sim.utils.replay_parser import ReplayParser

    scenario_json = {
        "start_time": "08:00",
        "end_time": "10:00",
    }

    keyframe_json = {
        "clock": {
            "simSecondsPassed": 1800,
            "startTime": 0,
            "running": False,
            "realTimeFactor": 0.5,
            "pausedByUser": True,
        },
        "stations": [],
        "vehicles": [],
        "drivers": [],
        "tasks": [],
    }

    state = ReplayParser.parse(
        scenario_json=scenario_json,
        keyframe_json=keyframe_json,
    )

    assert state.was_running is False
    assert state.real_time_factor == 0.5
    assert state.paused_by_user is True


def test_replay_parser_restores_service_context() -> None:
    from sim.utils.replay_parser import ReplayParser

    scenario_json = {
        "start_time": "08:00",
        "end_time": "10:00",
    }

    keyframe_json = {
        "clock": {
            "simSecondsPassed": 1800,
            "startTime": 0,
        },
        "stations": [{"id": 1, "name": "Station A", "position": [0.0, 0.0]}],
        "vehicles": [{"id": 100, "batteryCount": 5}],
        "drivers": [
            {
                "id": 10,
                "name": "alfa",
                "position": [0.0, 0.0],
                "state": "servicing_station",
                "vehicleId": 100,
                "taskIds": [500],
                "route": None,
                "serviceChainStationId": 1,
                "shift": {
                    "startTime": 0,
                    "endTime": 7200,
                    "lunchBreak": None,
                },
            }
        ],
        "tasks": [
            {
                "id": 500,
                "stationId": 1,
                "state": "inservice",
                "assignedDriverId": 10,
                "serviceTimeRemaining": 37,
            }
        ],
    }

    state = ReplayParser.parse(
        scenario_json=scenario_json,
        keyframe_json=keyframe_json,
    )

    driver = next(iter(state.input_parameters.driver_entities.values()))
    task = next(iter(state.input_parameters.task_entities.values()))

    assert driver.service_chain_station_id == 1
    assert task.service_time_remaining == 37


def test_replay_parser_playback_fields_fallback_defaults() -> None:
    """Test that ReplayParser uses correct fallback defaults for missing playback
    fields."""
    from sim.utils.replay_parser import ReplayParser

    scenario_json = {
        "start_time": "08:00",
        "end_time": "10:00",
    }

    # Keyframe without playback fields
    keyframe_json = {
        "clock": {
            "simSecondsPassed": 1800,
            "startTime": 0,
        },
        "stations": [],
        "vehicles": [],
        "drivers": [],
        "tasks": [],
    }

    state = ReplayParser.parse(
        scenario_json=scenario_json,
        keyframe_json=keyframe_json,
    )

    # Should default to running=True, realTimeFactor=1.0, pausedByUser=False
    assert state.was_running is True
    assert state.real_time_factor == 1.0
    assert state.paused_by_user is False


def test_replay_parser_should_auto_resume_when_not_paused_by_user() -> None:
    """Test that should_auto_resume returns True when paused_by_user=False."""
    from sim.utils.replay_parser import ReplayParser

    scenario_json = {
        "start_time": "08:00",
        "end_time": "10:00",
    }

    keyframe_json = {
        "clock": {
            "simSecondsPassed": 1800,
            "startTime": 0,
            "pausedByUser": False,
        },
        "stations": [],
        "vehicles": [],
        "drivers": [],
        "tasks": [],
    }

    state = ReplayParser.parse(
        scenario_json=scenario_json,
        keyframe_json=keyframe_json,
    )

    assert state.paused_by_user is False
    assert state.should_auto_resume is True


def test_replay_parser_should_not_auto_resume_when_paused_by_user() -> None:
    """Test that should_auto_resume returns False when paused_by_user=True."""
    from sim.utils.replay_parser import ReplayParser

    scenario_json = {
        "start_time": "08:00",
        "end_time": "10:00",
    }

    keyframe_json = {
        "clock": {
            "simSecondsPassed": 1800,
            "startTime": 0,
            "pausedByUser": True,
        },
        "stations": [],
        "vehicles": [],
        "drivers": [],
        "tasks": [],
    }

    state = ReplayParser.parse(
        scenario_json=scenario_json,
        keyframe_json=keyframe_json,
    )

    assert state.paused_by_user is True
    assert state.should_auto_resume is False


def test_replay_parser_extracts_traffic_config_from_scenario() -> None:
    """Test that ReplayParser extracts traffic config from scenario."""
    from sim.utils.replay_parser import ReplayParser

    scenario_json = {
        "start_time": "day1:08:00",
        "end_time": "day1:17:00",
        "traffic": {"traffic_level": "high_congestion"},
    }

    keyframe_json = {
        "clock": {
            "simSecondsPassed": 0,
            "startTime": 0,
        },
        "stations": [],
        "vehicles": [],
        "drivers": [],
        "tasks": [],
    }

    state = ReplayParser.parse(
        scenario_json=scenario_json,
        keyframe_json=keyframe_json,
    )

    assert state.input_parameters.map_payload is not None
    assert state.input_parameters.map_payload.traffic is not None
    assert state.input_parameters.map_payload.traffic.traffic_level == (
        "high_congestion"
    )
    assert state.input_parameters.map_payload.traffic.traffic_csv_data is None


def test_replay_parser_uses_in_memory_traffic_csv_data() -> None:
    """Test that ReplayParser uses persisted traffic CSV data for resume."""
    from sim.utils.replay_parser import ReplayParser

    scenario_json = {
        "start_time": "day1:08:00",
        "end_time": "day1:17:00",
        "traffic": {"traffic_level": "medium_congestion"},
    }

    keyframe_json = {
        "clock": {
            "simSecondsPassed": 1800,
            "startTime": 0,
        },
        "stations": [],
        "vehicles": [],
        "drivers": [],
        "tasks": [],
    }

    csv_data = (
        "TYPE,start_time,segment_key,name,duration,weight\n"
        'local_traffic,"08:00","((-73.5,45.5),(-73.6,45.6))",event,10,0.5\n'
    )

    state = ReplayParser.parse(
        scenario_json=scenario_json,
        keyframe_json=keyframe_json,
        traffic_csv_data=csv_data,
    )

    assert state.input_parameters.map_payload is not None
    assert state.input_parameters.map_payload.traffic is not None
    assert state.input_parameters.map_payload.traffic.traffic_csv_data == csv_data
    # Level is preserved but CSV data takes precedence
    assert state.input_parameters.map_payload.traffic.traffic_level == (
        "medium_congestion"
    )


def test_replay_parser_creates_traffic_config_from_csv_only() -> None:
    """Test backwards compat: create traffic config from CSV data even
    without traffic block."""
    from sim.utils.replay_parser import ReplayParser

    scenario_json = {
        "start_time": "day1:08:00",
        "end_time": "day1:17:00",
        # No traffic block in scenario
    }

    keyframe_json = {
        "clock": {
            "simSecondsPassed": 1800,
            "startTime": 0,
        },
        "stations": [],
        "vehicles": [],
        "drivers": [],
        "tasks": [],
    }

    csv_data = (
        "TYPE,start_time,segment_key,name,duration,weight\n"
        'local_traffic,"08:00","((-73.5,45.5),(-73.6,45.6))",event,10,0.5\n'
    )

    state = ReplayParser.parse(
        scenario_json=scenario_json,
        keyframe_json=keyframe_json,
        traffic_csv_data=csv_data,
    )

    assert state.input_parameters.map_payload is not None
    assert state.input_parameters.map_payload.traffic is not None
    assert state.input_parameters.map_payload.traffic.traffic_csv_data == csv_data
    assert state.input_parameters.map_payload.traffic.traffic_level == "default"


def test_replay_parser_no_traffic_when_no_config_or_csv() -> None:
    """Test that map_payload is None when no traffic config or CSV data."""
    from sim.utils.replay_parser import ReplayParser

    scenario_json = {
        "start_time": "day1:08:00",
        "end_time": "day1:17:00",
    }

    keyframe_json = {
        "clock": {
            "simSecondsPassed": 0,
            "startTime": 0,
        },
        "stations": [],
        "vehicles": [],
        "drivers": [],
        "tasks": [],
    }

    state = ReplayParser.parse(
        scenario_json=scenario_json,
        keyframe_json=keyframe_json,
        traffic_csv_data=None,
    )

    assert state.input_parameters.map_payload is None


def test_time_str_to_seconds_basic() -> None:

    assert ReplayParser._time_str_to_seconds("08:30") == 8 * 3600 + 30 * 60


def test_time_str_to_seconds_with_day() -> None:
    from sim.utils.replay_parser import ReplayParser

    # day2 = 1 day offset
    assert ReplayParser._time_str_to_seconds("day2:01:00") == (24 * 3600 + 1 * 3600)


def test_time_str_to_seconds_invalid_format() -> None:

    with pytest.raises(ValueError):
        ReplayParser._time_str_to_seconds("invalid")


def test_is_valid_coordinate_pair_valid() -> None:

    assert ReplayParser._is_valid_coordinate_pair([1.0, 2.0]) is True
    assert ReplayParser._is_valid_coordinate_pair((1, 2)) is True


def test_is_valid_coordinate_pair_invalid() -> None:
    from sim.utils.replay_parser import ReplayParser

    assert ReplayParser._is_valid_coordinate_pair([1.0]) is False
    assert ReplayParser._is_valid_coordinate_pair("bad") is False
    assert ReplayParser._is_valid_coordinate_pair([1.0, "x"]) is False


def test_replay_parser_restores_simulation_report() -> None:

    scenario_json = {"start_time": "08:00", "end_time": "10:00"}

    keyframe_json = {
        "clock": {"simSecondsPassed": 0, "startTime": 0},
        "stations": [],
        "vehicles": [],
        "drivers": [],
        "tasks": [],
        "reportingSnapshot": {
            "total_driving_time": 100,
            "total_servicing_time": 50,
            "tasks_completed_per_shift": [1, 2],
            "response_times": [10.5],
            "vehicle_idle_time": 20,
            "vehicle_active_time": 80,
            "completed_vehicle_distance": 123.4,
        },
    }

    state = ReplayParser.parse(scenario_json, keyframe_json)
    report = state.sim_report

    assert report.total_driving_time == 100
    assert report.total_servicing_time == 50
    assert report.tasks_completed_per_shift == [1, 2]
    assert report.response_times == [10.5]
    assert report.vehicle_idle_time == 20
    assert report.vehicle_active_time == 80
    assert report._completed_vehicle_distance == 123.4


def test_replay_parser_active_routes_empty_when_no_routes() -> None:

    scenario_json = {"start_time": "08:00", "end_time": "10:00"}

    keyframe_json = {
        "clock": {"simSecondsPassed": 0, "startTime": 0},
        "stations": [],
        "vehicles": [],
        "drivers": [],
        "tasks": [],
    }

    state = ReplayParser.parse(scenario_json, keyframe_json)

    assert state.sim_report._active_vehicle_routes == set()


def test_restore_routes_happy_path() -> None:

    driver = Mock()
    driver.id = 1
    driver.get_position.return_value = Mock()

    map_controller = Mock()
    fake_route = Mock()
    map_controller.get_route.return_value = fake_route

    key_frame = {
        "drivers": [
            {
                "id": 1,
                "routes": [[[0, 0], [1, 1]]],
            }
        ]
    }

    ReplayParser.restore_routes([driver], key_frame, map_controller)

    map_controller.get_route.assert_called_once()
    driver.set_routes.assert_called_once_with([fake_route])
    driver.set_map_controller.assert_called_once_with(map_controller)


def test_restore_routes_driver_not_found() -> None:

    driver = Mock()
    driver.id = 1

    key_frame = {"drivers": [{"id": 999, "routes": []}]}

    map_controller = Mock()

    ReplayParser.restore_routes([driver], key_frame, map_controller)

    driver.set_routes.assert_not_called()
    map_controller.get_route.assert_not_called()


def test_restore_routes_invalid_json() -> None:

    driver = Mock()
    driver.id = 1

    key_frame = {"drivers": [{"id": 1, "routes": "INVALID_JSON"}]}

    map_controller = Mock()

    ReplayParser.restore_routes([driver], key_frame, map_controller)

    driver.set_route.assert_not_called()
    map_controller.get_route.assert_not_called()


def test_restore_routes_multiple_routes() -> None:

    driver = Mock()
    driver.id = 1
    driver.get_position.return_value = Mock()

    map_controller = Mock()
    route1 = Mock()
    route2 = Mock()

    map_controller.get_route.side_effect = [route1, route2]

    key_frame = {
        "drivers": [
            {
                "id": 1,
                "routes": [
                    [[0, 0], [1, 1]],
                    [[2, 2], [3, 3]],
                ],
            }
        ]
    }

    ReplayParser.restore_routes([driver], key_frame, map_controller)

    assert map_controller.get_route.call_count == 2
    driver.set_routes.assert_called_once_with([route1, route2])
