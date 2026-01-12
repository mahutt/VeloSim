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

from sim.entities.BatterySwapTask import BatterySwapTask
from sim.entities.inputParameters import InputParameter
from sim.entities.position import Position
from sim.entities.shift import Shift
from sim.entities.station import Station
from sim.entities.driver import Driver, DriverState
from sim.entities.task_state import State
from sim.entities.vehicle import Vehicle
from sim.map.MapController import MapController


STATE_MAP = {
    "scheduled": State.SCHEDULED,
    "open": State.OPEN,
    "assigned": State.ASSIGNED,
    "in_progress": State.IN_PROGRESS,
    "inprogress": State.IN_PROGRESS,
    "closed": State.CLOSED,
}


class ReplayParser:
    """
    Reconstructs InputParameter from Scenario + Keyframe DTOs.
    Replay is authoritative state hydration.
    """

    @staticmethod
    def _time_str_to_seconds(time_str: str) -> int:
        """
        Converts:
        - HH:MM
        - dayN:HH:MM
        into seconds since sim start
        """
        parts = time_str.split(":")

        if len(parts) == 2:
            hour_str, minute_str = parts
            days = 0
            hours = int(hour_str)
            minutes = int(minute_str)

        elif len(parts) == 3:
            day_part, hour_str, minute_str = parts
            days = int(day_part.replace("day", ""))
            hours = int(hour_str)
            minutes = int(minute_str)

        else:
            raise ValueError(f"Invalid time format: {time_str}")

        return days * 24 * 3600 + hours * 3600 + minutes * 60

    @classmethod
    def parse(
        cls,
        scenario_json: dict,
        keyframe_json: dict,
    ) -> tuple[InputParameter, MapController]:
        """
        Reconstruct simulation input parameters from scenario and keyframe data.

        This method hydrates domain entities (stations, vehicles, drivers, tasks)
        and reconnects relationships based on persisted replay data.

        Args:
            scenario_json: Serialized scenario configuration.
            keyframe_json: Serialized keyframe snapshot of simulation state.

        Returns:
            A tuple containing:
                - The reconstructed InputParameter object.
                - The MapController used for route reconstruction.
        """

        input_param = InputParameter(
            station_entities={},
            driver_entities={},
            vehicle_entities={},
            task_entities={},
            sim_time=keyframe_json["clock"]["simSecondsPassed"],
            start_time=keyframe_json["clock"]["startTime"],
        )

        # Entity lookup tables
        stations_by_id: dict[int, Station] = {}
        drivers_by_id: dict[int, Driver] = {}
        vehicles_by_id: dict[int, Vehicle] = {}
        tasks_by_id: dict[int, BatterySwapTask] = {}

        # Stations
        for s in keyframe_json["stations"]:
            station = Station(
                station_id=s["id"],
                name=s["name"],
                position=Position(s["position"]),
                tasks=[],
            )
            stations_by_id[station.id] = station
            input_param.add_station(station)

        # Vehicles

        for v in keyframe_json["vehicles"]:
            vehicle = Vehicle(
                vehicle_id=v["id"],
                battery_count=v["batteryCount"],
            )
            vehicles_by_id[vehicle.id] = vehicle
            input_param.add_vehicle(vehicle)

        # Drivers

        map_controller = MapController()

        for d in keyframe_json["drivers"]:
            route = None
            route_data = d.get("route")

            if route_data:
                coordinates = route_data.get("coordinates")
                if coordinates and len(coordinates) >= 2:
                    start = Position([coordinates[0][0], coordinates[0][1]])
                    end = Position([coordinates[-1][0], coordinates[-1][1]])
                    route = map_controller.get_route(a=start, b=end)

            driver = Driver(
                driver_id=d["id"],
                position=Position(d["position"]),
                route=route,
                shift=Shift(1, 1, 1, 1, 1),
            )

            driver.set_map_controller(map_controller)
            drivers_by_id[driver.id] = driver
            input_param.add_driver(driver)

        # Tasks

        for t in keyframe_json["tasks"]:
            task = BatterySwapTask(
                task_id=t["id"],
                station=None,
                spawn_delay=0,
            )

            state_str = t["state"].lower()
            if state_str not in STATE_MAP:
                raise ValueError(f"Unknown task state: {state_str}")

            task.set_state(STATE_MAP[state_str])
            tasks_by_id[task.id] = task
            input_param.add_task(task)

        # Station → Tasks

        for t in keyframe_json["tasks"]:
            station = stations_by_id[t["stationId"]]
            task = tasks_by_id[t["id"]]
            station.add_task(task)

        # Driver → Vehicle

        for d in keyframe_json["drivers"]:
            vehicle_id = d.get("vehicleId")
            if vehicle_id is not None:
                driver = drivers_by_id[d["id"]]
                vehicle = vehicles_by_id[vehicle_id]
                driver.set_vehicle(vehicle)

        # Driver → Tasks + State

        for d in keyframe_json["drivers"]:
            driver = drivers_by_id[d["id"]]

            for task_id in d.get("taskIds", []):
                task = tasks_by_id[task_id]
                driver.task_list.append(task)
                task.set_assigned_driver(driver)

            in_progress_id = d.get("inProgressTaskId")
            if in_progress_id is not None:
                task = tasks_by_id[in_progress_id]
                task.set_state(State.IN_PROGRESS)
                driver.state = DriverState.SERVICING_STATION
            elif driver.get_task_count() > 0:
                driver.state = DriverState.ON_ROUTE
            else:
                driver.state = DriverState.IDLE

        return input_param, map_controller
