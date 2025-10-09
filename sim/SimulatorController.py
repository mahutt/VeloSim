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

from sim.RealTimeDriver import RealTimeDriver
import simpy
import threading
from typing import List
from sim.entities.station import Station
from sim.frame_emitter import FrameEmitter
from sim.entities.frame import Frame

class SimulatorController:

    # TODO Add entity Collections. Ex Resources, Stations, Tasks, etc.
    stationEntities : List[Station]
    frameCounter : int = 0 # No frames emitted until sim is running


    def __init__(
        self, simEnv: simpy.Environment, frameEmitter: FrameEmitter, strict: bool, realTimeFactor: float = None
    ) -> None:
        self.simEnv = simEnv
        self.realTimeDriver = RealTimeDriver(simEnv, realTimeFactor, strict)
        self.frameEmitter = frameEmitter

    def start(self, simTime: int) -> None:
        # TODO process initial entities into the sim env
        # Add a dummy process to keep the simulation running
        self.simEnv.process(self._dummy_simulation_process(simTime))

        self.sim_thread = threading.Thread(target=self.realTimeDriver.runUntil,args=(simTime,self.emit_frame))
        self.sim_thread.start()

    def _dummy_simulation_process(self, simTime: int):
        """A dummy process that yields every second to keep the simulation active."""
        for i in range(simTime):
            yield self.simEnv.timeout(1)  # Wait 1 simulation second

    def stop(self) -> None:
        self.realTimeDriver.stop()

    def pause(self) -> None:
        self.realTimeDriver.pause()

    def resume(self) -> None:
        self.realTimeDriver.resume()

    def set_factor(self, factor: float) -> None:
        self.realTimeDriver.setRealTimeFactor(factor)

    def subscribe_to_frames(self) -> None:
        pass

    # should call frame emitter
    def emit_frame(self) -> None:
        payload = { 
            "sim_id" : self.frameEmitter.sim_id,
            "tasks" : "TODO : Add task detials",
            "resources": "TODO : Add resource details",
            "stations" : "TODO: Add station details"
        }
        frame = Frame(seq_numb= self.frameCounter, payload= payload)
        self.frameEmitter.notify(frame= frame)
        self.frameCounter += 1

    # First frame sent from back to front end with station data, etc
    def get_initial_frame(self) -> None:
        pass

    
