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

from unittest.mock import Mock

from sim.entities.position import Position
from sim.entities.road import Road
from sim.entities.route import Route
from sim.entities.driver import Driver
from sim.entities.shift import Shift
from sim.entities.traffic_data import (
    CongestionLevel,
    TrafficTriple,
)
from sim.map.routing_provider import RouteResult, SegmentKey


# ── Helpers ──────────────────────────────────────────────────────────


def _make_road(
    positions: list[Position],
    geometry: list[Position] | None = None,
    road_id: int = 1,
    length: float = 100.0,
    maxspeed: float = 10.0,
) -> Road:
    """Create a Road with given pointcollection and optional geometry."""
    return Road(
        road_id=road_id,
        name="test",
        pointcollection=positions,
        length=length,
        maxspeed=maxspeed,
        geometry=geometry,
    )


def _make_route(roads: list[Road]) -> Route:
    """Create a Route with minimal mocking."""
    coords = []
    for road in roads:
        if road.geometry:
            coords.extend(road.geometry)

    route_result = Mock(spec=RouteResult)
    route_result.coordinates = coords
    route_result.distance = 100.0
    route_result.duration = 10.0
    route_result.steps = []
    route_result.start_position = coords[0] if coords else Position([0, 0])
    route_result.end_position = coords[-1] if coords else Position([1, 1])

    routing_provider = Mock()

    return Route(
        route_data=route_result,
        routing_provider=routing_provider,
        config={},
        roads=roads,
    )


def _apply_traffic(
    road: Road,
    route: Route,
    overlap: list[Position],
    multiplier: float,
    seg_key: SegmentKey,
) -> None:
    """Apply traffic to a road and notify its route (mirrors TrafficController)."""
    road.apply_traffic_for_overlap(overlap, multiplier, seg_key)
    route.notify_traffic_changed()


# ── TrafficTriple Tests ─────────────────────────────────────────────


class TestTrafficTriple:
    def test_to_json(self) -> None:
        triple = TrafficTriple(1, 3, CongestionLevel.SEVERE)
        assert triple.to_json() == {
            "startCoordinateIndex": 1,
            "endCoordinateIndex": 3,
            "congestionLevel": "severe",
        }

    def test_to_json_moderate(self) -> None:
        triple = TrafficTriple(0, 5, CongestionLevel.MODERATE)
        assert triple.to_json() == {
            "startCoordinateIndex": 0,
            "endCoordinateIndex": 5,
            "congestionLevel": "moderate",
        }

    def test_to_json_free_flow(self) -> None:
        triple = TrafficTriple(2, 4, CongestionLevel.FREE_FLOW)
        assert triple.to_json() == {
            "startCoordinateIndex": 2,
            "endCoordinateIndex": 4,
            "congestionLevel": "free_flow",
        }

    def test_to_json_with_offset(self) -> None:
        triple = TrafficTriple(1, 3, CongestionLevel.SEVERE)
        assert triple.to_json_with_offset(5) == {
            "startCoordinateIndex": 6,
            "endCoordinateIndex": 8,
            "congestionLevel": "severe",
        }

    def test_to_json_with_zero_offset(self) -> None:
        triple = TrafficTriple(1, 3, CongestionLevel.MODERATE)
        assert triple.to_json_with_offset(0) == {
            "startCoordinateIndex": 1,
            "endCoordinateIndex": 3,
            "congestionLevel": "moderate",
        }


# ── Road.get_traffic_geometry_ranges() Tests ─────────────────────────


class TestRoadGetTrafficGeometryRanges:
    def test_no_traffic_returns_empty(self) -> None:
        positions = [Position([0, 0]), Position([1, 1])]
        road = _make_road(positions, geometry=positions)
        assert road.get_traffic_geometry_ranges() == []

    def test_free_flow_excluded(self) -> None:
        """FREE_FLOW ranges should not appear in output."""
        geom = [Position([0, 0]), Position([0.5, 0.5]), Position([1, 1])]
        road = _make_road(geom, geometry=geom)
        seg_key: SegmentKey = ((0, 0), (1, 1))
        road.apply_traffic_for_overlap(geom, 1.0, seg_key)
        assert road.get_traffic_geometry_ranges() == []

    def test_severe_traffic_returned(self) -> None:
        geom = [Position([0, 0]), Position([0.5, 0.5]), Position([1, 1])]
        road = _make_road(geom, geometry=geom)
        seg_key: SegmentKey = ((0, 0), (1, 1))
        road.apply_traffic_for_overlap(geom, 0.15, seg_key)

        ranges = road.get_traffic_geometry_ranges()
        assert len(ranges) == 1
        assert ranges[0][2] == CongestionLevel.SEVERE

    def test_partial_overlap_geometry_indices(self) -> None:
        """Only overlapping positions should define the geometry range."""
        geom = [
            Position([0, 0]),
            Position([1, 0]),
            Position([2, 0]),
            Position([3, 0]),
            Position([4, 0]),
        ]
        road = _make_road(geom, geometry=geom)
        overlap = [Position([1, 0]), Position([2, 0]), Position([3, 0])]
        seg_key: SegmentKey = ((0, 0), (4, 0))
        road.apply_traffic_for_overlap(overlap, 0.15, seg_key)

        ranges = road.get_traffic_geometry_ranges()
        assert len(ranges) == 1
        geom_start, geom_end, level = ranges[0]
        assert geom_start == 1
        assert geom_end == 3
        assert level == CongestionLevel.SEVERE

    def test_full_overlap(self) -> None:
        geom = [Position([0, 0]), Position([1, 0]), Position([2, 0])]
        road = _make_road(geom, geometry=geom)
        seg_key: SegmentKey = ((0, 0), (2, 0))
        road.apply_traffic_for_overlap(geom, 0.5, seg_key)

        ranges = road.get_traffic_geometry_ranges()
        assert len(ranges) == 1
        assert ranges[0][0] == 0
        assert ranges[0][1] == 2
        assert ranges[0][2] == CongestionLevel.MODERATE


# ── Route.get_traffic_triples() + notify_traffic_changed() Tests ─────


class TestRouteGetTrafficTriples:
    def test_no_traffic_returns_empty(self) -> None:
        geom = [Position([0, 0]), Position([1, 0]), Position([2, 0])]
        road = _make_road(geom, geometry=geom)
        route = _make_route([road])
        assert route.get_traffic_triples() == []

    def test_single_road_traffic(self) -> None:
        geom = [Position([0, 0]), Position([1, 0]), Position([2, 0])]
        road = _make_road(geom, geometry=geom)
        route = _make_route([road])

        seg_key: SegmentKey = ((0, 0), (2, 0))
        _apply_traffic(road, route, geom, 0.15, seg_key)

        triples = route.get_traffic_triples()
        assert len(triples) == 1
        assert triples[0].start_index == 0
        assert triples[0].end_index == 2
        assert triples[0].congestion_level == CongestionLevel.SEVERE

    def test_multi_road_offset(self) -> None:
        """Second road indices offset by first road's geom length - 1."""
        geom1 = [Position([0, 0]), Position([1, 0]), Position([2, 0])]
        geom2 = [Position([2, 0]), Position([3, 0]), Position([4, 0])]
        road1 = _make_road(geom1, geometry=geom1, road_id=1)
        road2 = _make_road(geom2, geometry=geom2, road_id=2)
        route = _make_route([road1, road2])

        # Apply traffic only to road2
        seg_key: SegmentKey = ((2, 0), (4, 0))
        _apply_traffic(road2, route, geom2, 0.15, seg_key)

        triples = route.get_traffic_triples()
        assert len(triples) == 1
        # Road1 has 3 geometry points, so offset = 3-1 = 2
        # Road2's geom range is 0-2, so abs = 2-4
        assert triples[0].start_index == 2
        assert triples[0].end_index == 4
        assert triples[0].congestion_level == CongestionLevel.SEVERE

    def test_sub_road_precision(self) -> None:
        """Traffic affecting part of a road should give sub-road indices."""
        geom = [
            Position([0, 0]),
            Position([1, 0]),
            Position([2, 0]),
            Position([3, 0]),
            Position([4, 0]),
        ]
        road = _make_road(geom, geometry=geom)
        route = _make_route([road])

        overlap = [Position([1, 0]), Position([2, 0])]
        seg_key: SegmentKey = ((0, 0), (4, 0))
        _apply_traffic(road, route, overlap, 0.5, seg_key)

        triples = route.get_traffic_triples()
        assert len(triples) == 1
        assert triples[0].start_index == 1
        assert triples[0].end_index == 2
        assert triples[0].congestion_level == CongestionLevel.MODERATE

    def test_merging_adjacent_same_level(self) -> None:
        """Adjacent ranges on consecutive roads with same level should merge."""
        geom1 = [Position([0, 0]), Position([1, 0]), Position([2, 0])]
        geom2 = [Position([2, 0]), Position([3, 0]), Position([4, 0])]
        road1 = _make_road(geom1, geometry=geom1, road_id=1)
        road2 = _make_road(geom2, geometry=geom2, road_id=2)
        route = _make_route([road1, road2])

        seg_key1: SegmentKey = ((0, 0), (2, 0))
        seg_key2: SegmentKey = ((2, 0), (4, 0))
        _apply_traffic(road1, route, geom1, 0.15, seg_key1)
        _apply_traffic(road2, route, geom2, 0.15, seg_key2)

        triples = route.get_traffic_triples()
        # Should merge into single triple since adjacent + same level
        assert len(triples) == 1
        assert triples[0].start_index == 0
        assert triples[0].end_index == 4
        assert triples[0].congestion_level == CongestionLevel.SEVERE

    def test_different_levels_not_merged(self) -> None:
        """Adjacent ranges with different levels should remain separate."""
        geom1 = [Position([0, 0]), Position([1, 0]), Position([2, 0])]
        geom2 = [Position([2, 0]), Position([3, 0]), Position([4, 0])]
        road1 = _make_road(geom1, geometry=geom1, road_id=1)
        road2 = _make_road(geom2, geometry=geom2, road_id=2)
        route = _make_route([road1, road2])

        seg_key1: SegmentKey = ((0, 0), (2, 0))
        seg_key2: SegmentKey = ((2, 0), (4, 0))
        _apply_traffic(road1, route, geom1, 0.15, seg_key1)  # SEVERE
        _apply_traffic(road2, route, geom2, 0.5, seg_key2)  # MODERATE

        triples = route.get_traffic_triples()
        assert len(triples) == 2
        assert triples[0].congestion_level == CongestionLevel.SEVERE
        assert triples[1].congestion_level == CongestionLevel.MODERATE

    def test_road_without_geometry_skipped(self) -> None:
        """Roads without geometry should be skipped gracefully."""
        geom = [Position([0, 0]), Position([1, 0])]
        road_with_geom = _make_road(geom, geometry=geom, road_id=1)
        road_no_geom = _make_road(geom, geometry=None, road_id=2)

        route = _make_route([road_no_geom, road_with_geom])
        # Should not crash
        triples = route.get_traffic_triples()
        assert triples == []

    def test_notify_sets_traffic_changed(self) -> None:
        """notify_traffic_changed should set the traffic_changed flag."""
        geom = [Position([0, 0]), Position([1, 0]), Position([2, 0])]
        road = _make_road(geom, geometry=geom)
        route = _make_route([road])

        assert route.has_traffic_changed is False
        seg_key: SegmentKey = ((0, 0), (2, 0))
        _apply_traffic(road, route, geom, 0.15, seg_key)
        assert route.has_traffic_changed is True

    def test_notify_updates_cache_on_traffic_removal(self) -> None:
        """Cache should update when traffic is removed."""
        geom = [Position([0, 0]), Position([1, 0]), Position([2, 0])]
        road = _make_road(geom, geometry=geom)
        route = _make_route([road])

        seg_key: SegmentKey = ((0, 0), (2, 0))
        _apply_traffic(road, route, geom, 0.15, seg_key)
        assert len(route.get_traffic_triples()) == 1

        # Remove traffic and notify
        road.remove_traffic(seg_key)
        route.notify_traffic_changed()
        assert route.get_traffic_triples() == []


# ── Driver.traffic_changed + clear_update() Tests ───────────────────


class TestDriverTrafficChanged:
    def _make_driver(self, routes: list[Route] | None = None) -> Driver:
        shift = Shift(0.0, 24.0, None, 0.0, 24.0, None)
        driver = Driver(
            driver_id=1,
            position=Position([0, 0]),
            shift=shift,
        )
        if routes is not None:
            driver.routes = routes
        return driver

    def test_no_routes_not_changed(self) -> None:
        driver = self._make_driver()
        assert driver.traffic_changed is False

    def test_no_traffic_not_changed(self) -> None:
        geom = [Position([0, 0]), Position([1, 0])]
        road = _make_road(geom, geometry=geom)
        route = _make_route([road])
        driver = self._make_driver([route])
        assert driver.traffic_changed is False

    def test_traffic_change_propagates(self) -> None:
        """When traffic is applied to a route's road, driver.traffic_changed is True."""
        geom = [Position([0, 0]), Position([1, 0]), Position([2, 0])]
        road = _make_road(geom, geometry=geom)
        route = _make_route([road])
        driver = self._make_driver([route])

        seg_key: SegmentKey = ((0, 0), (2, 0))
        _apply_traffic(road, route, geom, 0.15, seg_key)
        assert driver.traffic_changed is True

    def test_clear_update_resets_traffic_changed(self) -> None:
        geom = [Position([0, 0]), Position([1, 0]), Position([2, 0])]
        road = _make_road(geom, geometry=geom)
        route = _make_route([road])
        driver = self._make_driver([route])

        seg_key: SegmentKey = ((0, 0), (2, 0))
        _apply_traffic(road, route, geom, 0.15, seg_key)
        assert driver.traffic_changed is True

        driver.clear_update()
        assert driver.traffic_changed is False

    def test_multi_route_any_changed(self) -> None:
        """traffic_changed is True if ANY route has changed."""
        geom1 = [Position([0, 0]), Position([1, 0])]
        geom2 = [Position([2, 0]), Position([3, 0]), Position([4, 0])]
        road1 = _make_road(geom1, geometry=geom1, road_id=1)
        road2 = _make_road(geom2, geometry=geom2, road_id=2)
        route1 = _make_route([road1])
        route2 = _make_route([road2])
        driver = self._make_driver([route1, route2])

        assert driver.traffic_changed is False

        seg_key: SegmentKey = ((2, 0), (4, 0))
        _apply_traffic(road2, route2, geom2, 0.15, seg_key)
        assert driver.traffic_changed is True
