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

import simpy
from sim.entities.BatterySwapTask import BatterySwapTask
from sim.entities.inputParameters import InputParameter
from sim.entities.position import Position
from sim.entities.resource import Resource
from sim.entities.station import Station


def create_default_input_parameters() -> InputParameter:
    """
    Create a default InputParameter with a minimal, valid simulation setup.
    """

    env = simpy.Environment()

    # Stations
    station_1 = Station(env, 1, "Station A", Position([0.0, 0.0]))
    station_2 = Station(env, 2, "Station B", Position([10.0, 5.0]))

    # Resources
    resource_1 = Resource(env, 1, Position([1.0, 1.0]))
    resource_2 = Resource(env, 2, Position([9.0, 4.0]))

    # Tasks ---
    task_1 = BatterySwapTask(env, 1, station_1)
    task_2 = BatterySwapTask(env, 2, station_1)
    task_3 = BatterySwapTask(env, 3, station_2)

    # Assign tasks to stations
    station_1.add_task(task_1)
    station_1.add_task(task_2)
    station_2.add_task(task_3)

    # Assign resources to some tasks
    resource_1.assign_task(task_1)  # Assigned to Station A
    resource_2.assign_task(task_3)  # Assigned to Station B

    # Optionally, mark a task as in-progress
    resource_1.dispatch_task(task_1)

    # Wrap entities in dictionaries
    stations = {station_1.id: station_1, station_2.id: station_2}
    resources = {resource_1.id: resource_1, resource_2.id: resource_2}
    tasks = {task_1.id: task_1, task_2.id: task_2, task_3.id: task_3}

    # Build and return the InputParameter
    params = InputParameter(
        station_entities=stations,
        resource_entities=resources,
        task_entities=tasks,
        real_time_factor=1.0,
        key_frame_freq=10,
    )

    return params
