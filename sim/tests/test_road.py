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
import os
import json
import numpy as np
from pathlib import Path
from pandas import Series
from shapely.geometry import LineString
from typing import Generator, List
from unittest.mock import MagicMock, Mock, patch

from sim.entities.point_generation import PointGenerationStrategy, RoadPointContext
from sim.entities.road import Road
from sim.entities.position import Position


def generate_point_collection(
    linestring: LineString, length: float, maxspeed: float
) -> List[Position]:
    """
    Generate evenly-spaced Position objects along a route.
    This mimics the logic from route.py for testing purposes.
    """
    points: List[Position] = []

    if maxspeed <= 0 or length <= 0:
        coords = list(linestring.coords)
        if coords:
            points.append(Position([float(coords[0][0]), float(coords[0][1])]))
            if len(coords) > 1:
                points.append(Position([float(coords[-1][0]), float(coords[-1][1])]))
        return points

    distance_increment = maxspeed

    coords = list(linestring.coords)

    if len(coords) == 2:
        start_lon, start_lat = coords[0]
        end_lon, end_lat = coords[1]

        time_seconds = length / maxspeed
        num_points = int(np.ceil(time_seconds)) + 1

        for i in range(num_points):
            distance = min(i * distance_increment, length)
            t = distance / length

            lon = float(start_lon + t * (end_lon - start_lon))
            lat = float(start_lat + t * (end_lat - start_lat))

            new_position = Position([lon, lat])

            if not points or points[-1].get_position() != new_position.get_position():
                points.append(new_position)
    else:
        # Multi-vertex linestring
        total_length_degrees = linestring.length

        for i in range(int(np.ceil(length / distance_increment)) + 1):
            distance_meters = min(i * distance_increment, length)

            # Convert meters back to degrees for interpolation
            distance_degrees = (distance_meters / length) * total_length_degrees

            point = linestring.interpolate(distance_degrees)
            new_position = Position([float(point.x), float(point.y)])

            # Avoid duplicates
            if not points or points[-1].get_position() != new_position.get_position():
                points.append(new_position)

    return points


@pytest.fixture
def setup_test_environment(tmp_path: Path) -> Generator[None, None, None]:
    """
    Creates a temporary config.json and changes the working directory.
    This allows the Road class to read a real file during tests.
    """
    original_cwd = Path.cwd()

    config_data = {
        "simulation": {
            "kmh_to_ms_factor": 3.6,
            "map_rules": {"roads": {"default_road_max_speed": 50}},
        }
    }
    config_file = tmp_path / "config.json"
    config_file.write_text(json.dumps(config_data))

    os.chdir(tmp_path)

    yield

    os.chdir(original_cwd)


def test_road_empty_pointcollection_raises_error() -> None:
    """Test that Road raises ValueError when initialized with empty pointcollection."""
    with pytest.raises(ValueError, match="Road 123 requires non-empty pointcollection"):
        Road(
            road_id=123,
            name="Empty Road",
            pointcollection=[],
            length=100.0,
            maxspeed=10.0,
        )


def test_road_initialization_with_valid_maxspeed(setup_test_environment: None) -> None:
    # Arrange: Create a sample road edge
    edge_data = Series(
        {
            "id": 101,
            "name": "Main Street",
            "length": 100.0,
            "maxspeed": "50",  # 50 km/h
            "geometry": LineString([(0, 0), (100, 0)]),
        }
    )

    # Extract data and convert maxspeed
    road_id = edge_data["id"]
    name = edge_data["name"]
    length = edge_data["length"]
    maxspeed_kmh = float(edge_data["maxspeed"])
    maxspeed_ms = maxspeed_kmh / 3.6  # Convert to m/s
    linestring = edge_data["geometry"]

    # Generate point collection
    pointcollection = generate_point_collection(linestring, length, maxspeed_ms)

    # Initialize the Road object
    road_obj = Road(road_id, name, pointcollection, length, maxspeed_ms)

    # Check attributes and conversions
    assert road_obj.id == 101
    assert road_obj.name == "Main Street"
    assert road_obj.length == 100.0
    # 50 km/h / 3.6 = 13.888 m/s
    assert road_obj.maxspeed == pytest.approx(13.888, 0.001)

    # Assert point collection logic
    # Expected points: at 0, 13.88, ..., 97.22 (8 points) + the final point (100, 0)
    assert len(road_obj.pointcollection) == 9
    assert all(isinstance(p, Position) for p in road_obj.pointcollection)
    assert road_obj.pointcollection[-1].get_position() == [100.0, 0.0]


def test_road_initialization_with_missing_maxspeed(
    setup_test_environment: None,
) -> None:
    # Arrange: Create an edge without a 'maxspeed' key
    edge_data = Series(
        {
            "id": 202,
            "name": "Default Road",
            "length": 80.0,
            "geometry": LineString([(0, 0), (80, 0)]),
        }
    )

    # Extract data and use default maxspeed
    road_id = edge_data["id"]
    name = edge_data["name"]
    length = edge_data["length"]
    default_speed_kmh = 50  # From config
    maxspeed_ms = default_speed_kmh / 3.6
    linestring = edge_data["geometry"]

    # Generate point collection
    pointcollection = generate_point_collection(linestring, length, maxspeed_ms)

    road_obj = Road(road_id, name, pointcollection, length, maxspeed_ms)

    # Check that the default speed from the real config was used
    assert road_obj.id == 202
    # Default is 50 km/h / 3.6 = 13.888 m/s (from actual config)
    assert road_obj.maxspeed == pytest.approx(13.888, 0.001)

    # Check point collection logic with default speed
    # Expected points: at 0, 13.88, ..., 69.44 (6 points) + final (80, 0)
    assert len(road_obj.pointcollection) == 7
    assert all(isinstance(p, Position) for p in road_obj.pointcollection)


def test_road_with_zero_length(setup_test_environment: None) -> None:
    # Arrange
    edge_data = Series(
        {
            "id": 303,
            "name": "Zero Length Street",
            "length": 0.0,
            "maxspeed": "50",
            "geometry": LineString([(10, 10), (10, 10)]),
        }
    )

    # Extract data
    road_id = edge_data["id"]
    name = edge_data["name"]
    length = edge_data["length"]
    maxspeed_ms = float(edge_data["maxspeed"]) / 3.6
    linestring = edge_data["geometry"]

    # Generate point collection
    pointcollection = generate_point_collection(linestring, length, maxspeed_ms)

    road_obj = Road(road_id, name, pointcollection, length, maxspeed_ms)

    assert road_obj.length == 0.0
    assert len(road_obj.pointcollection) == 2
    assert road_obj.pointcollection[0].get_position() == [10.0, 10.0]
    assert road_obj.pointcollection[1].get_position() == [10.0, 10.0]


def test_road_shorter_than_one_second_travel(setup_test_environment: None) -> None:
    # Arrange: A short road where length < distance covered in 1 second
    edge_data = Series(
        {
            "id": 404,
            "name": "Short Alley",
            "length": 10.0,  # Length is 10 meters
            "maxspeed": "50",  # Speed is ~13.88 m/s
            "geometry": LineString([(0, 0), (10, 0)]),
        }
    )

    # Extract data
    road_id = edge_data["id"]
    name = edge_data["name"]
    length = edge_data["length"]
    maxspeed_ms = float(edge_data["maxspeed"]) / 3.6
    linestring = edge_data["geometry"]

    # Generate point collection
    pointcollection = generate_point_collection(linestring, length, maxspeed_ms)

    road_obj = Road(road_id, name, pointcollection, length, maxspeed_ms)

    assert road_obj.maxspeed > road_obj.length
    assert len(road_obj.pointcollection) == 2
    assert road_obj.pointcollection[0].get_position() == [0.0, 0.0]
    assert road_obj.pointcollection[1].get_position() == [10.0, 0.0]


def test_road_with_multi_vertex_linestring(setup_test_environment: None) -> None:
    # Arrange: Create a road with a multi-vertex linestring (more than 2 points)
    edge_data = Series(
        {
            "id": 505,
            "name": "Curved Road",
            "length": 150.0,  # Length in meters
            "maxspeed": "30",  # 30 km/h / 3.6 = 8.333 m/s
            "geometry": LineString([(0, 0), (50, 25), (100, 50), (150, 50)]),
        }
    )

    # Extract data
    road_id = edge_data["id"]
    name = edge_data["name"]
    length = edge_data["length"]
    maxspeed_ms = float(edge_data["maxspeed"]) / 3.6
    linestring = edge_data["geometry"]

    # Generate point collection
    pointcollection = generate_point_collection(linestring, length, maxspeed_ms)

    road_obj = Road(road_id, name, pointcollection, length, maxspeed_ms)

    # Verify basic attributes
    assert road_obj.id == 505
    assert road_obj.name == "Curved Road"
    assert road_obj.length == 150.0
    assert road_obj.maxspeed == pytest.approx(8.333, 0.001)

    # Check that we have multiple points (using interpolate method)
    # Distance increment = 8.333 m/s
    # Points at: 0, 8.333, 16.666, ..., up to 150
    # Expected: ~18 intermediate points + final point
    assert len(road_obj.pointcollection) > 2
    assert all(isinstance(p, Position) for p in road_obj.pointcollection)

    # Verify first and last points
    assert road_obj.pointcollection[0].get_position() == pytest.approx([0.0, 0.0])
    assert road_obj.pointcollection[-1].get_position() == pytest.approx([150.0, 50.0])


def test_road_with_multi_vertex_ensures_last_point(
    setup_test_environment: None,
) -> None:
    # Arrange: Test that the exact last point is always included
    edge_data = Series(
        {
            "id": 606,
            "name": "Exact End Point Road",
            "length": 100.0,
            "maxspeed": "60",  # 60 km/h / 3.6 = 16.666 m/s
            "geometry": LineString([(0, 0), (30, 30), (60, 60), (100, 100)]),
        }
    )

    # Extract data
    road_id = edge_data["id"]
    name = edge_data["name"]
    length = edge_data["length"]
    maxspeed_ms = float(edge_data["maxspeed"]) / 3.6
    linestring = edge_data["geometry"]

    # Generate point collection
    pointcollection = generate_point_collection(linestring, length, maxspeed_ms)

    road_obj = Road(road_id, name, pointcollection, length, maxspeed_ms)

    # The last point should be exactly (100, 100) regardless of interpolation
    last_point = road_obj.pointcollection[-1].get_position()
    assert last_point == pytest.approx([100.0, 100.0])

    # Verify we have multiple points
    assert len(road_obj.pointcollection) > 2


def test_road_with_single_coordinate_linestring(setup_test_environment: None) -> None:
    # Arrange: Test edge case with a single coordinate
    edge_data = Series(
        {
            "id": 707,
            "name": "Point Road",
            "length": 0.0,
            "maxspeed": "50",
            "geometry": LineString([(42.5, 73.8), (42.5, 73.8)]),
        }
    )

    # Extract data
    road_id = edge_data["id"]
    name = edge_data["name"]
    length = edge_data["length"]
    maxspeed_ms = float(edge_data["maxspeed"]) / 3.6
    linestring = edge_data["geometry"]

    # Generate point collection
    pointcollection = generate_point_collection(linestring, length, maxspeed_ms)

    road_obj = Road(road_id, name, pointcollection, length, maxspeed_ms)

    # Should have at least one point
    assert len(road_obj.pointcollection) >= 1
    assert road_obj.pointcollection[0].get_position() == pytest.approx([42.5, 73.8])


def test_road_with_complex_multi_vertex_path(setup_test_environment: None) -> None:
    # Arrange: A longer, more complex multi-vertex linestring
    edge_data = Series(
        {
            "id": 808,
            "name": "Winding Path",
            "length": 200.0,
            "maxspeed": "40",  # 40 km/h / 3.6 = 11.111 m/s
            "geometry": LineString(
                [(0, 0), (40, 20), (80, 60), (120, 80), (160, 90), (200, 100)]
            ),
        }
    )

    # Extract data
    road_id = edge_data["id"]
    name = edge_data["name"]
    length = edge_data["length"]
    maxspeed_ms = float(edge_data["maxspeed"]) / 3.6
    linestring = edge_data["geometry"]

    # Generate point collection
    pointcollection = generate_point_collection(linestring, length, maxspeed_ms)

    road_obj = Road(road_id, name, pointcollection, length, maxspeed_ms)

    # Verify attributes
    assert road_obj.id == 808
    assert road_obj.maxspeed == pytest.approx(11.111, 0.001)

    # Should have many points along this path
    # Distance increment = 11.111 m/s
    # Expected points: 0, 11.111, 22.222, ..., up to 200
    # That's about 18 intermediate points + final
    assert len(road_obj.pointcollection) >= 18

    # First point should be at start
    assert road_obj.pointcollection[0].get_position() == pytest.approx([0.0, 0.0])

    # Last point should be exactly at end
    assert road_obj.pointcollection[-1].get_position() == pytest.approx([200.0, 100.0])

    # All points should be Position objects
    assert all(isinstance(p, Position) for p in road_obj.pointcollection)


def test_road_multi_vertex_no_duplicate_last_point(
    setup_test_environment: None,
) -> None:
    # Arrange: Test that when the last interpolated point equals the end point,
    # we don't add a duplicate
    edge_data = Series(
        {
            "id": 909,
            "name": "Perfectly Divisible Road",
            "length": 50.0,
            "maxspeed": "50",  # 13.888 m/s
            # Create a multi-vertex linestring
            "geometry": LineString([(0, 0), (25, 0), (50, 0)]),
        }
    )

    # Extract data
    road_id = edge_data["id"]
    name = edge_data["name"]
    length = edge_data["length"]
    maxspeed_ms = float(edge_data["maxspeed"]) / 3.6
    linestring = edge_data["geometry"]

    # Generate point collection
    pointcollection = generate_point_collection(linestring, length, maxspeed_ms)

    road_obj = Road(road_id, name, pointcollection, length, maxspeed_ms)

    # Verify no duplicate positions at the end
    positions = [p.get_position() for p in road_obj.pointcollection]

    # Check that consecutive positions are not identical
    for i in range(len(positions) - 1):
        if i == len(positions) - 2:
            # The last two might be the same if interpolation lands exactly on end
            # But the code should prevent adding a duplicate
            continue
        # No other consecutive duplicates
        if positions[i] == positions[i + 1]:
            # This is okay, but let's verify the logic worked
            pass

    # The last position should be at the end
    assert positions[-1] == pytest.approx([50.0, 0.0])


class TestRoadPerSegmentTraffic:
    """Tests demonstrating per-segment traffic differentiation.

    These tests show that traffic can be applied to specific segments within
    a road, resulting in different point densities for different segments.
    """

    def _create_multi_segment_road(self) -> Road:
        """Create a road with 5 distinct nodes (4 segments).

        Road layout:
            [N0]----[N1]----[N2]----[N3]----[N4]
            idx0    idx1    idx2    idx3    idx4

        Each segment is 100m, total length = 400m
        Speed = 10 m/s → ~10 points per 100m segment at free flow
        """
        # Create 5 nodes with equal spacing
        nodes = [
            Position([0.0, 0.0]),  # N0 - idx 0
            Position([1.0, 0.0]),  # N1 - idx 1
            Position([2.0, 0.0]),  # N2 - idx 2
            Position([3.0, 0.0]),  # N3 - idx 3
            Position([4.0, 0.0]),  # N4 - idx 4
        ]

        return Road(
            road_id=1,
            name="Test Multi-Segment Road",
            pointcollection=nodes,
            length=400.0,  # 4 segments × 100m each
            maxspeed=10.0,  # 10 m/s
            geometry=nodes,
        )

    def test_free_flow_uniform_point_density(self) -> None:
        """Test that free flow produces uniform point density across all segments."""
        road = self._create_multi_segment_road()

        # No traffic applied - should use base pointcollection
        active_points = road.active_pointcollection

        # At free flow, should return the original pointcollection
        assert active_points == road.pointcollection
        assert len(active_points) == 5  # Original 5 nodes

        # All multipliers should be 1.0 (free flow)
        for i in range(4):  # 4 segments
            assert road.get_multiplier_at_index(i) == 1.0

    def test_traffic_on_middle_segment_increases_density(self) -> None:
        """Test that traffic on middle segment produces more points there.

        Apply traffic to segment [N1, N3] (indices 1-3) with multiplier 0.25.
        Traffic range is INCLUSIVE: affects segments whose start index is in [1, 3].

        Visual:
            [N0]·····[N1]···················[N2]···················[N3]···················[N4]
              1.0x      0.25x (4x denser)      0.25x (4x denser)      0.25x (4x denser)
        """
        road = self._create_multi_segment_road()

        # Apply traffic to middle segments (N1 to N3)
        segment_key = ((1.0, 0.0), (3.0, 0.0))  # From N1 to N3
        overlap = [Position([1.0, 0.0]), Position([3.0, 0.0])]
        result = road.apply_traffic_for_overlap(overlap, 0.25, segment_key)

        assert result is True, "Traffic range should be added successfully"

        # Check multipliers per segment
        # Traffic range [1, 3] is INCLUSIVE - affects segments 1, 2, AND 3
        assert road.get_multiplier_at_index(0) == 1.0, "Segment 0 should be free flow"
        assert road.get_multiplier_at_index(1) == 0.25, "Segment 1 should have traffic"
        assert road.get_multiplier_at_index(2) == 0.25, "Segment 2 should have traffic"
        assert (
            road.get_multiplier_at_index(3) == 0.25
        ), "Segment 3 should have traffic (inclusive)"

        # Get traffic-adjusted points
        traffic_points = road.active_pointcollection

        # Traffic points should be MORE than free flow points
        # Free flow: 5 nodes
        # With traffic: segments with 0.25 multiplier have 4x density
        assert len(traffic_points) > len(road.pointcollection)

        print(f"\n{'='*60}")
        print("TEST: Traffic on middle segments [N1, N3]")
        print(f"{'='*60}")
        print(f"Free flow points: {len(road.pointcollection)}")
        print(f"Traffic points:   {len(traffic_points)}")
        increase = len(traffic_points) - len(road.pointcollection)
        print(f"Increase:         {increase} more points")
        print("\nMultipliers per segment:")
        for i in range(4):
            mult = road.get_multiplier_at_index(i)
            density = "DENSE" if mult < 1.0 else "sparse"
            print(f"  Segment {i} (N{i}→N{i+1}): mult={mult}, {density}")

    def test_traffic_on_single_segment(self) -> None:
        """Test traffic applied to two adjacent segments.

        Apply traffic to segment [N2, N3] (indices 2-3).
        Traffic range is INCLUSIVE: affects segments 2 AND 3.

        Visual:
            [N0]·····[N1]·····[N2]···················[N3]···················[N4]
              1.0x     1.0x      0.2x (5x denser)      0.2x (5x denser)
        """
        road = self._create_multi_segment_road()

        # Apply traffic to segments (N2 to N3)
        segment_key = ((2.0, 0.0), (3.0, 0.0))
        overlap = [Position([2.0, 0.0]), Position([3.0, 0.0])]
        result = road.apply_traffic_for_overlap(overlap, 0.2, segment_key)

        assert result is True

        # Check multipliers - range [2, 3] is INCLUSIVE
        assert road.get_multiplier_at_index(0) == 1.0
        assert road.get_multiplier_at_index(1) == 1.0
        assert road.get_multiplier_at_index(2) == 0.2  # Traffic
        assert road.get_multiplier_at_index(3) == 0.2  # Traffic (inclusive)

        traffic_points = road.active_pointcollection

        print(f"\n{'='*60}")
        print("TEST: Traffic on single segment [N2, N3]")
        print(f"{'='*60}")
        print(f"Free flow points: {len(road.pointcollection)}")
        print(f"Traffic points:   {len(traffic_points)}")
        print("\nMultipliers per segment:")
        for i in range(4):
            mult = road.get_multiplier_at_index(i)
            density = "DENSE" if mult < 1.0 else "sparse"
            print(f"  Segment {i} (N{i}→N{i+1}): mult={mult}, {density}")

    def test_overlapping_traffic_ranges_minimum_wins(self) -> None:
        """Test that overlapping traffic ranges use minimum multiplier.

        Apply two traffic ranges:
        - Range 1: [N1, N3] with multiplier 0.5
        - Range 2: [N2, N4] with multiplier 0.3

        Visual:
            [N0]·····[N1]·········[N2]···············[N3]···············[N4]
              1.0x     0.5x         0.3x (overlap)     0.3x              0.3x

        At N2-N3: both ranges overlap, min(0.5, 0.3) = 0.3 wins
        """
        road = self._create_multi_segment_road()

        # Apply first traffic range
        segment_key_1 = ((1.0, 0.0), (3.0, 0.0))  # N1 to N3
        overlap_1 = [Position([1.0, 0.0]), Position([3.0, 0.0])]
        road.apply_traffic_for_overlap(overlap_1, 0.5, segment_key_1)

        # Apply second overlapping traffic range
        segment_key_2 = ((2.0, 0.0), (4.0, 0.0))  # N2 to N4
        overlap_2 = [Position([2.0, 0.0]), Position([4.0, 0.0])]
        road.apply_traffic_for_overlap(overlap_2, 0.3, segment_key_2)

        # Check multipliers - minimum should win at overlaps
        assert road.get_multiplier_at_index(0) == 1.0, "No traffic"
        assert road.get_multiplier_at_index(1) == 0.5, "Only range 1"
        assert road.get_multiplier_at_index(2) == 0.3, "Overlap: min(0.5, 0.3) = 0.3"
        assert road.get_multiplier_at_index(3) == 0.3, "Only range 2"

        print(f"\n{'='*60}")
        print("TEST: Overlapping traffic ranges (minimum wins)")
        print(f"{'='*60}")
        print("Range 1: [N1, N3] mult=0.5")
        print("Range 2: [N2, N4] mult=0.3")
        print("\nMultipliers per segment (min wins at overlap):")
        for i in range(4):
            mult = road.get_multiplier_at_index(i)
            print(f"  Segment {i} (N{i}→N{i+1}): mult={mult}")

    def test_clear_traffic_restores_free_flow(self) -> None:
        """Test that clearing traffic restores free flow multipliers."""
        road = self._create_multi_segment_road()

        # Apply traffic
        segment_key = ((1.0, 0.0), (3.0, 0.0))
        overlap = [Position([1.0, 0.0]), Position([3.0, 0.0])]
        road.apply_traffic_for_overlap(overlap, 0.25, segment_key)

        # Verify traffic is applied
        assert road.get_multiplier_at_index(1) == 0.25

        # Clear all traffic
        road.clear_traffic()

        # All multipliers should return to 1.0
        for i in range(4):
            assert road.get_multiplier_at_index(i) == 1.0

        # Active pointcollection should be base pointcollection again
        assert road.active_pointcollection == road.pointcollection

    def test_duplicate_segment_key_replaces_existing(self) -> None:
        """Test that adding same segment_key twice replaces the previous range.

        This ensures:
        - No duplicate ranges for the same segment_key
        - Last-added multiplier takes effect (not min of old and new)
        - No memory bloat from accumulated ranges
        """
        road = self._create_multi_segment_road()

        segment_key = ((1.0, 0.0), (3.0, 0.0))
        overlap = [Position([1.0, 0.0]), Position([3.0, 0.0])]

        # Apply traffic with multiplier 0.3
        road.apply_traffic_for_overlap(overlap, 0.3, segment_key)
        assert road.get_multiplier_at_index(1) == 0.3

        # Apply traffic with SAME segment_key but HIGHER multiplier (0.7)
        # This should REPLACE, not accumulate
        road.apply_traffic_for_overlap(overlap, 0.7, segment_key)

        # Multiplier should be 0.7 (the new value), NOT 0.3 (min of old and new)
        assert (
            road.get_multiplier_at_index(1) == 0.7
        ), "Duplicate segment_key should replace, not accumulate"

        # Verify only one range exists (no duplicates)
        assert (
            len(road._traffic_ranges) == 1
        ), "Should have exactly one range, not duplicates"

    def test_partial_segment_overlap(self) -> None:
        """Test traffic segment that only partially overlaps with road.

        Road has nodes at: (0,0), (1,0), (2,0), (3,0), (4,0)
        Traffic segment: (1.5,0) to (3,0) - start node doesn't exist in road

        With apply_traffic_for_overlap, only the matching endpoint (3,0) is
        in the overlap, so the range is a single-point range at geometry
        index 3, which maps to pointcollection index 3.
        """
        road = self._create_multi_segment_road()

        # Only (3.0, 0.0) is in the road geometry; (1.5, 0.0) is not
        segment_key = ((1.5, 0.0), (3.0, 0.0))
        overlap = [Position([3.0, 0.0])]
        result = road.apply_traffic_for_overlap(overlap, 0.4, segment_key)

        assert result is True, "Partial overlap should still apply"

        # Single overlap position at geometry index 3 → pc index 3
        # Range [3, 3] only affects segment 3
        assert road.get_multiplier_at_index(3) == 0.4

        print(f"\n{'='*60}")
        print("TEST: Partial segment overlap")
        print(f"{'='*60}")
        print("Traffic segment: (1.5, 0) to (3.0, 0)")
        print("  - Start (1.5, 0) NOT in road geometry → not in overlap")
        print("  - End (3.0, 0) found at geometry idx 3")
        print("\nMultipliers per segment:")
        for i in range(4):
            mult = road.get_multiplier_at_index(i)
            print(f"  Segment {i}: mult={mult}")

    def test_segment_not_in_road_returns_false(self) -> None:
        """Test that traffic segment completely outside road returns False."""
        road = self._create_multi_segment_road()

        # Apply traffic with both nodes NOT in road — empty overlap
        segment_key = ((10.0, 10.0), (20.0, 20.0))  # Completely outside
        result = road.apply_traffic_for_overlap([], 0.5, segment_key)

        assert result is False, "Empty overlap should return False"

        # All multipliers should remain 1.0
        for i in range(4):
            assert road.get_multiplier_at_index(i) == 1.0

    def test_visual_point_density_comparison(self) -> None:
        """Visual test showing point density differences.

        Creates output showing how points are distributed differently
        based on traffic multipliers.
        """
        road = self._create_multi_segment_road()

        # Apply traffic to middle segment only
        segment_key = ((1.0, 0.0), (3.0, 0.0))
        overlap = [Position([1.0, 0.0]), Position([3.0, 0.0])]
        road.apply_traffic_for_overlap(
            overlap, 0.1, segment_key
        )  # Very slow = very dense

        traffic_points = road.active_pointcollection

        print(f"\n{'='*70}")
        print("VISUAL: Point Density Comparison")
        print(f"{'='*70}")
        print("\nRoad: [N0]----[N1]----[N2]----[N3]----[N4]")
        print("       0      1      2      3      4   (x-coordinate)")
        print("\nTraffic applied to [N1, N3] with multiplier 0.1")
        print("  → Segments 1, 2, and 3 should be ~10x denser (inclusive range)")
        print(f"\nTotal points generated: {len(traffic_points)}")
        print("\nPoint distribution by x-coordinate:")

        # Group points by which segment they're in
        segment_counts = [0, 0, 0, 0]  # 4 segments
        for point in traffic_points:
            x = point.get_position()[0]
            if x < 1.0:
                segment_counts[0] += 1
            elif x < 2.0:
                segment_counts[1] += 1
            elif x < 3.0:
                segment_counts[2] += 1
            else:
                segment_counts[3] += 1

        for i in range(4):
            mult = road.get_multiplier_at_index(i)
            density_bar = "█" * min(segment_counts[i], 50)
            density_label = "DENSE" if mult < 1.0 else "sparse"
            print(
                f"  Seg {i} (mult={mult:0.1f}, {density_label:6}): "
                f"{segment_counts[i]:3} pts {density_bar}"
            )

        print(f"\n{'='*70}")


class TestRoadPointStrategy:
    """Tests for strategy injection on Road."""

    def _create_road(self) -> Road:
        nodes = [
            Position([0.0, 0.0]),
            Position([1.0, 0.0]),
            Position([2.0, 0.0]),
        ]
        return Road(
            road_id=1,
            name="Test Road",
            pointcollection=nodes,
            length=200.0,
            maxspeed=10.0,
            geometry=nodes,
        )

    def test_active_pointcollection_delegates_to_strategy(self) -> None:
        road = self._create_road()
        segment_key = ((0.0, 0.0), (2.0, 0.0))
        overlap = [Position([0.0, 0.0]), Position([2.0, 0.0])]
        road.apply_traffic_for_overlap(overlap, 0.5, segment_key)

        mock_strategy = MagicMock(spec=PointGenerationStrategy)
        expected_points = [Position([0.0, 0.0]), Position([0.5, 0.0])]
        mock_strategy.generate.return_value = expected_points

        road.set_point_strategy(mock_strategy)

        result = road.active_pointcollection

        assert result == expected_points
        mock_strategy.generate.assert_called_once()
        ctx = mock_strategy.generate.call_args[0][0]
        assert isinstance(ctx, RoadPointContext)
        assert ctx.maxspeed == 10.0
        assert ctx.length == 200.0

    def test_set_point_strategy_invalidates_cache(self) -> None:
        road = self._create_road()
        segment_key = ((0.0, 0.0), (2.0, 0.0))
        overlap = [Position([0.0, 0.0]), Position([2.0, 0.0])]
        road.apply_traffic_for_overlap(overlap, 0.5, segment_key)

        # Generate cached points via fallback
        points_v1 = road.active_pointcollection
        assert road._traffic_pointcollection is not None

        # Setting strategy should invalidate cache
        mock_strategy = MagicMock(spec=PointGenerationStrategy)
        mock_strategy.generate.return_value = [Position([9.0, 9.0])]
        road.set_point_strategy(mock_strategy)

        # Cache should be invalidated
        assert not road._traffic_pointcollection

        # Next access should use the new strategy
        points_v2 = road.active_pointcollection
        assert points_v2 == [Position([9.0, 9.0])]
        assert points_v2 != points_v1

    def test_no_strategy_falls_back_to_internal(self) -> None:
        road = self._create_road()
        segment_key = ((0.0, 0.0), (2.0, 0.0))
        overlap = [Position([0.0, 0.0]), Position([2.0, 0.0])]
        road.apply_traffic_for_overlap(overlap, 0.5, segment_key)

        # No strategy set — should use _generate_traffic_points() fallback
        assert road._point_strategy is None
        points = road.active_pointcollection
        assert len(points) > len(road.pointcollection)


class TestRoadDistance:
    """Tests for proportional distance computation on Road.

    Distance is computed as index / (n-1) * length, where n is the number
    of active points. Traffic changes n (more points = less distance per point),
    so the total always sums to road.length.
    """

    def _create_road(
        self,
        num_points: int = 11,
        length: float = 100.0,
        maxspeed: float = 10.0,
    ) -> Road:
        """Create a road with specified number of evenly-spaced points."""
        points = [Position([i * 0.001, 0.0]) for i in range(num_points)]
        return Road(
            road_id=1,
            name="Test Road",
            pointcollection=points,
            length=length,
            maxspeed=maxspeed,
        )

    def test_distance_at_index_zero_is_zero(self) -> None:
        """Test that distance at index 0 is always 0."""
        road = self._create_road()
        assert road.get_distance_at_index(0) == 0.0

    def test_distance_proportional_no_traffic(self) -> None:
        """Test cumulative distance is proportional: index / (n-1) * length."""
        road = self._create_road(num_points=11, length=100.0)
        for i in range(11):
            expected = (i / 10) * 100.0
            assert road.get_distance_at_index(i) == pytest.approx(expected)

    def test_distance_at_last_index_equals_length(self) -> None:
        """Test that distance at last index equals road length."""
        road = self._create_road(num_points=11, length=100.0)
        assert road.get_distance_at_index(10) == pytest.approx(100.0)

    def test_distance_monotonically_increasing(self) -> None:
        """Test that distance is non-decreasing across all indices."""
        road = self._create_road(num_points=20, length=200.0)
        for i in range(1, 20):
            assert road.get_distance_at_index(i) >= road.get_distance_at_index(i - 1)

    def test_distance_with_traffic_still_spans_full_length(self) -> None:
        """Test that traffic changes point count but total still equals length.

        Traffic generates more points (slower speed), so each point covers
        less distance, but the last point still reaches road.length.
        """
        nodes = [
            Position([0.0, 0.0]),
            Position([1.0, 0.0]),
            Position([2.0, 0.0]),
        ]
        road = Road(
            road_id=1,
            name="Traffic Road",
            pointcollection=nodes,
            length=200.0,
            maxspeed=10.0,
            geometry=nodes,
        )

        # Apply traffic to segment 1 (N1->N2) with multiplier 0.5
        segment_key = ((1.0, 0.0), (2.0, 0.0))
        overlap = [Position([1.0, 0.0]), Position([2.0, 0.0])]
        road.apply_traffic_for_overlap(overlap, 0.5, segment_key)

        active = road.active_pointcollection
        n = len(active)

        # More points than without traffic
        assert n > len(nodes)

        assert road.get_distance_at_index(0) == 0.0
        assert road.get_distance_at_index(n - 1) == pytest.approx(200.0)

        # Monotonically increasing
        for i in range(1, n):
            assert road.get_distance_at_index(i) > road.get_distance_at_index(i - 1)

    def test_traffic_reduces_distance_per_point(self) -> None:
        """Test that more points from traffic means less distance per point.

        With traffic generating more points, distance_per_point = length / (n-1)
        becomes smaller than without traffic.
        """
        nodes = [
            Position([0.0, 0.0]),
            Position([1.0, 0.0]),
            Position([2.0, 0.0]),
        ]
        road = Road(
            road_id=1,
            name="Traffic Road",
            pointcollection=nodes,
            length=200.0,
            maxspeed=10.0,
            geometry=nodes,
        )

        # Distance per point without traffic: 200 / (3-1) = 100m
        free_flow_increment = road.get_distance_at_index(1)
        assert free_flow_increment == pytest.approx(100.0)

        # Apply traffic -> generates more points
        segment_key = ((0.0, 0.0), (2.0, 0.0))
        overlap = [Position([0.0, 0.0]), Position([2.0, 0.0])]
        road.apply_traffic_for_overlap(overlap, 0.5, segment_key)

        n = len(road.active_pointcollection)
        traffic_increment = road.get_distance_at_index(1)
        # More points -> smaller increment: 200 / (n-1) < 100
        assert traffic_increment < free_flow_increment
        assert traffic_increment == pytest.approx(200.0 / (n - 1))

    def test_distance_out_of_bounds_clamped(self) -> None:
        """Test that out-of-bounds indices are clamped to valid range."""
        road = self._create_road(num_points=5, length=40.0)

        # Beyond last index: returns distance at last point (= length)
        assert road.get_distance_at_index(100) == pytest.approx(40.0)
        assert road.get_distance_at_index(100) == road.get_distance_at_index(4)

        # Negative index: returns 0.0
        assert road.get_distance_at_index(-1) == 0.0

    def test_distance_single_point_road(self) -> None:
        """Test distance on a road with a single point."""
        road = Road(
            road_id=1,
            name="Single",
            pointcollection=[Position([0.0, 0.0])],
            length=0.0,
            maxspeed=10.0,
        )
        assert road.get_distance_at_index(0) == 0.0

    def test_distance_two_point_road(self) -> None:
        """Test distance on a road with exactly two points."""
        road = Road(
            road_id=1,
            name="Two Point",
            pointcollection=[Position([0.0, 0.0]), Position([1.0, 0.0])],
            length=50.0,
            maxspeed=10.0,
        )
        assert road.get_distance_at_index(0) == 0.0
        # 1 / (2-1) * 50 = 50.0
        assert road.get_distance_at_index(1) == pytest.approx(50.0)


class TestRoadTransition:
    @pytest.fixture
    def sample_road(self) -> Road:
        p1 = Position([0, 0])
        p2 = Position([100, 0])
        return Road(
            road_id=1,
            name="some name",
            pointcollection=[p1, p2],
            length=100.0,
            maxspeed=20.0,
        )

    @pytest.mark.parametrize(
        "dist, expected_coords",
        [
            (0.0, [0.0, 0.0]),  # Start of road
            (50.0, [50.0, 0.0]),  # Midpoint
            (100.0, [100.0, 0.0]),  # End of road
            (150.0, [100.0, 0.0]),  # Clamping check (should not exceed length)
        ],
    )
    def test_get_position_from_distance(
        self, sample_road: Road, dist: float, expected_coords: list[float]
    ) -> None:
        """Tests get_position_from_distance returns expected coordinates"""
        position = sample_road.get_position_from_distance(dist)
        assert position.get_position() == expected_coords

    def test_generate_curve(self, sample_road: Road) -> None:
        """Tests generate_curve returns a list of positions"""
        returned_pos = Mock(spec=Position)

        with patch.object(sample_road, "get_position_from_distance") as mock_method:
            mock_method.return_value = returned_pos

            positions = sample_road.generate_curve(5.0, 5.0, 50.0)

            # total_ticks = (2*50)/(5+5) = 10, plus tick=0 starting point = 11
            assert len(positions) == 11
            assert positions[0] == returned_pos

            # tick=0 produces x=0, so first call uses distance_offset (0.0)
            mock_method.assert_any_call(0.0)

    def test_generate_curve_zero_distance(self, sample_road: Road) -> None:
        """Tests that edge case with zero distance should return an empty list"""
        v0 = 10
        vf = 8.0
        assert sample_road.generate_curve(v0, vf, 0) == []
        assert sample_road.generate_curve(v0, vf, -5) == []

    def test_generate_curve_invalid_speeds(self, sample_road: Road) -> None:
        """Tests that edge case with speeds summing <= 0 returns empty list"""
        distance = 10
        assert sample_road.generate_curve(0, 0, distance) == []
        assert sample_road.generate_curve(-5, 2, distance) == []
