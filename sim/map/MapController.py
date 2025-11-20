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
from sim.entities.osrm_result import OSRMResult
from sim.osm.OSRMConnection import OSRMConnection
from typing import Dict, List, Set, Any, Optional


class MapController:
    """Map controller using OSRM for routing.

    This uses OSRM instead of local graph-based routing.
    """

    _instance = None

    def __new__(cls, *args: Any, **kwargs: Any) -> "MapController":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, osrm_url: Optional[str] = None) -> None:
        if not hasattr(self, "_initialized"):
            # Initialize the OSRM connection
            self.osrm = OSRMConnection(osrm_url=osrm_url)

            # Dictionary mapping road_id -> set of routes using that road
            # Using set for O(1) add/remove operations
            self.road_subscriptions: Dict[int, Set[Route]] = {}

            self._initialized = True

    def getRoute(self, a: Position, b: Position) -> Route:
        """
        Given a starting position, a route object will be created
        containing the shortest path using OSRM.
        The route will be automatically subscribed to all roads
        it traverses.

        Args:
            a: Starting position
            b: Ending position

        Returns:
            Route: A new Route object subscribed to the MapController
        """
        # 1. Get coordinates from positions
        start_lon, start_lat = a.get_position()
        end_lon, end_lat = b.get_position()

        # 2. Get route from OSRM using coordinates
        osrm_result_dict = self.osrm.shortest_path_coords(
            start_lon, start_lat, end_lon, end_lat
        )

        if not osrm_result_dict:
            raise ValueError(
                f"No route found from ({start_lon}, {start_lat}) "
                f"to ({end_lon}, {end_lat})"
            )

        # 3. Convert OSRM dict to typed OSRMResult
        osrm_result = OSRMResult.from_dict(osrm_result_dict)

        # 4. Create a new route object with the typed result
        traversable_route = Route(osrm_result, self.osrm)

        # 5. Subscribe all the roads to this route in the road_subscriptions dictionary
        traversable_route.subscribe_to_map_controller(self)

        # 6. return the route
        return traversable_route

    def disableRoads(self, road_id_list: List[int]) -> None:
        """
        Given a list of road segments with their OSM ID, will disable
        the roads on the map.
        For any route containing this road, a new route will be
        calculated using OSRM.

        Note: Road disabling with OSRM requires either:
        1. Running a custom OSRM server with modified data
        2. Client-side filtering (which this implements)

        Args:
            road_id_list: List of road segment OSM IDs to disable
        """
        # Get all edges from OSRM
        all_edges = self.osrm.get_all_edges()

        for road_id in road_id_list:
            # Find routes subscribed to this road
            if road_id in self.road_subscriptions:
                # Create a copy of the set to avoid modification during iteration
                routes_to_recalculate = set(self.road_subscriptions[road_id])

                # Recalculate each route that uses this disabled road
                for route in routes_to_recalculate:
                    if not route.is_finished:
                        success = route.recalculate()
                        if not success:
                            msg = (
                                f"Warning: Route {route.id} could not be "
                                "recalculated after road "
                                f"{road_id} was disabled."
                            )
                            print(msg)

            # Disable the road in OSM data (for edge lookups)
            try:
                edge_mask = all_edges["id"] == road_id
                if edge_mask.any():
                    # Remove from edges dataframe
                    all_edges = all_edges[~edge_mask]
                    self.osrm.set_edges(all_edges)
                    print(f"Road {road_id} has been disabled locally.")
                else:
                    print(f"Warning: Road {road_id} not found in OSM data.")
            except Exception as e:
                print(f"Error disabling road {road_id}: {e}")

    def _subscribe_route_to_road(self, road_id: int, route: Route) -> None:
        """
        Subscribes a route to a specific road segment.

        Args:
            road_id: The OSM ID of the road segment
            route: The Route object to subscribe
        """
        if road_id not in self.road_subscriptions:
            self.road_subscriptions[road_id] = set()
        self.road_subscriptions[road_id].add(route)

    def _unsubscribe_route_from_road(self, road_id: int, route: Route) -> None:
        """
        Unsubscribes a route from a specific road segment.

        Args:
            road_id: The OSM ID of the road segment
            route: The Route object to unsubscribe
        """
        if road_id in self.road_subscriptions:
            self.road_subscriptions[road_id].discard(route)
            # Clean up empty sets to save memory
            if not self.road_subscriptions[road_id]:
                del self.road_subscriptions[road_id]
