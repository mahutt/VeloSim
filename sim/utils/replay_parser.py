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

from typing import Any
from sim.entities.battery_swap_task import BatterySwapTask
from sim.entities.input_parameter import InputParameter
from sim.entities.position import Position
from sim.entities.shift import Shift
from sim.entities.simulation_replay_state import SimulationRuntimeState
from sim.entities.station import Station
from sim.entities.driver import Driver, DriverState
from sim.entities.task_state import State
from sim.entities.vehicle import Vehicle
from sim.map.map_controller import MapController
from grafana_logging.logger import get_logger

logger = get_logger(__name__)


class ReplayParser:
    """
    Reconstructs InputParameter from Scenario + Keyframe DTOs.
    Replay is authoritative state hydration.
    """

    STATE_MAP = {str(e): e for e in State}
    DRIVER_STATE_MAP = {str(e): e for e in DriverState}

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
            days = int(day_part.replace("day", "")) - 1
            hours = int(hour_str)
            minutes = int(minute_str)

        else:
            raise ValueError(f"Invalid time format: {time_str}")

        return days * 24 * 3600 + hours * 3600 + minutes * 60

    @staticmethod
    def _is_valid_coordinate_pair(coord: Any) -> bool:
        """
        Validates a single coordinate pair [lon, lat].
        """
        if not isinstance(coord, (list, tuple)):
            return False
        if len(coord) != 2:
            return False
        if not all(isinstance(v, (int, float)) for v in coord):
            return False
        return True

    @classmethod
    def parse(
        cls,
        scenario_json: dict,
        keyframe_json: dict,
    ) -> SimulationRuntimeState:
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

        scenario_end = cls._time_str_to_seconds(scenario_json["end_time"])

        current_time_seconds = int(keyframe_json["clock"]["simSecondsPassed"])
        # Old keyframes persisted might not have values for these fields, hence fallback
        was_running = keyframe_json["clock"].get("running", True)
        real_time_factor = keyframe_json["clock"].get("realTimeFactor", 1.0)
        paused_by_user = keyframe_json["clock"].get("pausedByUser", False)

        input_param = InputParameter(
            station_entities={},
            driver_entities={},
            vehicle_entities={},
            task_entities={},
            sim_time=scenario_end,
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

                if not isinstance(coordinates, list) or len(coordinates) < 2:
                    logger.warning(
                        "Invalid route coordinates for driver %s: %s",
                        d["id"],
                        coordinates,
                    )
                else:
                    start_coord = coordinates[0]
                    end_coord = coordinates[-1]

                    if not (
                        cls._is_valid_coordinate_pair(start_coord)
                        and cls._is_valid_coordinate_pair(end_coord)
                    ):
                        logger.warning(
                            "Malformed route coordinates for "
                            "driver %s: start=%s end=%s",
                            d["id"],
                            start_coord,
                            end_coord,
                        )
                    else:
                        start = Position(start_coord)
                        end = Position(end_coord)

                        route = map_controller.get_route(a=start, b=end)

            shift_data = d.get("shift")

            shift = Shift(
                start_time=shift_data["startTime"],
                end_time=shift_data["endTime"],
                lunch_break=shift_data.get("lunchBreak"),
                sim_start_time=shift_data["startTime"],
                sim_end_time=shift_data["endTime"],
                sim_lunch_break=shift_data.get("lunchBreak"),
            )

            driver = Driver(
                driver_id=d["id"],
                position=Position(d["position"]),
                route=route,
                shift=shift,
            )

            driver.set_map_controller(map_controller)
            drivers_by_id[driver.id] = driver
            input_param.add_driver(driver)

        # Tasks

        for t in keyframe_json["tasks"]:
            task = BatterySwapTask(
                task_id=t["id"],
                station=None,
            )

            state_str = t["state"].lower()
            if state_str not in cls.STATE_MAP:
                raise ValueError(f"Unknown task state: {state_str}")

            task.set_state(cls.STATE_MAP[state_str])
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

            state_str = d.get("state")
            if state_str:
                state_key = state_str.lower()
                if state_key not in cls.DRIVER_STATE_MAP:
                    raise ValueError(f"Unknown driver state: {state_str}")
                driver.set_state(cls.DRIVER_STATE_MAP[state_key])

        # Construct Replay State

        replay_state = SimulationRuntimeState(
            input_param,
            map_controller,
            current_time_seconds,
            was_running=was_running,
            real_time_factor=real_time_factor,
            paused_by_user=paused_by_user,
        )

        return replay_state
