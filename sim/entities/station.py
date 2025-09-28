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
from position import Position

class Station:
    def __init__(self, env: simpy.Environment, station_id, name: str, position: Position, tasks: list = None):
        self.env = env
        self.id = station_id
        self.name = name
        self.position = position  
        self.tasks = tasks if tasks is not None else [] # list of tasks assigned to a given station

        # starting the process for periodic station operations
        self.action = env.process(self.run())

    def addTask(self, task):
        self.tasks.append(task)

    def removeTask(self, task):
        if task in self.tasks:
            self.tasks.remove(task)
            
    def getTaskCount(self) -> int:
        return len(self.tasks)

    def getStationPosition(self) -> Position: 
        return self.position

    # continous process that runs throughout the simulation        
    def run(self):
        # replace with periodic operations later on
        while True:
            yield self.env.timeout(1)
