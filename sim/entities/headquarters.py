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

from sim.entities.position import Position
from sim.entities.vehicle import Vehicle


class Headquarters:
    """Simulation bike sharing headquarters where vehicles are kept."""

    position: Position = Position([-73.60175631192361, 45.52975346053039])
    vehicles: list[Vehicle]  # List of vehicles at headquarters (no assigned driver)

    def __init__(self, vehicles: list[Vehicle] | None = None):
        self.vehicles = []
        if vehicles:
            for vehicle in vehicles:
                self.push_vehicle(vehicle)

    def push_vehicle(self, vehicle: Vehicle) -> None:
        """Add a vehicle to headquarters' vehicle list.

        Args:
            vehicle: The vehicle to add to headquarters.

        Returns:
            None
        """
        vehicle_driver = vehicle.get_driver()
        if vehicle_driver is not None:
            raise Exception(
                f"Cannot add vehicle {vehicle.id} to headquarters: "
                f"vehicle is assigned driver {vehicle_driver.id}"
            )
        self.vehicles.append(vehicle)

    def pop_vehicle(self) -> Vehicle | None:
        """Remove and return a vehicle from headquarters' vehicle list.

        Returns:
            The vehicle removed from headquarters or None if no vehicles are available.

        Raises:
            Exception: If there are no vehicles available at headquarters.
        """
        if not self.vehicles:
            return None
        return self.vehicles.pop(0)

    def has_vehicles(self) -> bool:
        """Check if headquarters has any vehicles available.

        Returns:
            True if there are vehicles available, False otherwise.
        """
        return len(self.vehicles) > 0
