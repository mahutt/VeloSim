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

from typing import Dict, List, Set
from sim.entities.position import Position
from sim.entities.road import Road
from sim.entities.traffic_event import TrafficEvent


class PositionRegistry:
    """Shared bidirectional index: geometry positions to roads/events.

    Created by MapController and injected into both RouteController
    and TrafficController. Enables O(1) intersection detection between
    road geometry and traffic event geometry via Position.__hash__.

    The registry indexes on raw provider geometry positions (not
    interpolated pointcollection), since both roads and traffic events
    resolve geometry from the same routing provider and will share
    identical coordinates.
    """

    def __init__(self) -> None:
        # Forward maps: position -> entities containing that position
        self._geom_to_roads: Dict[Position, Set[Road]] = {}
        self._geom_to_events: Dict[Position, Set[TrafficEvent]] = {}

        # Reverse maps: entity -> set of its registered positions
        self._road_positions: Dict[Road, Set[Position]] = {}
        self._event_positions: Dict[TrafficEvent, Set[Position]] = {}

    def register_road(self, road: Road, geometry: List[Position]) -> None:
        """Register a road's geometry positions in the index.

        If the road is already registered, it is unregistered first to
        prevent stale entries in the forward maps.

        Args:
            road: The road to register.
            geometry: Raw geometry positions from the routing provider.

        Returns:
            None.
        """
        if not geometry:
            return

        if road in self._road_positions:
            self.unregister_road(road)

        positions: Set[Position] = set()
        for pos in geometry:
            if pos not in self._geom_to_roads:
                self._geom_to_roads[pos] = set()
            self._geom_to_roads[pos].add(road)
            positions.add(pos)

        self._road_positions[road] = positions

    def unregister_road(self, road: Road) -> None:
        """Remove a road and all its positions from the index.

        Args:
            road: The road to unregister.

        Returns:
            None.
        """
        positions = self._road_positions.pop(road, set())
        for pos in positions:
            if pos in self._geom_to_roads:
                self._geom_to_roads[pos].discard(road)
                if not self._geom_to_roads[pos]:
                    del self._geom_to_roads[pos]

    def register_event(self, event: TrafficEvent, geometry: List[Position]) -> None:
        """Register a traffic event's resolved geometry in the index.

        If the event is already registered, it is unregistered first
        to prevent stale entries in the forward maps.

        Args:
            event: The traffic event to register.
            geometry: Route geometry positions from the routing provider.

        Returns:
            None.
        """
        if not geometry:
            return

        if event in self._event_positions:
            self.unregister_event(event)

        positions: Set[Position] = set()
        for pos in geometry:
            if pos not in self._geom_to_events:
                self._geom_to_events[pos] = set()
            self._geom_to_events[pos].add(event)
            positions.add(pos)

        self._event_positions[event] = positions

    def unregister_event(self, event: TrafficEvent) -> None:
        """Remove a traffic event and all its positions from the index.

        Args:
            event: The traffic event to unregister.

        Returns:
            None.
        """
        positions = self._event_positions.pop(event, set())
        for pos in positions:
            if pos in self._geom_to_events:
                self._geom_to_events[pos].discard(event)
                if not self._geom_to_events[pos]:
                    del self._geom_to_events[pos]

    def find_roads_for_event(self, event: TrafficEvent) -> Set[Road]:
        """Find all roads whose geometry shares at least one position with the event.

        This is the core allocation check: non-empty result = Allocated.

        Args:
            event: The traffic event to query.

        Returns:
            Set of roads intersecting the event's geometry.
        """
        event_positions = self._event_positions.get(event, set())
        roads: Set[Road] = set()
        for pos in event_positions:
            roads |= self._geom_to_roads.get(pos, set())
        return roads

    def find_events_for_road(self, road: Road) -> Set[TrafficEvent]:
        """Find all events sharing at least one position with the road.

        Used by road lifecycle callbacks to apply/remove traffic when roads
        are created or deallocated.

        Args:
            road: The road to query.

        Returns:
            Set of traffic events intersecting the road's geometry.
        """
        road_positions = self._road_positions.get(road, set())
        events: Set[TrafficEvent] = set()
        for pos in road_positions:
            events |= self._geom_to_events.get(pos, set())
        return events

    def find_roads_at_position(self, pos: Position) -> Set[Road]:
        """Find all roads registered at a specific position.

        Args:
            pos: The position to query.

        Returns:
            Set of roads containing this position in their geometry.
        """
        return self._geom_to_roads.get(pos, set()).copy()

    def get_overlap_positions(self, road: Road, event: TrafficEvent) -> Set[Position]:
        """Get the set of positions shared between a road and an event.

        Args:
            road: The road.
            event: The traffic event.

        Returns:
            Set of Position objects present in both geometries.
        """
        road_positions = self._road_positions.get(road, set())
        event_positions = self._event_positions.get(event, set())
        return road_positions & event_positions

    def is_event_allocated(self, event: TrafficEvent) -> bool:
        """Check if at least one road intersects the event's geometry.

        Args:
            event: The traffic event to check.

        Returns:
            True if at least one road shares a geometry position with the event.
        """
        return len(self.find_roads_for_event(event)) > 0
