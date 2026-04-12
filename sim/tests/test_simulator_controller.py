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

import simpy
import pytest
from typing import List, Any
from unittest.mock import Mock, patch

from sim.core.simulator_controller import SimulatorController
from sim.core.frame_emitter import FrameEmitter
from sim.core.simulation_environment import SimulationEnvironment
from sim.entities.input_parameter import InputParameter
from sim.entities.frame import Frame
from sim.entities.station import Station
from sim.entities.driver import Driver, DriverState
from sim.entities.shift import Shift
from sim.entities.battery_swap_task import BatterySwapTask
from sim.entities.position import Position
from sim.entities.task_state import State
from sim.utils.subscriber import Subscriber
from sim.behaviour.sim_behaviour import SimBehaviour
import sim.core.real_time_driver as rtd
import sim.core.simulator_controller as sc_mod
from types import SimpleNamespace


class FakeTPUStrategy:
    def check_for_new_task(self, station: Station) -> List[BatterySwapTask]:
        return []


class FakeRCNTStrategy:
    def select_next_task(self, driver: Driver) -> None:
        return None


class FakeSimBehaviour(SimBehaviour):
    def __init__(self) -> None:
        super().__init__()
        self.TPU_strategy = FakeTPUStrategy()  # type: ignore[assignment]
        self.RCNT_strategy = FakeRCNTStrategy()  # type: ignore[assignment]


# Real time driver depends on real time passing by. Too slow for tests.
# Use fake time to run tests instantly
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


class FakeSubscriber(Subscriber):
    def __init__(self) -> None:
        self.received: List[Frame] = []

    def on_frame(self, frame: Frame) -> None:
        self.received.append(frame)


@pytest.fixture()
def env() -> SimulationEnvironment:
    return SimulationEnvironment()


@pytest.fixture()
def fake_time(monkeypatch: Any) -> MockClock:
    clock = MockClock()
    # Replace time methods in RealTimeDriver and SimulatorController modules
    monkeypatch.setattr(rtd.time, "perf_counter", clock.perf_counter)
    monkeypatch.setattr(rtd.time, "sleep", clock.sleep)
    # Prevent actual thread start
    monkeypatch.setattr(sc_mod.threading.Thread, "start", lambda self: None)
    return clock


@pytest.fixture()
def frame_emitter() -> FrameEmitter:
    return FrameEmitter("test-sim-123")


@pytest.fixture()
def input_params(env: SimulationEnvironment) -> InputParameter:
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

    # Add test drivers
    shift1 = Shift(
        start_time=28800,
        end_time=43200,
        lunch_break=36000,
        sim_start_time=0,
    )
    shift2 = Shift(
        start_time=28900,
        end_time=43200,
        lunch_break=38000,
        sim_start_time=0,
    )
    # Ensure Driver.env is set before creating Driver instances
    Driver.env = env
    driver1 = Driver(driver_id=1, position=Position([15.0, 25.0]), shift=shift1)
    driver2 = Driver(driver_id=2, position=Position([35.0, 45.0]), shift=shift2)
    # Stub initial state for tests that access driver.state
    driver1.state = DriverState.IDLE
    driver2.state = DriverState.IDLE
    params.add_driver(driver1)
    params.add_driver(driver2)

    # Add test tasks using concrete BatterySwapTask
    task1 = BatterySwapTask(task_id=1, station=station1)
    task2 = BatterySwapTask(task_id=2, station=station2)
    params.add_task(task1)
    params.add_task(task2)

    return params


@pytest.fixture()
def simulator_controller(
    env: SimulationEnvironment,
    frame_emitter: FrameEmitter,
    input_params: InputParameter,
    fake_time: MockClock,
    monkeypatch: Any,
) -> SimulatorController:
    # Set GraphHopper URL environment variable to avoid ValueError
    monkeypatch.setenv("GRAPHHOPPER_URL", "http://localhost:8989")

    # Mock GraphHopperConnection initialization to avoid file I/O
    with (
        patch(
            "sim.osm.graphhopper_connection"
            ".GraphHopperConnection"
            "._verify_graphhopper_connection",
            return_value=True,
        ),
    ):
        controller = SimulatorController(
            sim_env=env,
            frame_emitter=frame_emitter,
            input_parameters=input_params,
            sim_behaviour=FakeSimBehaviour(),
            strict=False,
        )
    controller.sim_time = 0
    return controller


def test_simulator_controller_initialization(
    simulator_controller: SimulatorController, input_params: InputParameter
) -> None:
    """Test that SimulatorController initializes correctly with proper attributes."""
    # Check that the map has the expected attributes
    assert simulator_controller.sim_env is not None
    assert simulator_controller.frame_emitter is not None
    assert simulator_controller.real_time_driver is not None
    assert simulator_controller.clock is not None

    # Check that entities are properly loaded from InputParameter
    assert len(simulator_controller.station_entities) == 2
    assert len(simulator_controller.driver_entities) == 2
    assert len(simulator_controller.task_entities) == 2

    # Check keyframe frequency
    assert simulator_controller.keyframe_freq == 20  # default value

    # Check frame counter initialization
    assert simulator_controller.frame_counter == 0


def test_emit_initial_frame(
    simulator_controller: SimulatorController, frame_emitter: FrameEmitter
) -> None:
    """Test that emit_initial_frame creates and emits a frame."""
    subscriber = FakeSubscriber()
    frame_emitter.attach(subscriber)

    simulator_controller.emit_initial_frame()

    # Check that a frame was emitted
    assert len(subscriber.received) == 1
    frame = subscriber.received[0]

    # Check frame structure
    assert frame.seq_number == 0
    assert "simId" in frame.payload_dict
    assert "tasks" in frame.payload_dict
    assert "stations" in frame.payload_dict
    assert "drivers" in frame.payload_dict
    assert "vehicles" in frame.payload_dict
    assert "clock" in frame.payload_dict

    # Check that frame counter was incremented
    assert simulator_controller.frame_counter == 1


def test_create_key_frame(simulator_controller: SimulatorController) -> None:
    """Test that create_frame generates a complete frame with all entities."""
    frame = simulator_controller.create_frame(is_key=True)

    # Check frame structure
    assert frame.seq_number == 0
    assert isinstance(frame.payload_dict, dict)

    payload = frame.payload_dict
    assert "simId" in payload
    assert "tasks" in payload
    assert "stations" in payload
    assert "drivers" in payload
    assert "vehicles" in payload
    assert "clock" in payload
    assert "reporting" in payload

    # Check that all entities are included in key frame
    assert len(payload["tasks"]) == 2
    assert len(payload["stations"]) == 2
    assert len(payload["drivers"]) == 2

    # Check task structure
    task = payload["tasks"][0]
    assert "id" in task
    assert "state" in task
    assert "stationId" in task
    assert "assignedDriverId" in task

    # Check station structure
    station = payload["stations"][0]
    assert "id" in station
    assert "name" in station
    assert "position" in station
    assert "taskIds" in station

    # Check driver structure
    driver = payload["drivers"][0]
    assert "id" in driver
    assert "position" in driver
    assert "taskIds" in driver
    assert "inProgressTaskId" in driver

    reporting = payload["reporting"]
    assert reporting["vehicleDistanceTraveled"] == pytest.approx(
        simulator_controller.sim_env.report.get_vehicle_distance_traveled()
    )


def test_create_diff_frame(simulator_controller: SimulatorController) -> None:
    """Test that create_frame generates a frame with only updated entities."""
    # Mark one entity as updated (using ID keys instead of indices)
    simulator_controller.station_entities[1].has_updated = True
    simulator_controller.task_entities[1].has_updated = True
    simulator_controller.driver_entities[1].has_updated = True
    # Ensure driver is not filtered out due to off_shift state
    driver = simulator_controller.driver_entities[1]
    # Set a non-off-shift state so it appears in diff frames
    driver.state = driver.get_state()  # keep current if valid
    # Force to IDLE to satisfy diff-frame inclusion
    from sim.entities.driver import DriverState

    driver.state = DriverState.IDLE

    frame = simulator_controller.create_frame(is_key=False)

    # Check frame structure
    assert frame.seq_number == 0
    assert isinstance(frame.payload_dict, dict)

    payload = frame.payload_dict

    # Check that only updated entities are included
    assert len(payload["tasks"]) == 1
    assert len(payload["stations"]) == 1
    assert len(payload["drivers"]) == 1


def test_emit_frame_with_provided_frame(
    simulator_controller: SimulatorController, frame_emitter: FrameEmitter
) -> None:
    """Test emit_frame when a frame is provided."""
    subscriber = FakeSubscriber()
    frame_emitter.attach(subscriber)

    custom_frame = Frame(seq_numb=99, payload={"test": "data"})
    simulator_controller.emit_frame(custom_frame)

    # Check that the custom frame was emitted
    assert len(subscriber.received) == 1
    assert subscriber.received[0] == custom_frame

    # Check that frame counter was incremented
    assert simulator_controller.frame_counter == 1


def test_emit_frame_without_provided_frame_key_frame(
    simulator_controller: SimulatorController, frame_emitter: FrameEmitter
) -> None:
    """Test emit_frame without provided frame creates key frame when
    frameCounter is multiple of keyframeFreq."""
    subscriber = FakeSubscriber()
    frame_emitter.attach(subscriber)

    # Set frame counter to multiple of keyframe frequency
    simulator_controller.frame_counter = 60  # Should create key frame

    simulator_controller.emit_frame()

    # Check that a frame was emitted
    assert len(subscriber.received) == 1
    frame = subscriber.received[0]

    # Should be a key frame (includes all entities)
    assert len(frame.payload_dict["tasks"]) == 2
    assert len(frame.payload_dict["stations"]) == 2
    assert len(frame.payload_dict["drivers"]) == 2


def test_emit_frame_without_provided_frame_diff_frame(
    simulator_controller: SimulatorController, frame_emitter: FrameEmitter
) -> None:
    """Test emit_frame without provided frame creates diff frame when
    sim time in seconds is not multiple of keyframeFreq."""
    subscriber = FakeSubscriber()
    frame_emitter.attach(subscriber)

    # Mark some entities as updated (using ID keys instead of indices)
    simulator_controller.station_entities[1].has_updated = True
    simulator_controller.clock.sim_time_seconds = 1  # Should create diff frame
    simulator_controller.sim_time = 3600

    simulator_controller.emit_frame()

    # Check that a frame was emitted
    assert len(subscriber.received) == 1
    frame = subscriber.received[0]

    # Should be a diff frame (only updated entities)
    assert len(frame.payload_dict["stations"]) == 1
    assert len(frame.payload_dict["tasks"]) == 0  # No tasks marked as updated
    assert len(frame.payload_dict["drivers"]) == 0  # No resources marked as updated


def test_emit_frame_clears_update_flags(
    simulator_controller: SimulatorController, frame_emitter: FrameEmitter
) -> None:
    subscriber = FakeSubscriber()
    frame_emitter.attach(subscriber)

    # Mark entities as updated
    simulator_controller.station_entities[1].has_updated = True
    simulator_controller.task_entities[1].has_updated = True
    simulator_controller.driver_entities[1].has_updated = True

    # Emit a provided frame to avoid depending on internal selection
    custom_frame = Frame(seq_numb=0, payload={})
    simulator_controller.emit_frame(custom_frame)

    assert simulator_controller.station_entities[1].has_updated is False
    assert simulator_controller.task_entities[1].has_updated is False
    assert simulator_controller.driver_entities[1].has_updated is False


def test_controller_batch_assign_success(
    simulator_controller: SimulatorController,
) -> None:
    """All tasks exist and are assigned successfully via controller batch helper."""
    # Patch the low-level assign so this unit test runs instantly
    with patch.object(
        simulator_controller, "assign_task_to_driver", return_value=None
    ) as mock_assign:
        results = simulator_controller.batch_assign_tasks_to_driver(1, [1, 2])
        mock_assign.assert_any_call(1, 1)
        mock_assign.assert_any_call(2, 1)

    assert isinstance(results, list)
    assert len(results) == 2
    assert all(r.get("success") is True for r in results)


def test_controller_batch_assign_partial_failure(
    simulator_controller: SimulatorController,
) -> None:
    """Missing tasks return success=False and include an error string."""
    # Task 1 exists (unassigned), task 999 does not exist
    mock_task = Mock()
    mock_task.get_assigned_driver.return_value = None

    def get_task_side_effect(task_id: int) -> Mock | None:
        return mock_task if task_id == 1 else None

    with (
        patch.object(
            simulator_controller, "get_task_by_id", side_effect=get_task_side_effect
        ),
        patch.object(
            simulator_controller, "assign_task_to_driver", return_value=None
        ) as mock_assign,
    ):
        results = simulator_controller.batch_assign_tasks_to_driver(1, [1, 999])
        # Only task 1 should trigger assign (task 999 fails at lookup)
        mock_assign.assert_called_once_with(1, 1)

    assert len(results) == 2
    assert results[0]["success"] is True
    assert results[1]["success"] is False
    assert "Could not find task" in (results[1]["error"] or "")


def test_controller_batch_assign_with_reassignment(
    simulator_controller: SimulatorController,
) -> None:
    """Tasks already assigned to different driver are reassigned successfully."""
    # Simulate task already assigned to driver 2, reassigning to driver 1
    mock_task = Mock()
    mock_task.get_assigned_driver.return_value = Mock(id=2)

    with (
        patch.object(simulator_controller, "get_task_by_id", return_value=mock_task),
        patch.object(
            simulator_controller, "reassign_task", return_value=None
        ) as mock_reassign,
    ):
        results = simulator_controller.batch_assign_tasks_to_driver(1, [1])
        mock_reassign.assert_called_once_with(1, 2, 1)

    assert len(results) == 1
    assert results[0]["success"] is True
    assert results[0]["driver_id"] == 1
    assert results[0]["task_id"] == 1


def test_controller_batch_assign_already_assigned_to_same_driver(
    simulator_controller: SimulatorController,
) -> None:
    """Tasks already assigned to target driver are treated as no-op success."""
    # Task already assigned to driver 1, batch assigning to driver 1 should be no-op
    mock_task = Mock()
    mock_task.get_assigned_driver.return_value = Mock(id=1)

    with (
        patch.object(simulator_controller, "get_task_by_id", return_value=mock_task),
        patch.object(
            simulator_controller, "assign_task_to_driver", return_value=None
        ) as mock_assign,
        patch.object(
            simulator_controller, "reassign_task", return_value=None
        ) as mock_reassign,
    ):
        results = simulator_controller.batch_assign_tasks_to_driver(1, [1])
        # Neither assign nor reassign should be called
        mock_assign.assert_not_called()
        mock_reassign.assert_not_called()

    assert len(results) == 1
    assert results[0]["success"] is True


def test_controller_batch_assign_mixed_fresh_and_reassign(
    simulator_controller: SimulatorController,
) -> None:
    """Batch handles mix of unassigned tasks and already-assigned tasks."""
    # Task 1: unassigned (fresh assign)
    # Task 2: assigned to driver 2 (reassign to driver 1)
    # Task 3: assigned to driver 1 (no-op)
    mock_task_unassigned = Mock()
    mock_task_unassigned.get_assigned_driver.return_value = None

    mock_task_other_driver = Mock()
    mock_task_other_driver.get_assigned_driver.return_value = Mock(id=2)

    mock_task_same_driver = Mock()
    mock_task_same_driver.get_assigned_driver.return_value = Mock(id=1)

    task_map = {
        1: mock_task_unassigned,
        2: mock_task_other_driver,
        3: mock_task_same_driver,
    }

    with (
        patch.object(
            simulator_controller,
            "get_task_by_id",
            side_effect=lambda tid: task_map.get(tid),
        ),
        patch.object(
            simulator_controller, "assign_task_to_driver", return_value=None
        ) as mock_assign,
        patch.object(
            simulator_controller, "reassign_task", return_value=None
        ) as mock_reassign,
    ):
        results = simulator_controller.batch_assign_tasks_to_driver(1, [1, 2, 3])
        # Fresh assign called for task 1
        mock_assign.assert_called_once_with(1, 1)
        # Reassign called for task 2 (from driver 2 to driver 1)
        mock_reassign.assert_called_once_with(2, 2, 1)

    assert len(results) == 3
    assert all(r["success"] is True for r in results)


def test_controller_batch_unassign_success(
    simulator_controller: SimulatorController,
) -> None:
    """Batch unassign succeeds when tasks are assigned and not in-service."""
    mock_task_1 = Mock()
    mock_task_1.get_state.return_value = State.ASSIGNED
    mock_task_1.get_assigned_driver.return_value = Mock(id=1)

    mock_task_2 = Mock()
    mock_task_2.get_state.return_value = State.IN_PROGRESS
    mock_task_2.get_assigned_driver.return_value = Mock(id=2)

    with (
        patch.object(
            simulator_controller,
            "get_task_by_id",
            side_effect=lambda tid: {1: mock_task_1, 2: mock_task_2}.get(tid),
        ),
        patch.object(
            simulator_controller, "unassign_task_from_driver", return_value=None
        ) as mock_unassign,
    ):
        results = simulator_controller.batch_unassign_tasks_from_drivers([1, 2])
        mock_unassign.assert_any_call(1, 1)
        mock_unassign.assert_any_call(2, 2)

    assert len(results) == 2
    assert all(r["success"] is True for r in results)


def test_controller_batch_unassign_in_service_returns_failure(
    simulator_controller: SimulatorController,
) -> None:
    """IN_SERVICE tasks are rejected and reported as failures."""
    mock_task = Mock()
    mock_task.get_state.return_value = State.IN_SERVICE
    mock_task.get_assigned_driver.return_value = Mock(id=1)

    with patch.object(simulator_controller, "get_task_by_id", return_value=mock_task):
        results = simulator_controller.batch_unassign_tasks_from_drivers([1])

    assert len(results) == 1
    assert results[0]["success"] is False
    assert results[0]["driver_id"] == 1
    assert "currently in service" in (results[0]["error"] or "")


def test_controller_batch_unassign_missing_or_unassigned_failure(
    simulator_controller: SimulatorController,
) -> None:
    """Missing tasks fail; already-unassigned tasks are successful no-ops."""
    mock_task = Mock()
    mock_task.get_state.return_value = State.OPEN
    mock_task.get_assigned_driver.return_value = None

    with patch.object(
        simulator_controller,
        "get_task_by_id",
        side_effect=lambda tid: None if tid == 999 else mock_task,
    ):
        results = simulator_controller.batch_unassign_tasks_from_drivers([999, 1])

    assert len(results) == 2
    assert results[0]["success"] is False
    assert "Could not find task" in (results[0]["error"] or "")
    assert results[1]["success"] is True
    assert results[1]["driver_id"] is None
    assert results[1]["error"] is None


def test_key_frame_includes_new_tasks_and_clears_popups(
    env: simpy.Environment,
    simulator_controller: SimulatorController,
) -> None:
    station1 = simulator_controller.get_station_by_id(1)
    assert station1 is not None
    # create a popup task and attach to station
    new_task = BatterySwapTask(task_id=99, station=station1)
    station1.pop_up_tasks.append(new_task)

    frame = simulator_controller.create_frame(is_key=True)
    payload = frame.payload_dict
    assert "tasks" in payload
    assert any(t["id"] == 99 for t in payload["tasks"])
    # ensure task added to map task_entities
    assert simulator_controller.get_task_by_id(99) is not None
    # ensure popups cleared after frame generation
    assert station1.pop_up_tasks == []


def test_pause_and_resume(simulator_controller: SimulatorController) -> None:
    """Test pause and resume functionality."""
    # Mock the real time driver methods
    with (
        patch.object(simulator_controller.real_time_driver, "pause") as mock_pause,
        patch.object(simulator_controller.real_time_driver, "resume") as mock_resume,
    ):

        simulator_controller.pause()
        mock_pause.assert_called_once()

        simulator_controller.resume()
        mock_resume.assert_called_once()


def test_stop(simulator_controller: SimulatorController) -> None:
    """Test stop functionality."""
    # Mock the real time driver stop method
    with patch.object(simulator_controller.real_time_driver, "stop") as mock_stop:
        simulator_controller.stop()
        mock_stop.assert_called_once()


def test_set_factor(simulator_controller: SimulatorController) -> None:
    """Test set_factor functionality."""
    # Mock the real time driver set_real_time_factor method
    with patch.object(
        simulator_controller.real_time_driver, "set_real_time_factor"
    ) as mock_set_factor:
        simulator_controller.set_factor(2.0)
        mock_set_factor.assert_called_once_with(2.0)


def test_add_task_success(
    env: simpy.Environment, simulator_controller: SimulatorController
) -> None:
    """Test add_task functionality"""
    # Arrange
    task_id = 3
    station1 = simulator_controller.get_station_by_id(1)
    new_task = BatterySwapTask(task_id, station1)

    # Act
    simulator_controller.add_task(new_task)

    # Assert
    assert simulator_controller.get_task_by_id(task_id) is not None
    assert new_task in simulator_controller.task_entities.values()


def test_add_task_fail(
    env: simpy.Environment, simulator_controller: SimulatorController
) -> None:
    """Test add_task functionality with existent task id"""
    # Arrange
    task_id = 2
    station1 = simulator_controller.get_station_by_id(1)
    new_task = BatterySwapTask(task_id, station1)

    # Act and Assert
    with pytest.raises(Exception, match=f"Task with id {task_id} already exists"):
        simulator_controller.add_task(new_task)
    # Verify map state was not mutated: the existing task with id=2 remains,
    # and the map does not hold a reference to the new_task instance.
    existing = simulator_controller.get_task_by_id(task_id)
    assert existing is not None
    assert existing is not new_task
    # Optionally ensure the size did not grow
    assert set(simulator_controller.task_entities.keys()) == {1, 2}


def test_assign_task_to_driver_success(
    simulator_controller: SimulatorController,
) -> None:
    """Test assign_task_to_driver functionality."""
    # Arrange
    task_id = 1
    driver_id = 1

    # Act
    simulator_controller.assign_task_to_driver(task_id, driver_id)

    # Assert
    task = simulator_controller.get_task_by_id(task_id)
    driver = simulator_controller.get_driver_by_id(driver_id)
    assert task is not None
    assert driver is not None
    assert task.get_assigned_driver() == driver
    assert driver.get_task_list()[0] == task


def test_assign_task_to_driver_with_bad_task_id(
    simulator_controller: SimulatorController,
) -> None:
    """Test assign_task_to_driver functionality with an invalid task_id."""
    # Arrange
    task_id = 6  # Non-existent id
    driver_id = 1

    # Act and Assert
    with pytest.raises(
        Exception, match=f"Could not find task in sim with id: {task_id}"
    ):
        simulator_controller.assign_task_to_driver(task_id, driver_id)


def test_assign_task_to_driver_with_bad_driver_id(
    simulator_controller: SimulatorController,
) -> None:
    """Test assign_task_to_driver functionality with an invalid driver_id."""
    # Arrange
    task_id = 1
    driver_id = 6  # Non-existent id

    # Act and Assert
    with pytest.raises(
        Exception, match=f"Could not find driver in sim with id: {driver_id}"
    ):
        simulator_controller.assign_task_to_driver(task_id, driver_id)


def test_unassign_task_from_driver_success(
    simulator_controller: SimulatorController,
) -> None:
    """Test unassign_task_from_driver functionality."""
    # Arrange
    task_id = 1
    driver_id = 1
    simulator_controller.assign_task_to_driver(task_id, driver_id)

    # Act
    simulator_controller.unassign_task_from_driver(task_id, driver_id)

    # Assert
    task = simulator_controller.get_task_by_id(task_id)
    driver = simulator_controller.get_driver_by_id(driver_id)
    assert task is not None
    assert driver is not None
    assert task.get_assigned_driver() is None
    assert driver.get_task_count() == 0


def test_unassign_task_from_driver_with_bad_task_id(
    simulator_controller: SimulatorController,
) -> None:
    """Test unassign_task_from_driver functionality with an invalid task_id."""
    # Arrange
    task_id = 6  # Non-existent id
    driver_id = 1

    # Act and Assert
    with pytest.raises(
        Exception, match=f"Could not find task in sim with id: {task_id}"
    ):
        simulator_controller.unassign_task_from_driver(task_id, driver_id)


def test_unassign_task_from_driver_with_bad_driver_id(
    simulator_controller: SimulatorController,
) -> None:
    """Test unassign_task_from_driver functionality with an invalid driver_id."""
    # Arrange
    task_id = 1
    driver_id = 6  # Non-existent id

    # Act and Assert
    with pytest.raises(
        Exception, match=f"Could not find driver in sim with id: {driver_id}"
    ):
        simulator_controller.unassign_task_from_driver(task_id, driver_id)


def test_unassign_task_from_driver_already_unassigned_raises(
    simulator_controller: SimulatorController,
) -> None:
    """Single-task unassign should fail when task has no assigned driver."""
    mock_task = Mock()
    mock_task.get_assigned_driver.return_value = None
    mock_driver = Mock()

    with (
        patch.object(simulator_controller, "get_task_by_id", return_value=mock_task),
        patch.object(
            simulator_controller, "get_driver_by_id", return_value=mock_driver
        ),
    ):
        with pytest.raises(Exception, match="not assigned to any driver"):
            simulator_controller.unassign_task_from_driver(task_id=1, driver_id=1)


def test_unassign_task_from_driver_in_service_raises(
    simulator_controller: SimulatorController,
) -> None:
    """Single-task unassign should fail for IN_SERVICE tasks."""
    assigned_driver = Mock(id=1)
    mock_task = Mock()
    mock_task.get_assigned_driver.return_value = assigned_driver
    mock_task.get_state.return_value = State.IN_SERVICE
    mock_driver = Mock()

    with (
        patch.object(simulator_controller, "get_task_by_id", return_value=mock_task),
        patch.object(
            simulator_controller, "get_driver_by_id", return_value=mock_driver
        ),
    ):
        with pytest.raises(Exception, match="currently in service"):
            simulator_controller.unassign_task_from_driver(task_id=1, driver_id=1)


def test_reassign_task_success(
    simulator_controller: SimulatorController,
) -> None:
    """Test reassign_task functionality"""
    # Arrange
    task_id = 1
    old_driver_id = 1
    new_driver_id = 2

    simulator_controller.assign_task_to_driver(task_id, old_driver_id)

    # Act
    simulator_controller.reassign_task(task_id, old_driver_id, new_driver_id)

    # Assert
    task = simulator_controller.get_task_by_id(task_id)
    assert task is not None
    old_driver = simulator_controller.get_driver_by_id(old_driver_id)
    assert old_driver is not None
    new_driver = simulator_controller.get_driver_by_id(new_driver_id)
    assert new_driver is not None
    assert task.get_assigned_driver() == new_driver
    assert task in new_driver.get_task_list()
    assert task not in old_driver.get_task_list()


def test_reassign_task_fail_with_bad_task_id(
    simulator_controller: SimulatorController,
) -> None:
    """Test reassign_task functionality with bad task_id"""
    # Arrange
    task_id = 6  # Non-existent task
    old_driver_id = 1
    new_driver_id = 2

    # Act and Assert
    with pytest.raises(
        Exception, match=f"Reassigning task failed as could not find task {task_id}"
    ):
        simulator_controller.reassign_task(task_id, old_driver_id, new_driver_id)


def test_reassign_task_fail_with_bad_old_driver_id(
    simulator_controller: SimulatorController,
) -> None:
    """Test reassign_task functionality with bad old_driver_id"""
    # Arrange
    task_id = 1
    old_driver_id = 6  # Non-existent driver
    new_driver_id = 2

    # Act and Assert
    with pytest.raises(
        Exception,
        match=f"Reassigning failed as could not find driver {old_driver_id}",
    ):
        simulator_controller.reassign_task(task_id, old_driver_id, new_driver_id)


def test_reassign_task_fail_with_bad_new_driver_id(
    simulator_controller: SimulatorController,
) -> None:
    """Test reassign_task functionality with bad new_driver_id"""
    # Arrange
    task_id = 1
    old_driver_id = 1
    new_driver_id = 6  # Non-existent driver

    simulator_controller.assign_task_to_driver(task_id, old_driver_id)

    # Act and Assert
    with pytest.raises(
        Exception,
        match=f"Reassigning failed as could not find driver {new_driver_id}",
    ):
        simulator_controller.reassign_task(task_id, old_driver_id, new_driver_id)

    task = simulator_controller.get_task_by_id(task_id)
    assert task is not None
    old_driver = simulator_controller.get_driver_by_id(old_driver_id)
    assert old_driver is not None
    assert task.get_assigned_driver() == old_driver
    assert task in old_driver.get_task_list()


def test_start_simulation(
    simulator_controller: SimulatorController, fake_time: MockClock
) -> None:
    """Test that start method properly starts the clock and creates a
    simulation thread."""
    # Mock the clock and thread creation
    with (
        patch.object(simulator_controller.clock, "run") as mock_clock_run,
        patch("threading.Thread") as mock_thread_class,
    ):

        mock_thread = Mock()
        mock_thread_class.return_value = mock_thread

        # Patch heavy routing
        with patch.object(
            simulator_controller.map_controller,
            "get_route",
            return_value=SimpleNamespace(roads=[1, 2]),
        ):
            simulator_controller.start(3600)

        # Check that clock was started
        mock_clock_run.assert_called_once()

        # Check that thread was created with correct parameters
        mock_thread_class.assert_called_once()
        _, kwargs = mock_thread_class.call_args
        assert callable(kwargs["target"])
        mock_thread.start.assert_called_once()

        # Check that thread was started
        mock_thread.start.assert_called_once()

        # Check that thread is stored
        assert simulator_controller.sim_thread == mock_thread


def test_custom_keyframe_frequency(
    env: SimulationEnvironment,
    frame_emitter: FrameEmitter,
    fake_time: MockClock,
    monkeypatch: Any,
) -> None:
    """Test that custom keyframe frequency is properly set."""
    # Set GraphHopper URL environment variable
    monkeypatch.setenv("GRAPHHOPPER_URL", "http://localhost:8989")

    params = InputParameter()
    params.set_key_frame_freq(30)  # Custom frequency

    with patch(
        "sim.osm.graphhopper_connection"
        ".GraphHopperConnection"
        "._verify_graphhopper_connection",
        return_value=True,
    ):
        controller = SimulatorController(
            sim_env=env,
            frame_emitter=frame_emitter,
            input_parameters=params,
            sim_behaviour=FakeSimBehaviour(),
            strict=False,
        )

    assert controller.keyframe_freq == 30


def test_strict_mode_initialization(
    env: SimulationEnvironment,
    frame_emitter: FrameEmitter,
    input_params: InputParameter,
    fake_time: MockClock,
    monkeypatch: Any,
) -> None:
    """Test that strict mode is properly passed to RealTimeDriver."""
    # Set GraphHopper URL environment variable
    monkeypatch.setenv("GRAPHHOPPER_URL", "http://localhost:8989")

    with patch(
        "sim.osm.graphhopper_connection"
        ".GraphHopperConnection"
        "._verify_graphhopper_connection",
        return_value=True,
    ):
        controller = SimulatorController(
            sim_env=env,
            frame_emitter=frame_emitter,
            input_parameters=input_params,
            sim_behaviour=FakeSimBehaviour(),
            strict=True,
        )

    # The strict parameter should be passed to RealTimeDriver
    assert controller.real_time_driver.strict is True


def test_reorder_driver_tasks_success(
    simulator_controller: SimulatorController, input_params: InputParameter
) -> None:
    """Test successful task reordering on a driver."""
    # Get a driver and add some tasks
    driver = simulator_controller.get_driver_by_id(1)
    assert driver is not None

    # Clear existing tasks and add new ones
    driver.task_list.clear()
    task1 = simulator_controller.get_task_by_id(1)
    task2 = simulator_controller.get_task_by_id(2)
    assert task1 is not None
    assert task2 is not None

    driver.task_list = [task1, task2]

    # Reorder tasks
    new_order = simulator_controller.reorder_driver_tasks(
        driver_id=1, task_ids_to_reorder=[2, 1], apply_from_top=True
    )

    assert new_order == [2, 1]
    assert driver.task_list == [task2, task1]


def test_reorder_driver_tasks_driver_not_found(
    simulator_controller: SimulatorController,
) -> None:
    """Test that reordering non-existent driver raises exception."""
    with pytest.raises(Exception, match="Could not find driver in sim with id: 999"):
        simulator_controller.reorder_driver_tasks(
            driver_id=999, task_ids_to_reorder=[1, 2], apply_from_top=True
        )


def test_reorder_driver_tasks_empty_list_raises_error(
    simulator_controller: SimulatorController,
) -> None:
    """Test that empty task list raises ValueError from driver layer."""
    with pytest.raises(ValueError, match="task_ids_to_reorder cannot be empty"):
        simulator_controller.reorder_driver_tasks(
            driver_id=1, task_ids_to_reorder=[], apply_from_top=True
        )


def test_reorder_driver_tasks_with_in_progress_tasks(
    simulator_controller: SimulatorController, input_params: InputParameter
) -> None:
    """Test reordering with in-progress tasks pinned to top."""
    driver = simulator_controller.get_driver_by_id(1)
    assert driver is not None

    # Add tasks and set one as in-progress
    driver.task_list.clear()
    task1 = simulator_controller.get_task_by_id(1)
    task2 = simulator_controller.get_task_by_id(2)
    assert task1 is not None
    assert task2 is not None

    task1.set_state(State.IN_PROGRESS)
    driver.task_list = [task1, task2]

    # Try to reorder - task1 should stay at top
    new_order = simulator_controller.reorder_driver_tasks(
        driver_id=1, task_ids_to_reorder=[2], apply_from_top=True
    )

    assert new_order == [2, 1]  # task2 specified, task1 moved back
    assert driver.task_list[0] == task2  # new in-progress task


def test_reorder_driver_tasks_bottom_mode(
    simulator_controller: SimulatorController, input_params: InputParameter
) -> None:
    """Test bottom mode task reordering."""
    driver = simulator_controller.get_driver_by_id(1)
    assert driver is not None

    # Set up tasks
    driver.task_list.clear()
    task1 = simulator_controller.get_task_by_id(1)
    task2 = simulator_controller.get_task_by_id(2)
    assert task1 is not None
    assert task2 is not None

    driver.task_list = [task1, task2]

    # Reorder with bottom mode
    new_order = simulator_controller.reorder_driver_tasks(
        driver_id=1, task_ids_to_reorder=[1], apply_from_top=False
    )

    # Expected: [2] (unspecified), [1] (specified, at bottom)
    assert new_order == [2, 1]
    assert driver.task_list == [task2, task1]


def test_create_frame_with_paused_by_user_true(
    simulator_controller: SimulatorController,
) -> None:
    """Test that create_frame includes pausedByUser=True in clock when specified."""
    frame = simulator_controller.create_frame(is_key=True, paused_by_user=True)

    payload = frame.payload_dict
    assert "clock" in payload
    clock = payload["clock"]
    assert "pausedByUser" in clock
    assert clock["pausedByUser"] is True


def test_create_frame_with_paused_by_user_false(
    simulator_controller: SimulatorController,
) -> None:
    """Test that create_frame includes pausedByUser=False in clock when specified."""
    frame = simulator_controller.create_frame(is_key=True, paused_by_user=False)

    payload = frame.payload_dict
    assert "clock" in payload
    clock = payload["clock"]
    assert "pausedByUser" in clock
    assert clock["pausedByUser"] is False


def test_create_frame_includes_running_state(
    simulator_controller: SimulatorController,
) -> None:
    """Test that create_frame includes running state from realTimeDriver."""
    # Driver should be running by default
    frame = simulator_controller.create_frame(is_key=True)

    payload = frame.payload_dict
    assert "clock" in payload
    clock = payload["clock"]
    assert "running" in clock
    assert clock["running"] is True

    # Pause and check again
    simulator_controller.real_time_driver.pause()
    frame_paused = simulator_controller.create_frame(is_key=True)
    clock_paused = frame_paused.payload_dict["clock"]
    assert "running" in clock_paused
    assert clock_paused["running"] is False


def test_create_frame_includes_real_time_factor(
    simulator_controller: SimulatorController,
) -> None:
    """Test that create_frame includes realTimeFactor from realTimeDriver."""
    # Default factor should be 1.0
    frame = simulator_controller.create_frame(is_key=True)

    payload = frame.payload_dict
    assert "clock" in payload
    clock = payload["clock"]
    assert "realTimeFactor" in clock
    assert clock["realTimeFactor"] == 1.0

    # Change factor and check again
    simulator_controller.real_time_driver.set_real_time_factor(0.5)  # 2x speed
    frame_fast = simulator_controller.create_frame(is_key=True)
    clock_fast = frame_fast.payload_dict["clock"]
    assert "realTimeFactor" in clock_fast
    assert clock_fast["realTimeFactor"] == 0.5


def test_stop_does_not_emit_keyframe_when_already_paused(
    simulator_controller: SimulatorController, frame_emitter: FrameEmitter
) -> None:
    """Test that stop() does NOT emit a keyframe when driver was already paused.

    This ensures that the correct keyframe emitted by user pause or cleanup_simulation
    is preserved and not overwritten by stop().
    """
    subscriber = FakeSubscriber()
    frame_emitter.attach(subscriber)

    # Pause the driver first (simulates user pausing or cleanup)
    simulator_controller.real_time_driver.pause()
    assert simulator_controller.real_time_driver.running is False

    # Now call stop
    simulator_controller.stop()

    # No keyframes should be emitted - the correct one was already emitted
    keyframes = [f for f in subscriber.received if f.is_key]
    assert len(keyframes) == 0


def test_stop_emits_keyframe_when_running(
    simulator_controller: SimulatorController, frame_emitter: FrameEmitter
) -> None:
    """Test that stop() emits final keyframe with pausedByUser=False when driver was
    running."""
    subscriber = FakeSubscriber()
    frame_emitter.attach(subscriber)

    # Driver should be running by default
    assert simulator_controller.real_time_driver.running is True

    # Call stop
    simulator_controller.stop()

    # A final keyframe should be emitted for naturally completing sims
    keyframes = [f for f in subscriber.received if f.is_key]
    assert len(keyframes) == 1
    final_keyframe = keyframes[-1]
    clock = final_keyframe.payload_dict["clock"]

    # The final frame should have pausedByUser=False since sim completed naturally
    assert clock["pausedByUser"] is False
