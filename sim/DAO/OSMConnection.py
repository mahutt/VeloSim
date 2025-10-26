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

import os
from typing import Optional, Self
from pyrosm import OSM  # type: ignore
from pyrosm import get_data
import networkx as nx
import geopandas as gpd
from pandas import Series
from shapely.geometry import Point, LineString


class OSMConnection(object):
    __instance = None

    def __new__(cls) -> Self:
        if cls.__instance is None:
            cls.__instance = super(OSMConnection, cls).__new__(cls)
            cls.__instance.__initialized = False
        return cls.__instance

    def __init__(self) -> None:
        if self.__initialized:
            return
        self.__initialized: bool = True
        self._osm: OSM = None  # OSM parser object
        self._nodes: gpd.GeoDataFrame = gpd.GeoDataFrame()  # intersections
        self._edges: gpd.GeoDataFrame = gpd.GeoDataFrame()  # roads
        self._initialize_osm_data_file()
        self._get_drivable_network()  # ~1min
        self._graph: nx.MultiDiGraph = nx.MultiDiGraph()  # networkx graph
        self.create_networkx_graph()  # ~40sec

    def _initialize_osm_data_file(self) -> None:
        # creates OSMData folder if doesnt exist
        if not os.path.exists("sim/DAO/OSMData"):
            os.makedirs("sim/DAO/OSMData")

        try:
            # downloads the OSM data if doesnt exist and
            # updates the file if corrupted/old
            fp = get_data("Montreal", directory="sim/DAO/OSMData", update=True)

            self._osm = OSM(fp)  # initializes OSM parser
        except Exception as e:
            raise Exception(f"Error while initializing OSM: {e}")

    # gets roads and intersections (edges and nodes)
    # takes around a minute to get the full network
    def _get_drivable_network(self) -> None:
        if self._osm is not None:
            self._nodes, self._edges = self._osm.get_network(
                nodes=True,
                network_type="driving",
            )
            if self._nodes.empty or self._edges.empty:
                raise Exception("Nodes or edges unavailable")
        else:
            raise Exception("Could not get network from uninitialized OSM")

    def get_all_nodes(self) -> gpd.GeoDataFrame:
        return self._nodes

    def get_all_edges(self) -> gpd.GeoDataFrame:
        return self._edges

    def get_graph(self) -> nx.MultiDiGraph:
        return self._graph

    # setters for when modifications to nodes and edges are made for road changes
    def set_nodes(self, nodes: gpd.GeoDataFrame) -> None:
        self._nodes = nodes

    def set_edges(self, edges: gpd.GeoDataFrame) -> None:
        self._edges = edges

    # returns POINT object with lng, lat
    def get_node_geometry(self, node: Series) -> Point:
        geometry: Point = node.geometry
        return geometry

    # returns node according to its id
    def get_node_by_id(self, id: int) -> Optional[Series]:
        node = self._nodes[self._nodes["id"] == id]
        if node.empty:
            print("No node could be found")
            return None
        else:
            return node.iloc[0]

    # returns source and target nodes of the edge
    def get_edge_intersections(self, edge: Series) -> tuple[Series, Series]:
        source_node = self._nodes[self._nodes["id"] == edge["u"]]
        target_node = self._nodes[self._nodes["id"] == edge["v"]]
        return source_node, target_node

    # gets nearest node according to passed coordinates
    def coordinates_to_nearest_node(self, lng: float, lat: float) -> Series:
        # converts nodes to GeoDataFrame with WGS84 CRS (EPSG:4326)
        nodes_gdf = gpd.GeoDataFrame(
            self._nodes,
            geometry=gpd.points_from_xy(self._nodes.lon, self._nodes.lat),
            crs="EPSG:4326",
        )

        # creates point from coordinates in WGS84
        point_gdf = gpd.GeoDataFrame([{"geometry": Point(lng, lat)}], crs="EPSG:4326")

        # find nearest node
        # gets node with the smallest distance from the input coordinates
        # project both to same CRS to calculate accurately distance
        projected_nodes = nodes_gdf.to_crs("EPSG:32633")
        projected_point = point_gdf.to_crs("EPSG:32633")

        nearest_node = projected_nodes.loc[
            projected_nodes.geometry.distance(projected_point.geometry.iloc[0]).idxmin()
        ]

        # nearest node in original geometry system
        node_from_gdf: Series = nodes_gdf[nodes_gdf["id"] == nearest_node["id"]].iloc[0]

        return node_from_gdf

    # creates networkx graph to allow its methods to read nodes/edges
    # separated from shortest path as takes time to create
    # and can have same graph reused
    # takes around 40 seconds
    def create_networkx_graph(self) -> None:
        if not self._nodes.empty and not self._edges.empty:
            node_columns = ["id", "geometry"]
            edge_columns = ["id", "u", "v", "name", "length", "geometry", "oneway"]

            # filtering nodes/edges sent to graph to heavily improve performance
            filtered_nodes = self._nodes[self._nodes.columns.intersection(node_columns)]
            filtered_edges = self._edges[self._edges.columns.intersection(edge_columns)]

            self._graph = self._osm.to_graph(
                filtered_nodes, filtered_edges, graph_type="networkx"
            )
        else:
            raise Exception("Cannot create network with empty nodes or edges")

    # gets shortest path between two nodes according to length measures
    # note: this method should be called after all self._nodes, self._edges
    # and create_networkx_graph have been updated if changes have been made
    # src:https://pyrosm.readthedocs.io/en/latest/graphs.html#calculate-shortest-paths
    def shortest_path(
        self, source_node: Series, target_node: Series, networkx_graph: nx.MultiDiGraph
    ) -> list[int]:
        if (
            not self._nodes.empty
            and not self._edges.empty
            and networkx_graph.number_of_nodes() != 0
        ):
            # get id of nodes since networkx_graph nodes are stored as ids
            source_node_id = source_node["id"]
            target_node_id = target_node["id"]
            if (
                source_node_id in networkx_graph.nodes()
                and target_node_id in networkx_graph.nodes()
            ):
                try:
                    # returns a list of nodes by their id passing through the route
                    route: list[int] = nx.shortest_path(
                        networkx_graph, source_node_id, target_node_id, weight="length"
                    )
                    return route
                except Exception as e:
                    print(f"Route creation failed: {e}")
            raise Exception("Route could not be created between the two nodes")
        else:
            raise Exception(
                "Could not create route with empty nodes, edges or networkx_graph"
            )

    # creates new node object
    def create_node(self, id: int, lng: float, lat: float) -> Optional[Series]:
        try:
            geometry = Point(lng, lat)
            node_data = {
                "id": id,
                "lon": lng,
                "lat": lat,
                "timestamp": 0,
                "visible": False,
                "version": 0,
                "tags": None,
                "changeset": 0,
                "geometry": geometry,
            }

            new_node: Series = Series(node_data)
            return new_node
        except Exception as e:
            print(f"Node creation failed: {e}")
            return None

    # creates new edge object
    def create_edge(
        self,
        id: int,
        name: str,  # name of street
        start_node: Series,
        end_node: Series,
        length: float,  # length of road in meters
        oneway: bool,  # oneway -> true, two ways -> false
        maxspeed: int,  # in km/h
    ) -> Optional[Series]:
        try:
            directions = "yes" if oneway else "no"

            start_point: Point = self.get_node_geometry(start_node)
            end_point: Point = self.get_node_geometry(end_node)
            geometry = LineString(
                [[start_point.x, start_point.y], [end_point.x, end_point.y]]
            )

            edge_data = {
                "id": id,
                "name": name,
                "u": start_node["id"],
                "v": end_node["id"],
                "length": length,
                "oneway": directions,
                "maxspeed": maxspeed,
                "geometry": geometry,
            }

            new_edge: Series = Series(edge_data)
            return new_edge
        except Exception as e:
            print(f"Edge creation failed: {e}")
            return None

    @classmethod
    def reset_instance(cls) -> None:  # for testing
        cls.__instance = None
