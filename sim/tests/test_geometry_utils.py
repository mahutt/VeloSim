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
from sim.osm.OSRMConnection import OSRMConnection


class TestPointToSegmentDistance:
    """Test point-to-line-segment distance calculation utility."""

    def test_point_to_segment_distance_perpendicular(self) -> None:
        """
        Test distance when point is perpendicular to segment.
        Point (5, 5) is perpendicular to segment from (0, 0) to (10, 0).
        Expected distance: 5.0
        """
        distance = OSRMConnection._point_to_segment_distance(5, 5, 0, 0, 10, 0)
        assert distance == pytest.approx(5.0, rel=1e-6)

    def test_point_to_segment_distance_at_endpoint(self) -> None:
        """
        Test distance when point is at segment endpoint.
        Point (0, 0) is at start of segment from (0, 0) to (10, 0).
        Expected distance: 0.0
        """
        distance = OSRMConnection._point_to_segment_distance(0, 0, 0, 0, 10, 0)
        assert distance == pytest.approx(0.0, rel=1e-6)

    def test_point_to_segment_distance_on_segment(self) -> None:
        """
        Test distance when point is on the segment.
        Point (5, 0) is on segment from (0, 0) to (10, 0).
        Expected distance: 0.0
        """
        distance = OSRMConnection._point_to_segment_distance(5, 0, 0, 0, 10, 0)
        assert distance == pytest.approx(0.0, rel=1e-6)

    def test_point_to_segment_distance_beyond_endpoint(self) -> None:
        """
        Test distance when point is beyond segment endpoint.
        Point (15, 0) is beyond end of segment from (0, 0) to (10, 0).
        Expected distance: 5.0 (distance from point to nearest endpoint)
        """
        distance = OSRMConnection._point_to_segment_distance(15, 0, 0, 0, 10, 0)
        assert distance == pytest.approx(5.0, rel=1e-6)

    def test_point_to_segment_distance_before_start(self) -> None:
        """
        Test distance when point is before segment start.
        Point (-5, 0) is before start of segment from (0, 0) to (10, 0).
        Expected distance: 5.0 (distance from point to nearest endpoint)
        """
        distance = OSRMConnection._point_to_segment_distance(-5, 0, 0, 0, 10, 0)
        assert distance == pytest.approx(5.0, rel=1e-6)

    def test_point_to_segment_distance_diagonal_segment(self) -> None:
        """
        Test distance for diagonal segment.
        Point (5, 5) relative to segment from (0, 0) to (10, 10).
        Point is on the line, so distance should be 0.
        """
        distance = OSRMConnection._point_to_segment_distance(5, 5, 0, 0, 10, 10)
        assert distance == pytest.approx(0.0, rel=1e-6)

    def test_point_to_segment_distance_diagonal_offset(self) -> None:
        """
        Test distance when point is offset from diagonal segment.
        Point (0, 5) relative to segment from (0, 0) to (10, 0).
        Expected distance: 5.0
        """
        distance = OSRMConnection._point_to_segment_distance(0, 5, 0, 0, 10, 0)
        assert distance == pytest.approx(5.0, rel=1e-6)

    def test_point_to_segment_distance_degenerate_segment(self) -> None:
        """
        Test distance when segment is degenerate (both endpoints are same).
        Segment from (5, 5) to (5, 5), point at (8, 9).
        Expected distance: sqrt((8-5)^2 + (9-5)^2) = sqrt(9 + 16) = 5.0
        """
        distance = OSRMConnection._point_to_segment_distance(8, 9, 5, 5, 5, 5)
        assert distance == pytest.approx(5.0, rel=1e-6)

    def test_point_to_segment_distance_vertical_segment(self) -> None:
        """
        Test distance for vertical segment.
        Point (5, 5) relative to vertical segment from (0, 0) to (0, 10).
        Expected distance: 5.0
        """
        distance = OSRMConnection._point_to_segment_distance(5, 5, 0, 0, 0, 10)
        assert distance == pytest.approx(5.0, rel=1e-6)

    def test_point_to_segment_distance_negative_coordinates(self) -> None:
        """
        Test distance with negative coordinates.
        Point (-5, -5) relative to segment from (-10, -10) to (0, 0).
        Point is on the line, so distance should be 0.
        """
        distance = OSRMConnection._point_to_segment_distance(-5, -5, -10, -10, 0, 0)
        assert distance == pytest.approx(0.0, rel=1e-6)

    def test_point_to_segment_distance_real_world_coordinates(self) -> None:
        """
        Test with real-world coordinate values (lon/lat).
        Blocked area at (-73.5600, 45.5050) relative to route segment
        from (-73.5673, 45.5017) to (-73.5533, 45.5017).
        This tests the actual use case for route blocking.
        """
        # Blocked point is slightly north of the horizontal route segment
        distance = OSRMConnection._point_to_segment_distance(
            -73.5600, 45.5050, -73.5673, 45.5017, -73.5533, 45.5017
        )
        # Distance should be approximately the latitude difference (0.0033 degrees)
        assert distance == pytest.approx(0.0033, rel=1e-2)

    def test_point_to_segment_catches_near_misses(self) -> None:
        """
        Test that point-to-segment distance correctly identifies near misses
        that point-only checking would miss.

        This is the key improvement: a blocked area near the middle of a
        segment should be detected even if the segment's waypoints are far
        from the blocked area.
        """
        # Route segment from (0, 0) to (100, 0)
        # Blocked area at (50, 1) - very close to middle of segment
        distance = OSRMConnection._point_to_segment_distance(50, 1, 0, 0, 100, 0)

        # Distance should be 1.0 (perpendicular distance)
        assert distance == pytest.approx(1.0, rel=1e-6)

        # This would be missed if we only checked endpoints (0,0) and (100,0)
        # against the blocked point (50, 1)
        dist_to_start = ((50 - 0) ** 2 + (1 - 0) ** 2) ** 0.5  # ~50.01
        dist_to_end = ((50 - 100) ** 2 + (1 - 0) ** 2) ** 0.5  # ~50.01

        # Both endpoints are far away, but segment is very close
        assert dist_to_start > 50
        assert dist_to_end > 50
        assert distance < 2  # But actual distance to segment is only 1
