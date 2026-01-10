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
from sim.entities.driver import Driver
from sim.entities.vehicle import Vehicle
from sim.entities.BatterySwapTask import BatterySwapTask
from sim.entities.inputParameters import InputParameter
from sim.entities.shift import Shift

# Default shift used for creating drivers in this module
DEFAULT_SHIFT = Shift(0.0, 24.0, None, 0.0, 24.0, None)


@pytest.fixture()
def env() -> simpy.Environment:
    env = simpy.Environment()
    # Ensure Driver has an env before any instantiation in this module
    Driver.env = env
    return env


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

    # Add Test Vehicles
    vehicles1 = Vehicle(vehicle_id=1, battery_count=999)
    vehicles2 = Vehicle(vehicle_id=2, battery_count=999)
    params.add_vehicle(vehicles1)
    params.add_vehicle(vehicles2)
    # Add test resources
    driver1 = Driver(driver_id=1, position=Position([15.0, 25.0]), shift=DEFAULT_SHIFT)
    driver2 = Driver(driver_id=2, position=Position([35.0, 45.0]), shift=DEFAULT_SHIFT)
    params.add_driver(driver1)
    params.add_driver(driver2)

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

    drivers = input_params.get_driver_entities()
    assert drivers is not None
    assert input_params.get_driver_count() == 2

    vehicles = input_params.get_vehicle_entities()
    assert vehicles is not None
    assert input_params.get_vehicle_count() == 2

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


def test_set_driver_entities(
    input_params: InputParameter, env: simpy.Environment
) -> None:
    original_drivers = input_params.get_driver_entities()
    assert input_params.get_driver_count() == 2

    # Act
    Driver.env = env
    driver = Driver(driver_id=45, position=Position([15.0, 25.0]), shift=DEFAULT_SHIFT)
    input_params.set_driver_entities({45: driver})

    # Assert
    drivers = input_params.get_driver_entities()
    assert drivers is not original_drivers
    assert driver in drivers.values()
    assert 1 not in drivers.keys()


def test_set_vehicle_entities(
    input_params: InputParameter, env: simpy.Environment
) -> None:
    original_vehicles = input_params.get_vehicle_entities()
    assert input_params.get_vehicle_count() == 2

    # Act
    vehicle = Vehicle(vehicle_id=45, battery_count=999)
    input_params.set_vehicle_entities({45: vehicle})

    # Assert
    vehicles = input_params.get_vehicle_entities()
    assert vehicles is not original_vehicles
    assert vehicle in vehicles.values()
    assert 1 not in vehicles.keys()


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


def test_add_driver(input_params: InputParameter, env: simpy.Environment) -> None:
    original_drivers = input_params.get_driver_entities()
    assert 12 not in original_drivers.keys()

    # Act
    Driver.env = env
    driver = Driver(driver_id=12, position=Position([15.0, 25.0]), shift=DEFAULT_SHIFT)
    input_params.add_driver(driver)

    # Assert
    drivers = input_params.get_driver_entities()
    assert driver in drivers.values()
    assert 12 in drivers.keys()


def test_add_vehicle(input_params: InputParameter, env: simpy.Environment) -> None:
    original_vehicles = input_params.get_vehicle_entities()
    assert 12 not in original_vehicles.keys()

    # Act
    vehicle = Vehicle(vehicle_id=12, battery_count=999)
    input_params.add_vehicle(vehicle)

    # Assert
    vehicles = input_params.get_vehicle_entities()
    assert vehicle in vehicles.values()
    assert 12 in vehicles.keys()


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


def test_remove_driver_success(
    input_params: InputParameter, env: simpy.Environment
) -> None:
    Driver.env = env
    driver = Driver(driver_id=12, position=Position([15.0, 25.0]), shift=DEFAULT_SHIFT)
    input_params.add_driver(driver)
    added_drivers = input_params.get_driver_entities()
    assert 12 in added_drivers.keys()
    assert input_params.get_driver_count() == 3

    # Act
    input_params.remove_driver(driver)

    # Assert
    drivers = input_params.get_driver_entities()
    assert driver not in drivers.values()
    assert 12 not in drivers.keys()
    assert input_params.get_driver_count() == 2


@patch("builtins.print")
def test_remove_driver_fail(
    mock_print: MagicMock, input_params: InputParameter, env: simpy.Environment
) -> None:
    drivers = input_params.get_driver_entities()
    assert 13 not in drivers.keys()
    assert input_params.get_driver_count() == 2

    # Act
    Driver.env = env
    driver = Driver(driver_id=13, position=Position([15.0, 25.0]), shift=DEFAULT_SHIFT)
    input_params.remove_driver(driver)

    # Assert
    error = "remove_driver(): driver: 13 not found"
    mock_print.assert_called_once_with(error)
    assert input_params.get_driver_count() == 2


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
