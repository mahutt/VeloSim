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
from typing import Optional
from pyrosm import OSM  # type: ignore
from pyrosm import get_data
import networkx as nx
import geopandas as gpd
from pandas import Series
from shapely.geometry import Point


class OSMConnection:
    def __init__(self) -> None:
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

        # downloads the OSM data if doesnt exist and updates the file if corrupted/old
        fp = get_data("Montreal", directory="sim/DAO/OSMData", update=True)

        self._osm = OSM(fp)  # initializes OSM parser

    # gets roads and intersections (edges and nodes)
    # takes around a minute to get the full network
    def _get_drivable_network(self) -> None:
        self._nodes, self._edges = self._osm.get_network(
            nodes=True,
            network_type="driving",
        )
        if self._nodes.empty or self._edges.empty:
            print("Nodes or edges unavailable")

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
    def get_node_by_id(self, id: int) -> Optional[gpd.GeoDataFrame]:
        node = self._nodes[self._nodes["id"] == id]
        if node.empty:
            print("No node could be found")
            return None
        else:
            return node

    # returns source and target nodes of the edge
    def get_edge_intersections(self, edge: Series) -> tuple[Series, Series]:
        source_node = self._nodes[self._nodes["id"] == edge["u"]]
        target_node = self._nodes[self._nodes["id"] == edge["v"]]
        return source_node, target_node

    # gets nearest node according to passed coordinates
    def coordinates_to_nearest_node(self, lng: float, lat: float) -> Series:
        # converts nodes to GeoDataFrame
        nodes_gdf = gpd.GeoDataFrame(
            self._nodes, geometry=gpd.points_from_xy(self._nodes.lon, self._nodes.lat)
        )

        # creates point from coordinates
        point = Point(lng, lat)

        # find nearest node
        # gets node with the smallest distance from the input coordinates
        projected_gdf = nodes_gdf.to_crs(
            "EPSG:32633"
        )  # project gdf to calculate accurately distance
        nearest_node = projected_gdf.loc[
            projected_gdf.geometry.distance(point).idxmin()
        ]

        # nearest node in original geometry system
        node_from_gdf: Series = nodes_gdf[nodes_gdf["id"] == nearest_node["id"]].iloc[0]

        return node_from_gdf

    # creates networkx graph to allow its methods to read nodes/edges
    # separated from shortest path as takes time to create
    # and can have same graph reused
    # takes around 40 seconds
    def create_networkx_graph(self) -> None:
        node_columns = ["id", "name", "geometry"]
        edge_columns = ["id", "u", "v", "name", "length", "geometry", "oneway"]

        # filtering nodes/edges sent to graph to heavily improve performance
        filtered_nodes = self._nodes[self._nodes.columns.intersection(node_columns)]
        filtered_edges = self._edges[self._edges.columns.intersection(edge_columns)]

        self._graph = self._osm.to_graph(
            filtered_nodes, filtered_edges, graph_type="networkx"
        )

    # gets shortest path between two nodes according to length measures
    # note: this method should be called after all self._nodes, self._edges
    # and create_networkx_graph have been updated if changes have been made
    # src:https://pyrosm.readthedocs.io/en/latest/graphs.html#calculate-shortest-paths
    def shortest_path(
        self, source_node: Series, target_node: Series, networkx_graph: nx.MultiDiGraph
    ) -> list[int]:
        # get id of nodes since networkx_graph nodes are stored as ids
        source_node_id = source_node["id"]
        target_node_id = target_node["id"]
        if (
            source_node_id in networkx_graph.nodes()
            and target_node_id in networkx_graph.nodes()
        ):
            # returns a list of nodes by their id passing through the route
            route: list[int] = nx.shortest_path(
                networkx_graph, source_node_id, target_node_id, weight="length"
            )
            return route
        print("route could not be created between the two nodes")
        return []


"""
if __name__ == "__main__":
    # start = time.perf_counter()
    conn = OSMConnection()
    # print(f'connected and roads: {time.perf_counter() - start}')
    #print(f"{conn.get_node_geometry(conn.get_all_nodes().iloc[0])}")
    # conn.create_networkx_graph()  # ~40sec
    #print(f'graph network: {time.perf_counter() - start}')
    #conn.get_edge_intersections(conn.get_all_edges().iloc[0])
    #print(f'intersection: {time.perf_counter() - start}')
    #node = conn.coordinates_to_nearest_node(-73.84, 45.44)
    #print(type(node))
    #print(node)
    #print(node['lat'])
    #print(f'coordinates: {time.perf_counter() - start}')
    #node1 = conn.get_all_nodes().iloc[0]
    #node2 = conn.get_all_nodes().iloc[5]
    #route = conn.shortest_path(node1, node2, conn.get_graph())
    #print(len(route))
    #print(f'path: {time.perf_counter() - start}')
    #node_id = conn.get_node_by_id(route[0])
    #print(conn.get_node_by_id(route[1]))"""
