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

# Create example stations
station1 = Station(temp_env, station_id=1, name="Station Alpha", position=position1)
station2 = Station(temp_env, station_id=2, name="Station Beta", position=position2)

# Create example resources
resource1 = Resource(temp_env, resource_id=101, position=position1)
resource2 = Resource(temp_env, resource_id=102, position=position3)

# Create InputParameter with example entities and simulation settings
params = InputParameter(
    station_entities=[station1, station2],
    resource_entities=[resource1, resource2],
    task_entities=[],  # No tasks for this example
    real_time_factor=1.0,  # Real-time simulation
    key_frame_freq=3,  # Key frame every 30 frames
)


sim1_sub = WebSocketSubscriber("SIM-1 WebSock")
sim_1_db_logger = LoggerSubscriber("Database-1_Logger")
sim_1_error_logger = LoggerSubscriber("Error-1_Logger")
sub_list_1: List[Subscriber] = [sim1_sub, sim_1_db_logger, sim_1_error_logger]


sim2_sub = WebSocketSubscriber("SIM-2 WebSock")
sim_2_db_logger = LoggerSubscriber("Database-2_Logger")
sim_2_error_logger = LoggerSubscriber("Error-2_Logger")
sub_list_2: List[Subscriber] = [sim2_sub, sim_2_db_logger, sim_2_error_logger]


if __name__ == "__main__":
    import time

    sim = Simulator()

    # Initialize simulations and send initial frames
    print("Initializing simulations...")
    r1 = sim.initialize(params, sub_list_1)
    r2 = sim.initialize(params, sub_list_2)

    print("Initial frames sent. Starting simulation loops...")

    # Start the simulation loops
    sim.start(r1, 3600)
    sim.start(r2, 3600)

    # Let simulations run for a bit
    time.sleep(12)

    # Stop simulations
    print("Stopping simulations...")
    sim.stop(r1)
    time.sleep(1)
    sim.stop(r2)
    print("Done.")
