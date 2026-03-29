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

from sim.osm.stop_sign_index import StopSignIndex


def test_find_near_route_returns_points_within_tolerance() -> None:
    index = StopSignIndex(
        stop_sign_coordinates=[
            [-73.5700, 45.5000],
            [-73.5705, 45.5005],
            [-73.5900, 45.5200],
        ]
    )

    route = [
        [-73.5702, 45.5001],
        [-73.5708, 45.5008],
    ]

    result = index.find_near_route(route, tolerance_degrees=0.00035)
    result_set = {(c[0], c[1]) for c in result}

    assert (-73.57, 45.5) not in result_set
    assert (-73.5705, 45.5005) in result_set
    assert (-73.59, 45.52) not in result_set


def test_find_near_route_deduplicates_duplicate_coordinates() -> None:
    index = StopSignIndex(
        stop_sign_coordinates=[
            [-73.57, 45.5],
            [-73.57, 45.5],
        ]
    )

    route = [
        [-73.5710, 45.5000],
        [-73.5690, 45.5000],
    ]

    result = index.find_near_route(route, tolerance_degrees=0.001)

    assert len(result) == 1
    assert result[0] == [-73.57, 45.5]
