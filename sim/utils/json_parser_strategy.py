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

from datetime import datetime
from typing import Dict
from sim.entities.inputParameters import InputParameter
from sim.entities.station import Station
from sim.entities.resource import Resource
from sim.entities.BatterySwapTask import BatterySwapTask
from sim.entities.position import Position
from sim.utils.base_parse_strategy import BaseParseStrategy


class JsonParseStrategy(BaseParseStrategy):
    """JSON-based scenario parsing strategy implementation."""

    def _time_to_seconds(self, time_str: str) -> int:
        """Convert day-time string to total seconds.

        Converts time format 'dayX:HH:MM' to total seconds from start.

        Args:
            time_str: Time string in format 'dayX:HH:MM' (e.g., 'day1:08:30').

        Returns:
            Total seconds from simulation start. Returns 0 if format is invalid.
        """
        try:
            daytime_split = time_str.split(":", 1)
            day = daytime_split[0]
            time = daytime_split[1]
            t = datetime.strptime(time, "%H:%M")
            day_int = int(day[-1]) - 1
            return (day_int * 24) * 3600 + t.hour * 3600 + t.minute * 60
        except Exception:
            print(f"Invalid time format '{time_str}', defaulting to 0s.")
            return 0

    def parse(self, scenario_json: dict) -> InputParameter:
        """Parse a single scenario JSON and return InputParameter.

        Converts scenario JSON format into an InputParameter object containing
        all simulation configuration including stations, resources, and tasks.

        Args:
            scenario_json: Dictionary containing scenario configuration data.

        Returns:
            InputParameter object with parsed simulation configuration.
        """
        content = scenario_json.get("content", {})
        start_time = self._time_to_seconds(str(content.get("start_time", "Day1:00:00")))
        end_time = self._time_to_seconds(str(content.get("end_time", "Day1:00:00")))

        sim_time = end_time - start_time

        # Build stations
        stations: Dict[int, Station] = {}
        for s in content.get("stations", []):
            station_id = int(s["station_id"])
            pos = Position(s.get("station_position", [0, 0]))
            stations[station_id] = Station(
                station_id=station_id,
                name=s.get("station_name", f"Station {station_id}"),
                position=pos,
            )

        # Build resources
        resources: Dict[int, Resource] = {}
        for r in content.get("resources", []):
            rid = int(r["resource_id"])
            pos = Position(r.get("resource_position", [0, 0]))
            resources[rid] = Resource(resource_id=rid, position=pos, task_list=[])

        # Build tasks
        tasks: Dict[int, BatterySwapTask] = {}
        task_id_counter = 1

        # Initial tasks
        for t in content.get("initial_tasks", []):
            tid = task_id_counter
            task_id_counter += 1

            station_ref = stations[int(t["station_id"])]
            task = BatterySwapTask(task_id=tid, station=station_ref, spawn_delay=0.0)
            tasks[tid] = task
            station_ref.add_task(task)

            # Assign to resource if specified
            assigned_rid = t.get("assigned_resource_id")
            if assigned_rid is not None:
                resources[int(assigned_rid)].assign_task(task)

        # Scheduled tasks
        for t in content.get("scheduled_tasks", []):
            tid = task_id_counter
            task_id_counter += 1

            station_ref = stations[int(t["station_id"])]
            raw_time = t.get("time", 0)
            if isinstance(raw_time, str):
                delay = self._time_to_seconds(raw_time) - start_time
            else:
                delay = int(raw_time)

            task = BatterySwapTask(task_id=tid, station=station_ref, spawn_delay=delay)
            tasks[tid] = task
            station_ref.add_task(task)

        params = InputParameter(
            station_entities=stations,
            resource_entities=resources,
            task_entities=tasks,
            real_time_factor=content.get("real_time_factor", 1.0),
            key_frame_freq=content.get("key_frame_freq", 20),
            sim_time=sim_time,
            start_time=start_time,
        )

        return params
