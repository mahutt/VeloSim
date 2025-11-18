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
    scenario_json = {
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
                {"resource_id": 1, "resource_position": [-64.0060, 75.7128]},
                {"resource_id": 2, "resource_position": [-123.2437, 64.0522]},
            ],
            "initial_tasks": [{"station_id": 8074}],
            "scheduled_tasks": [
                {"station_id": 2105, "time": 30},
                {"station_id": 2508, "time": 120},
            ],
        },
    }

    strategy = JsonParseStrategy()
    params: InputParameter = strategy.parse(scenario_json)

    assert isinstance(params, InputParameter)
    assert len(params.station_entities) == 3
    assert len(params.resource_entities) == 2
    assert len(params.task_entities) == 3

    tasks = params.task_entities
    stations = params.station_entities
    resources = params.resource_entities

    # IDs are auto-generated starting from 1, 2, 3...
    assert tasks[1].station == stations[8074]  # First task (initial)
    assert tasks[2].station == stations[2105]  # Second task (scheduled)
    assert tasks[3].station == stations[2508]  # Third task (scheduled)

    for res in resources.values():
        assert isinstance(res, Resource)
        assert isinstance(res.task_list, list)


def test_json_parse_strategy_invalid_json() -> None:
    strategy = JsonParseStrategy()
    with pytest.raises(AttributeError):
        strategy.parse("string_instead_of_dict")  # type: ignore[arg-type]


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
