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
    def __init__(self, env: simpy.Environment, station_id, name: str, position: Position, taskCount: int = 0):
        self.env = env
        self.id = station_id
        self.name = name
        self.position = position  
        self.taskCount = taskCount

    def incrementTaskCount(self):
        self.taskCount += 1

    def decrementTaskCount(self):
        if self.taskCount > 0:
            self.taskCount -= 1
                    
    def updateTaskCount(self, taskCount):
        self.taskCount = taskCount
            
    def getStationPosition(self) -> Position: 
        return self.position
            

            
