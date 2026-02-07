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

import logging
from typing import Dict, List, Optional, Set

from sim.entities.map_payload import TrafficConfig
from sim.entities.position import Position
from sim.entities.road import Road
from sim.entities.traffic_data import RoadTrafficState
from sim.entities.traffic_event import TrafficEvent
from sim.map.route_controller import RouteController
from sim.map.routing_provider import SegmentKey
from sim.traffic.traffic_parser import TrafficParser
from sim.traffic.traffic_state_factory import TrafficStateFactory

logger = logging.getLogger(__name__)


class TrafficController:
    """Manages traffic state for road segments.

    TrafficController owns RoadTrafficState instances and maintains a reverse
    index from Position objects to Roads for O(1) traffic lookups.
    """

    def __init__(
        self,
        route_controller: RouteController,
        traffic_config: Optional[TrafficConfig] = None,
    ) -> None:
        """Initialize TrafficController.

        Args:
            route_controller: RouteController for road lookups
            traffic_config: Optional TrafficConfig with traffic settings.
        """
        self._route_controller = route_controller
        self._active_traffic: Dict[SegmentKey, RoadTrafficState] = {}
        self._traffic_events: List[TrafficEvent] = []

        # Reverse index: Position -> set of roads containing that node
        self._node_to_roads: Dict[Position, Set[Road]] = {}

        # Register for road lifecycle events
        self._route_controller.register_on_road_created(self._on_road_created)
        self._route_controller.register_on_road_deallocated(self._on_road_deallocated)

        # Parse traffic events from CSV if config provided
        if traffic_config and traffic_config.traffic_path:
            parser = TrafficParser(traffic_config.traffic_path)
            self._traffic_events = parser.parse()
            logger.info(f"Loaded {len(self._traffic_events)} traffic event(s)")
            for i, event in enumerate(self._traffic_events):
                logger.debug(f"  [{i}] {event}")

    def _on_road_created(self, road: Road) -> None:
        """Register road's nodes in reverse index and apply existing traffic.

        When a new road is created, it needs to:
        1. Register its nodes in the reverse index
        2. Check if any existing active traffic affects this road

        Args:
            road: The newly created road
        """
        # Register nodes in reverse index
        for node in road.nodes:
            if node not in self._node_to_roads:
                self._node_to_roads[node] = set()
            self._node_to_roads[node].add(road)

        # Apply any existing active traffic to this new road
        self._apply_existing_traffic_to_road(road)

    def _apply_existing_traffic_to_road(self, road: Road) -> None:
        """Apply all existing active traffic states to a road if applicable.

        Checks each active traffic segment_key and applies it to the road
        if the road contains matching nodes.

        Args:
            road: The road to apply traffic to
        """
        for segment_key, state in self._active_traffic.items():
            road.add_traffic_range(segment_key, state.multiplier)

    def _on_road_deallocated(self, road: Road) -> None:
        """Unregister road's nodes from reverse index and clean up traffic state.

        Args:
            road: The road being deallocated
        """
        # Remove from node index
        for node in road.nodes:
            if node in self._node_to_roads:
                self._node_to_roads[node].discard(road)
                if not self._node_to_roads[node]:
                    del self._node_to_roads[node]

        # Clean up traffic state
        self._active_traffic.pop(road.segment_key, None)

    def _find_affected_roads(self, segment_key: SegmentKey) -> Set[Road]:
        """Find all roads that contain nodes from the segment_key.

        Args:
            segment_key: ((start_lon, start_lat), (end_lon, end_lat))

        Returns:
            Set of roads containing at least one of the segment's nodes
        """
        start_coords, end_coords = segment_key

        # Convert tuple coordinates to Position for lookup
        start_pos = Position([start_coords[0], start_coords[1]])
        end_pos = Position([end_coords[0], end_coords[1]])

        affected: Set[Road] = set()
        if start_pos in self._node_to_roads:
            affected |= self._node_to_roads[start_pos]
        if end_pos in self._node_to_roads:
            affected |= self._node_to_roads[end_pos]

        return affected

    def set_traffic(
        self,
        segment_key: SegmentKey,
        multiplier: float,
        source: Optional[str] = None,
    ) -> bool:
        """Set traffic state for a road segment.

        Uses reverse index to find affected roads and applies traffic ranges.
        Traffic state is always stored so it can be applied to roads created later.

        Args:
            segment_key: Geometry-based segment identifier
            multiplier: Speed factor (0.01-1.0), 1.0 = free flow
            source: Optional source identifier for tracking

        Returns:
            True if traffic was applied to at least one active road, False if
            traffic was only stored in memory (no active roads affected).
        """
        clamped = max(0.01, min(1.0, multiplier))

        state = TrafficStateFactory.create(
            multiplier=clamped,
            traffic_points=[],
            source=source,
        )

        # Always store traffic state (for current and future roads)
        self._active_traffic[segment_key] = state

        # Find affected roads via reverse index
        affected_roads = self._find_affected_roads(segment_key)

        # Apply traffic to each affected road
        for road in affected_roads:
            road.add_traffic_range(segment_key, clamped)

        return bool(affected_roads)

    def clear_traffic(self, segment_key: SegmentKey) -> bool:
        """Clear traffic state for a road segment.

        Removes the traffic from the internal state and from any matching roads.

        Args:
            segment_key: Geometry-based segment identifier

        Returns:
            True if traffic was cleared from at least one road, False if no roads
            were affected (traffic state is still removed from internal tracking).
        """
        # Find affected roads via reverse index
        affected_roads = self._find_affected_roads(segment_key)

        # Remove traffic from each affected road
        updated: Set[Road] = set()
        for road in affected_roads:
            if road.remove_traffic(segment_key):
                updated.add(road)

        self._active_traffic.pop(segment_key, None)
        return bool(updated)

    def clear_all_traffic(self) -> None:
        """Clear traffic state from all active roads.

        Returns:
            None
        """
        for road in self._route_controller.get_all_active_roads():
            road.clear_traffic()
        self._active_traffic.clear()

    def get_traffic_state(self, segment_key: SegmentKey) -> Optional[RoadTrafficState]:
        """Get traffic state for a segment.

        Args:
            segment_key: Geometry-based segment identifier

        Returns:
            RoadTrafficState if found, None otherwise
        """
        return self._active_traffic.get(segment_key)

    def get_traffic_events(self) -> List[TrafficEvent]:
        """Get the list of parsed traffic events.

        Returns:
            List of TrafficEvent objects parsed from the traffic CSV.
        """
        return self._traffic_events

    def cleanup(self) -> None:
        """Clean up TrafficController resources.

        Unregisters callbacks to prevent memory leaks when the controller
        is destroyed.

        Returns:
            None
        """
        self._route_controller.unregister_on_road_created(self._on_road_created)
        self._route_controller.unregister_on_road_deallocated(self._on_road_deallocated)
        self._active_traffic.clear()
        self._node_to_roads.clear()
