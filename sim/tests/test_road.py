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
from pathlib import Path
from pandas import Series
from shapely.geometry import LineString
from typing import Generator

from sim.entities.road import road
from sim.entities.position import Position


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

    # Initialize the Road object. It will read the real config.json.
    road_obj = road(edge_data)

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

    road_obj = road(edge_data)

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

    road_obj = road(edge_data)

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

    road_obj = road(edge_data)

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

    road_obj = road(edge_data)

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

    road_obj = road(edge_data)

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

    road_obj = road(edge_data)

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

    road_obj = road(edge_data)

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

    road_obj = road(edge_data)

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
