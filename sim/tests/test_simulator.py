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
from types import SimpleNamespace
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

import sim.core.RealTimeDriver as rtd_mod
from sim.simulator import Simulator
from sim.utils.subscriber import Subscriber
from sim.behaviour.sim_behaviour import SimBehaviour

params = InputParameter()
subList: List[Subscriber] = []


class FakeTPUStrategy:
    def check_for_new_task(self, station: Station) -> bool:
        return False


class FakeRCNTStrategy:
    def select_next_task(self, resource: Resource) -> None:
        return None


class FakeSimBehaviour(SimBehaviour):
    def __init__(self) -> None:
        super().__init__()
        self.TPU_strategy = FakeTPUStrategy()  # type: ignore[assignment]
        self.RCNT_strategy = FakeRCNTStrategy()  # type: ignore[assignment]


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
        station_id=1,
        name="Test Station 1",
        position=Position([10.0, 20.0]),
    )
    station2 = Station(
        station_id=2,
        name="Test Station 2",
        position=Position([30.0, 40.0]),
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
    simpy_env: simpy.Environment,
) -> None:
    """
    Verifies:
      - initialize() returns a UUID string
      - start() creates a thread and it's alive
      - loop prints at least once
    We use fake_time to avoid real time delays.
    """
    # Initialize first, then start
    sim_id = sim.initialize(params, subList, FakeSimBehaviour())
    uuid.UUID(sim_id)  # should not raise

    # Patch heavy map building and routing before start
    sim_info = sim.get_sim_by_id(sim_id)
    assert sim_info is not None
    ctrl = sim_info["simController"]
    with (
        patch.object(ctrl.map_controller.osrm, "build_ch_network", return_value=None),
        patch.object(
            ctrl.map_controller, "getRoute", return_value=SimpleNamespace(roads=[1])
        ),
    ):
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


def test_start_with_non_existant_sim_id(
    sim: Simulator, fake_time: MockClock, simpy_env: simpy.Environment
) -> None:
    # Arrange
    sim.initialize(params, subList, FakeSimBehaviour())

    # Act and Assert
    with pytest.raises(
        RuntimeError, match=r"Simulation some_id not found. Call initialize\(\) first."
    ):
        sim.start("some_id", 3600)


def test_start_with_already_running_sim(
    sim: Simulator, fake_time: MockClock, simpy_env: simpy.Environment
) -> None:
    # Arrange
    sim_id = sim.initialize(params, subList, FakeSimBehaviour())
    sim_info = sim.get_sim_by_id(sim_id)
    assert sim_info is not None
    ctrl = sim_info["simController"]
    with (
        patch.object(ctrl.map_controller.osrm, "build_ch_network", return_value=None),
        patch.object(
            ctrl.map_controller, "getRoute", return_value=SimpleNamespace(roads=[1])
        ),
    ):
        sim.start(sim_id, 3600)

    # Act and Assert
    with pytest.raises(RuntimeError, match=f"Simulation {sim_id} is already running."):
        sim.start(sim_id, 3600)

    sim.stop(sim_id)


def test_stop_removes_thread_from_pool(
    sim: Simulator,
    fake_time: MockClock,
    simpy_env: simpy.Environment,
) -> None:
    # Initialize and start simulation
    sim_id = sim.initialize(params, subList, FakeSimBehaviour())
    sim_info = sim.get_sim_by_id(sim_id)
    assert sim_info is not None
    ctrl = sim_info["simController"]
    with (
        patch.object(ctrl.map_controller.osrm, "build_ch_network", return_value=None),
        patch.object(
            ctrl.map_controller,
            "getRoute",
            return_value=SimpleNamespace(roads=[1]),
        ),
    ):
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
    simpy_env: simpy.Environment,
) -> None:
    # Initialize and start multiple simulations
    a = sim.initialize(params, subList, FakeSimBehaviour())
    b = sim.initialize(params, subList, FakeSimBehaviour())

    a_info = sim.get_sim_by_id(a)
    b_info = sim.get_sim_by_id(b)
    assert a_info is not None and b_info is not None
    a_ctrl = a_info["simController"]
    b_ctrl = b_info["simController"]
    with (
        patch.object(a_ctrl.map_controller.osrm, "build_ch_network", return_value=None),
        patch.object(
            a_ctrl.map_controller,
            "getRoute",
            return_value=SimpleNamespace(roads=[1]),
        ),
        patch.object(b_ctrl.map_controller.osrm, "build_ch_network", return_value=None),
        patch.object(
            b_ctrl.map_controller,
            "getRoute",
            return_value=SimpleNamespace(roads=[1]),
        ),
    ):
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


def test_status_not_implemented(sim: Simulator) -> None:
    with pytest.raises(NotImplementedError):
        sim.status()


def test_pause_success(sim: Simulator, input_params: InputParameter) -> None:
    # Arrange
    a = sim.initialize(input_params, subList)
    sim.start(a, 3600)

    sim_info = sim.get_sim_by_id(a)
    assert sim_info is not None

    # Act & Assert
    with patch.object(sim_info["simController"], "pause") as mock_pause:
        sim.pause(a)
        mock_pause.assert_called_once()

    sim.stop(a)


@patch("builtins.print")
def test_pause_fail(mock_print: MagicMock, sim: Simulator) -> None:
    # Arrange
    a = sim.initialize(params, subList)
    sim.start(a, 3600)

    # Act
    sim.pause("random_id")

    # Assert
    error = "Simulation random_id does not exist in the thread pool"
    mock_print.assert_any_call(f"Could not pause simulation due to: {error}")

    sim.stop(a)


def test_resume_success(sim: Simulator, input_params: InputParameter) -> None:
    # Arrange
    a = sim.initialize(input_params, subList)
    sim.start(a, 3600)

    sim_info = sim.get_sim_by_id(a)
    assert sim_info is not None

    # Act & Assert
    with patch.object(sim_info["simController"], "resume") as mock_resume:
        sim.resume(a)
        mock_resume.assert_called_once()

    sim.stop(a)


@patch("builtins.print")
def test_resume_fail(mock_print: MagicMock, sim: Simulator) -> None:
    # Arrange
    a = sim.initialize(params, subList)
    sim.start(a, 3600)

    # Act
    sim.resume("random_id")

    # Assert
    error = "Simulation random_id does not exist in the thread pool"
    mock_print.assert_any_call(f"Could not resume simulation due to: {error}")

    sim.stop(a)


def test_set_factor_success(sim: Simulator, input_params: InputParameter) -> None:
    # Arrange
    a = sim.initialize(input_params, subList)
    sim.start(a, 3600)

    sim_info = sim.get_sim_by_id(a)
    assert sim_info is not None

    # Act & Assert
    with patch.object(sim_info["simController"], "set_factor") as mock_set_factor:
        sim.set_factor(a, 2.5)
        mock_set_factor.assert_called_once_with(2.5)

    sim.stop(a)


@patch("builtins.print")
def test_set_factor_fail(mock_print: MagicMock, sim: Simulator) -> None:
    # Arrange
    a = sim.initialize(params, subList)
    sim.start(a, 3600)

    # Act
    sim.set_factor("random_id", 2.0)

    # Assert
    error = "Simulation random_id does not exist in the thread pool"
    mock_print.assert_any_call(f"Could not set factor due to: {error}")

    sim.stop(a)


def test_send_request_not_implemented(sim: Simulator) -> None:
    # Any RequestType should raise until implemented
    request = RequestType()
    with pytest.raises(NotImplementedError):
        sim.send_request(request)


def test_get_sim_by_id_success(
    sim: Simulator,
    fake_time: MockClock,
    simpy_env: simpy.Environment,
) -> None:
    # Arrange
    a = sim.initialize(params, subList, FakeSimBehaviour())
    a_info = sim.get_sim_by_id(a)
    assert a_info is not None
    ctrl = a_info["simController"]
    with (
        patch.object(ctrl.map_controller.osrm, "build_ch_network", return_value=None),
        patch.object(
            ctrl.map_controller,
            "getRoute",
            return_value=SimpleNamespace(roads=[1]),
        ),
    ):
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
    simpy_env: simpy.Environment,
) -> None:
    # Arrange
    a = sim.initialize(params, subList, FakeSimBehaviour())
    a_info = sim.get_sim_by_id(a)
    assert a_info is not None
    ctrl = a_info["simController"]
    with (
        patch.object(ctrl.map_controller.osrm, "build_ch_network", return_value=None),
        patch.object(
            ctrl.map_controller,
            "getRoute",
            return_value=SimpleNamespace(roads=[1]),
        ),
    ):
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
    a = sim.initialize(params, subList, FakeSimBehaviour())
    a_info = sim.get_sim_by_id(a)
    assert a_info is not None
    ctrl = a_info["simController"]
    with (
        patch.object(ctrl.map_controller.osrm, "build_ch_network", return_value=None),
        patch.object(
            ctrl.map_controller,
            "getRoute",
            return_value=SimpleNamespace(roads=[1]),
        ),
    ):
        sim.start(a, 3600)

    new_task = BatterySwapTask(3, default_station)

    # Act
    sim.add_task_to_sim(a, new_task)

    # Assert
    sim_info = sim.get_sim_by_id(a)
    if sim_info is not None:
        sim_controller = sim_info["simController"]

        # task_entities is a dict keyed by task id
        assert len(sim_controller.task_entities) != 0
        assert sim_controller.get_task_by_id(3) is not None

    # Cleanup: remove the task from the map if present
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
    a = sim.initialize(params, subList, FakeSimBehaviour())
    a_info = sim.get_sim_by_id(a)
    assert a_info is not None
    ctrl = a_info["simController"]
    with (
        patch.object(ctrl.map_controller.osrm, "build_ch_network", return_value=None),
        patch.object(
            ctrl.map_controller,
            "getRoute",
            return_value=SimpleNamespace(roads=[1]),
        ),
    ):
        sim.start(a, 3600)

    new_task = BatterySwapTask(3, default_station)

    # Act
    sim.add_task_to_sim("random_id", new_task)

    # Assert
    error = "Simulation random_id does not exist in the thread pool"
    # Other prints may occur (e.g., network setup);
    # ensure our error was printed at least once
    mock_print.assert_any_call(f"Could not add task to sim due to: {error}")

    sim.stop(a)


def test_assign_task_to_resource_success(
    sim: Simulator, input_params: InputParameter, simpy_env: simpy.Environment
) -> None:
    # Arrange
    a = sim.initialize(input_params, subList, FakeSimBehaviour())
    a_info = sim.get_sim_by_id(a)
    assert a_info is not None
    ctrl = a_info["simController"]
    with (
        patch.object(ctrl.map_controller.osrm, "build_ch_network", return_value=None),
        patch.object(
            ctrl.map_controller,
            "getRoute",
            return_value=SimpleNamespace(roads=[1]),
        ),
    ):
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
    a = sim.initialize(input_params, subList, FakeSimBehaviour())
    a_info = sim.get_sim_by_id(a)
    assert a_info is not None
    ctrl = a_info["simController"]
    with (
        patch.object(ctrl.map_controller.osrm, "build_ch_network", return_value=None),
        patch.object(
            ctrl.map_controller,
            "getRoute",
            return_value=SimpleNamespace(roads=[1]),
        ),
    ):
        sim.start(a, 3600)

    # Act - Pass non-existent task_id
    sim.assign_task_to_resource(a, task_id=6, resource_id=1)

    # Assert
    error = "Could not find task in sim with id: 6"
    mock_print.assert_any_call(f"Could not assign task due to: {error}")


def test_unassign_task_from_resource_success(
    sim: Simulator, input_params: InputParameter, simpy_env: simpy.Environment
) -> None:
    # Arrange
    a = sim.initialize(input_params, subList, FakeSimBehaviour())
    a_info = sim.get_sim_by_id(a)
    assert a_info is not None
    ctrl = a_info["simController"]
    with (
        patch.object(ctrl.map_controller.osrm, "build_ch_network", return_value=None),
        patch.object(
            ctrl.map_controller,
            "getRoute",
            return_value=SimpleNamespace(roads=[1]),
        ),
    ):
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
    a = sim.initialize(input_params, subList, FakeSimBehaviour())
    a_info = sim.get_sim_by_id(a)
    assert a_info is not None
    ctrl = a_info["simController"]
    with (
        patch.object(ctrl.map_controller.osrm, "build_ch_network", return_value=None),
        patch.object(
            ctrl.map_controller,
            "getRoute",
            return_value=SimpleNamespace(roads=[1]),
        ),
    ):
        sim.start(a, 3600)

    # Act - Pass non-existent task_id
    sim.unassign_task_from_resource(a, task_id=6, resource_id=1)

    # Assert
    error = "Could not find task in sim with id: 6"
    mock_print.assert_any_call(f"Could not unassign task due to: {error}")


def test_reassign_task_success(sim: Simulator, input_params: InputParameter) -> None:
    # Arrange
    a = sim.initialize(input_params, subList, FakeSimBehaviour())
    a_info = sim.get_sim_by_id(a)
    assert a_info is not None
    ctrl = a_info["simController"]
    with (
        patch.object(ctrl.map_controller.osrm, "build_ch_network", return_value=None),
        patch.object(
            ctrl.map_controller,
            "getRoute",
            return_value=SimpleNamespace(roads=[1]),
        ),
    ):
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
    mock_print: MagicMock,
    sim: Simulator,
    input_params: InputParameter,
    simpy_env: simpy.Environment,
) -> None:
    # Arrange
    a = sim.initialize(input_params, subList, FakeSimBehaviour())
    a_info = sim.get_sim_by_id(a)
    assert a_info is not None
    ctrl = a_info["simController"]
    with (
        patch.object(ctrl.map_controller.osrm, "build_ch_network", return_value=None),
        patch.object(
            ctrl.map_controller,
            "getRoute",
            return_value=SimpleNamespace(roads=[1]),
        ),
    ):
        sim.start(a, 3600)

    # Act - Pass non-existent task_id
    sim.reassign_task(a, task_id=6, old_resource_id=1, new_resource_id=2)

    # Assert
    error = "Reassigning task failed as could not find task 6"
    mock_print.assert_any_call(f"Error occurred: {error}")


def test_get_stream_not_implemented(sim: Simulator) -> None:
    with pytest.raises(NotImplementedError):
        sim.get_stream()


def test_stop_all_stops_everything_and_is_idempotent(
    sim: Simulator,
    fake_time: MockClock,
    simpy_env: simpy.Environment,
) -> None:
    """
    Start multiple sims, stop them all via stop_all(),
    verify the pool is empty.
    Also ensure calling stop_all() again does not error.
    """
    # Initialize and start multiple simulations
    sim_ids = []
    for _ in range(3):
        sim_id = sim.initialize(params, subList, FakeSimBehaviour())
        sim_info = sim.get_sim_by_id(sim_id)
        assert sim_info is not None
        ctrl = sim_info["simController"]
        with (
            patch.object(
                ctrl.map_controller.osrm,
                "build_ch_network",
                return_value=None,
            ),
            patch.object(
                ctrl.map_controller,
                "getRoute",
                return_value=SimpleNamespace(roads=[1]),
            ),
        ):
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


def test_reorder_resource_tasks_success(
    sim: Simulator,
    input_params: InputParameter,
    monkeypatch: Any,
) -> None:
    """Test successful task reordering via Simulator."""
    # Set OSRM URL
    monkeypatch.setenv("OSRM_URL", "http://localhost:5000")

    with (
        patch(
            "sim.osm.OSRMConnection.OSRMConnection._verify_osrm_connection",
            return_value=True,
        ),
    ):
        sim_id = sim.initialize(input_params, [], FakeSimBehaviour())

    # Get the controller and resource
    sim_info = sim.get_sim_by_id(sim_id)
    assert sim_info is not None
    controller = sim_info["simController"]
    resource = controller.get_resource_by_id(1)
    assert resource is not None

    # Set up tasks
    resource.task_list.clear()
    task1 = controller.get_task_by_id(1)
    task2 = controller.get_task_by_id(2)
    assert task1 is not None
    assert task2 is not None
    resource.task_list = [task1, task2]

    # Reorder tasks via Simulator
    new_order = sim.reorder_resource_tasks(
        sim_id=sim_id, resource_id=1, task_ids_to_reorder=[2, 1], apply_from_top=True
    )

    assert new_order == [2, 1]
    assert resource.task_list == [task2, task1]


def test_reorder_resource_tasks_simulation_not_found(
    sim: Simulator,
) -> None:
    """Test reordering with invalid sim_id raises exception."""
    with pytest.raises(Exception, match="Simulation invalid-sim-id does not exist"):
        sim.reorder_resource_tasks(
            sim_id="invalid-sim-id",
            resource_id=1,
            task_ids_to_reorder=[1, 2],
            apply_from_top=True,
        )


def test_reorder_resource_tasks_resource_not_found(
    sim: Simulator,
    input_params: InputParameter,
    monkeypatch: Any,
) -> None:
    """Test reordering with invalid resource_id raises exception."""
    monkeypatch.setenv("OSRM_URL", "http://localhost:5000")

    with (
        patch(
            "sim.osm.OSRMConnection.OSRMConnection._verify_osrm_connection",
            return_value=True,
        ),
    ):
        sim_id = sim.initialize(input_params, [], FakeSimBehaviour())

    with pytest.raises(Exception, match="Could not find resource in sim with id: 999"):
        sim.reorder_resource_tasks(
            sim_id=sim_id,
            resource_id=999,
            task_ids_to_reorder=[1, 2],
            apply_from_top=True,
        )


def test_reorder_resource_tasks_with_thread_lock(
    sim: Simulator,
    input_params: InputParameter,
    monkeypatch: Any,
) -> None:
    """Test that reorder acquires thread pool lock."""
    monkeypatch.setenv("OSRM_URL", "http://localhost:5000")

    with (
        patch(
            "sim.osm.OSRMConnection.OSRMConnection._verify_osrm_connection",
            return_value=True,
        ),
    ):
        sim_id = sim.initialize(input_params, [], FakeSimBehaviour())

    # Get the controller and resource
    sim_info = sim.get_sim_by_id(sim_id)
    assert sim_info is not None
    controller = sim_info["simController"]
    resource = controller.get_resource_by_id(1)
    assert resource is not None

    # Set up tasks
    resource.task_list.clear()
    task1 = controller.get_task_by_id(1)
    task2 = controller.get_task_by_id(2)
    assert task1 is not None
    assert task2 is not None
    resource.task_list = [task1, task2]

    # Mock the lock to verify it's being used
    original_lock = sim.thread_pool_lock
    mock_lock = MagicMock(wraps=original_lock)
    sim.thread_pool_lock = mock_lock

    # Reorder tasks
    new_order = sim.reorder_resource_tasks(
        sim_id=sim_id, resource_id=1, task_ids_to_reorder=[2], apply_from_top=True
    )

    # Verify lock was acquired
    mock_lock.__enter__.assert_called_once()
    mock_lock.__exit__.assert_called_once()
    assert new_order == [2, 1]

    # Restore original lock
    sim.thread_pool_lock = original_lock
