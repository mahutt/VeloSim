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
from typing import Optional

from sim.entities.traffic_event_state import TrafficEventState
from sim.map.routing_provider import SegmentKey


@dataclass
class TrafficEvent:
    """Represents a single traffic event parsed from a CSV row.

    This is a data wrapper only -- it does not contain logic for
    state transitions, point generation, or road linkage. Those
    responsibilities belong to a future traffic event manager.

    Attributes:
        event_type: The type of traffic event (e.g. "local_traffic").
        tick_start: The simulation tick at which this event should trigger.
        segment_key: Geometry-based segment identifier matching SegmentKey format:
            ((start_lon, start_lat), (end_lon, end_lat)).
        duration: How many ticks the traffic event lasts.
        weight: Traffic weight/multiplier (0.0-1.0), where 1.0 = free flow,
            0.0 = stopped.
        name: Optional human-readable name/label for the event.
        state: Current lifecycle state, initialized to PENDING.
    """

    event_type: str
    tick_start: int
    segment_key: SegmentKey
    duration: int
    weight: float
    name: Optional[str] = None
    state: TrafficEventState = field(default=TrafficEventState.PENDING)
