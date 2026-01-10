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

from sim.entities.position import Position
from sim.entities.route import Route
from sim.osm.OSRMConnection import OSRMConnection
from sim.map.route_controller import RouteController
from typing import Optional
import json
from pathlib import Path


class MapController:
    """Map controller using OSRM for routing.

    This uses OSRM instead of local graph-based routing.
    """

    def __init__(self, osrm_url: Optional[str] = None) -> None:
        """Initialize the MapController with OSRM routing.

        Sets up the OSRM connection for routing operations and initializes
        the RouteController for road/route management.

        Args:
            osrm_url: Optional URL for the OSRM server. If not provided,
                will use environment variables to determine the server.
        """
        # Initialize the OSRM connection
        self.osrm = OSRMConnection(osrm_url=osrm_url)

        # Load config once for all routes
        config_path = Path(__file__).parent.parent / "config.json"
        with open(config_path, "r") as f:
            self.config = json.load(f)

        # Initialize RouteController for road/route management
        self.route_controller = RouteController(self)

    def get_route(self, a: Position, b: Position) -> Route:
        """
        Create a route between two positions.

        Delegates entirely to RouteController.

        Args:
            a: Starting position
            b: Ending position

        Returns:
            Route: A new Route object

        Raises:
            ValueError: If no route can be found
        """
        return self.route_controller.get_route_from_positions(
            a, b, self.osrm, self.config
        )
