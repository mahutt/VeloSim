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

import time
from typing import cast

import pytest
import simpy
from sim.behaviour.default.default_TPU_strategy import DefaultTPUStrategy
from sim.behaviour.station_behaviour.strategies.task_popup_strategy import (
    TaskPopupStrategy,
)
from sim.entities.battery_swap_task import BatterySwapTask
from sim.entities.station import Station
from sim.entities.task_state import State


class _BaseTaskPopupCaller(TaskPopupStrategy):
    def check_for_new_task(self, station: Station) -> list[BatterySwapTask]:
        return []


class MockClock:
    """Mock clock for controlling time in tests."""

    def __init__(self, start: float = 0.0) -> None:
        self.now = float(start)
        self.sleeps: list[float] = []

    def perf_counter(self) -> float:
        return self.now

    def sleep(self, dt: float) -> None:
        if dt and dt > 0:
            self.sleeps.append(dt)
            self.now += dt


class _FakeStation:
    """Mock station for testing."""

    def __init__(self, station_id: int, env: simpy.Environment) -> None:
        self.id = station_id
        self.env = env


class TestDefaultTPUStrategy:
    """Test suite for DefaultTPUStrategy."""

    @pytest.fixture
    def fake_time(self, monkeypatch: pytest.MonkeyPatch) -> MockClock:
        """Patch time functions so no real time passes during tests."""
        clock = MockClock()
        monkeypatch.setattr(time, "perf_counter", clock.perf_counter)
        monkeypatch.setattr(time, "sleep", clock.sleep)
        return clock

    @pytest.fixture
    def simpy_env(self, fake_time: MockClock) -> simpy.Environment:
        """Create a SimPy environment."""
        return simpy.Environment()

    @pytest.fixture
    def strategy(self) -> DefaultTPUStrategy:
        """Create a DefaultTPUStrategy instance."""
        return DefaultTPUStrategy()

    @pytest.fixture
    def fake_station(self, simpy_env: simpy.Environment) -> _FakeStation:
        """Create a fake station."""
        return _FakeStation(1, simpy_env)

    def test_initial_state(self, strategy: DefaultTPUStrategy) -> None:
        """Test that strategy initializes with None scheduled tasks."""
        assert strategy.get_station_scheduled_tasks() == {}

    def test_set_and_get_station_scheduled_tasks(
        self, strategy: DefaultTPUStrategy
    ) -> None:
        """Test setting and getting station scheduled tasks."""
        scheduled_tasks = {
            1: {100: [1, 2, 3], 200: [4, 5]},
            2: {150: [6]},
        }

        strategy.set_station_scheduled_tasks(scheduled_tasks)

        assert strategy.get_station_scheduled_tasks() == scheduled_tasks

    def test_build_scheduled_tasks_set(self, strategy: DefaultTPUStrategy) -> None:
        """Test that setting tasks builds the internal set correctly."""
        scheduled_tasks = {
            1: {100: [1, 2], 200: [3]},
            2: {150: [4, 5]},
        }

        strategy.set_station_scheduled_tasks(scheduled_tasks)
        tasks_set = strategy.get_scheduled_tasks()

        expected_set = {
            (1, 100, 1),
            (1, 100, 2),
            (1, 200, 3),
            (2, 150, 4),
            (2, 150, 5),
        }

        assert tasks_set == expected_set

    def test_check_for_new_task_no_scheduled_tasks(
        self, strategy: DefaultTPUStrategy, fake_station: _FakeStation
    ) -> None:
        """Test check_for_new_task when no tasks are scheduled."""
        tasks = strategy.check_for_new_task(fake_station)  # type: ignore[arg-type]
        assert tasks == []

    def test_check_for_new_task_no_tasks_for_station(
        self, strategy: DefaultTPUStrategy, fake_station: _FakeStation
    ) -> None:
        """Test check_for_new_task when station has no scheduled tasks."""
        scheduled_tasks = {
            2: {100: [1, 2]},  # Different station
        }

        strategy.set_station_scheduled_tasks(scheduled_tasks)
        tasks = strategy.check_for_new_task(fake_station)  # type: ignore[arg-type]

        assert tasks == []

    def test_check_for_new_task_no_tasks_at_current_time(
        self,
        strategy: DefaultTPUStrategy,
        fake_station: _FakeStation,
        simpy_env: simpy.Environment,
        fake_time: MockClock,
    ) -> None:
        """Test check_for_new_task when no tasks scheduled at current time."""
        scheduled_tasks = {
            1: {100: [1, 2]},  # Tasks at time 100
        }

        fake_station.env = simpy_env
        strategy.set_station_scheduled_tasks(scheduled_tasks)

        # Advance env to time 50 (no tasks scheduled)
        simpy_env.run(until=50)

        tasks = strategy.check_for_new_task(fake_station)  # type: ignore[arg-type]
        assert tasks == []

    def test_check_for_new_task_creates_tasks_at_scheduled_time(
        self,
        strategy: DefaultTPUStrategy,
        fake_station: _FakeStation,
        simpy_env: simpy.Environment,
        fake_time: MockClock,
    ) -> None:
        """Test that tasks are created at the scheduled time."""
        scheduled_tasks = {
            1: {100: [10, 20, 30]},
        }

        fake_station.env = simpy_env
        strategy.set_station_scheduled_tasks(scheduled_tasks)

        simpy_env.run(until=100)

        tasks = strategy.check_for_new_task(fake_station)  # type: ignore[arg-type]

        assert len(tasks) == 3
        assert all(task.get_state() == State.OPEN for task in tasks)
        assert all(task.has_updated for task in tasks)
        assert {task.get_task_id() for task in tasks} == {10, 20, 30}

    def test_pop_scheduled_task(self, strategy: DefaultTPUStrategy) -> None:
        """Test removing a scheduled task from the set."""
        scheduled_tasks = {
            1: {100: [1, 2, 3]},
        }

        strategy.set_station_scheduled_tasks(scheduled_tasks)
        initial_set = strategy.get_scheduled_tasks()

        assert (1, 100, 2) in initial_set

        strategy.pop_scheduled_task(1, 100, 2)

        updated_set = strategy.get_scheduled_tasks()
        assert (1, 100, 2) not in updated_set
        assert (1, 100, 1) in updated_set
        assert (1, 100, 3) in updated_set

    def test_pop_scheduled_task_nonexistent(self, strategy: DefaultTPUStrategy) -> None:
        """Test that popping nonexistent task doesn't raise error."""
        scheduled_tasks = {
            1: {100: [1, 2]},
        }

        strategy.set_station_scheduled_tasks(scheduled_tasks)

    def test_check_for_new_task_removes_tasks_from_set(
        self,
        strategy: DefaultTPUStrategy,
        fake_station: _FakeStation,
        simpy_env: simpy.Environment,
        fake_time: MockClock,
    ) -> None:
        """Test that created tasks are removed from scheduled set."""
        scheduled_tasks = {
            1: {100: [1, 2]},
        }

        fake_station.env = simpy_env
        strategy.set_station_scheduled_tasks(scheduled_tasks)

        initial_set = strategy.get_scheduled_tasks()
        assert (1, 100, 1) in initial_set
        assert (1, 100, 2) in initial_set

        simpy_env.run(until=100)
        tasks = strategy.check_for_new_task(fake_station)  # type: ignore[arg-type]

        assert len(tasks) == 2

        updated_set = strategy.get_scheduled_tasks()
        assert (1, 100, 1) not in updated_set
        assert (1, 100, 2) not in updated_set
        updated_set = strategy.get_scheduled_tasks()
        assert (1, 100, 1) not in updated_set
        assert (1, 100, 2) not in updated_set

    def test_multiple_stations_multiple_times(
        self,
        strategy: DefaultTPUStrategy,
        simpy_env: simpy.Environment,
    ) -> None:
        """Test complex scenario with multiple stations and times."""
        scheduled_tasks = {
            1: {100: [1, 2], 200: [3]},
            2: {100: [4], 300: [5, 6]},
        }

        strategy.set_station_scheduled_tasks(scheduled_tasks)

        station1 = _FakeStation(1, simpy_env)
        station2 = _FakeStation(2, simpy_env)

        simpy_env.run(until=100)
        tasks_s1 = strategy.check_for_new_task(station1)  # type: ignore[arg-type]
        tasks_s2 = strategy.check_for_new_task(station2)  # type: ignore[arg-type]

        assert len(tasks_s1) == 2
        assert len(tasks_s2) == 1
        assert {t.get_task_id() for t in tasks_s1} == {1, 2}
        assert {t.get_task_id() for t in tasks_s2} == {4}

        simpy_env.run(until=200)
        tasks_s1 = strategy.check_for_new_task(station1)  # type: ignore[arg-type]
        tasks_s2 = strategy.check_for_new_task(station2)  # type: ignore[arg-type]

        assert len(tasks_s1) == 1
        assert len(tasks_s2) == 0
        assert tasks_s1[0].get_task_id() == 3

        simpy_env.run(until=300)
        tasks_s1 = strategy.check_for_new_task(station1)  # type: ignore[arg-type]
        tasks_s2 = strategy.check_for_new_task(station2)  # type: ignore[arg-type]

        assert len(tasks_s1) == 0
        assert len(tasks_s2) == 2
        assert {t.get_task_id() for t in tasks_s2} == {5, 6}

    def test_empty_scheduled_tasks(self, strategy: DefaultTPUStrategy) -> None:
        """Test setting empty scheduled tasks."""
        strategy.set_station_scheduled_tasks({})

        assert strategy.get_station_scheduled_tasks() == {}
        assert strategy.get_scheduled_tasks() == set()


def test_task_popup_strategy_base_raises_not_implemented() -> None:
    with pytest.raises(NotImplementedError):
        TaskPopupStrategy.check_for_new_task(
            _BaseTaskPopupCaller(),
            cast(Station, object()),
        )
