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
from typing import List, Any, Generator
from unittest.mock import Mock, patch

from sim.core.SimulatorController import SimulatorController
from sim.core.frame_emitter import FrameEmitter
from sim.entities.inputParameters import InputParameter
from sim.entities.frame import Frame
from sim.entities.station import Station
from sim.entities.resource import Resource
from sim.entities.BatterySwapTask import BatterySwapTask
from sim.entities.position import Position
from sim.utils.subscriber import Subscriber
from sim.behaviour.sim_behaviour import SimBehaviour
import sim.core.RealTimeDriver as rtd
import sim.core.SimulatorController as sc_mod
from types import SimpleNamespace


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


@pytest.fixture(autouse=True)
def reset_singleton() -> Generator[None, None, None]:
    """Reset OSRMConnection singleton before each test"""
    from sim.osm.OSRMConnection import OSRMConnection

    OSRMConnection._instance = None
    yield
    OSRMConnection._instance = None


@pytest.fixture()
def env() -> simpy.Environment:
    return simpy.Environment()


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


@pytest.fixture()
def simulator_controller(
    env: simpy.Environment,
    frame_emitter: FrameEmitter,
    input_params: InputParameter,
    fake_time: MockClock,
    monkeypatch: Any,
) -> SimulatorController:
    # Set OSRM URL environment variable to avoid ValueError
    monkeypatch.setenv("OSRM_URL", "http://localhost:5000")

    # Mock OSRMConnection initialization to avoid file I/O
    with (
        patch(
            "sim.osm.OSRMConnection.OSRMConnection._verify_osrm_connection",
            return_value=True,
        ),
    ):
        controller = SimulatorController(
            simEnv=env,
            frameEmitter=frame_emitter,
            inputParameters=input_params,
            sim_behaviour=FakeSimBehaviour(),
            strict=False,
        )
    return controller


def test_simulator_controller_initialization(
    simulator_controller: SimulatorController, input_params: InputParameter
) -> None:
    """Test that SimulatorController initializes correctly with proper attributes."""
    # Check that the map has the expected attributes
    assert simulator_controller.simEnv is not None
    assert simulator_controller.frameEmitter is not None
    assert simulator_controller.realTimeDriver is not None
    assert simulator_controller.clock is not None

    # Check that entities are properly loaded from InputParameter
    assert len(simulator_controller.station_entities) == 2
    assert len(simulator_controller.resource_entities) == 2
    assert len(simulator_controller.task_entities) == 2

    # Check keyframe frequency
    assert simulator_controller.keyframeFreq == 60  # default value

    # Check frame counter initialization
    assert simulator_controller.frameCounter == 0


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
    assert "sim_id" in frame.payload_dict
    assert "tasks" in frame.payload_dict
    assert "stations" in frame.payload_dict
    assert "resources" in frame.payload_dict
    assert "new_tasks" in frame.payload_dict
    assert frame.payload_dict["new_tasks"] == []
    assert "clock" in frame.payload_dict

    # Check that frame counter was incremented
    assert simulator_controller.frameCounter == 1


def test_create_key_frame(simulator_controller: SimulatorController) -> None:
    """Test that create_key_frame generates a complete frame with all entities."""
    frame = simulator_controller.create_key_frame()

    # Check frame structure
    assert frame.seq_number == 0
    assert isinstance(frame.payload_dict, dict)

    payload = frame.payload_dict
    assert "sim_id" in payload
    assert "tasks" in payload
    assert "stations" in payload
    assert "resources" in payload
    assert "clock" in payload
    assert "new_tasks" in payload
    assert payload["new_tasks"] == []

    # Check that all entities are included in key frame
    assert len(payload["tasks"]) == 2
    assert len(payload["stations"]) == 2
    assert len(payload["resources"]) == 2

    # Check task structure
    task = payload["tasks"][0]
    assert "id" in task
    assert "state" in task
    assert "station_id" in task
    assert "station_name" in task
    assert "assigned_resource_id" in task
    assert "is_assigned" in task

    # Check station structure
    station = payload["stations"][0]
    assert "station_id" in station
    assert "station_name" in station
    assert "station_position" in station
    assert "station_tasks" in station
    assert "task_count" in station

    # Check resource structure
    resource = payload["resources"][0]
    assert "resource_id" in resource
    assert "resource_position" in resource
    assert "resource_tasks" in resource
    assert "task_count" in resource
    assert "in_progress_task_id" in resource


def test_create_diff_frame(simulator_controller: SimulatorController) -> None:
    """Test that create_diff_frame generates a frame with only updated entities."""
    # Mark one entity as updated (using ID keys instead of indices)
    simulator_controller.station_entities[1].has_updated = True
    simulator_controller.task_entities[1].has_updated = True
    simulator_controller.resource_entities[1].has_updated = True

    frame = simulator_controller.create_diff_frame()

    # Check frame structure
    assert frame.seq_number == 0
    assert isinstance(frame.payload_dict, dict)

    payload = frame.payload_dict

    # Check that only updated entities are included
    assert len(payload["tasks"]) == 1
    assert len(payload["stations"]) == 1
    assert len(payload["resources"]) == 1
    assert "new_tasks" in payload
    assert payload["new_tasks"] == []


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
    assert simulator_controller.frameCounter == 1


def test_emit_frame_without_provided_frame_key_frame(
    simulator_controller: SimulatorController, frame_emitter: FrameEmitter
) -> None:
    """Test emit_frame without provided frame creates key frame when
    frameCounter is multiple of keyframeFreq."""
    subscriber = FakeSubscriber()
    frame_emitter.attach(subscriber)

    # Set frame counter to multiple of keyframe frequency
    simulator_controller.frameCounter = 60  # Should create key frame

    simulator_controller.emit_frame()

    # Check that a frame was emitted
    assert len(subscriber.received) == 1
    frame = subscriber.received[0]

    # Should be a key frame (includes all entities)
    assert len(frame.payload_dict["tasks"]) == 2
    assert len(frame.payload_dict["stations"]) == 2
    assert len(frame.payload_dict["resources"]) == 2
    assert "new_tasks" in frame.payload_dict
    assert frame.payload_dict["new_tasks"] == []


def test_emit_frame_without_provided_frame_diff_frame(
    simulator_controller: SimulatorController, frame_emitter: FrameEmitter
) -> None:
    """Test emit_frame without provided frame creates diff frame when
    frameCounter is not multiple of keyframeFreq."""
    subscriber = FakeSubscriber()
    frame_emitter.attach(subscriber)

    # Set frame counter to non-multiple of keyframe frequency
    simulator_controller.frameCounter = 30  # Should create diff frame

    # Mark some entities as updated (using ID keys instead of indices)
    simulator_controller.station_entities[1].has_updated = True
    simulator_controller.sim_time = 3600

    simulator_controller.emit_frame()

    # Check that a frame was emitted
    assert len(subscriber.received) == 1
    frame = subscriber.received[0]

    # Should be a diff frame (only updated entities)
    assert len(frame.payload_dict["stations"]) == 1
    assert len(frame.payload_dict["tasks"]) == 0  # No tasks marked as updated
    assert len(frame.payload_dict["resources"]) == 0  # No resources marked as updated
    assert "new_tasks" in frame.payload_dict
    assert frame.payload_dict["new_tasks"] == []


def test_emit_frame_clears_update_flags(
    simulator_controller: SimulatorController, frame_emitter: FrameEmitter
) -> None:
    subscriber = FakeSubscriber()
    frame_emitter.attach(subscriber)

    # Mark entities as updated
    simulator_controller.station_entities[1].has_updated = True
    simulator_controller.task_entities[1].has_updated = True
    simulator_controller.resource_entities[1].has_updated = True

    # Emit a provided frame to avoid depending on internal selection
    custom_frame = Frame(seq_numb=0, payload={})
    simulator_controller.emit_frame(custom_frame)

    assert simulator_controller.station_entities[1].has_updated is False
    assert simulator_controller.task_entities[1].has_updated is False
    assert simulator_controller.resource_entities[1].has_updated is False


def test_key_frame_includes_new_tasks_and_clears_popups(
    env: simpy.Environment,
    simulator_controller: SimulatorController,
) -> None:
    station1 = simulator_controller.get_station_by_id(1)
    assert station1 is not None
    # create a popup task and attach to station
    new_task = BatterySwapTask(task_id=99, station=station1)
    station1.pop_up_tasks.append(new_task)

    frame = simulator_controller.create_key_frame()
    payload = frame.payload_dict
    assert "new_tasks" in payload
    assert any(t["id"] == 99 for t in payload["new_tasks"])
    # ensure task added to map task_entities
    assert simulator_controller.get_task_by_id(99) is not None
    # ensure popups cleared after frame generation
    assert station1.pop_up_tasks == []


def test_pause_and_resume(simulator_controller: SimulatorController) -> None:
    """Test pause and resume functionality."""
    # Mock the real time driver methods
    with (
        patch.object(simulator_controller.realTimeDriver, "pause") as mock_pause,
        patch.object(simulator_controller.realTimeDriver, "resume") as mock_resume,
    ):

        simulator_controller.pause()
        mock_pause.assert_called_once()

        simulator_controller.resume()
        mock_resume.assert_called_once()


def test_stop(simulator_controller: SimulatorController) -> None:
    """Test stop functionality."""
    # Mock the real time driver stop method
    with patch.object(simulator_controller.realTimeDriver, "stop") as mock_stop:
        simulator_controller.stop()
        mock_stop.assert_called_once()


def test_set_factor(simulator_controller: SimulatorController) -> None:
    """Test set_factor functionality."""
    # Mock the real time driver set_real_time_factor method
    with patch.object(
        simulator_controller.realTimeDriver, "set_real_time_factor"
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


def test_assign_task_to_resource_success(
    simulator_controller: SimulatorController,
) -> None:
    """Test assign_task_to_resource functionality."""
    # Arrange
    task_id = 1
    resource_id = 1

    # Act
    simulator_controller.assign_task_to_resource(task_id, resource_id)

    # Assert
    task = simulator_controller.get_task_by_id(task_id)
    resource = simulator_controller.get_resource_by_id(resource_id)
    assert task is not None
    assert resource is not None
    assert task.get_assigned_resource() == resource
    assert resource.get_task_list()[0] == task


def test_assign_task_to_resource_with_bad_task_id(
    simulator_controller: SimulatorController,
) -> None:
    """Test assign_task_to_resource functionality with an invalid task_id."""
    # Arrange
    task_id = 6  # Non-existant id
    resource_id = 1

    # Act and Assert
    with pytest.raises(
        Exception, match=f"Could not find task in sim with id: {task_id}"
    ):
        simulator_controller.assign_task_to_resource(task_id, resource_id)


def test_assign_task_to_resource_with_bad_resource_id(
    simulator_controller: SimulatorController,
) -> None:
    """Test assign_task_to_resource functionality with an invalid resouruce_id."""
    # Arrange
    task_id = 1
    resource_id = 6  # Non-existant id

    # Act and Assert
    with pytest.raises(
        Exception, match=f"Could not find resource in sim with id: {resource_id}"
    ):
        simulator_controller.assign_task_to_resource(task_id, resource_id)


def test_unassign_task_from_resource_success(
    simulator_controller: SimulatorController,
) -> None:
    """Test unassign_task_from_resource functionality."""
    # Arrange
    task_id = 1
    resource_id = 1

    # Act
    simulator_controller.unassign_task_from_resource(task_id, resource_id)

    # Assert
    task = simulator_controller.get_task_by_id(task_id)
    resource = simulator_controller.get_resource_by_id(resource_id)
    assert task is not None
    assert resource is not None
    assert task.get_assigned_resource() is None
    assert resource.get_task_count() == 0


def test_unassign_task_from_resource_with_bad_task_id(
    simulator_controller: SimulatorController,
) -> None:
    """Test unassign_task_from_resource functionality with an invalid task_id."""
    # Arrange
    task_id = 6  # Non-existant id
    resource_id = 1

    # Act and Assert
    with pytest.raises(
        Exception, match=f"Could not find task in sim with id: {task_id}"
    ):
        simulator_controller.unassign_task_from_resource(task_id, resource_id)


def test_unassign_task_from_resource_with_bad_resource_id(
    simulator_controller: SimulatorController,
) -> None:
    """Test unassign_task_from_resource functionality with an invalid resource_id."""
    # Arrange
    task_id = 1
    resource_id = 6  # Non-existant id

    # Act and Assert
    with pytest.raises(
        Exception, match=f"Could not find resource in sim with id: {resource_id}"
    ):
        simulator_controller.unassign_task_from_resource(task_id, resource_id)


def test_reassign_task_success(
    simulator_controller: SimulatorController,
) -> None:
    """Test reassign_task functionality"""
    # Arrange
    task_id = 1
    old_resource_id = 1
    new_resource_id = 2

    simulator_controller.assign_task_to_resource(task_id, old_resource_id)

    # Act
    simulator_controller.reassign_task(task_id, old_resource_id, new_resource_id)

    # Assert
    task = simulator_controller.get_task_by_id(task_id)
    assert task is not None
    old_resource = simulator_controller.get_resource_by_id(old_resource_id)
    assert old_resource is not None
    new_resource = simulator_controller.get_resource_by_id(new_resource_id)
    assert new_resource is not None
    assert task.get_assigned_resource() == new_resource
    assert task in new_resource.get_task_list()
    assert task not in old_resource.get_task_list()


def test_reassign_task_fail_with_bad_task_id(
    simulator_controller: SimulatorController,
) -> None:
    """Test reassign_task functionality with bad task_id"""
    # Arrange
    task_id = 6  # Non-existent task
    old_resource_id = 1
    new_resource_id = 2

    # Act and Assert
    with pytest.raises(
        Exception, match=f"Reassigning task failed as could not find task {task_id}"
    ):
        simulator_controller.reassign_task(task_id, old_resource_id, new_resource_id)


def test_reassign_task_fail_with_bad_old_resource_id(
    simulator_controller: SimulatorController,
) -> None:
    """Test reassign_task functionality with bad old_resource_id"""
    # Arrange
    task_id = 1
    old_resource_id = 6  # Non-existent resource
    new_resource_id = 2

    # Act and Assert
    with pytest.raises(
        Exception,
        match=f"Reassigning failed as could not find resource {old_resource_id}",
    ):
        simulator_controller.reassign_task(task_id, old_resource_id, new_resource_id)


def test_reassign_task_fail_with_bad_new_resource_id(
    simulator_controller: SimulatorController,
) -> None:
    """Test reassign_task functionality with bad new_resource_id"""
    # Arrange
    task_id = 1
    old_resource_id = 1
    new_resource_id = 6  # Non-existent resource

    simulator_controller.assign_task_to_resource(task_id, old_resource_id)

    # Act and Assert
    with pytest.raises(
        Exception,
        match=f"Reassigning failed as could not find resource {new_resource_id}",
    ):
        simulator_controller.reassign_task(task_id, old_resource_id, new_resource_id)

    task = simulator_controller.get_task_by_id(task_id)
    assert task is not None
    old_resource = simulator_controller.get_resource_by_id(old_resource_id)
    assert old_resource is not None
    assert task.get_assigned_resource() == old_resource
    assert task in old_resource.get_task_list()


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

        # Patch heavy routing (OSRM doesn't have build_ch_network)
        with patch.object(
            simulator_controller.map_controller,
            "getRoute",
            return_value=SimpleNamespace(roads=[1, 2]),
        ):
            simulator_controller.start(3600)

        # Check that clock was started
        mock_clock_run.assert_called_once()

        # Check that thread was created with correct parameters
        mock_thread_class.assert_called_once()
        args, kwargs = mock_thread_class.call_args
        assert kwargs["target"] == simulator_controller.realTimeDriver.run_until
        assert kwargs["args"] == (3600, simulator_controller.emit_frame)

        # Check that thread was started
        mock_thread.start.assert_called_once()

        # Check that thread is stored
        assert simulator_controller.sim_thread == mock_thread


def test_custom_keyframe_frequency(
    env: simpy.Environment,
    frame_emitter: FrameEmitter,
    fake_time: MockClock,
    monkeypatch: Any,
) -> None:
    """Test that custom keyframe frequency is properly set."""
    # Set OSRM URL environment variable
    monkeypatch.setenv("OSRM_URL", "http://localhost:5000")

    params = InputParameter()
    params.set_key_frame_freq(30)  # Custom frequency

    with patch(
        "sim.osm.OSRMConnection.OSRMConnection._verify_osrm_connection",
        return_value=True,
    ):
        controller = SimulatorController(
            simEnv=env,
            frameEmitter=frame_emitter,
            inputParameters=params,
            sim_behaviour=FakeSimBehaviour(),
            strict=False,
        )

    assert controller.keyframeFreq == 30


def test_strict_mode_initialization(
    env: simpy.Environment,
    frame_emitter: FrameEmitter,
    input_params: InputParameter,
    fake_time: MockClock,
    monkeypatch: Any,
) -> None:
    """Test that strict mode is properly passed to RealTimeDriver."""
    # Set OSRM URL environment variable
    monkeypatch.setenv("OSRM_URL", "http://localhost:5000")

    with patch(
        "sim.osm.OSRMConnection.OSRMConnection._verify_osrm_connection",
        return_value=True,
    ):
        controller = SimulatorController(
            simEnv=env,
            frameEmitter=frame_emitter,
            inputParameters=input_params,
            sim_behaviour=FakeSimBehaviour(),
            strict=True,
        )

    # The strict parameter should be passed to RealTimeDriver
    assert controller.realTimeDriver.strict is True
