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

from typing import TYPE_CHECKING

from grafana_logging.logger import get_logger

if TYPE_CHECKING:
    from sim.entities.route import Route


logger = get_logger(__name__)


class SimulationReport:
    """
    Tracks simulation-wide metrics such as driving time and servicing time.
    """

    def __init__(self) -> None:
        self.total_driving_time = 0
        self.total_servicing_time = 0
        self.tasks_completed_per_shift: list[int] = []
        self.response_times: list[float] = []
        self.vehicle_idle_time = 0
        self.vehicle_active_time = 0
        self._active_vehicle_routes: set["Route"] = set()
        self._completed_vehicle_distance = 0.0

    def reset(self) -> None:
        """Reset all metrics to zero.

        Returns:
            None
        """
        self.total_driving_time = 0
        self.total_servicing_time = 0
        self.tasks_completed_per_shift = []
        self.response_times = []
        self.vehicle_idle_time = 0
        self.vehicle_active_time = 0
        self.reset_vehicle_distance_traveled()

    def increment_driving_time(self) -> None:
        """
        Increment the total driving time.

        Returns:
            None
        """
        self.total_driving_time += 1

    def increment_servicing_time(self) -> None:
        """
        Increment the total servicing time.

        Returns:
            None
        """
        self.total_servicing_time += 1

    def increment_vehicle_idle_time(self) -> None:
        """
        Increment the total vehicle idle time.

        Returns:
            None
        """
        self.vehicle_idle_time += 1

    def increment_vehicle_active_time(self) -> None:
        """
        Increment the total vehicle active time.

        Returns:
            None
        """
        self.vehicle_active_time += 1

    def add_task_count_for_shift(self, task_count: int) -> None:
        """
        Adds task count for a driver's shift.

        Args:
            task_count (int): Number of tasks completed during the shift.

        Returns:
            None
        """
        self.tasks_completed_per_shift.append(task_count)

    def add_service_time(self, service_time: float) -> None:
        """
        Adds the service time for a task from spawn to being serviced to the list.
        Args:
            service_time (float): time of task from spawn to being serviced.

        Returns:
            None
        """

        self.response_times.append(service_time)

    def register_vehicle_route(self, route: "Route") -> None:
        """Register an active route for distance aggregation.

        Args:
            route: The route to register for distance tracking.

        Returns:
            None
        """

        self._active_vehicle_routes.add(route)

    def unregister_vehicle_route(self, route: "Route") -> None:
        """Finalize an active route's traveled distance and remove it.

        Args:
            route: The route to unregister and finalize.

        Returns:
            None
        """

        if route not in self._active_vehicle_routes:
            logger.debug(
                "unregister_vehicle_route called for untracked route; ignoring."
            )
            return

        self._completed_vehicle_distance += route.get_distance_traveled()
        self._active_vehicle_routes.discard(route)

    def reset_vehicle_distance_traveled(self) -> None:
        """Clear all vehicle-distance tracking state.

        Returns:
            None
        """

        self._active_vehicle_routes.clear()
        self._completed_vehicle_distance = 0.0

    def get_servicing_to_driving_ratio(self) -> float:
        """
        Compute the ratio of servicing time to driving time.

        Returns:
            float: The servicing-to-driving ratio, or 0 if driving time is zero.
        """
        if self.total_driving_time == 0:
            return 0.0

        return self.total_servicing_time / self.total_driving_time

    def get_average_tasks_per_shift(self) -> float:
        """
        Retrieves the average task per shift
        Returns:
            float: average task per shift.
        """
        if len(self.tasks_completed_per_shift) == 0:
            return 0.0

        return sum(self.tasks_completed_per_shift) / len(self.tasks_completed_per_shift)

    def get_vehicle_utilization_ratio(self) -> float:
        """
        Computes the vehicle utilization ratio,
        defined as the ratio of active time to idle.

        Returns:
            float: The vehicle utilization ratio.
        """
        if self.vehicle_idle_time == 0 and self.vehicle_active_time > 0:
            return 1.0
        elif self.vehicle_idle_time == 0 and self.vehicle_active_time == 0:
            return 0.0
        else:
            return self.vehicle_active_time / self.vehicle_idle_time

    def get_average_service_time_for_tasks(self) -> float:
        """
        Retrieves the average service time for tasks.
        Returns:
            float: average service time for tasks.
        """
        if len(self.response_times) == 0:
            return 0.0

        return sum(self.response_times) / len(self.response_times)

    def get_vehicle_distance_traveled(self) -> float:
        """Return aggregate distance across active and completed routes.

        Returns:
            float: Total distance traveled by all vehicles in meters.
        """

        active_distance = sum(
            route.get_distance_traveled() for route in self._active_vehicle_routes
        )
        return self._completed_vehicle_distance + active_distance
