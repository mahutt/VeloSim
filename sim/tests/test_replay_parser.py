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

from typing import Any
import pytest
from unittest.mock import patch, Mock
from unittest.mock import MagicMock


@pytest.fixture
def mock_map_controller() -> Any:
    with patch("sim.utils.replay_parser.MapController") as MockMapController:
        mock_instance = Mock()
        mock_instance.get_route.return_value = None
        MockMapController.return_value = mock_instance
        yield MockMapController


def test_replay_parser_parse_minimal_valid_replay(
    mock_map_controller: MagicMock,
) -> None:
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


def test_replay_parser_extracts_playback_state_fields(
    mock_map_controller: MagicMock,
) -> None:
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


def test_replay_parser_playback_fields_fallback_defaults(
    mock_map_controller: MagicMock,
) -> None:
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


def test_replay_parser_should_auto_resume_when_not_paused_by_user(
    mock_map_controller: MagicMock,
) -> None:
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


def test_replay_parser_should_not_auto_resume_when_paused_by_user(
    mock_map_controller: MagicMock,
) -> None:
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
