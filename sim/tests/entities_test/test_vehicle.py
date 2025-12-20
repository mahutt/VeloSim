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
from sim.entities.vehicle import Vehicle
from sim.entities.driver import Driver
from sim.entities.position import Position


class TestVehicle:

    @pytest.fixture
    def default_position(self) -> Position:
        return Position([-73.5673, 45.5017])

    @pytest.fixture
    def simpy_env(self) -> simpy.Environment:
        return simpy.Environment()

    @pytest.fixture
    def driver(self, default_position: Position) -> Driver:
        return Driver(1, default_position)

    @pytest.fixture
    def vehicle(self) -> Vehicle:
        return Vehicle(1, battery_count=3)

    @pytest.fixture
    def vehicle_with_driver(self, driver: Driver) -> Vehicle:
        return Vehicle(2, driver=driver, battery_count=3)

    def test_vehicle_init(self, driver: Driver) -> None:
        battery_count = 3
        vehicle = Vehicle(1, driver, battery_count)

        assert vehicle.id == 1
        assert vehicle.has_updated == False
        assert vehicle.driver is not None
        assert battery_count == 3

    def test_get_vehicle_driver(
        self, vehicle_with_driver: Vehicle, default_position: Position
    ) -> None:

        driver = vehicle_with_driver.get_vehicle_driver()

        assert isinstance(driver, Driver)
        assert driver.id == 1
        assert driver.position == default_position

    def test_vehicle_get_battery_count(self, vehicle: Vehicle) -> None:
        battery_count = vehicle.get_vehicle_battery_count()
        assert battery_count == 3

    def test_set_vehicle_driver(
        self, vehicle_with_driver: Vehicle, default_position: Position
    ) -> None:
        new_driver = Driver(3, position=default_position)
        vehicle_with_driver.set_vehicle_driver(new_driver)

        drv = vehicle_with_driver.get_vehicle_driver()
        assert drv is not None
        assert drv.id == new_driver.id

    def test_set_vehicle_battery_count(self, vehicle: Vehicle) -> None:
        new_battery_count = 8
        vehicle.set_vehicle_battery_count(new_battery_count)

        assert vehicle.battery_count == new_battery_count

    def test_clear_update(self, vehicle: Vehicle) -> None:
        vehicle.has_updated = True
        vehicle.clear_update()
        assert vehicle.has_updated == False
