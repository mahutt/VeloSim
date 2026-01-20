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

from typing import Dict, List, Optional

from sim.entities.position import Position
from sim.entities.road import Road
from sim.entities.traffic_data import RoadTrafficState
from sim.map.route_controller import RouteController
from sim.map.routing_provider import SegmentKey
from sim.traffic.traffic_state_factory import TrafficStateFactory


class TrafficController:
    """Manages traffic state for road segments.

    TrafficController owns RoadTrafficState instances and uses RouteController
    to look up roads. Road objects hold references to traffic state but
    do not own them.
    """

    def __init__(self, route_controller: RouteController) -> None:
        """Initialize TrafficController.

        Args:
            route_controller: RouteController for road lookups
        """
        self._route_controller = route_controller
        self._segment_key_to_traffic: Dict[SegmentKey, RoadTrafficState] = {}

        # Register for road deallocation events to clean up traffic state
        self._route_controller.register_on_road_deallocated(self._on_road_deallocated)

    def _on_road_deallocated(self, segment_key: SegmentKey) -> None:
        """Clean up traffic state when a road is deallocated.

        Args:
            segment_key: The segment key of the deallocated road
        """
        self._segment_key_to_traffic.pop(segment_key, None)

    def _generate_traffic_points(
        self,
        road: Road,
        multiplier: float,
    ) -> List[Position]:
        """Generate traffic-adjusted point collection for a road.

        Args:
            road: Road to generate points for
            multiplier: Speed multiplier (0.01-1.0)

        Returns:
            List of Position objects spaced for traffic-adjusted speed

        Raises:
            ValueError: If road has no pointcollection or effective speed is <= 0
        """
        if not road.pointcollection:
            raise ValueError(
                f"Road '{road.name}' (id={road.id}) has no pointcollection"
            )

        effective_speed = road.maxspeed * multiplier
        if effective_speed <= 0:
            raise ValueError(
                f"Effective speed must be > 0, got {effective_speed} "
                f"(maxspeed={road.maxspeed}, multiplier={multiplier})"
            )

        return self._route_controller.generate_point_collection(
            geometry=road.pointcollection,
            length=road.length,
            maxspeed=effective_speed,
        )

    def set_traffic(
        self,
        segment_key: SegmentKey,
        multiplier: float,
        source: Optional[str] = None,
    ) -> bool:
        """Set traffic state for a road segment.

        Args:
            segment_key: Geometry-based segment identifier
            multiplier: Speed factor (0.01-1.0), 1.0 = free flow
            source: Optional source identifier for tracking

        Returns:
            True if road found and updated, False otherwise
        """
        road = self._route_controller.get_road_by_segment_key(segment_key)
        if road is None:
            return False

        # Clamp multiplier for point generation (same as factory)
        clamped = max(0.01, min(1.0, multiplier))
        traffic_points = self._generate_traffic_points(road, clamped)

        state = TrafficStateFactory.create(
            multiplier=multiplier,
            traffic_points=traffic_points,
            source=source,
        )
        self._segment_key_to_traffic[segment_key] = state
        road.set_traffic_state(state)
        return True

    def clear_traffic(self, segment_key: SegmentKey) -> bool:
        """Clear traffic state for a road segment.

        Args:
            segment_key: Geometry-based segment identifier

        Returns:
            True if road found and cleared, False otherwise
        """
        road = self._route_controller.get_road_by_segment_key(segment_key)
        if road is None:
            return False
        self._segment_key_to_traffic.pop(segment_key, None)
        road.clear_traffic()
        return True

    def clear_all_traffic(self) -> None:
        """Clear traffic state from all active roads.

        Returns:
            None
        """
        for road in self._route_controller.get_all_active_roads():
            road.clear_traffic()
        self._segment_key_to_traffic.clear()

    def get_traffic_state(self, segment_key: SegmentKey) -> Optional[RoadTrafficState]:
        """Get traffic state for a segment.

        Args:
            segment_key: Geometry-based segment identifier

        Returns:
            RoadTrafficState if found, None otherwise
        """
        return self._segment_key_to_traffic.get(segment_key)

    def cleanup(self) -> None:
        """Clean up TrafficController resources.

        Unregisters callbacks to prevent memory leaks when the controller
        is destroyed.

        Returns:
            None
        """
        self._route_controller.unregister_on_road_deallocated(self._on_road_deallocated)
        self._segment_key_to_traffic.clear()
