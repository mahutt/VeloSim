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

import numpy as np
from pandas import Series
from shapely.geometry import LineString
from .position import Position
import json


class road:
    def __init__(self, edge: Series):
        # Store essential attributes
        self.id: int = edge["id"]
        self.name: str = edge["name"]
        self.length: float = edge["length"]  # Length in meters

        # Load settings from config file
        with open("config.json", "r") as f:
            config = json.load(f)
        conversion_factor = config["simulation"]["kmh_to_ms_factor"]

        # Try to get the max speed of the road; use default if not available
        try:
            self.maxspeed: float = int(edge["maxspeed"]) / conversion_factor
        except (ValueError, TypeError, KeyError):
            default_speed_kmh = config["simulation"]["map_rules"]["roads"][
                "default_road_max_speed"
            ]
            # Ensure default speed is also converted from km/h to m/s
            self.maxspeed = default_speed_kmh / conversion_factor

        # Get the road's geometry
        linestring: LineString = edge["geometry"]

        # generate the points for this road and store them
        self.pointcollection: list[Position] = self._generate_point_collection(
            linestring
        )

    def _generate_point_collection(self, linestring: LineString) -> list[Position]:
        """
        Generates a list of Position objects along the road's geometry based on
        the road's max speed.
        """
        points = []
        if self.maxspeed > 0 and self.length > 0:  # Edge Case

            # Distance traveled in one second (distance_increment) ~ ds.
            distance_increment = self.maxspeed

            # Logic: Space out the points via the delta
            # (distance_increment), within range of the length.
            for distance in np.arange(0, self.length, distance_increment):
                point = linestring.interpolate(float(distance))
                # ensure we are staying on the path
                # via interpolating on the line segement.
                points.append(Position([point.x, point.y]))
                # Apply the new position in a position object.

            # Always include the exact
            # last point of the road segment (for intersection later)
            last_coord = linestring.coords[-1]
            points.append(Position([last_coord[0], last_coord[1]]))
        else:
            # If speed or length is 0,
            # we fall back to the start and end points.
            points = [Position(list(coord)) for coord in linestring.coords]

        return points
