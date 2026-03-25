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

from sim.entities.map_payload import MapPayload
from sim.entities.position import Position
from sim.entities.route import Route
from sim.map.routing_provider import RoutingProvider
from sim.osm.graphhopper_adapter import GraphHopperAdapter
from sim.map.route_controller import RouteController
from sim.traffic.traffic_controller import TrafficController
from sim.map.position_registry import PositionRegistry
from typing import Optional
import json
import os
from pathlib import Path


class MapController:
    """Map controller for routing operations.

    Provides routing services through a RoutingProvider interface,
    allowing different routing backends to be used.
    """

    def __init__(
        self,
        map_payload: Optional[MapPayload] = None,
    ) -> None:
        """Initialize the MapController with a routing provider.

        Sets up the routing provider for routing operations and initializes
        the RouteController for road/route management.

        GraphHopper profile is controlled by GRAPHHOPPER_COSTING environment
        variable (default: "car"). Options: car, bike, foot, etc.

        Args:
            map_payload: Optional MapPayload containing traffic
                configuration and other map-related settings.
        """
        # Initialize the routing provider
        self.map_payload = map_payload
        sim_id = map_payload.sim_id if map_payload else ""
        graphhopper_profile = os.getenv("GRAPHHOPPER_COSTING", "car")
        self.routing_provider: RoutingProvider = GraphHopperAdapter(
            sim_id=sim_id,
            profile=graphhopper_profile,
        )

        # Load config once for all routes
        config_path = Path(__file__).parent.parent / "config.json"
        with open(config_path, "r") as f:
            self.config = json.load(f)

        # Extract config from payload
        traffic_config = map_payload.traffic if map_payload else None
        env = map_payload.env if map_payload else None
        report = map_payload.report if map_payload else None

        # Create shared PositionRegistry
        self.position_registry = PositionRegistry()

        # Initialize RouteController for road/route management
        self.route_controller = RouteController(
            self,
            registry=self.position_registry,
            report=report,
            map_payload=map_payload,
        )

        # Initialize TrafficController for traffic layer management
        self.traffic_controller = TrafficController(
            self.route_controller,
            traffic_config=traffic_config,
            env=env,
            routing_provider=self.routing_provider,
            registry=self.position_registry,
        )

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
            a, b, self.routing_provider, self.config
        )

    def close(self) -> None:
        """Clean up routing provider resources.

        Returns:
            None
        """
        if self.routing_provider:
            self.routing_provider.close()
