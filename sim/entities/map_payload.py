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

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    import simpy


@dataclass
class TrafficConfig:
    """Configuration for traffic event loading.

    Attributes:
        traffic_level: Desired traffic level template to use.
        sim_start_time: Start time of simulation.
        sim_end_time: End time of simulation.
    """

    traffic_level: str = ""
    sim_start_time: str = field(default="day1:00:00")
    sim_end_time: str = field(default="day1:00:00")


@dataclass
class MapPayload:
    """Configuration payload for map-related settings.

    Attributes:
        traffic: Optional traffic configuration.
        env: Optional SimPy environment for time-based operations.
        sim_id: Simulation ID.
    """

    traffic: Optional[TrafficConfig] = field(default=None)
    env: Optional["simpy.Environment"] = field(default=None)
    sim_id: str = field(default="")
