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

from typing import Optional, TYPE_CHECKING


# to avoid circular imports
if TYPE_CHECKING:  # pragma: no cover
    from .driver import Driver


class Vehicle:
    """Simulation Vehicles entity that can be associated with a driver."""

    env: simpy.Environment
    driver: Optional["Driver"]

    def __init__(
        self,
        vehicle_id: int,
        driver: Optional["Driver"] = None,
        battery_count: int = 0,
        max_battery_count: int = 50,
    ) -> None:
        self.id = vehicle_id
        self.driver = driver
        self.battery_count = battery_count
        self.max_battery_count = max_battery_count
        self.has_updated = False  # flag to track if a vehicle was updated
        self.tasks_completed = 0

    def get_driver(self) -> Optional["Driver"]:
        """Get the vehicle's current driver.

        Returns:
            Driver| None: The vehicle's current Driver if one is set. None otherwise.
        """
        return self.driver

    def get_battery_count(self) -> int:
        """Get the vehicle's current battery count.

        Returns:
            battery_count: The vehicle's current battery_count.
        """
        return self.battery_count

    def get_max_battery_count(self) -> int:
        """Get the vehicle's max battery count.

        Returns:
            max_battery_count: The vehicle's max_battery_count.
        """
        return self.max_battery_count

    def set_driver(self, driver: "Driver") -> None:
        """Set the vehicle's driver and marks it as updated.

        Args:
            driver: Driver to be associated to this vehicle.

        Returns:
            None
        """
        # Reject only if vehicle is bound to a DIFFERENT driver
        if self.driver is not None and self.driver.id != driver.id:
            raise Exception(
                f"Vehicle Error: vehicle: {self.id} "
                f"already assigned to driver: {self.driver.id}"
            )
        # Reject only if driver is bound to a DIFFERENT vehicle
        current_vehicle = driver.get_vehicle()
        if current_vehicle is not None and current_vehicle.id != self.id:
            raise Exception(
                f"Vehicle Error: driver: {driver.id} "
                f"already assigned to vehicle: {current_vehicle.id}"
            )

        self.driver = driver
        self.has_updated = True

    def unassign_driver(self) -> None:
        """Unassign the current driver from this vehicle.

        Clears the association to the driver and marks the vehicle as updated.

        Returns:
            None
        """
        if self.driver is not None:
            self.driver = None
            self.has_updated = True

    def set_battery_count(self, new_battery_count: int) -> None:
        """Set the vehicle's inventory and marks it as updated.

        Args:
            battery_count: int corresponding to a quantity of batteries.

        Returns:
            None
        """
        self.battery_count = new_battery_count
        self.has_updated = True

    def use_battery(self) -> int:
        """
        Decreases by one the vehicle's battery count as long as it is bigger than 0.

        Returns:
            The battery count after its been decreased.
        """
        if self.battery_count > 0:
            self.battery_count = self.battery_count - 1
            self.has_updated = True
        else:
            raise Exception(
                f"Cannot use a battery since vehicle {self.id} has none available."
            )
        return self.battery_count

    def add_battery(self) -> None:
        """
        Increases by one the vehicle's battery count while ensuring its value is
        never higher than the max_battery_count.

        Returns:
            None
        """
        if self.battery_count < self.max_battery_count:
            self.battery_count = self.battery_count + 1
            self.has_updated = True

    def clear_update(self) -> None:
        """Clear the update flag for this vehicle.

        Resets the has_updated flag to False, indicating that changes to this
        vehicle have been processed or acknowledged.

        Returns:
            None
        """
        self.has_updated = False
