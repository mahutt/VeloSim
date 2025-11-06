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
from sim.utils.scenario_parser import ScenarioParser
from sim.entities.inputParameters import InputParameter
from sim.entities.resource import Resource
from sim.entities.BatterySwapTask import BatterySwapTask


def test_base_parse_strategy_is_abstract() -> None:
    class DummyStrategy(BaseParseStrategy):
        pass

    with pytest.raises(TypeError):
        DummyStrategy()  # type: ignore[abstract]


def test_json_parse_strategy_valid_input() -> None:
    env: simpy.Environment = simpy.Environment()

    data: dict[str, Any] = {
        "stations": {
            "8074": {
                "id": 8074,
                "name": "Lionel-Groulx",
                "position": [-74.0060, 40.7128],
                "tasks": [3],
            },
            "2105": {
                "id": 2105,
                "name": "Guy-Concordia",
                "position": [-118.2437, 34.0522],
                "tasks": [4],
            },
            "2508": {
                "id": 2508,
                "name": "Peel",
                "position": [-87.6298, 41.8781],
                "tasks": [5],
            },
        },
        "resources": {
            "1": {
                "id": 1,
                "name": "Resource 1",
                "position": [-64.0060, 75.7128],
                "tasks": [3, 4, 5],
            },
            "2": {
                "id": 2,
                "name": "Resource 2",
                "position": [-123.2437, 64.0522],
                "tasks": [3, 4, 5],
            },
        },
        "tasks": {
            "3": {
                "id": 3,
                "name": "BatterySwapTask 3",
                "station_id": 8074,
                "spawn_delay": None,
            },
            "4": {
                "id": 4,
                "name": "BatterySwapTask 4",
                "station_id": 2105,
                "spawn_delay": 30.0,
            },
            "5": {
                "id": 5,
                "name": "BatterySwapTask 5",
                "station_id": 2508,
                "spawn_delay": 120.0,
            },
        },
        "realTimeFactor": 1.0,
        "keyFrameFreq": 30,
    }

    strategy = JsonParseStrategy()
    params: InputParameter = strategy.parse(env, json.dumps(data))

    assert isinstance(params, InputParameter)
    assert len(params.station_entities) == 3
    assert len(params.task_entities) == 3
    assert len(params.resource_entities) == 2

    tasks = params.task_entities
    stations = params.station_entities
    resources = params.resource_entities

    assert tasks[3].station == stations[8074]
    assert tasks[4].station == stations[2105]
    assert tasks[5].station == stations[2508]

    for res in resources.values():
        assert isinstance(res, Resource)
        assert all(isinstance(t, BatterySwapTask) for t in res.task_list)

    assert params.realTimeFactor == 1.0
    assert params.keyFrameFreq == 30


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
    json_str = json.dumps(
        {
            "stations": {"1": {"name": "Station A"}},
            "resources": {"2": {"position": [10, 20]}},
            "tasks": {},
        }
    )

    strategy = JsonParseStrategy()
    params: InputParameter = strategy.parse(env, json_str)

    assert isinstance(params, InputParameter)
    out, _ = capfd.readouterr()
    assert "missing key" in out.lower()


def test_scenario_parser_delegates_to_strategy() -> None:
    env: simpy.Environment = simpy.Environment()

    fake_input_param = InputParameter({}, {}, {})

    class MockStrategy(BaseParseStrategy):
        def __init__(self) -> None:
            self.called: bool = False

        def parse(self, env: simpy.Environment, source: str) -> InputParameter:
            self.called = True
            assert source == "fake_input"
            return fake_input_param

    mock_strategy = MockStrategy()
    parser = ScenarioParser(mock_strategy)
    result = parser.parse(env, "fake_input")

    assert mock_strategy.called
    assert result is fake_input_param


def test_scenario_parser_can_switch_strategies() -> None:
    env: simpy.Environment = simpy.Environment()

    dummy_param_a = InputParameter({}, {}, {})
    dummy_param_b = InputParameter({}, {}, {})

    class StrategyA(BaseParseStrategy):
        def parse(self, env: simpy.Environment, source: str) -> InputParameter:
            return dummy_param_a

    class StrategyB(BaseParseStrategy):
        def parse(self, env: simpy.Environment, source: str) -> InputParameter:
            return dummy_param_b

    parser = ScenarioParser(StrategyA())
    result_a = parser.parse(env, "x")
    assert result_a is dummy_param_a

    parser.setStrategy(StrategyB())
    result_b = parser.parse(env, "x")
    assert result_b is dummy_param_b
