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

from sim.entities.position import Position
from sim.entities.station import Station


# Example setup (like before)
env = simpy.Environment()

pos1_station = Position([-74.0060, 40.7128])
pos2_station = Position([-118.2437, 34.0522])
pos3_station = Position([-87.6298, 41.8781])

pos1_ressource = Position([-74.0060, 40.7128])
pos2_ressource = Position([-118.2437, 34.0522])
pos3_ressource = Position([-87.6298, 41.8781])

station1 = Station(
    station_id=8074, name="Lionel-Groulx", position=pos1_station, env=env
)
station2 = Station(
    station_id=2105, name="Guy-Concordia", position=pos2_station, env=env
)
station3 = Station(station_id=2508, name="Peel", position=pos2_station, env=env)
