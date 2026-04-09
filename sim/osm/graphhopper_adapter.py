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
from typing import Dict, List, Optional, Tuple, cast

from sim.entities.position import Position
from sim.map.routing_provider import (
    EdgeIdentifier,
    RouteResult,
    RouteSegment,
    RouteStep,
    RoutingProvider,
    SegmentKey,
    TrafficUpdate,
)
from sim.osm.graphhopper_connection import GraphHopperConnection
from sim.osm.graphhopper_result import GraphHopperResult
from sim.osm.graphhopper_segment_mapper import graphhopper_segment_mapper
from sim.osm.traffic_state_store import traffic_state_store

logger = logging.getLogger(__name__)


class ToleranceKey:
    """Segment key with coordinate normalization for O(1) traffic lookups.

    Encapsulates the tolerance constraint (1e-5) by rounding coordinates to
    consistent precision. This enables O(1) dict lookups instead of linear scans
    while preserving fuzzy-match semantics.

    Provides bidirectional queryability: a key stored in forward direction (A→B)
    can be retrieved as reverse (B→A) via the probe() method, supporting traffic
    applied in either direction between coordinates.

    Design rationale:
        - Tolerance of 1e-5 enables fuzzy coordinate matching
        - Rounding to 5 decimals (10^-5) preserves this: rounds within ±0.5e-5
        - Normalizing at write time enables O(1) lookup at read time
        - Bidirectional probe supports traffic applied in either direction
    """

    # Tolerance threshold for fuzzy coordinate matching
    TOLERANCE = 1e-5

    # Derived precision: rounding to 5 decimals = 10^-5 = one digit beyond tolerance
    PRECISION = 5

    def __init__(self, key: SegmentKey) -> None:
        """Initialize from raw segment key, normalizing coordinates.

        Args:
            key: Raw SegmentKey ((start_lon, start_lat), (end_lon, end_lat))
        """
        self.forward, self.reverse = self._normalize_key(key)

    @staticmethod
    def _normalize_key(key: SegmentKey) -> tuple[SegmentKey, SegmentKey]:
        """Normalize both endpoints to consistent precision.

        Returns:
            Tuple of (forward_key, reverse_key) for bidirectional lookup
        """

        def round_coord(coord: Tuple[float, float]) -> Tuple[float, float]:
            """Round coordinate to PRECISION decimals.

            Args:
                coord: Coordinate tuple (lon, lat)

            Returns:
                Rounded coordinate tuple
            """
            return (
                round(coord[0], ToleranceKey.PRECISION),
                round(coord[1], ToleranceKey.PRECISION),
            )

        fwd = (round_coord(key[0]), round_coord(key[1]))
        rev = (fwd[1], fwd[0])
        return fwd, rev

    def store_key(self) -> SegmentKey:
        """Key to use when storing in traffic dict (forward direction only).

        Returns:
            Normalized forward-direction segment key
        """
        return self.forward

    def probe(self, traffic_dict: Dict[SegmentKey, float]) -> Optional[float]:
        """Lookup in traffic dict, checking forward then reverse direction.

        Implements bidirectional matching: returns traffic factor if found in
        either direction, matching original _find_traffic_for_segment behavior.

        Args:
            traffic_dict: Dict mapping normalized SegmentKey to speed_factor

        Returns:
            Speed factor if found, None otherwise
        """
        # Check forward first
        if self.forward in traffic_dict:
            return traffic_dict[self.forward]
        # Fall back to reverse
        if self.reverse in traffic_dict:
            return traffic_dict[self.reverse]
        return None


class GraphHopperAdapter(RoutingProvider):
    """RoutingProvider adapter for GraphHopper with per-request traffic."""

    def __init__(
        self,
        graphhopper_url: Optional[str] = None,
        sim_id: str = "",
        profile: str = "car",
    ) -> None:
        self._connection = GraphHopperConnection(graphhopper_url=graphhopper_url)
        self._sim_id = str(sim_id)
        self._profile = profile

    def get_route(
        self,
        start: Position,
        end: Position,
    ) -> Optional[RouteResult]:
        """Compute a route between two positions with traffic awareness.

        First computes baseline route, then fetches traffic-aware route if
        traffic data exists for the route segments.

        Args:
            start: Starting position
            end: Ending position

        Returns:
            RouteResult with coordinates, distance, duration, steps, and segments,
            or None if route cannot be computed
        """
        start_lon, start_lat = start.get_position()
        end_lon, end_lat = end.get_position()

        baseline_result = self._connection.shortest_path_coords(
            start_lon,
            start_lat,
            end_lon,
            end_lat,
            profile=self._profile,
            custom_model=None,
        )

        if not baseline_result:
            return None

        custom_model = self._build_custom_model_for_route(baseline_result)
        if not custom_model:
            return self._convert_to_route_result(baseline_result)

        traffic_result = self._connection.shortest_path_coords(
            start_lon,
            start_lat,
            end_lon,
            end_lat,
            profile=self._profile,
            custom_model=custom_model,
        )

        if not traffic_result:
            logger.warning(
                "Traffic-aware route request failed; falling back to baseline route",
                extra={
                    "sim_id": self._sim_id,
                    "profile": self._profile,
                    "start": (start_lon, start_lat),
                    "end": (end_lon, end_lat),
                    "has_custom_model": True,
                    "custom_model_areas_count": len(custom_model.get("areas", {})),
                    "custom_model_rules_count": len(custom_model.get("speed", [])),
                },
            )
            return self._convert_to_route_result(baseline_result)

        return self._convert_to_route_result(traffic_result)

    def get_distance(
        self,
        start: Position,
        end: Position,
    ) -> Optional[float]:
        """Get distance in meters between two positions.

        Args:
            start: Starting position
            end: Ending position

        Returns:
            Distance in meters, or None if route cannot be computed
        """
        route = self.get_route(start, end)
        return route.distance if route else None

    def snap_to_road(self, position: Position) -> Position:
        """Snap a position to the nearest road.

        Args:
            position: Position to snap

        Returns:
            Snapped position on nearest road, or original position if snap fails
        """
        lon, lat = position.get_position()
        snapped_lon, snapped_lat = self._connection.snap_to_road(
            lon,
            lat,
            profile=self._profile,
        )
        return Position([snapped_lon, snapped_lat])

    def close(self) -> None:
        """Clean up adapter resources and traffic state.

        Returns:
            None
        """
        traffic_state_store.cleanup_sim(self._sim_id)
        graphhopper_segment_mapper.clear_sim(self._sim_id)
        self._connection.close()

    def set_edge_traffic(self, update: TrafficUpdate) -> bool:
        """Set traffic speed factor for a single edge.

        Args:
            update: TrafficUpdate with edge and speed_factor

        Returns:
            True if traffic was set successfully
        """
        key = ToleranceKey(update.edge.segment_key)
        traffic_state_store.set(self._sim_id, key.store_key(), update.speed_factor)
        return True

    def set_edges_traffic(self, updates: List[TrafficUpdate]) -> bool:
        """Set traffic speed factors for multiple edges.

        Args:
            updates: List of TrafficUpdate objects

        Returns:
            True if all traffic updates were set successfully
        """
        for update in updates:
            key = ToleranceKey(update.edge.segment_key)
            traffic_state_store.set(self._sim_id, key.store_key(), update.speed_factor)
        return True

    def get_edge_traffic(self, edge: EdgeIdentifier) -> Optional[float]:
        """Get traffic speed factor for an edge.

        Args:
            edge: Edge identifier

        Returns:
            Speed factor (0.0-1.0), or None if not set
        """
        key = ToleranceKey(edge.segment_key)
        return traffic_state_store.get(self._sim_id, key.store_key())

    def clear_edge_traffic(self, edge: EdgeIdentifier) -> bool:
        """Clear traffic speed factor for a single edge.

        Args:
            edge: Edge identifier

        Returns:
            True if traffic was cleared successfully
        """
        key = ToleranceKey(edge.segment_key)
        return traffic_state_store.clear_edge(self._sim_id, key.store_key())

    def clear_all_traffic(self) -> bool:
        """Clear all traffic speed factors for this simulation.

        Returns:
            True if all traffic was cleared successfully
        """
        return traffic_state_store.clear_all(self._sim_id)

    def _find_traffic_for_segment(
        self,
        start_coord: Tuple[float, float],
        end_coord: Tuple[float, float],
        sim_traffic: Dict[SegmentKey, float],
    ) -> Optional[float]:
        """Find traffic factor for a segment using bidirectional lookup.

        Uses ToleranceKey normalization for O(1) access, checking both
        forward and reverse directions.

        Args:
            start_coord: Start point as (lon, lat)
            end_coord: End point as (lon, lat)
            sim_traffic: Dict of segment keys to speed factors

        Returns:
            Speed factor if found, None otherwise
        """
        key = ToleranceKey((start_coord, end_coord))
        return key.probe(sim_traffic)

    def _build_custom_model_for_route(
        self, result: GraphHopperResult
    ) -> Optional[Dict]:
        sim_traffic = traffic_state_store.get_all_for_sim(self._sim_id)
        if not sim_traffic:
            return None

        areas: Dict[str, Dict] = {}
        speed_rules: List[Dict] = []

        for segment in result.segments:
            if not segment.geometry or len(segment.geometry) < 2:
                continue

            start = cast(Tuple[float, float], tuple(segment.geometry[0]))
            end = cast(Tuple[float, float], tuple(segment.geometry[-1]))
            factor = self._find_traffic_for_segment(start, end, sim_traffic)
            if factor is None:
                continue

            segment_key: SegmentKey = (start, end)
            area_name, area_feature = graphhopper_segment_mapper.get_or_create_area(
                self._sim_id,
                segment_key,
            )

            areas[area_name] = area_feature
            speed_rules.append(
                {
                    "if": f"in_{area_name}",
                    "multiply_by": max(0.01, min(1.0, float(factor))),
                }
            )

        if not areas or not speed_rules:
            return None

        return {
            "areas": areas,
            "speed": speed_rules,
        }

    def _convert_to_route_result(self, result: GraphHopperResult) -> RouteResult:
        coordinates = [Position([coord[0], coord[1]]) for coord in result.coordinates]

        steps = [
            RouteStep(
                name=instruction.street_name or instruction.text,
                distance=instruction.distance,
                duration=instruction.time / 1000.0,
                geometry=self._geometry_for_interval(
                    result.coordinates, instruction.interval
                ),
                speed=(
                    instruction.distance / (instruction.time / 1000.0)
                    if instruction.time > 0 and instruction.distance > 0
                    else None
                ),
            )
            for instruction in result.instructions
        ]

        segments = [
            RouteSegment(
                distance=segment.distance,
                duration=segment.duration,
                geometry=[Position([p[0], p[1]]) for p in segment.geometry],
                road_name=segment.road_name,
                maxspeed=(
                    segment.distance / segment.duration
                    if segment.duration > 0 and segment.distance > 0
                    else None
                ),
            )
            for segment in result.segments
        ]

        # Detect stop signs using OSM PBF spatial index
        from sim.osm.stop_sign_index import get_stop_sign_index
        from sim.osm.traffic_light_index import get_traffic_light_index

        osm_stop_sign_coordinates = get_stop_sign_index().find_near_route(
            result.coordinates
        )

        # Combine OSM-detected stops with any provider-specific stops
        combined_stop_signs = [
            *osm_stop_sign_coordinates,
            *result.stop_sign_coordinates,
        ]

        # Deduplicate stop sign coordinates
        unique_stops: list[list[float]] = []
        seen: set[tuple[float, float]] = set()
        for coord in combined_stop_signs:
            key = (float(coord[0]), float(coord[1]))
            if key not in seen:
                seen.add(key)
                unique_stops.append([key[0], key[1]])

        osm_traffic_light_coordinates = get_traffic_light_index().find_near_route(
            result.coordinates
        )

        provider_traffic_lights = getattr(result, "traffic_light_coordinates", [])
        combined_traffic_lights = [
            *osm_traffic_light_coordinates,
            *provider_traffic_lights,
        ]

        unique_traffic_lights: list[list[float]] = []
        seen_traffic_lights: set[tuple[float, float]] = set()
        for coord in combined_traffic_lights:
            key = (float(coord[0]), float(coord[1]))
            if key not in seen_traffic_lights:
                seen_traffic_lights.add(key)
                unique_traffic_lights.append([key[0], key[1]])

        stop_sign_positions = [Position([c[0], c[1]]) for c in unique_stops]
        traffic_light_positions = [
            Position([c[0], c[1]]) for c in unique_traffic_lights
        ]

        return RouteResult(
            coordinates=coordinates,
            distance=result.distance,
            duration=result.duration,
            steps=steps,
            segments=segments,
            stop_sign_positions=stop_sign_positions,
            traffic_light_positions=traffic_light_positions,
        )

    @staticmethod
    def _geometry_for_interval(
        route_coordinates: List[List[float]], interval: List[int]
    ) -> List[Position]:
        if not route_coordinates:
            return []
        start = max(0, int(interval[0]))
        end = min(len(route_coordinates) - 1, int(interval[1]))
        if end < start:
            return []
        return [
            Position([coord[0], coord[1]])
            for coord in route_coordinates[start : end + 1]
        ]

    @property
    def connection(self) -> GraphHopperConnection:
        """Access the underlying GraphHopper connection.

        Returns:
            GraphHopperConnection instance
        """
        return self._connection
