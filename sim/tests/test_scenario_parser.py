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

import json
import pytest
import simpy
from typing import Any

from sim.utils.base_parse_strategy import BaseParseStrategy
from sim.utils.json_parser_strategy import JsonParseStrategy
from sim.entities.inputParameters import InputParameter
from sim.entities.resource import Resource
from sim.utils.scenario_parser import ScenarioParser


def test_base_parse_strategy_is_abstract() -> None:
    class DummyStrategy(BaseParseStrategy):
        pass

    with pytest.raises(TypeError):
        DummyStrategy()  # type: ignore[abstract]


def test_json_parse_strategy_valid_input() -> None:
    env: simpy.Environment = simpy.Environment()

    # New parser expects a top-level "scenarios" list where each scenario
    # has an "id" and a "content" object containing stations/resources/tasks.
    data: dict[str, Any] = {
        "scenarios": [
            {
                "id": 1,
                "name": "Test Scenario",
                "content": {
                    "start_time": "00:00",
                    "end_time": "01:00",
                    "stations": [
                        {
                            "station_id": 8074,
                            "station_name": "Lionel-Groulx",
                            "station_position": [-74.0060, 40.7128],
                        },
                        {
                            "station_id": 2105,
                            "station_name": "Guy-Concordia",
                            "station_position": [-118.2437, 34.0522],
                        },
                        {
                            "station_id": 2508,
                            "station_name": "Peel",
                            "station_position": [-87.6298, 41.8781],
                        },
                    ],
                    "resources": [
                        {
                            "resource_id": 1,
                            "resource_position": [-64.0060, 75.7128],
                        },
                        {
                            "resource_id": 2,
                            "resource_position": [-123.2437, 64.0522],
                        },
                    ],
                    "initial_tasks": [
                        {"id": "t3", "station_id": 8074},
                    ],
                    "scheduled_tasks": [
                        {"id": "t4", "station_id": 2105, "time": 30.0},
                        {"id": "t5", "station_id": 2508, "time": 120.0},
                    ],
                },
            }
        ]
    }

    strategy = JsonParseStrategy()
    parsed = strategy.parse(env, json.dumps(data))

    assert isinstance(parsed, dict)
    assert 1 in parsed

    params: InputParameter = parsed[1]

    assert isinstance(params, InputParameter)
    assert len(params.station_entities) == 3
    assert len(params.task_entities) == 3
    assert len(params.resource_entities) == 2

    tasks = params.task_entities
    stations = params.station_entities
    resources = params.resource_entities

    # tasks were created with ids stripped of leading 't'
    assert tasks[3].station == stations[8074]
    assert tasks[4].station == stations[2105]
    assert tasks[5].station == stations[2508]

    for res in resources.values():
        assert isinstance(res, Resource)
        # Parser creates Resource objects with an empty task_list by default
        assert isinstance(res.task_list, list)

    # JsonParseStrategy currently sets these defaults in the InputParameter
    assert params.realTimeFactor == 1.0
    assert params.keyFrameFreq == 3000


def test_json_parse_strategy_invalid_json() -> None:
    env: simpy.Environment = simpy.Environment()
    invalid_json = "{ bad json ]"
    strategy = JsonParseStrategy()

    with pytest.raises(ValueError) as excinfo:
        strategy.parse(env, invalid_json)
    assert "Invalid JSON input" in str(excinfo.value)


def test_json_parse_strategy_handles_missing_keys_gracefully(
    capfd: pytest.CaptureFixture[str],
) -> None:
    env: simpy.Environment = simpy.Environment()

    # Provide a scenario with stations/resources missing expected keys
    json_str = json.dumps(
        {
            "scenarios": [
                {
                    "id": 42,
                    "content": {
                        "start_time": "00:00",
                        "end_time": "00:00",
                        "stations": [{"station_name": "Station A"}],
                        "resources": [{"resource_position": [10, 20]}],
                        "initial_tasks": [],
                        "scheduled_tasks": [],
                    },
                }
            ]
        }
    )

    strategy = JsonParseStrategy()
    params_dict = strategy.parse(env, json_str)

    assert isinstance(params_dict, dict)
    # Parser should still return an InputParameter for the scenario id
    assert 42 in params_dict
    params: InputParameter = params_dict[42]
    assert isinstance(params, InputParameter)

    out, _ = capfd.readouterr()
    # The parser prints warnings for failed items; check for that indication
    assert "failed to parse" in out.lower() or "warn" in out.lower()


def test_scenario_parser_delegates_to_strategy() -> None:
    env: simpy.Environment = simpy.Environment()
    fake_input_param = InputParameter({}, {}, {})

    class MockStrategy(BaseParseStrategy):
        def __init__(self) -> None:
            self.called: bool = False

        def parse(
            self, env: simpy.Environment, source: str
        ) -> dict[int, InputParameter]:
            self.called = True
            assert source == "fake_input"
            return {0: fake_input_param}

    mock_strategy = MockStrategy()
    parser = ScenarioParser(mock_strategy)
    result = parser.parse(env, "fake_input")

    assert mock_strategy.called
    assert result[0] is fake_input_param
