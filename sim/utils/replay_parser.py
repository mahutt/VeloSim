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

from typing import Any, Optional
from sim.core.simulation_report import SimulationReport
from sim.entities.battery_swap_task import BatterySwapTask
from sim.entities.input_parameter import InputParameter
from sim.entities.position import Position
from sim.entities.route import Route
from sim.entities.shift import Shift
from sim.entities.simulation_replay_state import SimulationRuntimeState
from sim.entities.station import Station
from sim.entities.driver import Driver, DriverState
from sim.entities.task_state import State
from sim.entities.vehicle import Vehicle
from sim.entities.map_payload import MapPayload
from sim.map.map_controller import MapController
from sim.utils.traffic_config_extractor import extract_traffic_config
from grafana_logging.logger import get_logger

logger = get_logger(__name__)


def _coerce_tasks_completed(value: object) -> int:
    """Convert tasks_completed_per_shift from any persisted format to int.

    Old keyframes stored this as a list[int] (per-shift counts).
    New keyframes store it as a plain int (running total).
    """
    if isinstance(value, int):
        return value
    if isinstance(value, list):
        return sum(int(v) for v in value)
    return 0


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
        into seconds since day start
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
        traffic_csv_data: Optional[str] = None,
    ) -> SimulationRuntimeState:
        """
        Reconstruct simulation input parameters from scenario and keyframe data.

        This method hydrates domain entities (stations, vehicles, drivers, tasks)
        and reconnects relationships based on persisted replay data.

        Args:
            scenario_json: Serialized scenario configuration.
            keyframe_json: Serialized keyframe snapshot of simulation state.
            traffic_csv_data: Optional persisted traffic CSV content for replay.

        Returns:
            A tuple containing:
                - The reconstructed InputParameter object.
                - The MapController used for route reconstruction.
        """

        scenario_end = cls._time_str_to_seconds(scenario_json["end_time"])

        current_time_seconds = int(keyframe_json["clock"]["simSecondsPassed"])
        sim_start_time = keyframe_json["clock"]["startTime"]
        # Old keyframes persisted might not have values for these fields, hence fallback
        was_running = keyframe_json["clock"].get("running", True)
        real_time_factor = keyframe_json["clock"].get("realTimeFactor", 1.0)
        paused_by_user = keyframe_json["clock"].get("pausedByUser", False)

        # Extract traffic config from scenario + persisted CSV data
        traffic_config = extract_traffic_config(scenario_json, traffic_csv_data)
        map_payload = MapPayload(traffic=traffic_config) if traffic_config else None

        input_param = InputParameter(
            station_entities={},
            driver_entities={},
            vehicle_entities={},
            task_entities={},
            sim_time=scenario_end,
            start_time=sim_start_time,
            map_payload=map_payload,
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

        for d in keyframe_json["drivers"]:

            shift_data = d.get("shift")

            shift = Shift(
                start_time=shift_data["startTime"],
                end_time=shift_data["endTime"],
                lunch_break=shift_data.get("lunchBreak"),
                sim_start_time=sim_start_time,
            )

            driver = Driver(
                driver_id=d["id"],
                position=Position(d["position"]),
                routes=[],
                shift=shift,
                name=d["name"],
            )

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
            task.service_time_remaining = t.get("serviceTimeRemaining")
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

            driver.service_chain_station_id = d.get("serviceChainStationId")

        # Construct Replay State

        report_snapshot = keyframe_json.get("reportingSnapshot")

        sim_report = SimulationReport()

        snapshot = report_snapshot or {}

        sim_report.restore_state(
            total_driving_time=float(snapshot.get("total_driving_time", 0)),
            total_servicing_time=float(snapshot.get("total_servicing_time", 0)),
            tasks_completed_per_shift=_coerce_tasks_completed(
                snapshot.get("tasks_completed_per_shift", 0)
            ),
            response_times=snapshot.get("response_times", []),
            vehicle_idle_time=float(snapshot.get("vehicle_idle_time", 0)),
            vehicle_active_time=float(snapshot.get("vehicle_active_time", 0)),
            completed_vehicle_distance=float(
                snapshot.get("completed_vehicle_distance", 0.0)
            ),
        )
        replay_state = SimulationRuntimeState(
            input_param,
            current_time_seconds,
            was_running=was_running,
            real_time_factor=real_time_factor,
            paused_by_user=paused_by_user,
            sim_report=sim_report,
        )

        return replay_state

    @staticmethod
    def restore_routes(
        drivers: list[Driver],
        keyframe_json: dict[str, Any],
        map_controller: MapController,
    ) -> None:
        """Reconstruct and assign routes to drivers from
        persisted keyframe data.

        This method parses serialized route coordinate
        data from the keyframe
        and regenerates corresponding Route objects
        using the provided
        MapController. It restores each driver's route
        sequence and assigns
        the necessary dependencies for route
        execution.

        For the first route, the driver's current
        position is used as the
        starting point to ensure continuity from the
        last persisted state.
        Subsequent routes use the stored coordinates
        directly.

        Invalid or malformed route data is skipped with
        appropriate logging.

        Args:
            drivers (list[Driver]): The list of
            active driver entities to restore routes for.
            keyframe_json (dict[str, Any]): The persisted
            simulation snapshot containing driver route data.
            map_controller (MapController): The map controller
            used to generate Route objects.

        Returns:
            None
        """

        driver_lookup = {driver.id: driver for driver in drivers}

        for d in keyframe_json.get("drivers", []):
            driver_id = d.get("id")

            driver = driver_lookup.get(driver_id)
            if not driver:
                logger.warning("Driver %s not found in active drivers", driver_id)
                continue

            route_data = d.get("routes", [])

            if not isinstance(route_data, list):
                logger.warning("Invalid routes format for driver %s", driver_id)
                continue

            routes: list[Route] = []

            first_route = True

            for route_load in route_data:

                if not isinstance(route_load, list) or len(route_load) != 2:
                    logger.warning(
                        "Invalid route coordinates for driver %s: %s",
                        driver_id,
                        route_load,
                    )
                    continue

                # This ensures for the first route
                # the driver spawns at his last saved position.
                if first_route == True:
                    start = driver.get_position()
                    first_route = False
                else:
                    start = Position(route_load[0])

                end = Position(route_load[1])

                try:
                    generated_route = map_controller.get_route(a=start, b=end)

                    routes.append(generated_route)

                except Exception as e:
                    logger.error(
                        "Exception generating route for driver %s: %s - skipping",
                        driver_id,
                        e,
                    )
                    continue

            if routes:
                driver.set_routes(routes)
                driver.set_map_controller(map_controller)
            else:
                logger.warning(
                    "No routes restored for driver %s.",
                    driver_id,
                )

    @staticmethod
    def get_active_routes(drivers: list[Driver]) -> set[Route]:
        """Extract the set of active (in-progress) routes from drivers.

        This method iterates through all drivers and collects their current
        active routes, excluding:
        - Drivers without a current route
        - Invalid route types (e.g., incorrectly assigned lists)
        - Routes that have already been completed

        The resulting set is used for real-time distance tracking and
        reporting within the simulation.

        Args:
            drivers (list[Driver]): The list of driver entities to inspect.

        Returns:
            set[Route]: A set of active routes currently being followed by drivers.
        """
        active_routes: set[Route] = set()

        for driver in drivers:
            current_route = driver.current_route

            # Skip if no current route
            if current_route is None:
                continue

            # Safety check (in case bad data slipped through)
            if isinstance(current_route, list):
                continue

            # Skip finished routes
            if current_route.is_finished:
                continue

            # Add valid active route
            active_routes.add(current_route)

        return active_routes
