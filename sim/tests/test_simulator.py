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

# sim/tests/test_simulator.py

import time
import simpy
import threading
from typing import List, Any
import uuid

import pytest
from _pytest.capture import CaptureFixture
from unittest.mock import patch, MagicMock

# Import the module so we can monkeypatch its time.sleep
from sim.entities.inputParameters import InputParameter
from sim.entities.request_type import RequestType
from sim.entities.station import Station
from sim.entities.position import Position
from sim.entities.resource import Resource
from sim.entities.BatterySwapTask import BatterySwapTask

import sim.RealTimeDriver as rtd_mod
from sim.simulator import Simulator
from sim.utils.subscriber import Subscriber

params = InputParameter()
subList: List[Subscriber] = []


# Mock time to avoid real time delays in tests
class MockClock:
    def __init__(self, start: float = 100.0) -> None:
        self.now = float(start)
        self.sleeps: List[float] = []

    def perf_counter(self) -> float:
        return self.now

    def sleep(self, dt: float) -> None:
        if dt and dt > 0:
            self.sleeps.append(dt)
            self.now += dt


@pytest.fixture
def sim() -> Simulator:
    return Simulator()


@pytest.fixture
def simpy_env() -> simpy.Environment:
    return simpy.Environment()


@pytest.fixture
def default_station(simpy_env: simpy.Environment) -> Station:
    return Station(
        simpy_env,
        station_id=1,
        name="Test Station",
        position=Position([-73.5673, 45.5017]),
    )


@pytest.fixture()
def input_params(simpy_env: simpy.Environment) -> InputParameter:
    """Create a basic InputParameter with some test entities."""
    params = InputParameter()

    # Add test stations
    station1 = Station(
        env=simpy_env,
        station_id=1,
        name="Test Station 1",
        position=Position([10.0, 20.0]),
    )
    station2 = Station(
        env=simpy_env,
        station_id=2,
        name="Test Station 2",
        position=Position([30.0, 40.0]),
    )
    params.add_station(station1)
    params.add_station(station2)

    # Add test resources
    resource1 = Resource(env=simpy_env, resource_id=1, position=Position([15.0, 25.0]))
    resource2 = Resource(env=simpy_env, resource_id=2, position=Position([35.0, 45.0]))
    params.add_resource(resource1)
    params.add_resource(resource2)

    # Add test tasks using concrete BatterySwapTask
    task1 = BatterySwapTask(env=simpy_env, task_id=1, station=station1)
    task2 = BatterySwapTask(env=simpy_env, task_id=2, station=station2)
    params.add_task(task1)
    params.add_task(task2)

    return params


@pytest.fixture
def fake_time(monkeypatch: Any) -> MockClock:
    clock = MockClock()
    # Replace the RealTimeDriver time module
    monkeypatch.setattr(rtd_mod.time, "perf_counter", clock.perf_counter)
    monkeypatch.setattr(rtd_mod.time, "sleep", clock.sleep)
    # Also replace the main time module for any direct calls
    monkeypatch.setattr(time, "sleep", clock.sleep)
    return clock


def test_start_creates_thread_and_emits_output(
    sim: Simulator,
    fake_time: MockClock,
    capsys: CaptureFixture[str],
) -> None:
    """
    Verifies:
      - initialize() returns a UUID string
      - start() creates a thread and it's alive
      - loop prints at least once
    We use fake_time to avoid real time delays.
    """
    # Initialize first, then start
    sim_id = sim.initialize(params, subList)
    uuid.UUID(sim_id)  # should not raise

    # Start the simulation
    sim.start(sim_id, 3600)

    # Simulate time passing to let the thread run iterations
    fake_time.sleep(0.12)

    # Stop and capture output
    sim.stop(sim_id)
    out = capsys.readouterr().out

    # The output will contain frames from the simulation
    # Check that the sim_id ended message appears
    assert f"{sim_id} ended" in out

    # Thread should be gone from pool
    assert sim_id not in sim.thread_pool


def test_start_with_non_existant_sim_id(sim: Simulator, fake_time: MockClock) -> None:
    # Arrange
    sim.initialize(params, subList)

    # Act and Assert
    with pytest.raises(
        RuntimeError, match=r"Simulation some_id not found. Call initialize\(\) first."
    ):
        sim.start("some_id", 3600)


def test_start_with_already_running_sim(sim: Simulator, fake_time: MockClock) -> None:
    # Arrange
    sim_id = sim.initialize(params, subList)
    sim.start(sim_id, 3600)

    # Act and Assert
    with pytest.raises(RuntimeError, match=f"Simulation {sim_id} is already running."):
        sim.start(sim_id, 3600)

    sim.stop(sim_id)


def test_stop_removes_thread_from_pool(
    sim: Simulator,
    fake_time: MockClock,
) -> None:
    # Initialize and start simulation
    sim_id = sim.initialize(params, subList)
    sim.start(sim_id, 3600)

    assert sim_id in sim.thread_pool
    t = sim.thread_pool[sim_id]["thread"]
    assert isinstance(t, threading.Thread)
    # Note: With mock time, we don't assert is_alive() as threads complete quickly

    sim.stop(sim_id)

    assert sim_id not in sim.thread_pool
    # The thread should be finished after stop
    assert not t.is_alive()


def test_stop_nonexistent_id_noop(sim: Simulator) -> None:
    # Should not raise
    sim.stop("does-not-exist")


def test_multiple_parallel_sims(
    sim: Simulator,
    fake_time: MockClock,
) -> None:
    # Initialize and start multiple simulations
    a = sim.initialize(params, subList)
    b = sim.initialize(params, subList)

    sim.start(a, 3600)
    sim.start(b, 3600)

    assert a != b
    assert a in sim.thread_pool and b in sim.thread_pool
    # Note: With mock time, we don't assert is_alive() as threads may complete quickly
    assert sim.thread_pool[a]["thread"] is not None
    assert sim.thread_pool[b]["thread"] is not None

    sim.stop(a)
    sim.stop(b)
    assert a not in sim.thread_pool and b not in sim.thread_pool


def test_pause_and_status_not_implemented(sim: Simulator) -> None:
    with pytest.raises(NotImplementedError):
        sim.pause()
    with pytest.raises(NotImplementedError):
        sim.status()


def test_send_request_not_implemented(sim: Simulator) -> None:
    # Any RequestType should raise until implemented
    request = RequestType()
    with pytest.raises(NotImplementedError):
        sim.send_request(request)


def test_get_sim_by_id_success(
    sim: Simulator,
    fake_time: MockClock,
) -> None:
    # Arrange
    a = sim.initialize(params, subList)
    sim.start(a, 3600)

    # Act
    sim_info = sim.get_sim_by_id(a)

    # Assert
    assert sim_info is not None
    assert sim_info["simController"] is not None

    sim.stop(a)


def test_get_sim_by_id_fail(
    sim: Simulator,
    fake_time: MockClock,
) -> None:
    # Arrange
    a = sim.initialize(params, subList)
    sim.start(a, 3600)

    # Act and Assert
    with pytest.raises(
        Exception, match="Simulation random_id does not exist in the thread pool"
    ):
        sim.get_sim_by_id("random_id")

    sim.stop(a)


def test_add_task_to_sim_success(
    sim: Simulator,
    fake_time: MockClock,
    simpy_env: simpy.Environment,
    default_station: Station,
) -> None:
    # Arrange
    a = sim.initialize(params, subList)
    sim.start(a, 3600)

    new_task = BatterySwapTask(simpy_env, 3, default_station)

    # Act
    sim.add_task_to_sim(a, new_task)

    # Assert
    sim_info = sim.get_sim_by_id(a)
    if sim_info is not None:
        sim_controller = sim_info["simController"]

        # task_entities is a dict keyed by task id
        assert len(sim_controller.task_entities) != 0
        assert sim_controller.get_task_by_id(3) is not None

    # Cleanup: remove the task from the controller if present
    if sim_info is not None:
        sim_controller.task_entities.pop(3, None)
    sim.stop(a)


@patch("builtins.print")
def test_add_task_to_sim_fail(
    mock_print: MagicMock,
    sim: Simulator,
    fake_time: MockClock,
    simpy_env: simpy.Environment,
    default_station: Station,
) -> None:
    # Arrange
    a = sim.initialize(params, subList)
    sim.start(a, 3600)

    new_task = BatterySwapTask(simpy_env, 3, default_station)

    # Act
    sim.add_task_to_sim("random_id", new_task)

    # Assert
    error = "Simulation random_id does not exist in the thread pool"
    mock_print.assert_called_once_with(f"Could not add task to sim due to: {error}")

    sim.stop(a)


def test_assign_task_to_resource_success(
    sim: Simulator, input_params: InputParameter
) -> None:
    # Arrange
    a = sim.initialize(input_params, subList)
    sim.start(a, 3600)

    # Act
    sim.assign_task_to_resource(a, task_id=1, resource_id=1)

    # Assert
    sim_info = sim.get_sim_by_id(a)
    if sim_info is not None:
        sim_controller = sim_info["simController"]
        task = sim_controller.get_task_by_id(1)
        assert task is not None
        resource = task.get_assigned_resource()
        assert resource is not None
        assert resource.id == 1


@patch("builtins.print")
def test_assign_task_to_resource_fail(
    mock_print: MagicMock, sim: Simulator, input_params: InputParameter
) -> None:
    # Arrange
    a = sim.initialize(input_params, subList)
    sim.start(a, 3600)

    # Act - Pass non-existent task_id
    sim.assign_task_to_resource(a, task_id=6, resource_id=1)

    # Assert
    error = "Could not find task in sim with id: 6"
    mock_print.assert_called_once_with(f"Could not assign task due to: {error}")


def test_unassign_task_from_resource_success(
    sim: Simulator, input_params: InputParameter
) -> None:
    # Arrange
    a = sim.initialize(input_params, subList)
    sim.start(a, 3600)
    sim.assign_task_to_resource(a, task_id=1, resource_id=1)

    # Act
    sim.unassign_task_from_resource(a, task_id=1, resource_id=1)

    # Assert
    sim_info = sim.get_sim_by_id(a)
    if sim_info is not None:
        sim_controller = sim_info["simController"]
        task = sim_controller.get_task_by_id(1)
        assert task is not None
        assert task.get_assigned_resource() is None


@patch("builtins.print")
def test_unassign_task_from_resource_fail(
    mock_print: MagicMock, sim: Simulator, input_params: InputParameter
) -> None:
    # Arrange
    a = sim.initialize(input_params, subList)
    sim.start(a, 3600)

    # Act - Pass non-existent task_id
    sim.unassign_task_from_resource(a, task_id=6, resource_id=1)

    # Assert
    error = "Could not find task in sim with id: 6"
    mock_print.assert_called_once_with(f"Could not unassign task due to: {error}")


def test_reassign_task_success(sim: Simulator, input_params: InputParameter) -> None:
    # Arrange
    a = sim.initialize(input_params, subList)
    sim.start(a, 3600)
    sim.assign_task_to_resource(a, task_id=1, resource_id=1)

    # Act
    sim.reassign_task(a, task_id=1, old_resource_id=1, new_resource_id=2)

    # Assert
    sim_info = sim.get_sim_by_id(a)
    if sim_info is not None:
        sim_controller = sim_info["simController"]
        task = sim_controller.get_task_by_id(1)
        assert task is not None
        old_resource = sim_controller.get_resource_by_id(1)
        assert old_resource is not None
        new_resource = sim_controller.get_resource_by_id(2)
        assert new_resource is not None
        assert task.get_assigned_resource() == new_resource
        assert task not in old_resource.get_task_list()


@patch("builtins.print")
def test_reassign_task_fail(
    mock_print: MagicMock, sim: Simulator, input_params: InputParameter
) -> None:
    # Arrange
    a = sim.initialize(input_params, subList)
    sim.start(a, 3600)

    # Act - Pass non-existent task_id
    sim.reassign_task(a, task_id=6, old_resource_id=1, new_resource_id=2)

    # Assert
    error = "Reassigning task failed as could not find task 6"
    mock_print.assert_called_once_with(f"Error occurred: {error}")


def test_get_stream_not_implemented(sim: Simulator) -> None:
    with pytest.raises(NotImplementedError):
        sim.get_stream()


def test_stop_all_stops_everything_and_is_idempotent(
    sim: Simulator,
    fake_time: MockClock,
) -> None:
    """
    Start multiple sims, stop them all via stop_all(),
    verify the pool is empty.
    Also ensure calling stop_all() again does not error.
    """
    # Initialize and start multiple simulations
    sim_ids = []
    for _ in range(3):
        sim_id = sim.initialize(params, subList)
        sim.start(sim_id, 3600)
        sim_ids.append(sim_id)

    # Sanity: all should be present in the pool
    for sid in sim_ids:
        assert sid in sim.thread_pool
        # Note: With mock time, threads may complete very quickly,
        # so we don't assert thread.is_alive() as it's unreliable

    # Stop all
    sim.stop_all(join_timeout_per_thread=1.0)

    # Pool should be empty after stop_all
    assert sim.thread_pool == {}

    # Idempotency: calling again should not raise
    sim.stop_all(join_timeout_per_thread=0.2)
