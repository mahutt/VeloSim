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

import pytest
from sim.osm.stop_sign_index import StopSignIndex


class TestStopSignDirectionalFiltering:
    """Test stop sign filtering to ensure only route-relevant stops are returned."""

    def test_straight_route_with_perpendicular_stops(self) -> None:
        """Stop signs on perpendicular roads should NOT be included."""
        # Route going EAST (horizontal line)
        route = [
            [-73.600, 45.500],  # Start
            [-73.590, 45.500],  # End (same latitude, moving east)
        ]

        # Stop signs: one on route, two on perpendicular roads (north/south)
        stop_signs = [
            [-73.595, 45.500],  # ON the route (should be included)
            [-73.595, 45.501],  # NORTH of route (perpendicular, should be excluded)
            [-73.595, 45.499],  # SOUTH of route (perpendicular, should be excluded)
        ]

        index = StopSignIndex(stop_sign_coordinates=stop_signs)
        result = index.find_near_route(route, tolerance_degrees=0.00012)

        # Should only find the stop sign ON the route
        assert len(result) == 1
        assert result[0] == pytest.approx([-73.595, 45.500], abs=1e-6)

    def test_four_way_intersection_entry_vs_exit(self) -> None:
        """At 4-way stop, entry stops should be included, far exit stops excluded."""
        # Route going NORTH through intersection at [-73.595, 45.500]
        route = [
            [-73.595, 45.499],  # Start (south of intersection)
            [-73.595, 45.500],  # Intersection center
            [-73.595, 45.501],  # End (north of intersection)
        ]

        # 4-way stop: stops on all sides of intersection
        stop_signs = [
            [-73.595, 45.4995],  # SOUTH side (ENTRY - should be included)
            [
                -73.595,
                45.5008,
            ],  # NORTH side, 80% through segment (EXIT - should be excluded)
            [-73.594, 45.500],  # WEST side (perpendicular - should be excluded)
            [-73.596, 45.500],  # EAST side (perpendicular - should be excluded)
        ]

        index = StopSignIndex(stop_sign_coordinates=stop_signs)
        result = index.find_near_route(route, tolerance_degrees=0.00012)

        # Should only find the ENTRY stop (south side)
        # The exit stop at 80% should be filtered out
        assert len(result) == 1
        # The entry stop should be before the intersection
        assert result[0][1] < 45.500  # Latitude less than intersection center

    def test_route_with_multiple_intersections(self) -> None:
        """Multiple intersections should each have only entry stops."""
        # Route with two intersections
        route = [
            [-73.600, 45.500],  # Start
            [-73.595, 45.500],  # First intersection
            [-73.590, 45.500],  # Second intersection
            [-73.585, 45.500],  # End
        ]

        # Stop signs at both intersections (entry and exit for each)
        stop_signs = [
            [
                -73.5975,
                45.500,
            ],  # Intersection 1 ENTRY (first 50% of segment 1 - should be included)
            [
                -73.5925,
                45.500,
            ],  # Intersection 1 EXIT / Intersection 2 ENTRY (boundary between segments)
            [
                -73.5875,
                45.500,
            ],  # Intersection 2 EXIT (last 50% of segment 2 - should be excluded)
        ]

        index = StopSignIndex(stop_sign_coordinates=stop_signs)
        result = index.find_near_route(route, tolerance_degrees=0.00012)

        # The middle stop [-73.5925, 45.500] is at 50% of segment 1 (exit) but also
        # at the start of segment 2 (entry), so it may appear in segment 2
        # We should get at least 2 stops (entry for each of the first two segments)
        assert len(result) >= 2

    def test_stop_sign_behind_route_start(self) -> None:
        """Stop signs behind the route start should be excluded."""
        route = [
            [-73.595, 45.500],  # Start
            [-73.590, 45.500],  # End (moving east)
        ]

        stop_signs = [
            [
                -73.596,
                45.500,
            ],  # BEHIND start (west of start) - projection ratio would be negative
            [-73.5935, 45.500],  # ON route at 30% (should be included)
        ]

        index = StopSignIndex(stop_sign_coordinates=stop_signs)
        result = index.find_near_route(route, tolerance_degrees=0.00012)

        # Should only find the stop ON the route (at 30%), not behind it
        assert len(result) == 1
        assert result[0][0] == pytest.approx(-73.5935, abs=1e-6)

    def test_stop_sign_projection_ratio_filtering(self) -> None:
        """Stop signs beyond 75% of segment should be excluded (exit filtering)."""
        # Short segment
        route = [
            [-73.600, 45.500],
            [-73.599, 45.500],  # 0.001 degrees east
        ]

        # Stop signs at different positions along segment
        stop_signs = [
            [-73.5997, 45.500],  # 30% along segment (should be included)
            [-73.5995, 45.500],  # 50% along segment (should be included)
            [-73.5993, 45.500],  # 70% along segment (should be included)
            [-73.5991, 45.500],  # 90% along segment (should be excluded - exit stop)
        ]

        index = StopSignIndex(stop_sign_coordinates=stop_signs)
        result = index.find_near_route(route, tolerance_degrees=0.00012)

        # Should only include stops in first 75% of segment
        # This filters out exit stops while keeping entry/turn stops
        assert len(result) == 3  # First three stops (30%, 50%, 70%)
        # The 90% stop should be excluded
        assert [-73.5991, 45.500] not in result

    def test_curved_route_with_stops(self) -> None:
        """Curved routes should only include stops along the path."""
        # Route curves from east to north
        route = [
            [-73.600, 45.500],  # Start (moving east)
            [-73.595, 45.500],  # Curve point
            [-73.595, 45.505],  # End (now moving north)
        ]

        # Stop signs: some on route, some off to sides
        stop_signs = [
            [-73.598, 45.500],  # On first segment (should be included)
            [-73.595, 45.502],  # On second segment (should be included)
            [-73.592, 45.500],  # Off route to east (should be excluded)
            [-73.598, 45.505],  # Off route to north (should be excluded)
        ]

        index = StopSignIndex(stop_sign_coordinates=stop_signs)
        result = index.find_near_route(route, tolerance_degrees=0.00012)

        # Should find exactly 2 stops (one on each segment)
        assert len(result) == 2

    def test_empty_route_returns_empty_list(self) -> None:
        """Empty or single-point routes should return empty list."""
        stop_signs = [[-73.595, 45.500]]
        index = StopSignIndex(stop_sign_coordinates=stop_signs)

        assert index.find_near_route([], tolerance_degrees=0.00012) == []
        assert (
            index.find_near_route([[-73.600, 45.500]], tolerance_degrees=0.00012) == []
        )

    def test_no_stop_signs_returns_empty_list(self) -> None:
        """Route with no nearby stop signs should return empty list."""
        route = [
            [-73.600, 45.500],
            [-73.590, 45.500],
        ]

        index = StopSignIndex(stop_sign_coordinates=[])
        result = index.find_near_route(route, tolerance_degrees=0.00012)

        assert result == []

    def test_stop_sign_deduplication(self) -> None:
        """Duplicate stop signs should only appear once in results."""
        route = [
            [-73.600, 45.500],
            [-73.590, 45.500],
        ]

        # Same stop sign listed multiple times (data quality issue simulation)
        stop_signs = [
            [-73.595, 45.500],
            [-73.595, 45.500],
            [-73.595, 45.500],
        ]

        index = StopSignIndex(stop_sign_coordinates=stop_signs)
        result = index.find_near_route(route, tolerance_degrees=0.00012)

        # Should return exactly one stop despite duplicates
        assert len(result) == 1


class TestStopSignControllerIntegration:
    """Integration tests for stop sign controller with roads."""

    def test_stop_sign_assigned_to_correct_road_at_intersection(self) -> None:
        """At intersection, sign should map to route road, not perpendicular road."""
        # This test would require full Road and PositionRegistry setup
        # Left as placeholder for integration testing
        pass

    def test_intersection_clustering_removes_duplicates(self) -> None:
        """Multiple stops at same intersection should cluster to one."""
        # This test would require full StopSignController setup
        # Left as placeholder for integration testing
        pass
