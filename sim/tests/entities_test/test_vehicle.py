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
import time
from sim.core.simulation_environment import SimulationEnvironment
from sim.entities.vehicle import Vehicle
from sim.entities.driver import Driver
from sim.entities.position import Position
from sim.entities.shift import Shift
from sim.core.simulation_report import SimulationReport
from sim.entities.battery_swap_task import BatterySwapTask
from sim.entities.task import Task
from typing import List

# Ensure Driver has a default environment for initialization in this module
Driver.env = SimulationEnvironment()


class MockClock:
    def __init__(self, start: float = 0.0) -> None:
        self.now = start
        self.sleeps: list[float] = []

    def perf_counter(self) -> float:
        return self.now

    def sleep(self, dt: float) -> None:
        if dt and dt > 0:
            self.sleeps.append(dt)
            self.now += dt


class TestVehicle:

    @pytest.fixture
    def fake_time(self, monkeypatch: pytest.MonkeyPatch) -> MockClock:
        """Patch time functions so no real time passes during tests."""
        clock = MockClock()
        monkeypatch.setattr(time, "perf_counter", clock.perf_counter)
        monkeypatch.setattr(time, "sleep", clock.sleep)
        return clock

    @pytest.fixture
    def default_position(self) -> Position:
        return Position([-73.5673, 45.5017])

    @pytest.fixture
    def simpy_env(self) -> SimulationEnvironment:
        return SimulationEnvironment()

    @pytest.fixture
    def default_shift(self) -> Shift:
        return Shift(0.0, 24.0, None, 0.0, 24.0, None)

    @pytest.fixture
    def driver(self, default_position: Position, default_shift: Shift) -> Driver:
        return Driver(1, default_position, default_shift)

    @pytest.fixture
    def vehicle(self) -> Vehicle:
        return Vehicle(1, battery_count=3, max_battery_count=20)

    @pytest.fixture
    def vehicle_with_driver(self, driver: Driver) -> Vehicle:
        return Vehicle(2, driver=driver, battery_count=3)

    @pytest.fixture
    def simulation_metrics(self) -> SimulationReport:
        return SimulationReport()

    @pytest.fixture
    def task_list(self) -> List[Task]:
        task1 = BatterySwapTask(1)
        task2 = BatterySwapTask(2)
        task3 = BatterySwapTask(3)
        return [task1, task2, task3]

    def test_vehicle_init(self, driver: Driver) -> None:
        battery_count = 3
        vehicle = Vehicle(1, driver, battery_count)

        assert vehicle.id == 1
        assert vehicle.has_updated == False
        assert vehicle.driver is not None
        assert battery_count == 3

    def test_get_driver(
        self, vehicle_with_driver: Vehicle, default_position: Position
    ) -> None:

        driver = vehicle_with_driver.get_driver()

        assert isinstance(driver, Driver)
        assert driver.id == 1
        assert driver.position == default_position

    def test_get_max_battery_count(self, vehicle: Vehicle) -> None:
        assert vehicle.get_max_battery_count() == 20

        vehicle.max_battery_count = 10
        assert vehicle.get_max_battery_count() == 10

    def test_vehicle_get_battery_count(self, vehicle: Vehicle) -> None:
        battery_count = vehicle.get_battery_count()
        assert battery_count == 3

    def test_set_driver(
        self, vehicle_with_driver: Vehicle, default_position: Position
    ) -> None:
        # Idempotent reassignment with the same driver should not error
        same_driver = vehicle_with_driver.get_driver()
        assert same_driver is not None
        vehicle_with_driver.set_driver(same_driver)

        drv = vehicle_with_driver.get_driver()
        assert drv is not None
        assert drv.id == same_driver.id

    def test_set_battery_count(self, vehicle: Vehicle) -> None:
        new_battery_count = 8
        vehicle.set_battery_count(new_battery_count)

        assert vehicle.battery_count == new_battery_count

    def test_use_battery(self, vehicle: Vehicle) -> None:
        # Arrange
        new_battery_count = 8
        vehicle.set_battery_count(new_battery_count)

        # Act
        vehicle.use_battery()

        # Assert
        assert vehicle.battery_count == new_battery_count - 1

    def test_add_battery(self, vehicle: Vehicle) -> None:
        # Arrange
        new_battery_count = 8
        vehicle.set_battery_count(new_battery_count)

        # Act
        vehicle.add_battery()

        # Assert
        assert vehicle.battery_count == new_battery_count + 1

    def test_add_battery_at_max(self, vehicle: Vehicle) -> None:
        # Arrange
        vehicle.max_battery_count = 8
        new_battery_count = 8
        vehicle.set_battery_count(new_battery_count)

        # Act
        vehicle.add_battery()

        # Assert
        assert vehicle.battery_count == new_battery_count

    def test_clear_update(self, vehicle: Vehicle) -> None:
        vehicle.has_updated = True
        vehicle.clear_update()
        assert vehicle.has_updated == False

    def test_records_utilization_above_one(
        self,
        vehicle: Vehicle,
        driver: Driver,
        fake_time: MockClock,
        task_list: List[Task],
    ) -> None:
        env = SimulationEnvironment()
        Driver.env = env
        Vehicle.env = env
        driver.task_list = task_list
        env.process(vehicle.run())
        env.run(until=2)

        assert env.report.vehicle_idle_time == 2

        vehicle.set_driver(driver)
        env.run(until=6)

        assert env.report.vehicle_active_time == 4

        assert env.report.get_vehicle_utilization_ratio() == 2.0

    def test_records_utilization_below_one(
        self,
        vehicle: Vehicle,
        driver: Driver,
        fake_time: MockClock,
        task_list: List[Task],
    ) -> None:
        env = SimulationEnvironment()
        Driver.env = env
        Vehicle.env = env
        driver.task_list = task_list
        env.process(vehicle.run())
        env.run(until=2)

        assert env.report.vehicle_idle_time == 2

        vehicle.set_driver(driver)
        env.run(until=3)

        assert env.report.vehicle_active_time == 1

        assert env.report.get_vehicle_utilization_ratio() == 0.5

    def test_records_full_utilization(
        self,
        vehicle: Vehicle,
        driver: Driver,
        fake_time: MockClock,
        task_list: List[Task],
    ) -> None:

        env = SimulationEnvironment()
        Driver.env = env
        Vehicle.env = env
        driver.task_list = task_list
        env.process(vehicle.run())
        vehicle.set_driver(driver)
        env.run(until=3)

        assert env.report.vehicle_idle_time == 0
        assert env.report.vehicle_active_time == 3

        assert env.report.get_vehicle_utilization_ratio() == 1

    def test_records_zero_utilization(
        self,
        vehicle: Vehicle,
        driver: Driver,
        fake_time: MockClock,
        task_list: List[Task],
    ) -> None:

        env = SimulationEnvironment()
        Vehicle.env = env
        env.process(vehicle.run())
        env.run(until=3)

        assert env.report.vehicle_idle_time == 3
        assert env.report.vehicle_active_time == 0

        assert env.report.get_vehicle_utilization_ratio() == 0.0

    def test_records_idle_time_with_driver(
        self,
        vehicle: Vehicle,
        driver: Driver,
        fake_time: MockClock,
        task_list: List[Task],
    ) -> None:

        env = SimulationEnvironment()
        Vehicle.env = env
        Driver.env = env
        vehicle.set_driver(driver)
        env.process(vehicle.run())
        env.run(until=3)

        assert env.report.vehicle_idle_time == 3
        assert env.report.vehicle_active_time == 0

        driver.task_list = task_list
        env.run(until=5)

        assert env.report.vehicle_active_time == 2
