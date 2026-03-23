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

# mypy: ignore-errors

from typing import List
from unittest.mock import Mock

from sim.entities.route import Route
from sim.entities.road import Road
from sim.entities.position import Position
from sim.entities.traffic_data import TrafficRange
from sim.map.routing_provider import RoutingProvider, RouteResult, RouteStep, SegmentKey


# ---------------------------------------------------------------------------
# Constants for the straight-line test road
# ---------------------------------------------------------------------------
ROAD_LENGTH = 500.0  # meters
MAXSPEED = 13.89  # m/s  (~50 km/h)
NUM_GEOMETRY_POINTS = 11  # sparse geometry (every ~50 m)
NUM_POINTCOLLECTION = 36  # ~1 point per second at free-flow for 500 m

# Traffic event starts around 250 m (geometry index 5 out of 0..10)
TRAFFIC_GEOM_START = 5
TRAFFIC_GEOM_END = 10
TRAFFIC_MULTIPLIER = 0.3  # severe congestion


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _make_straight_positions(n: int) -> List[Position]:
    """Create *n* positions along a straight north-bound line.

    Longitude is constant at 0.0, latitude increases linearly from 0.0 to
    0.005 (~556 m at the equator, close enough to the 500 m road length for
    test purposes).

    Returns positions in [lon, lat] order as expected by Position.
    """
    return [Position([0.0, i * 0.005 / (n - 1)]) for i in range(n)]


def _build_road_with_traffic() -> Road:
    """Build a single 500 m straight road with traffic applied.

    The road has:
    - geometry: 11 sparse positions (indices 0..10)
    - pointcollection: 36 interpolated positions (1 per sim second)
    - traffic: severe congestion from geometry index 5..10 (latter half)

    After traffic is applied, `active_pointcollection` returns a denser
    set of points in the congested zone.
    """
    geometry = _make_straight_positions(NUM_GEOMETRY_POINTS)
    pointcollection = _make_straight_positions(NUM_POINTCOLLECTION)

    road = Road(
        road_id=1,
        name="Test Road",
        pointcollection=pointcollection,
        length=ROAD_LENGTH,
        maxspeed=MAXSPEED,
        geometry=geometry,
    )

    # Apply traffic covering the second half of the road
    segment_key: SegmentKey = road.segment_key
    traffic_range = TrafficRange(
        start_index=0,
        end_index=len(road.nodes) - 1,
        multiplier=TRAFFIC_MULTIPLIER,
        segment_key=segment_key,
        geom_start_index=TRAFFIC_GEOM_START,
        geom_end_index=TRAFFIC_GEOM_END,
    )
    road._traffic_ranges = {segment_key: traffic_range}
    # Let the road auto-generate the traffic pointcollection on first access
    # by leaving _traffic_pointcollection = None (the default).

    return road


def _build_route_result(positions: List[Position]) -> RouteResult:
    """Build a minimal RouteResult wrapping a single step."""
    step = RouteStep(
        name="Test Road",
        distance=ROAD_LENGTH,
        duration=ROAD_LENGTH / MAXSPEED,
        geometry=positions,
        speed=MAXSPEED,
    )
    return RouteResult(
        coordinates=positions,
        distance=ROAD_LENGTH,
        duration=ROAD_LENGTH / MAXSPEED,
        steps=[step],
        segments=[],
    )


def _make_route(road: Road) -> Route:
    """Create a Route with a single road and traffic event indices rebuilt."""
    route_result = _build_route_result(list(road.pointcollection))
    route = Route(
        route_data=route_result,
        routing_provider=Mock(spec=RoutingProvider),
        config={
            "simulation": {
                "kmh_to_ms_factor": 3.6,
                "map_rules": {"roads": {"default_road_max_speed": 30}},
            }
        },
        roads=[road],
        route_controller=None,
        route_recalculation_interval_seconds=99999,
    )
    # Rebuild event indices so the route knows about the traffic event
    route.notify_traffic_changed()
    return route


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------
class TestBackwardTeleportationBug:
    """Diagnostic tests for the backward-teleportation bug in smooth
    transitions.

    The core issue: after the transition buffer is consumed,
    `_sync_indices_after_transition` uses `find_nearest_index` on the
    active_pointcollection.  Because the traffic pointcollection has a
    *different density* than the original, the nearest-index can map to a
    point that is geographically BEHIND where the driver currently is,
    causing `get_distance_traveled()` to decrease.
    """

    def test_monotonic_distance_during_transition(self) -> None:
        """Traverse the route while tracking get_distance_traveled().

        Distance must NEVER decrease.  If _sync_indices_after_transition
        maps the driver backward, this assertion will fail.
        """
        road = _build_road_with_traffic()
        route = _make_route(road)

        distances: List[float] = []
        max_ticks = 200  # generous upper bound

        for _ in range(max_ticks):
            pos = route.next()
            if pos is None:
                break
            distances.append(route.get_distance_traveled())

        assert len(distances) > 1, "Route should have produced multiple positions"

        # Check monotonic non-decreasing distance
        for i in range(1, len(distances)):
            assert distances[i] >= distances[i - 1], (
                f"Distance decreased at tick {i}: "
                f"{distances[i - 1]:.4f} -> {distances[i]:.4f} "
                f"(delta={distances[i] - distances[i - 1]:.4f}). "
                f"This indicates backward teleportation after sync."
            )

    def test_position_always_forward(self) -> None:
        """On a straight north-bound road (constant lon, increasing lat),
        latitude must never decrease during traversal.

        This directly catches backward teleportation in geographic space.
        """
        road = _build_road_with_traffic()
        route = _make_route(road)

        latitudes: List[float] = []
        max_ticks = 200

        for _ in range(max_ticks):
            pos = route.next()
            if pos is None:
                break
            lat = pos.get_position()[1]
            latitudes.append(lat)

        assert len(latitudes) > 1, "Route should have produced multiple positions"

        for i in range(1, len(latitudes)):
            assert latitudes[i] >= latitudes[i - 1] - 1e-12, (
                f"Latitude decreased at tick {i}: "
                f"{latitudes[i - 1]:.10f} -> {latitudes[i]:.10f} "
                f"(delta={latitudes[i] - latitudes[i - 1]:.10f}). "
                f"Backward teleportation detected."
            )

    def test_sync_does_not_go_backward(self) -> None:
        """Directly test _sync_indices_after_transition.

        Set up a route mid-traversal, then call sync with a position that
        is geographically ahead.  The resulting indices must represent
        forward (or equal) progress compared to the pre-sync state.
        """
        road = _build_road_with_traffic()
        route = _make_route(road)

        active_points = road.active_pointcollection
        total_points = len(active_points)

        # Place the driver at roughly 60% through the road
        mid_index = int(total_points * 0.6)
        route.current_road_index = 0
        route.current_point_index = mid_index
        route._last_point_count = total_points

        pre_distance = route.get_distance_traveled()
        pre_point_index = route.current_point_index

        # Pick a sync target that is ahead (70% through)
        ahead_index = min(int(total_points * 0.7), total_points - 1)
        target_pos = active_points[ahead_index]

        route._sync_indices_after_transition(target_pos)

        post_distance = route.get_distance_traveled()

        assert route.current_road_index >= 0, "Road index should be valid"
        assert post_distance >= pre_distance - 1e-6, (
            f"Sync moved driver backward: "
            f"pre_distance={pre_distance:.4f}, post_distance={post_distance:.4f} "
            f"(pre_point_idx={pre_point_index}, "
            f"post_point_idx={route.current_point_index}). "
            f"_sync_indices_after_transition must guarantee forward-only mapping."
        )

    def test_notify_traffic_during_transition_does_not_teleport(self) -> None:
        """Start a transition, call notify_traffic_changed() mid-buffer,
        then continue consuming.  Distance must never decrease.

        This tests the interaction between smooth transitions and traffic
        change notifications, which can trigger an early sync via the
        `if self._transition_buffer:` path in `notify_traffic_changed`.
        """
        road = _build_road_with_traffic()
        route = _make_route(road)

        distances: List[float] = []
        transition_started = False
        notified = False
        max_ticks = 200

        for tick in range(max_ticks):
            pos = route.next()
            if pos is None:
                break

            distances.append(route.get_distance_traveled())

            # Detect when a transition buffer is active
            if route._transition_buffer and not transition_started:
                transition_started = True

            # Once in a transition, fire notify_traffic_changed mid-buffer
            if (
                transition_started
                and not notified
                and len(route._transition_buffer) > 1
            ):
                # Simulate a traffic change notification mid-transition
                route.notify_traffic_changed()
                notified = True

                # Record distance right after notification
                distances.append(route.get_distance_traveled())

        assert len(distances) > 1, "Route should have produced multiple positions"

        # Check monotonic non-decreasing distance
        for i in range(1, len(distances)):
            assert distances[i] >= distances[i - 1] - 1e-6, (
                f"Distance decreased at tick {i}: "
                f"{distances[i - 1]:.4f} -> {distances[i]:.4f} "
                f"(delta={distances[i] - distances[i - 1]:.4f}). "
                f"notify_traffic_changed during transition caused backward jump."
            )

    def test_no_oscillation_with_partial_traffic(self) -> None:
        """With traffic covering only part of the road (non-uniform density),
        the transition must not oscillate.

        Non-uniform density means get_distance_at_index must use geographic
        projection instead of uniform index-based mapping.  Without this fix,
        the curve starts behind the vehicle and the route loops forever.
        """
        geometry = _make_straight_positions(NUM_GEOMETRY_POINTS)
        pointcollection = _make_straight_positions(NUM_POINTCOLLECTION)

        road = Road(
            road_id=2,
            name="Partial Traffic Road",
            pointcollection=pointcollection,
            length=ROAD_LENGTH,
            maxspeed=MAXSPEED,
            geometry=geometry,
        )
        segment_key: SegmentKey = road.segment_key
        # Traffic only on 2nd half → non-uniform active_pointcollection
        traffic_range = TrafficRange(
            start_index=17,
            end_index=len(road.nodes) - 1,
            multiplier=TRAFFIC_MULTIPLIER,
            segment_key=segment_key,
            geom_start_index=TRAFFIC_GEOM_START,
            geom_end_index=TRAFFIC_GEOM_END,
        )
        road._traffic_ranges = {segment_key: traffic_range}

        route_result = _build_route_result(list(road.pointcollection))
        route = Route(
            route_data=route_result,
            routing_provider=Mock(spec=RoutingProvider),
            config={
                "simulation": {
                    "kmh_to_ms_factor": 3.6,
                    "map_rules": {"roads": {"default_road_max_speed": 30}},
                }
            },
            roads=[road],
            route_controller=None,
            route_recalculation_interval_seconds=99999,
        )
        route.notify_traffic_changed()

        latitudes: List[float] = []
        max_ticks = 200

        for _ in range(max_ticks):
            pos = route.next()
            if pos is None:
                break
            latitudes.append(pos.get_position()[1])

        assert len(latitudes) > 1, "Route should produce multiple positions"
        assert route.is_finished, (
            f"Route did not finish in {max_ticks} ticks — "
            f"possible infinite oscillation loop"
        )

        for i in range(1, len(latitudes)):
            assert latitudes[i] >= latitudes[i - 1] - 1e-12, (
                f"Latitude decreased at tick {i}: "
                f"{latitudes[i - 1]:.10f} -> {latitudes[i]:.10f}. "
                f"Oscillation detected with non-uniform point density."
            )
