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

# sim/main.py
from typing import List
import simpy
from sim.entities.frame import Frame
from sim.entities.inputParameters import InputParameter
from sim.entities.station import Station
from sim.entities.resource import Resource
from sim.entities.position import Position
from sim.utils.subscriber import Subscriber
from sim.simulator import Simulator
from sim.entities.BatterySwapTask import BatterySwapTask

from sim.behaviour.sim_behaviour import SimBehaviour


class LoggerSubscriber(Subscriber):
    def __init__(self, name: str) -> None:
        self.name = name

    def on_frame(self, frame: Frame) -> None:
        print(f"[{self.name}] Received: {frame}\n\n")


class WebSocketSubscriber(Subscriber):
    def __init__(self, name: str) -> None:
        self.name = name

    def on_frame(self, frame: Frame) -> None:
        print(f"[{self.name}] Received: {frame}\n\n")


# Create a temporary environment for entity creation
temp_env = simpy.Environment()

temp_env2 = simpy.Environment()

# Montreal coordinates - various stations
ikea = Position([-73.691993, 45.490198])  # IKEA
concordia = Position([-73.577797, 45.495009])  # Concordia University
mcgill = Position([-73.577309, 45.504600])  # McGill University
downtown = Position([-73.569740, 45.501689])  # Downtown Montreal
old_montreal = Position([-73.554250, 45.508888])  # Old Montreal
olympic_stadium = Position([-73.551659, 45.557583])  # Olympic Stadium
jean_talon_market = Position([-73.613426, 45.534917])  # Jean-Talon Market
mont_royal = Position([-73.587807, 45.508840])  # Mount Royal

# Create example stations
station1 = Station(temp_env, station_id=1, name="Ikea", position=ikea)
station2 = Station(temp_env, station_id=2, name="Concordia", position=concordia)
station3 = Station(temp_env, station_id=3, name="McGill", position=mcgill)
station4 = Station(temp_env, station_id=4, name="Downtown", position=downtown)
station5 = Station(temp_env, station_id=5, name="Old Montreal", position=old_montreal)
station6 = Station(
    temp_env, station_id=6, name="Olympic Stadium", position=olympic_stadium
)

# Create example resources at different starting positions
resource1 = Resource(temp_env, resource_id=101, position=ikea)
resource2 = Resource(temp_env, resource_id=102, position=mcgill)
resource3 = Resource(temp_env, resource_id=103, position=jean_talon_market)
resource4 = Resource(temp_env, resource_id=104, position=mont_royal)

# Create tasks for different stations
task1 = BatterySwapTask(temp_env, 1, station2)  # Task at Concordia
task2 = BatterySwapTask(temp_env, 2, station3)  # Task at McGill
task3 = BatterySwapTask(temp_env, 3, station5)  # Task at Old Montreal
task4 = BatterySwapTask(temp_env, 4, station6)  # Task at Olympic Stadium

# Add tasks to their respective stations
station2.add_task(task1)
station3.add_task(task2)
station5.add_task(task3)
station6.add_task(task4)

# Assign initial task to first resource
resource1.assign_task(task1)

# ===== SECOND SIMULATION ENTITIES =====
# Additional Montreal locations for second simulation
verdun = Position([-73.569000, 45.453140])  # Verdun
plateau = Position([-73.586273, 45.523064])  # Plateau Mont-Royal
chinatown = Position([-73.561989, 45.508614])  # Chinatown
atwater_market = Position([-73.583092, 45.477344])  # Atwater Market
parc_jarry = Position([-73.628571, 45.534180])  # Parc Jarry
notre_dame = Position([-73.553810, 45.504722])  # Notre-Dame Basilica

# Create stations for second simulation
station7 = Station(temp_env2, station_id=7, name="Verdun", position=verdun)
station8 = Station(temp_env2, station_id=8, name="Plateau", position=plateau)
station9 = Station(temp_env2, station_id=9, name="Chinatown", position=chinatown)
station10 = Station(
    temp_env2, station_id=10, name="Atwater Market", position=atwater_market
)
station11 = Station(temp_env2, station_id=11, name="Parc Jarry", position=parc_jarry)
station12 = Station(temp_env2, station_id=12, name="Notre-Dame", position=notre_dame)

# Create resources for second simulation
resource5 = Resource(temp_env2, resource_id=201, position=verdun)
resource6 = Resource(temp_env2, resource_id=202, position=plateau)
resource7 = Resource(temp_env2, resource_id=203, position=atwater_market)
resource8 = Resource(temp_env2, resource_id=204, position=parc_jarry)

# Create tasks for second simulation
task5 = BatterySwapTask(temp_env2, 5, station8)  # Task at Plateau
task6 = BatterySwapTask(temp_env2, 6, station9)  # Task at Chinatown
task7 = BatterySwapTask(temp_env2, 7, station10)  # Task at Atwater Market
task8 = BatterySwapTask(temp_env2, 8, station12)  # Task at Notre-Dame

# Add tasks to their respective stations
station8.add_task(task5)
station9.add_task(task6)
station10.add_task(task7)
station12.add_task(task8)

# Assign initial task to first resource of second simulation
resource5.assign_task(task5)

# Create InputParameter with example entities and simulation settings
params = InputParameter(
    station_entities={
        1: station1,
        2: station2,
        3: station3,
        4: station4,
        5: station5,
        6: station6,
    },
    resource_entities={
        101: resource1,
        102: resource2,
        103: resource3,
        104: resource4,
    },
    task_entities={
        1: task1,
        2: task2,
        3: task3,
        4: task4,
    },
    real_time_factor=1,  # Real-time simulation
    key_frame_freq=3000,  # Key frame every 3000 frames
)

# Create InputParameter for second simulation
params2 = InputParameter(
    station_entities={
        7: station7,
        8: station8,
        9: station9,
        10: station10,
        11: station11,
        12: station12,
    },
    resource_entities={
        201: resource5,
        202: resource6,
        203: resource7,
        204: resource8,
    },
    task_entities={
        5: task5,
        6: task6,
        7: task7,
        8: task8,
    },
    real_time_factor=1,  # Real-time simulation
    key_frame_freq=3000,  # Key frame every 3000 frames
)


sim1_sub = WebSocketSubscriber("SIM-1 WebSock")
sim_1_db_logger = LoggerSubscriber("Database-1_Logger")
sim_1_error_logger = LoggerSubscriber("Error-1_Logger")
sub_list_1: List[Subscriber] = [sim1_sub]


# sim2_sub = WebSocketSubscriber("SIM-2 WebSock")
# sim_2_db_logger = LoggerSubscriber("Database-2_Logger")
# sim_2_error_logger = LoggerSubscriber("Error-2_Logger")
# sub_list_2: List[Subscriber] = [sim2_sub, sim_2_db_logger, sim_2_error_logger]


if __name__ == "__main__":
    import time

    sim_behaviour = SimBehaviour()
    sim = Simulator()

    # Initialize simulations and send initial frames
    print("Initializing simulations...")
    r1 = sim.initialize(params, sub_list_1, sim_behaviour=sim_behaviour)
    r2 = sim.initialize(params2, sub_list_1, sim_behaviour=sim_behaviour)

    print("Initial frames sent. Starting simulation loops...")

    # Start the simulation loops
    sim.start(r1, 5)
    thread = sim.thread_pool[r1]["thread"]
    if thread is not None:
        thread.join()

    time.sleep(5)

    sim.start(r2, 5)
    # # Let first resource run for a bit
    # print("Resource 101 started with task 1 (Concordia)...")
    # time.sleep(5)

    # # Assign task to second resource after 5 seconds
    # print("\nAssigning task 2 to resource 102 (McGill)...")
    # sim.assign_task_to_resource(r1, task_id=2, resource_id=102)
    # time.sleep(5)

    # Assign task to third resource after another 5 seconds
    # print("\nAssigning task 3 to resource 103 (Old Montreal)...")
    # sim.assign_task_to_resource(r1, task_id=3, resource_id=103)
    # time.sleep(5)

    # # Assign task to fourth resource after another 5 seconds
    # print("\nAssigning task 4 to resource 104 (Olympic Stadium)...")
    # sim.assign_task_to_resource(r1, task_id=4, resource_id=104)

    # Let all resources run
    print("\nAll resources now running with their assigned tasks...")
    time.sleep(3500)
    print("Done.")
