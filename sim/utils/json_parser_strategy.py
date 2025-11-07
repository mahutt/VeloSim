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

import json
import simpy
from datetime import datetime
from typing import Dict
from sim.entities.inputParameters import InputParameter
from sim.entities.station import Station
from sim.entities.resource import Resource
from sim.entities.BatterySwapTask import BatterySwapTask
from sim.entities.position import Position
from sim.utils.base_parse_strategy import BaseParseStrategy


class JsonParseStrategy(BaseParseStrategy):

    def _time_to_seconds(self, time_str: str) -> int:
        try:
            t = datetime.strptime(time_str, "%H:%M")
            return t.hour * 3600 + t.minute * 60
        except Exception:
            print(f"Invalid time format '{time_str}', defaulting to 0s.")
            return 0

    def parse(self, env: simpy.Environment, source: str) -> Dict[int, InputParameter]:
        try:
            data = json.loads(source)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON input: {e}") from e

        scenarios = data.get("scenarios", [])
        if not isinstance(scenarios, list) or not scenarios:
            raise ValueError("No scenarios found in JSON")

        parsed: Dict[int, InputParameter] = {}

        for scenario in scenarios:
            sid = scenario.get("id")
            content = scenario.get("content", {})
            name = scenario.get("name", f"Scenario {sid}")

            # Convers HH:MM to seconds for the sim
            start_str = str(content.get("start_time", "00:00"))
            end_str = str(content.get("end_time", "00:00"))
            start_time = self._time_to_seconds(start_str)
            end_time = self._time_to_seconds(end_str)

            sim_time = end_time - start_time
            if sim_time < 0:
                sim_time += 24 * 3600
            sim_time = int(sim_time)
            # Stations
            stations: Dict[int, Station] = {}
            for s in content.get("stations", []):
                try:
                    station_id = int(s["station_id"])
                    pos = s.get("station_position", [0, 0])
                    stations[station_id] = Station(
                        env=env,
                        station_id=station_id,
                        name=s.get("station_name", f"Station {station_id}"),
                        position=Position(pos),
                    )
                except Exception as e:
                    print(f"[WARN] Failed to parse station {s}: {e}")

            # Tasks
            tasks: Dict[int, BatterySwapTask] = {}

            for t in content.get("initial_tasks", []):
                try:
                    tid = int(str(t["id"]).strip("t"))
                    station_ref = stations.get(int(t["station_id"]))
                    tasks[tid] = BatterySwapTask(
                        env=env,
                        task_id=tid,
                        station=station_ref,
                        spawn_delay=0.0,
                    )
                except Exception as e:
                    print(f"[WARN] Failed to parse initial task {t}: {e}")

            for t in content.get("scheduled_tasks", []):
                try:
                    tid = int(str(t["id"]).strip("t"))
                    station_ref = stations.get(int(t["station_id"]))
                    delay = float(t.get("time", 0))
                    tasks[tid] = BatterySwapTask(
                        env=env,
                        task_id=tid,
                        station=station_ref,
                        spawn_delay=delay,
                    )
                except Exception as e:
                    print(f"[WARN] Failed to parse scheduled task {t}: {e}")

            # Ressources
            resources: Dict[int, Resource] = {}
            for r in content.get("resources", []):
                try:
                    rid = int(r["resource_id"])
                    pos = r.get("resource_position", [0, 0])

                    resources[rid] = Resource(
                        env=env,
                        resource_id=rid,
                        position=Position(pos),
                        task_list=[],
                    )
                except Exception as e:
                    print(f"[WARN] Failed to parse resource {r}: {e}")

            params = InputParameter(
                station_entities=stations,
                resource_entities=resources,
                task_entities=tasks,
                real_time_factor=1.0,
                key_frame_freq=3000,
                sim_time=int(sim_time),
            )

            parsed[sid] = params

            print(
                f"Parsed Scenario '{name}' (id={sid}) → "
                f"{len(stations)} stations, {len(resources)} resources, "
                f"{len(tasks)} tasks, sim_time={sim_time:.0f}s"
            )

        return parsed
