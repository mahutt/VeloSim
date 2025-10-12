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
from sim.entities.resource import Resource
from sim.entities.clock import Clock
from sim.entities.task import Task
class SimulatorController:

    # TODO Add Task Entities

    stationEntities : List[Station]
    resourcEntities: List[Resource]
    taskEntities: List[Task]


    clock : Clock # Keep track of sim time and real time passed in minutes & seconds
    frameCounter : int = 0 # No frames emitted until sim is running


    def __init__(
        self, simEnv: simpy.Environment, frameEmitter: FrameEmitter, strict: bool, 
        realTimeFactor: float = None,
        keyframeFreq: int = None,
    ) -> None:
        self.simEnv = simEnv
        self.realTimeDriver = RealTimeDriver(simEnv, realTimeFactor, strict)
        self.frameEmitter = frameEmitter
        self.keyframeFreq = keyframeFreq # key frame every nth frame

    def start(self, simTime: int) -> None:
        # TODO process initial entities into the sim env
        
        #start sim clock
        self.clock.run()
        self.sim_thread = threading.Thread(target=self.realTimeDriver.runUntil,args=(simTime,self.emit_frame))
        self.sim_thread.start()

   
    def stop(self) -> None:
        self.realTimeDriver.stop()

    def pause(self) -> None:
        self.realTimeDriver.pause()

    def resume(self) -> None:
        self.realTimeDriver.resume()

    def set_factor(self, factor: float) -> None:
        self.realTimeDriver.setRealTimeFactor(factor)

    # First frame sent from back to front end with station data, etc
    def emit_initial_frame(self) -> None:
        frame = self.create_key_frame()
        self.emit_frame(frame)
    
    # Should call frame emitter
    def emit_frame(self, frame: Frame) -> None:

        frame = self.create_frame()
        self.frameEmitter.notify(frame= frame)
        self.frameCounter += 1

    def create_frame(self) -> Frame:
        pass

    def create_key_frame(self) -> Frame: 
        payload= {
            "sim_id" : self.frameEmitter.sim_id,
            "tasks": [
                {
                    "task_id": task.get_task_id(),
                    "task_state": task.get_state().value if hasattr(task.get_state(), 'value') else str(task.get_state()),
                    "station_id": task.get_station().id if task.get_station() else None,
                    "station_name": task.get_station().name if task.get_station() else None,
                    "assigned_resource_id": task.get_assigned_resource().id if task.get_assigned_resource() else None,
                    "is_assigned": task.is_assigned()
                } for task in self.taskEntities
            ],
            "stations": [
                {
                   "station_id":  station.id,
                   "station_name" :station.name,
                   "station_position": station.get_station_position(),
                   "station_tasks" : station.tasks,
                   "task_count": station.get_task_count()
                } for station in self.stationEntities
            ],
            "resources":[
                {
                    "resource_id": resource.id,
                    "resource_position": resource.get_resource_position(),
                    "resource_tasks": resource.get_task_list(),
                    "task_count": resource.get_task_count(),
                    "dispatched_task_id": resource.get_dispatched_task().get_task_id() if resource.get_dispatched_task() else None

                } for resource in self.resourcEntities
            ],

            "clock" : {
                "realSecondsPassed" : self.clock.realSecondsPassed,
                "realMinutesPassed" : self.clock.realMinutesPassed,
                "simSecondsPassed" : self.clock.simTimeSeconds,
                "simSecondsPassed" : self.clock.simTimeSeconds
            }
        }
        frame = Frame(seq_numb= self.frameCounter, payload= payload)

        return frame


      
  