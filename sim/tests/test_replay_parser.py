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
    from sim.entities.inputParameters import InputParameter
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

    input_param, map_controller, current_sim = ReplayParser.parse(
        scenario_json=scenario_json,
        keyframe_json=keyframe_json,
    )

    assert isinstance(input_param, InputParameter)
    assert current_sim == 1800

    station = next(iter(input_param.station_entities.values()))
    task = station.tasks[0]
    assert task.state == State.OPEN

    driver = next(iter(input_param.driver_entities.values()))
    assert driver.state == DriverState.IDLE
