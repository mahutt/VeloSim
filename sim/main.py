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
from sim.entities.frame import Frame
from sim.entities.inputParameters import InputParameter
from sim.utils.subscriber import Subscriber
from .simulator import Simulator


class LoggerSubscriber(Subscriber):
    def __init__(self, name: str) -> None:
        self.name = name

    def on_frame(self, frame: Frame) -> None:
        print(f"[{self.name}] Received: {frame}")


class WebSocketSubscriber(Subscriber):
    def __init__(self, name: str) -> None:
        self.name = name

    def on_frame(self, frame: Frame) -> None:
        print(f"[{self.name}] Received: {frame}")


params = InputParameter()


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

    r1 = sim.start(params, sub_list_1)
    r2 = sim.start(params, sub_list_2)
    time.sleep(3)
    sim.stop(r1)
    time.sleep(1)
    sim.stop(r2)
    print("Done.")
