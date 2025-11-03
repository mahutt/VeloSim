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
from sim.DAO.OSMConnection import OSMConnection
from typing import Dict, List, Set, Any


class MapController:
    _instance = None

    def __new__(cls, *args: Any, **kwargs: Any) -> "MapController":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        if not hasattr(self, "_initialized"):
            # Initialize the OSMConnection:
            self.osm = OSMConnection()

            # Dictionary mapping road_id -> set of routes using that road
            # Using set for O(1) add/remove operations
            self.road_subscriptions: Dict[int, Set[Route]] = {}

            self._initialized = True

    def getRoute(self, a: Position, b: Position) -> Route:
        """
        Given a starting position, a route object will be created
        containing the shortest path.
        The route will be automatically subscribed to all roads
        it traverses.

        Args:
            a: Starting position
            b: Ending position

        Returns:
            Route: A new Route object subscribed to the MapController
        """
        # 1. Find the nearest valid node in OSM:
        starting_node = self.osm.coordinates_to_nearest_node(
            a.get_position()[0], a.get_position()[1]
        )
        ending_node = self.osm.coordinates_to_nearest_node(
            b.get_position()[0], b.get_position()[1]
        )

        # 2. Generate the path:
        osm_route = self.osm.shortest_path(starting_node, ending_node, use_ch=True)

        # 3. Create a new route object
        traversable_route = Route(osm_route, self.osm)

        # 4. Subscribe all the roads to this route in the road_subscriptions dictionary
        traversable_route.subscribe_to_map_controller(self)

        # 5. return the route
        return traversable_route

    def disableRoads(self, road_id_list: List[int]) -> None:
        """
        Given a list of road segments with their OSM ID, will disable
        the roads on the map.
        For any route containing this road, a new route will be
        calculated.

        Args:
            road_id_list: List of road segment OSM IDs to disable
        """
        # Get all edges from OSM
        all_edges = self.osm.get_all_edges()

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
                                f"recalculated after road {road_id} was "
                                f"disabled."
                            )
                            print(msg)

            # Disable the road in OSM data
            # Find the edge(s) with this road_id and remove them from the graph
            try:
                edge_mask = all_edges["id"] == road_id
                if edge_mask.any():
                    # Get the edge details before removing
                    disabled_edge = all_edges[edge_mask].iloc[0]
                    u_node = disabled_edge["u"]
                    v_node = disabled_edge["v"]

                    # Remove from edges dataframe
                    all_edges = all_edges[~edge_mask]
                    self.osm.set_edges(all_edges)

                    # Remove from networkx graph
                    graph = self.osm.get_graph()
                    if graph.has_edge(u_node, v_node):
                        # NetworkX MultiDiGraph can have multiple edges between nodes
                        # Remove all edges between these nodes with this road_id
                        edges_to_remove = []
                        for key, data in graph[u_node][v_node].items():
                            if data.get("id") == road_id:
                                edges_to_remove.append(key)

                        for key in edges_to_remove:
                            graph.remove_edge(u_node, v_node, key)

                    print(f"Road {road_id} has been disabled.")
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
