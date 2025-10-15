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
            "map_rules": {"roads": {"default_road_max_speed": 30}},
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
    # Default is 30 km/h / 3.6 = 8.333 m/s
    assert road_obj.maxspeed == pytest.approx(8.333, 0.001)

    # Check point collection logic with default speed
    # Expected points: at 0, 8.33, ..., 75.0 (10 points) + the final point (80, 0)
    assert len(road_obj.pointcollection) == 11
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
