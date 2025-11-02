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
from sim.behaviour.sim_behaviour_builder import SimBehaviourBuilder
from sim.behaviour.default.defualt_RCNT_strategy import DefaultRCNTStrategy


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

# Create example positions
position1 = Position([-74.0060, 40.7128])  # New York [longitude, latitude]
position2 = Position([-118.2437, 34.0522])  # Los Angeles [longitude, latitude]
position3 = Position([-87.6298, 41.8781])  # Chicago [longitude, latitude]

ikea = Position([-73.691993, 45.490198])  # IKEA
concordia = Position([-73.577797, 45.495009])  # Concordia

# Create example stations
station1 = Station(temp_env, station_id=1, name="Ikea", position=ikea)
station2 = Station(temp_env, station_id=2, name="Concordia", position=concordia)

# Create example resources
resource1 = Resource(temp_env, resource_id=101, position=ikea)
# resource2 = Resource(temp_env, resource_id=102, position=position3)

task1 = BatterySwapTask(temp_env, 1, station2)
# task2 = BatterySwapTask(temp_env, 2, station2)
station2.add_task(task1)
resource1.assign_task(task1)

# Create InputParameter with example entities and simulation settings
params = InputParameter(
    station_entities={1: station1},
    resource_entities={101: resource1},
    task_entities={1: task1},
    real_time_factor=1.0,  # Real-time simulation
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

    sim_behaviour_builder = SimBehaviourBuilder()
    sim_behaviour_builder.set_RCNT_strategy(DefaultRCNTStrategy())
    sim_behaviour = sim_behaviour_builder.get_sim_behaviour()

    sim = Simulator()

    # Initialize simulations and send initial frames
    print("Initializing simulations...")
    r1 = sim.initialize(params, sub_list_1,sim_env=temp_env,sim_behaviour=sim_behaviour)
    # r2 = sim.initialize(params, sub_list_2)

    print("Initial frames sent. Starting simulation loops...")

    # Start the simulation loops
    sim.start(r1, 3600)
    # sim.start(r2, 3600)

    # Let simulations run for a bit
    time.sleep(4000)

    # Add a new task
    # print("Adding new task with id 3 in sim r1...")
    # print("===========================================================")
    # some_new_task = BatterySwapTask(temp_env, 3, station1)
    # sim.add_task_to_sim(sim_id=r1, task=some_new_task)
    # time.sleep(4)

    # # Assigning task
    # print("Assigning task 3 to resource with id 102 in sim r1...")
    # print("===========================================================")
    # sim.assign_task_to_resource(r1, task_id=3, resource_id=102)
    # time.sleep(2)

    # # Unassign task
    # print("Unassiging task 1 from resource 101 in r2...")
    # print("===========================================================")
    # sim.unassign_task_from_resource(r2, task_id=1, resource_id=101)
    # time.sleep(2)

    # # Reassign task
    # print("Reassigning task 3 from resource 102 to resource 101 in r1...")
    # print("===========================================================")
    # sim.reassign_task(r1, task_id=3, old_resource_id=102, new_resource_id=101)
    # time.sleep(2)

    # Stop simulations
    # print("Stopping simulations...")
    # # sim.stop(r1)

    # sim.stop(r2)
    print("Done.")
