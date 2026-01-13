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

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Optional, Tuple, TYPE_CHECKING

if TYPE_CHECKING:
    from sim.entities.position import Position

# Type alias for geometry-based segment identification
SegmentKey = Tuple[Tuple[float, float], Tuple[float, float]]
"""Geometry-based segment key: ((start_lon, start_lat), (end_lon, end_lat))"""


# =============================================================================
# Core Routing Data Classes
# =============================================================================


@dataclass
class RouteSegment:
    """
    A segment of a route between two points.

    Represents the smallest unit of a route - a single edge in the road network.
    Provider-neutral: uses geometry endpoints for identification instead of
    provider-specific node IDs.
    """

    distance: float
    """Segment distance in meters."""

    duration: float
    """Segment duration in seconds."""

    geometry: List["Position"]
    """Segment geometry as list of Position objects."""

    road_name: Optional[str] = None
    """Street name, if available."""

    maxspeed: Optional[float] = None
    """Maximum speed in m/s, if available."""

    @property
    def segment_key(self) -> SegmentKey:
        """
        Provider-neutral segment identifier based on geometry endpoints.

        Returns:
            SegmentKey: ((start_lon, start_lat), (end_lon, end_lat))
        """
        start = self.geometry[0].get_position()
        end = self.geometry[-1].get_position()
        return ((start[0], start[1]), (end[0], end[1]))


@dataclass
class RouteStep:
    """
    A maneuver/turn in the route.

    Represents a navigation instruction - typically a turn or road change
    that requires driver attention.
    """

    name: Optional[str]
    """Street name at this step."""

    distance: float
    """Step distance in meters."""

    duration: float
    """Step duration in seconds."""

    geometry: List["Position"]
    """Step geometry as list of Position objects."""

    speed: Optional[float] = None
    """Speed limit in m/s, if available."""


@dataclass
class RouteResult:
    """
    Complete route result from any routing provider.

    Contains all the information needed to navigate from origin to destination,
    including the full geometry, turn-by-turn instructions, and segment-level details.
    """

    coordinates: List["Position"]
    """Complete route waypoints as list of Position objects."""

    distance: float
    """Total route distance in meters."""

    duration: float
    """Total route duration in seconds."""

    steps: List[RouteStep]
    """Turn-by-turn navigation instructions."""

    segments: List[RouteSegment]
    """Node-to-node segments (finest granularity)."""

    @property
    def start_position(self) -> "Position":
        """
        Get the starting position.

        Returns:
            Starting Position object.
            Returns Position([0.0, 0.0]) if no coordinates available.
        """
        from sim.entities.position import Position

        if not self.coordinates:
            return Position([0.0, 0.0])
        return self.coordinates[0]

    @property
    def end_position(self) -> "Position":
        """
        Get the ending position.

        Returns:
            Ending Position object.
            Returns Position([0.0, 0.0]) if no coordinates available.
        """
        from sim.entities.position import Position

        if not self.coordinates:
            return Position([0.0, 0.0])
        return self.coordinates[-1]


# =============================================================================
# Traffic Data Classes (for future CRUD operations)
# =============================================================================


@dataclass
class EdgeIdentifier:
    """
    Identifies a road edge using geometry endpoints.

    Provider-neutral identification based on start/end coordinates.
    This works across all routing engines regardless of their internal
    identification schemes.
    """

    start_position: "Position"
    """Starting position of the edge."""

    end_position: "Position"
    """Ending position of the edge."""

    @property
    def segment_key(self) -> SegmentKey:
        """
        Geometry-based segment key for lookups.

        Returns:
            SegmentKey: ((start_lon, start_lat), (end_lon, end_lat))
        """
        start = self.start_position.get_position()
        end = self.end_position.get_position()
        return ((start[0], start[1]), (end[0], end[1]))


@dataclass
class TrafficUpdate:
    """
    Traffic update for a single directed edge.

    Direction is implicit in the EdgeIdentifier:
        edge.start_position -> edge.end_position defines the direction.
        To update both directions, submit two TrafficUpdate objects with
        swapped positions.

    speed_factor semantics:
        0.0 = blocked/standstill (no traffic can pass)
        0.5 = 50% of normal speed (heavy congestion)
        1.0 = free flow (normal conditions)

    Example usage (future):
        from sim.entities.position import Position

        # Block a road segment (A -> B direction)
        update_forward = TrafficUpdate(
            edge=EdgeIdentifier(
                start_position=Position([-73.5673, 45.5017]),  # Point A
                end_position=Position([-73.5680, 45.5020])     # Point B
            ),
            speed_factor=0.0
        )

        # To block both directions, submit two updates:
        update_backward = TrafficUpdate(
            edge=EdgeIdentifier(
                start_position=Position([-73.5680, 45.5020]),  # Point B
                end_position=Position([-73.5673, 45.5017])     # Point A
            ),
            speed_factor=0.0
        )
    """

    edge: EdgeIdentifier
    """Identifier for the directed edge to update."""

    speed_factor: float
    """Speed multiplier from 0.0 (blocked) to 1.0 (free flow)."""


# =============================================================================
# RoutingProvider Interface
# =============================================================================


class RoutingProvider(ABC):
    """
    Abstract interface for routing services.

    This interface defines the contract that all routing adapters must implement.
    It provides methods for route calculation, distance queries, and coordinate
    snapping, as well as optional methods for traffic data management.

    Implementations:
        - OSRMAdapter: Wraps OSRM routing engine
        - ValhallaAdapter: Wraps Valhalla routing engine
        - GraphHopperAdapter: Wraps GraphHopper routing engine
        - pgRoutingAdapter: Wraps pgRouting (PostgreSQL-based)
    """

    # =========================================================================
    # Core Routing Methods (Required)
    # =========================================================================

    @abstractmethod
    def get_route(
        self,
        start: "Position",
        end: "Position",
    ) -> Optional[RouteResult]:
        """
        Get route between two positions.

        Args:
            start: Starting position.
            end: Ending position.

        Returns:
            RouteResult with coordinates, distance, duration, steps, and segments.
            Returns None if no route is found.
        """
        pass

    @abstractmethod
    def get_distance(
        self,
        start: "Position",
        end: "Position",
    ) -> Optional[float]:
        """
        Get distance in meters between two positions.

        This is a convenience method that returns only the distance
        without the full route details.

        Args:
            start: Starting position.
            end: Ending position.

        Returns:
            Distance in meters, or None if no route is found.
        """
        pass

    @abstractmethod
    def snap_to_road(self, position: "Position") -> "Position":
        """
        Snap position to nearest road.

        Projects a position onto the nearest road in the network.
        Useful for correcting GPS coordinates or placing points on the road.

        Args:
            position: Position to snap.

        Returns:
            Snapped Position on the road network.
        """
        pass

    @abstractmethod
    def close(self) -> None:
        """
        Clean up resources.

        Should be called when the routing provider is no longer needed.
        Implementations should close HTTP sessions, database connections, etc.

        Returns:
            None
        """
        pass

    # =========================================================================
    # Traffic CRUD Methods (Optional - Future)
    # =========================================================================

    def set_edge_traffic(self, update: TrafficUpdate) -> bool:
        """
        Set traffic/speed factor for a single edge.

        Args:
            update: TrafficUpdate with edge identifier and speed_factor (0-1).

        Returns:
            True if successful, False otherwise.

        Note:
            Implementation varies by adapter:
                - OSRM: Requires data rebuild (not runtime)
                - GraphHopper: Adds to custom model rules
                - Valhalla: Updates traffic.tar file
                - pgRouting: SQL UPDATE on cost column
        """
        raise NotImplementedError("Traffic updates not supported by this adapter")

    def set_edges_traffic(self, updates: List[TrafficUpdate]) -> bool:
        """
        Batch update traffic for multiple edges.

        Args:
            updates: List of TrafficUpdate objects.

        Returns:
            True if all updates successful, False otherwise.
        """
        raise NotImplementedError("Traffic updates not supported by this adapter")

    def get_edge_traffic(self, edge: EdgeIdentifier) -> Optional[float]:
        """
        Get current speed_factor for an edge.

        Args:
            edge: EdgeIdentifier specifying which edge to query.

        Returns:
            Current speed_factor (0-1), or None if not available.
        """
        raise NotImplementedError("Traffic queries not supported by this adapter")

    def clear_edge_traffic(self, edge: EdgeIdentifier) -> bool:
        """
        Reset edge to default speed (speed_factor = 1.0).

        Args:
            edge: EdgeIdentifier specifying which edge to reset.

        Returns:
            True if successful, False otherwise.
        """
        raise NotImplementedError("Traffic updates not supported by this adapter")

    def clear_all_traffic(self) -> bool:
        """
        Reset all edges to default speeds.

        Returns:
            True if successful, False otherwise.
        """
        raise NotImplementedError("Traffic updates not supported by this adapter")
