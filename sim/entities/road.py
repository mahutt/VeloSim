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
from pathlib import Path


class road:
    def __init__(self, edge: Series):
        # Store essential attributes
        self.id: int = edge["id"]
        self.name: str = edge["name"]
        self.length: float = edge["length"]  # Length in meters

        # Load settings from config file
        config_path = Path(__file__).parent.parent / "config.json"
        with open(config_path, "r") as f:
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
        Generates a list of Position objects along the road's geometry.
        Points represent where the vehicle will be at each second of travel time.
        Spacing is determined by the road's max speed: faster roads = larger spacing.
        """
        points: list[Position] = []
        if self.maxspeed > 0 and self.length > 0:  # Edge Case

            # Distance traveled in one second at this road's max speed
            distance_increment = self.maxspeed  # meters per second

            # Get the coordinates of the linestring
            coords = list(linestring.coords)

            # If it's a simple 2-point line, manually interpolate
            if len(coords) == 2:
                start_x, start_y = coords[0]
                end_x, end_y = coords[1]

                # Calculate number of seconds needed to traverse this road
                time_seconds = self.length / self.maxspeed
                num_points = int(np.ceil(time_seconds)) + 1

                # Generate points for each second of travel
                for i in range(num_points):
                    # Distance traveled after i seconds
                    distance = min(i * distance_increment, self.length)

                    # Linear interpolation parameter (0 to 1)
                    t = distance / self.length

                    # Interpolate position
                    x = float(start_x + t * (end_x - start_x))
                    y = float(start_y + t * (end_y - start_y))

                    new_position = Position([x, y])

                    # Only add if it's different from
                    # the last position (avoid duplicates)
                    if (
                        not points
                        or points[-1].get_position() != new_position.get_position()
                    ):
                        points.append(new_position)
            else:
                # For multi-vertex linestrings, use shapely's interpolate
                for dist in np.arange(0, self.length, distance_increment):
                    distance = float(dist)
                    point = linestring.interpolate(distance)
                    # Convert to native Python float to avoid numpy types
                    new_position = Position([float(point.x), float(point.y)])
                    # Only add if it's different from the last position
                    # (avoid duplicates)
                    if (
                        not points
                        or points[-1].get_position() != new_position.get_position()
                    ):
                        points.append(new_position)
                # Always include the exact last point of the road segment
                # (for intersection later)
                last_coord = linestring.coords[-1]
                last_position = Position([float(last_coord[0]), float(last_coord[1])])

                # Only add if different from the last position
                if (
                    not points
                    or points[-1].get_position() != last_position.get_position()
                ):
                    points.append(last_position)
            # If we ended up with no points (very short road),
            # add at least start and end
            if len(points) == 0:
                first_coord = linestring.coords[0]
                points.append(Position([float(first_coord[0]), float(first_coord[1])]))
                last_coord = linestring.coords[-1]
                if first_coord != last_coord:
                    points.append(
                        Position([float(last_coord[0]), float(last_coord[1])])
                    )
        else:
            # If speed or length is 0, we fall back to start and end points.
            # For zero-length roads, we keep both points even if identical
            # to maintain the start/end point structure.
            coords_list = list(linestring.coords)
            if len(coords_list) >= 2:
                # Add start point
                first_coord = coords_list[0]
                points.append(Position([float(first_coord[0]), float(first_coord[1])]))
                # Add end point (even if same as start)
                last_coord = coords_list[-1]
                points.append(Position([float(last_coord[0]), float(last_coord[1])]))
            elif len(coords_list) == 1:
                # Edge case: single coordinate
                coord = coords_list[0]
                points.append(Position([float(coord[0]), float(coord[1])]))

        return points
