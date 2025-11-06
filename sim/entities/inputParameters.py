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
from typing import Dict, Mapping, Optional
from sim.entities.station import Station
from sim.entities.resource import Resource
from sim.entities.task import Task


class InputParameter:

    def __init__(
        self,
        station_entities: Optional[Dict[int, Station]] = None,
        resource_entities: Optional[Dict[int, Resource]] = None,
        task_entities: Optional[Mapping[int, Task]] = None,
        real_time_factor: Optional[float] = None,
        key_frame_freq: Optional[int] = None,
    ) -> None:
        self.station_entities: Dict[int, Station] = (
            station_entities if station_entities is not None else {}
        )
        self.resource_entities: Dict[int, Resource] = (
            resource_entities if resource_entities is not None else {}
        )

        self.task_entities: Dict[int, Task] = dict(task_entities or {})

        self.realTimeFactor: Optional[float] = real_time_factor
        self.keyFrameFreq: Optional[int] = key_frame_freq

    # Getter methods
    def get_station_entities(self) -> Dict[int, Station]:
        return self.station_entities

    def get_resource_entities(self) -> Dict[int, Resource]:
        return self.resource_entities

    def get_task_entities(self) -> Dict[int, Task]:
        return self.task_entities

    def get_real_time_factor(self) -> Optional[float]:
        return self.realTimeFactor

    def get_key_frame_freq(self) -> Optional[int]:
        return self.keyFrameFreq

    # Setter methods
    def set_station_entities(self, station_entities: Dict[int, Station]) -> None:
        self.station_entities = station_entities

    def set_resource_entities(self, resource_entities: Dict[int, Resource]) -> None:
        self.resource_entities = resource_entities

    def set_task_entities(self, task_entities: Dict[int, Task]) -> None:
        self.task_entities = task_entities

    def set_real_time_factor(self, real_time_factor: Optional[float]) -> None:
        self.realTimeFactor = real_time_factor

    def set_key_frame_freq(self, key_frame_freq: Optional[int]) -> None:
        self.keyFrameFreq = key_frame_freq

    # Utility methods to add individual entities
    def add_station(self, station: Station) -> None:
        self.station_entities[station.id] = station

    def add_resource(self, resource: Resource) -> None:
        self.resource_entities[resource.id] = resource

    def add_task(self, task: Task) -> None:
        self.task_entities[task.id] = task

    # Utility methods to remove individual entities
    def remove_station(self, station: Station) -> None:
        deleted_station = self.station_entities.pop(station.id, False)
        if not deleted_station:
            print(f"remove_station(): Station: {station.id} not found")

    def remove_resource(self, resource: Resource) -> None:
        deleted_resource = self.resource_entities.pop(resource.id, False)
        if not deleted_resource:
            print(f"remove_resource(): Resource: {resource.id} not found")

    def remove_task(self, task: Task) -> None:
        deleted_task = self.task_entities.pop(task.id, False)
        if not deleted_task:
            print(f"remove_task(): Task: {task.id} not found")

    # Get counts
    def get_station_count(self) -> int:
        return len(self.station_entities)

    def get_resource_count(self) -> int:
        return len(self.resource_entities)

    def get_task_count(self) -> int:
        return len(self.task_entities)

    def __str__(self) -> str:
        data = {
            "stations": {
                sid: station.name for sid, station in self.station_entities.items()
            },
            "resources": {
                rid: getattr(resource, "name", f"Resource {rid}")
                for rid, resource in self.resource_entities.items()
            },
            "tasks": {
                tid: (
                    task.station.name
                    if (task.station is not None and hasattr(task.station, "name"))
                    else "-"
                )
                for tid, task in self.task_entities.items()
            },
            "realTimeFactor": self.realTimeFactor,
            "keyFrameFreq": self.keyFrameFreq,
            "counts": {
                "stations": len(self.station_entities),
                "resources": len(self.resource_entities),
                "tasks": len(self.task_entities),
            },
        }

        return json.dumps(data, indent=2)
