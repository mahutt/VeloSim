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

# This class is a placeholder for when we define input params later down in the project.
import json
from sim.entities.map_payload import MapPayload
from typing import Dict, Mapping, Optional, List
from sim.entities.station import Station
from sim.entities.task import Task
from sim.entities.driver import Driver
from sim.entities.vehicle import Vehicle


class InputParameter:
    """Container for simulation input parameters and entities."""

    def __init__(
        self,
        station_entities: Optional[Dict[int, Station]] = None,
        driver_entities: Optional[Dict[int, Driver]] = None,
        vehicle_entities: Optional[Dict[int, Vehicle]] = None,
        task_entities: Optional[Mapping[int, Task]] = None,
        real_time_factor: Optional[float] = None,
        key_frame_freq: Optional[int] = None,
        station_scheduled_tasks: Optional[Dict[int, Dict[int, List[int]]]] = None,
        sim_time: Optional[int] = 0,
        start_time: Optional[int] = 0,
        map_payload: Optional[MapPayload] = None,
    ) -> None:
        self.station_entities: Dict[int, Station] = (
            station_entities if station_entities is not None else {}
        )

        self.driver_entities: Dict[int, Driver] = (
            driver_entities if driver_entities is not None else {}
        )

        self.vehicle_entities: Dict[int, Vehicle] = (
            vehicle_entities if vehicle_entities is not None else {}
        )

        self.task_entities: Dict[int, Task] = dict(task_entities or {})
        self.station_scheduled_tasks: Optional[Dict[int, Dict[int, List[int]]]] = (
            station_scheduled_tasks
        )
        self.real_time_factor: Optional[float] = real_time_factor
        self.key_frame_freq: Optional[int] = key_frame_freq
        self.sim_time: int = sim_time if sim_time is not None else 0
        self.start_time: int = start_time if start_time is not None else 0
        self.map_payload: Optional[MapPayload] = map_payload

    # Getter methods
    def get_station_entities(self) -> Dict[int, Station]:
        """Get the station entities dictionary.

        Returns:
            Dictionary mapping station IDs to Station objects.
        """
        return self.station_entities

    def get_driver_entities(self) -> Dict[int, Driver]:
        """Get the driver entities dictionary.

        Returns:
            Dictionary mapping resource IDs to driver objects.
        """
        return self.driver_entities

    def get_vehicle_entities(self) -> Dict[int, Vehicle]:
        """Get the vehicle entities dictionary.

        Returns:
            Dictionary mapping vehicle IDs to driver objects.
        """
        return self.vehicle_entities

    def get_task_entities(self) -> Dict[int, Task]:
        """Get the task entities dictionary.

        Returns:
            Dictionary mapping task IDs to Task objects.
        """
        return self.task_entities

    def get_real_time_factor(self) -> Optional[float]:
        """Get the real-time pacing factor.

        Returns:
            Real seconds per simulated second, or None.
        """
        return self.real_time_factor

    def get_key_frame_freq(self) -> Optional[int]:
        """Get the key frame frequency.

        Returns:
            Number of frames between key frames, or None.
        """
        return self.key_frame_freq

    def get_start_time(self) -> int:
        """Get the simulation start time.

        Returns:
            The simulation start time.
        """
        return self.start_time

    def get_map_payload(self) -> Optional[MapPayload]:
        """Get the map payload configuration.

        Returns:
            MapPayload with map configuration, or None.
        """
        return self.map_payload

    def get_station_scheduled_tasks(self) -> Optional[Dict[int, Dict[int, List[int]]]]:
        """Get the station scheduled tasks.

        Returns:
        A Dict mapping station IDs to a Dict of times mapping to task IDs, or None.
        """
        return self.station_scheduled_tasks

    def set_station_scheduled_tasks(
        self, station_scheduled_tasks: Dict[int, Dict[int, List[int]]]
    ) -> None:
        """Set the station scheduled tasks.

        Args:
        station_scheduled_tasks: A Dict mapping station IDs to a Dict of times
        mapping to task IDs.

        Returns:
            None
        """
        self.station_scheduled_tasks = station_scheduled_tasks

    def set_sim_time(self, sim_time: int) -> None:
        """Set the simulation time.

        Args:
            sim_time: Duration to run simulation in sim seconds.

        Returns:
            None
        """
        self.sim_time = sim_time

    # Setter methods
    def set_station_entities(self, station_entities: Dict[int, Station]) -> None:
        """Set the station entities dictionary.

        Args:
            station_entities: Dictionary mapping station IDs to stations.

        Returns:
            None
        """
        self.station_entities = station_entities

    def set_driver_entities(self, driver_entities: Dict[int, Driver]) -> None:
        """Set the driver entities dictionary.

        Args:
            driver_entities: Dictionary mapping driver IDs to driver.

        Returns:
            None
        """
        self.driver_entities = driver_entities

    def set_vehicle_entities(self, vehicle_entities: Dict[int, Vehicle]) -> None:
        """Set the vehicle entities dictionary.

        Args:
            vehicle_entities: Dictionary mapping vehicle IDs to vehicle.

        Returns:
            None
        """
        self.vehicle_entities = vehicle_entities

    def set_task_entities(self, task_entities: Dict[int, Task]) -> None:
        """Set the task entities dictionary.

        Args:
            task_entities: Dictionary mapping task IDs to tasks.

        Returns:
            None
        """
        self.task_entities = task_entities

    def set_real_time_factor(self, real_time_factor: Optional[float]) -> None:
        """Set the real-time pacing factor.

        Args:
            real_time_factor: Real seconds per simulated second.

        Returns:
            None
        """
        self.real_time_factor = real_time_factor

    def set_key_frame_freq(self, key_frame_freq: Optional[int]) -> None:
        """Set the key frame frequency.

        Args:
            key_frame_freq: Number of frames between key frames.

        Returns:
            None
        """
        self.key_frame_freq = key_frame_freq

    # Utility methods to add individual entities
    def add_station(self, station: Station) -> None:
        """Add a station to the entities.

        Args:
            station: The station to add.

        Returns:
            None
        """
        self.station_entities[station.id] = station

    def add_driver(self, driver: Driver) -> None:
        """Add a driver to the entities.

        Args:
            driver: The driver to add.

        Returns:
            None
        """
        self.driver_entities[driver.id] = driver

    def add_vehicle(self, vehicle: Vehicle) -> None:
        """Add a vehicle to the entities.

        Args:
            driver: The vehicle to add.

        Returns:
            None
        """
        self.vehicle_entities[vehicle.id] = vehicle

    def add_task(self, task: Task) -> None:
        """Add a task to the entities.

        Args:
            task: The task to add.

        Returns:
            None
        """
        self.task_entities[task.id] = task

    # Utility methods to remove individual entities
    def remove_station(self, station: Station) -> None:
        """Remove a station from the entities.

        Args:
            station: The station to remove.

        Returns:
            None
        """
        deleted_station = self.station_entities.pop(station.id, False)
        if not deleted_station:
            print(f"remove_station(): Station: {station.id} not found")

    def remove_driver(self, driver: Driver) -> None:
        """Remove a driver from the entities.

        Args:
            driver: The driver to remove.

        Returns:
            None
        """
        deleted_resource = self.driver_entities.pop(driver.id, False)
        if not deleted_resource:
            print(f"remove_driver(): driver: {driver.id} not found")

    def remove_vehicle(self, vehicle: Vehicle) -> None:
        """Remove a vehicle from the entities.

        Args:
            vehicle: The vehicle to remove.

        Returns:
            None
        """
        deleted_vehicle = self.vehicle_entities.pop(vehicle.id, False)
        if not deleted_vehicle:
            print(f"remove_resource(): Resource: {vehicle.id} not found")

    def remove_task(self, task: Task) -> None:
        """Remove a task from the entities.

        Args:
            task: The task to remove.

        Returns:
            None
        """
        deleted_task = self.task_entities.pop(task.id, False)
        if not deleted_task:
            print(f"remove_task(): Task: {task.id} not found")

    # Get counts
    def get_station_count(self) -> int:
        """Get the number of stations.

        Returns:
            The count of station entities.
        """
        return len(self.station_entities)

    def get_driver_count(self) -> int:
        """Get the number of drivers.

        Returns:
            The count of driver entities.
        """
        return len(self.driver_entities)

    def get_vehicle_count(self) -> int:
        """Get the number of vehicle.

        Returns:
            The count of vehicle entities.
        """
        return len(self.vehicle_entities)

    def get_task_count(self) -> int:
        """Get the number of tasks.

        Returns:
            The count of task entities.
        """
        return len(self.task_entities)

    def __str__(self) -> str:
        data = {
            "stations": {
                sid: station.name for sid, station in self.station_entities.items()
            },
            "drivers": {
                did: getattr(driver, "name", f"Resource {did}")
                for did, driver in self.driver_entities.items()
            },
            "vehicles": {
                vid: getattr(vehicle, "name", f"Resource {vid}")
                for vid, vehicle in self.vehicle_entities.items()
            },
            "tasks": {
                tid: {
                    "station": (
                        task.station.name
                        if (task.station is not None and hasattr(task.station, "name"))
                        else "-"
                    ),
                    "spawn_time": (
                        round(task.spawn_time, 2)
                        if hasattr(task, "spawn_time")
                        else None
                    ),
                    "state": str(task.state),
                }
                for tid, task in self.task_entities.items()
            },
            "realTimeFactor": self.real_time_factor,
            "sim_time": self.sim_time,
            "keyFrameFreq": self.key_frame_freq,
        }

        return json.dumps(data, indent=2)
