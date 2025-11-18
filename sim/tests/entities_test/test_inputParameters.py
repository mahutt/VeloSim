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
import simpy
from unittest.mock import patch, MagicMock
from sim.entities.station import Station
from sim.entities.position import Position
from sim.entities.resource import Resource
from sim.entities.BatterySwapTask import BatterySwapTask
from sim.entities.inputParameters import InputParameter


@pytest.fixture()
def env() -> simpy.Environment:
    return simpy.Environment()


@pytest.fixture()
def input_params(env: simpy.Environment) -> InputParameter:
    """Create a basic InputParameter with some test entities."""
    params = InputParameter()

    # Add test stations
    station1 = Station(
        station_id=1, name="Test Station 1", position=Position([10.0, 20.0])
    )
    station2 = Station(
        station_id=2, name="Test Station 2", position=Position([30.0, 40.0])
    )
    params.add_station(station1)
    params.add_station(station2)

    # Add test resources
    resource1 = Resource(resource_id=1, position=Position([15.0, 25.0]))
    resource2 = Resource(resource_id=2, position=Position([35.0, 45.0]))
    params.add_resource(resource1)
    params.add_resource(resource2)

    # Add test tasks using concrete BatterySwapTask
    task1 = BatterySwapTask(task_id=1, station=station1)
    task2 = BatterySwapTask(task_id=2, station=station2)
    params.add_task(task1)
    params.add_task(task2)

    return params


def test_get_methods(input_params: InputParameter) -> None:
    stations = input_params.get_station_entities()
    assert stations is not None
    assert input_params.get_station_count() == 2

    resources = input_params.get_resource_entities()
    assert resources is not None
    assert input_params.get_resource_count() == 2

    tasks = input_params.get_task_entities()
    assert tasks is not None
    assert input_params.get_task_count() == 2

    real_time_factor = input_params.get_real_time_factor()
    assert real_time_factor is None  # by default

    key_frame_freq = input_params.get_key_frame_freq()
    assert key_frame_freq is None  # by default


def test_set_station_entities(
    input_params: InputParameter, env: simpy.Environment
) -> None:
    original_stations = input_params.get_station_entities()
    assert input_params.get_station_count() == 2

    # Act
    station = Station(
        station_id=45, name="Some New Station", position=Position([10.0, 20.0])
    )
    input_params.set_station_entities({45: station})

    # Assert
    stations = input_params.get_station_entities()
    assert stations is not original_stations
    assert station in stations.values()
    assert 1 not in stations.keys()


def test_set_resource_entities(
    input_params: InputParameter, env: simpy.Environment
) -> None:
    original_resources = input_params.get_resource_entities()
    assert input_params.get_resource_count() == 2

    # Act
    resource = Resource(resource_id=45, position=Position([15.0, 25.0]))
    input_params.set_resource_entities({45: resource})

    # Assert
    resources = input_params.get_resource_entities()
    assert resources is not original_resources
    assert resource in resources.values()
    assert 1 not in resources.keys()


def test_set_task_entities(
    input_params: InputParameter, env: simpy.Environment
) -> None:
    original_tasks = input_params.get_task_entities()
    assert input_params.get_task_count() == 2

    # Act
    task = BatterySwapTask(task_id=45)
    input_params.set_task_entities({45: task})

    # Assert
    tasks = input_params.get_task_entities()
    assert tasks is not original_tasks
    assert task in tasks.values()
    assert 1 not in tasks.keys()


def test_set_real_time_factor(input_params: InputParameter) -> None:
    original_rtf = input_params.get_real_time_factor()
    assert original_rtf is None

    # Act
    input_params.set_real_time_factor(1.0)

    # Assert
    real_time_factor = input_params.get_real_time_factor()
    assert real_time_factor == 1.0
    assert real_time_factor is not original_rtf


def test_set_key_frame_freq(input_params: InputParameter) -> None:
    original_kff = input_params.get_key_frame_freq()
    assert original_kff is None

    # Act
    input_params.set_key_frame_freq(3)

    # Assert
    key_frame_freq = input_params.get_key_frame_freq()
    assert key_frame_freq == 3
    assert key_frame_freq is not original_kff


def test_add_station(input_params: InputParameter, env: simpy.Environment) -> None:
    original_stations = input_params.get_station_entities()
    assert 12 not in original_stations.keys()

    # Act
    station = Station(
        station_id=12, name="Some New Station", position=Position([10.0, 20.0])
    )
    input_params.add_station(station)

    # Assert
    stations = input_params.get_station_entities()
    assert station in stations.values()
    assert 12 in stations.keys()


def test_add_resource(input_params: InputParameter, env: simpy.Environment) -> None:
    original_resources = input_params.get_resource_entities()
    assert 12 not in original_resources.keys()

    # Act
    resource = Resource(resource_id=12, position=Position([15.0, 25.0]))
    input_params.add_resource(resource)

    # Assert
    resources = input_params.get_resource_entities()
    assert resource in resources.values()
    assert 12 in resources.keys()


def test_add_task(input_params: InputParameter, env: simpy.Environment) -> None:
    original_tasks = input_params.get_task_entities()
    assert 12 not in original_tasks.keys()

    # Act
    task = BatterySwapTask(task_id=12)
    input_params.add_task(task)

    # Assert
    tasks = input_params.get_task_entities()
    assert task in tasks.values()
    assert 12 in tasks.keys()


def test_remove_station_success(
    input_params: InputParameter, env: simpy.Environment
) -> None:
    station = Station(
        station_id=12, name="Some New Station", position=Position([10.0, 20.0])
    )
    input_params.add_station(station)
    added_stations = input_params.get_station_entities()
    assert 12 in added_stations.keys()
    assert input_params.get_station_count() == 3

    # Act
    input_params.remove_station(station)

    # Assert
    stations = input_params.get_station_entities()
    assert station not in stations.values()
    assert 12 not in stations.keys()
    assert input_params.get_station_count() == 2


@patch("builtins.print")
def test_remove_station_fail(
    mock_print: MagicMock, input_params: InputParameter, env: simpy.Environment
) -> None:
    stations = input_params.get_station_entities()
    assert 13 not in stations.keys()
    assert input_params.get_station_count() == 2

    # Act
    station = Station(
        station_id=13,
        name="Some Random Station",
        position=Position([10.0, 20.0]),
    )
    input_params.remove_station(station)

    # Assert
    error = "remove_station(): Station: 13 not found"
    mock_print.assert_called_once_with(error)
    assert input_params.get_station_count() == 2


def test_remove_resource_success(
    input_params: InputParameter, env: simpy.Environment
) -> None:
    resource = Resource(resource_id=12, position=Position([15.0, 25.0]))
    input_params.add_resource(resource)
    addded_resources = input_params.get_resource_entities()
    assert 12 in addded_resources.keys()
    assert input_params.get_resource_count() == 3

    # Act
    input_params.remove_resource(resource)

    # Assert
    resources = input_params.get_resource_entities()
    assert resource not in resources.values()
    assert 12 not in resources.keys()
    assert input_params.get_resource_count() == 2


@patch("builtins.print")
def test_remove_resource_fail(
    mock_print: MagicMock, input_params: InputParameter, env: simpy.Environment
) -> None:
    resources = input_params.get_resource_entities()
    assert 13 not in resources.keys()
    assert input_params.get_resource_count() == 2

    # Act
    resource = Resource(resource_id=13, position=Position([15.0, 25.0]))
    input_params.remove_resource(resource)

    # Assert
    error = "remove_resource(): Resource: 13 not found"
    mock_print.assert_called_once_with(error)
    assert input_params.get_resource_count() == 2


def test_remove_task_success(
    input_params: InputParameter, env: simpy.Environment
) -> None:
    task = BatterySwapTask(task_id=12)
    input_params.add_task(task)
    added_tasks = input_params.get_task_entities()
    assert 12 in added_tasks.keys()
    assert input_params.get_task_count() == 3

    # Act
    input_params.remove_task(task)

    # Assert
    tasks = input_params.get_task_entities()
    assert task not in tasks.values()
    assert 12 not in tasks.keys()
    assert input_params.get_task_count() == 2


@patch("builtins.print")
def test_remove_task_fail(
    mock_print: MagicMock, input_params: InputParameter, env: simpy.Environment
) -> None:
    tasks = input_params.get_task_entities()
    assert 13 not in tasks.keys()
    assert input_params.get_task_count() == 2

    # Act
    task = BatterySwapTask(task_id=13)
    input_params.remove_task(task)

    # Assert
    error = "remove_task(): Task: 13 not found"
    mock_print.assert_called_once_with(error)
    assert input_params.get_task_count() == 2
