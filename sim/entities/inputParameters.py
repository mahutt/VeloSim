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
from typing import List, Optional
from sim.entities.station import Station
from sim.entities.resource import Resource
from sim.entities.task import Task


class InputParameter:

    def __init__(
        self,
        station_entities: Optional[List[Station]] = None,
        resource_entities: Optional[List[Resource]] = None,
        task_entities: Optional[List[Task]] = None,
        real_time_factor: Optional[float] = None,
        key_frame_freq: Optional[int] = None
    ) -> None:
        self.stationEntities: List[Station] = station_entities if station_entities is not None else []
        self.resourcEntities: List[Resource] = resource_entities if resource_entities is not None else []
        self.taskEntities: List[Task] = task_entities if task_entities is not None else []
        self.realTimeFactor: Optional[float] = real_time_factor
        self.keyFrameFreq: Optional[int] = key_frame_freq

    # Getter methods
    def get_station_entities(self) -> List[Station]:
        return self.stationEntities

    def get_resource_entities(self) -> List[Resource]:
        return self.resourcEntities

    def get_task_entities(self) -> List[Task]:
        return self.taskEntities

    def get_real_time_factor(self) -> Optional[float]:
        return self.realTimeFactor

    def get_key_frame_freq(self) -> Optional[int]:
        return self.keyFrameFreq

    # Setter methods
    def set_station_entities(self, station_entities: List[Station]) -> None:
        self.stationEntities = station_entities

    def set_resource_entities(self, resource_entities: List[Resource]) -> None:
        self.resourcEntities = resource_entities

    def set_task_entities(self, task_entities: List[Task]) -> None:
        self.taskEntities = task_entities

    def set_real_time_factor(self, real_time_factor: Optional[float]) -> None:
        self.realTimeFactor = real_time_factor

    def set_key_frame_freq(self, key_frame_freq: Optional[int]) -> None:
        self.keyFrameFreq = key_frame_freq

    # Utility methods to add individual entities
    def add_station(self, station: Station) -> None:
        self.stationEntities.append(station)

    def add_resource(self, resource: Resource) -> None:
        self.resourcEntities.append(resource)

    def add_task(self, task: Task) -> None:
        self.taskEntities.append(task)

    # Utility methods to remove individual entities
    def remove_station(self, station: Station) -> None:
        if station in self.stationEntities:
            self.stationEntities.remove(station)

    def remove_resource(self, resource: Resource) -> None:
        if resource in self.resourcEntities:
            self.resourcEntities.remove(resource)

    def remove_task(self, task: Task) -> None:
        if task in self.taskEntities:
            self.taskEntities.remove(task)

    # Get counts
    def get_station_count(self) -> int:
        return len(self.stationEntities)

    def get_resource_count(self) -> int:
        return len(self.resourcEntities)

    def get_task_count(self) -> int:
        return len(self.taskEntities)

    

