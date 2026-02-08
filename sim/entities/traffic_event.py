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
from typing import List, Optional, Set, TYPE_CHECKING

from sim.entities.traffic_event_state import TrafficEventState
from sim.map.routing_provider import SegmentKey

if TYPE_CHECKING:
    from sim.entities.position import Position
    from sim.entities.road import Road


@dataclass(eq=False)
class TrafficEvent:
    """Represents a single traffic event with lifecycle state tracking.

    Contains lifecycle state, resolved geometry, and affected road tracking
    for the traffic event state machine.

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
        route_geometry: Full route geometry resolved via RoutingProvider when
            the event transitions to TRIGGERED. None while PENDING.
        affected_roads: Set of Road objects currently affected by this event.
            Populated during the synchronization subprocess.
    """

    event_type: str
    tick_start: int
    segment_key: SegmentKey
    duration: int
    weight: float
    name: Optional[str] = None
    state: TrafficEventState = field(default=TrafficEventState.PENDING)
    route_geometry: Optional[List["Position"]] = field(default=None, repr=False)
    affected_roads: Set["Road"] = field(default_factory=set, repr=False)

    def __hash__(self) -> int:
        return hash((self.event_type, self.tick_start, self.segment_key, self.duration))

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, TrafficEvent):
            return NotImplemented
        return (
            self.event_type == other.event_type
            and self.tick_start == other.tick_start
            and self.segment_key == other.segment_key
            and self.duration == other.duration
        )
