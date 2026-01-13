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
from typing import Optional

from sim.entities.position import Position
from sim.map.routing_provider import (
    RoutingProvider,
    RouteResult,
    RouteStep,
    RouteSegment,
)
from sim.osm.OSRMConnection import OSRMConnection
from sim.osm.osrm_result import OSRMResult

logger = logging.getLogger(__name__)


class OSRMAdapter(RoutingProvider):
    """
    Adapter that implements RoutingProvider interface for OSRM routing engine.

    This adapter wraps the OSRMConnection class and converts OSRM-specific
    responses to the generic RoutingProvider types, allowing the rest of the
    simulator to be decoupled from the OSRM implementation.

    Example:
        adapter = OSRMAdapter(osrm_url="http://localhost:5000")
        route = adapter.get_route(-73.5673, 45.5017, -73.5533, 45.5017)
        if route:
            print(f"Route distance: {route.distance}m")
    """

    def __init__(self, osrm_url: Optional[str] = None) -> None:
        """
        Initialize the OSRM adapter.

        Args:
            osrm_url: Base URL of OSRM server. If not provided, will check
                     OSRM_URL, OSRM_LOCAL_URL, or OSRM_PUBLIC_URL environment
                     variables in that order.

        Raises:
            ValueError: If no OSRM URL is provided or configured via environment
            ConnectionError: If OSRM server is not accessible
        """
        self._connection = OSRMConnection(osrm_url=osrm_url)

    def get_route(
        self,
        start: Position,
        end: Position,
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
        start_lon, start_lat = start.get_position()
        end_lon, end_lat = end.get_position()

        osrm_result = self._connection.shortest_path_coords(
            start_lon, start_lat, end_lon, end_lat
        )

        if not osrm_result:
            return None

        # Convert OSRM-specific types to generic RoutingProvider types
        return self._convert_to_route_result(osrm_result)

    def get_distance(
        self,
        start: Position,
        end: Position,
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
        start_lon, start_lat = start.get_position()
        end_lon, end_lat = end.get_position()

        return self._connection.get_distance_coords(
            start_lon, start_lat, end_lon, end_lat
        )

    def snap_to_road(self, position: Position) -> Position:
        """
        Snap position to nearest road.

        Projects a position onto the nearest road in the network.
        Useful for correcting GPS coordinates or placing points on the road.

        Args:
            position: Position to snap.

        Returns:
            Snapped Position on the road network.
        """
        lon, lat = position.get_position()
        snapped_lon, snapped_lat = self._connection.snap_to_road(lon, lat)
        return Position([snapped_lon, snapped_lat])

    def close(self) -> None:
        """
        Clean up resources.

        Closes the underlying HTTP session.

        Returns:
            None
        """
        self._connection.close()

    def _convert_to_route_result(self, osrm_result: OSRMResult) -> RouteResult:
        """
        Convert OSRM-specific result to generic RouteResult.

        Args:
            osrm_result: The OSRM-specific route result.

        Returns:
            Generic RouteResult with all data converted to Position objects.
        """
        # Convert coordinates to Position objects
        coordinates = [
            Position([coord[0], coord[1]]) for coord in osrm_result.coordinates
        ]

        # Convert steps with Position geometry
        steps = [
            RouteStep(
                name=step.name,
                distance=step.distance,
                duration=step.duration,
                geometry=[Position([g[0], g[1]]) for g in step.geometry],
                speed=step.speed,
            )
            for step in osrm_result.steps
        ]

        # Convert segments with Position geometry (provider-neutral, no OSRM node IDs)
        segments = [
            RouteSegment(
                distance=seg.distance,
                duration=seg.duration,
                geometry=[Position([g[0], g[1]]) for g in seg.geometry],
                road_name=seg.road_name,
                maxspeed=(
                    seg.distance / seg.duration
                    if seg.duration > 0 and seg.distance > 0
                    else None
                ),
            )
            for seg in osrm_result.segments
        ]

        return RouteResult(
            coordinates=coordinates,
            distance=osrm_result.distance,
            duration=osrm_result.duration,
            steps=steps,
            segments=segments,
        )

    # Expose connection for internal use by RouteController
    # This allows RouteController to use OSRM-specific features when needed
    @property
    def connection(self) -> OSRMConnection:
        """
        Get the underlying OSRMConnection for internal use.

        Note: This is an OSRM-specific property used internally.
        Prefer using the RoutingProvider interface methods.

        Returns:
            The underlying OSRMConnection instance.
        """
        return self._connection
