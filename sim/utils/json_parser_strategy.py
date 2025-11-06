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
from sim.entities.inputParameters import InputParameter
from sim.entities.station import Station
from sim.entities.resource import Resource
from sim.entities.BatterySwapTask import BatterySwapTask
from sim.entities.position import Position
from sim.utils.base_parse_strategy import BaseParseStrategy


class JsonParseStrategy(BaseParseStrategy):

    def parse(self, env: simpy.Environment, source: str) -> InputParameter:

        try:
            data = json.loads(source)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON input: {e}") from e

        stations = {}
        for sid, sdata in data.get("stations", {}).items():
            try:
                stations[int(sid)] = Station(
                    env=env,
                    station_id=int(sid),
                    name=sdata.get("name", f"Station {sid}"),
                    position=Position(sdata["position"]),
                )
            except KeyError as e:
                print(f"Station {sid} missing key {e}")

        tasks = {}
        for tid, tdata in data.get("tasks", {}).items():
            try:
                station_ref = stations.get(tdata.get("station_id"))
                tasks[int(tid)] = BatterySwapTask(
                    env=env,
                    task_id=int(tid),
                    station=station_ref,
                    spawn_delay=tdata.get("spawn_delay"),
                )
            except Exception as e:
                print(f"Failed to parse Task {tid}: {e}")

        resources = {}
        for rid, rdata in data.get("resources", {}).items():
            try:
                resources[int(rid)] = Resource(
                    env=env,
                    resource_id=int(rid),
                    position=Position(rdata["position"]),
                    task_list=list(tasks.values()),
                )
            except KeyError as e:
                print(f"Resource {rid} missing key {e}")

        params = InputParameter(
            station_entities=stations,
            resource_entities=resources,
            task_entities=tasks,
            real_time_factor=data.get("realTimeFactor", 1.0),
            key_frame_freq=data.get("keyFrameFreq", 3000),
        )

        print(
            f"Parsed JSON: {len(stations)} stations, "
            f"{len(resources)} resources, {len(tasks)} tasks"
        )

        return params
