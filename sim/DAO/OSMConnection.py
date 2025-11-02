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
import numpy as np
from scipy.spatial import cKDTree
from pyproj import Transformer
import pandana as pdna
from tqdm import tqdm
import pandas as pd




class OSMConnection(object):
    __instance = None

    nodes_gdf : gpd.GeoDataFrame
    projected_nodes : gpd.GeoDataFrame
    edge_index: Optional[dict] = None
    _ch_network: Optional[pdna.Network] = None
    _node_id_mapping: Optional[dict] = None
    _reverse_node_id_mapping: Optional[dict] = None
  
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
        print("Initializing OSM data file")
        self._initialize_osm_data_file()
        print("Getting drivable network")
        self._get_drivable_network()  # ~1min
        print("Setting projected nodes")
        self._set_projected_nodes()
        self._build_edge_index()
        self._graph: nx.MultiDiGraph = nx.MultiDiGraph()  # networkx graph
        # Note: CH network will be built lazily when needed or via build_ch_network()

    def _initialize_osm_data_file(self) -> None:
        # creates OSMData folder if doesnt exist
        if not os.path.exists("sim/DAO/OSMData"):
            os.makedirs("sim/DAO/OSMData")

        try:
            # downloads the OSM data if doesnt exist and
            # updates the file if corrupted/old
            fp = get_data("Montreal", directory="sim/DAO/OSMData", update=False)

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
    
    def _set_projected_nodes(self) -> None:
        nodes_gdf = gpd.GeoDataFrame(
                self._nodes,
                geometry=gpd.points_from_xy(self._nodes.lon, self._nodes.lat),
                crs="EPSG:4326",
            )
       
         # Index by id for O(1) lookups later
        nodes_gdf = nodes_gdf.set_index("id", drop=False)
        self.nodes_gdf = nodes_gdf

        # Use a local metric CRS for Montreal
        target_crs = "EPSG:32633" 
        projected_nodes = nodes_gdf.to_crs(target_crs)
        self.projected_nodes = projected_nodes

        # Build + cache transformer
        self._to_proj = Transformer.from_crs("EPSG:4326", target_crs, always_xy=True)

         # Build KD-tree once 
        xs = projected_nodes.geometry.x.to_numpy()
        ys = projected_nodes.geometry.y.to_numpy()
        self._coords_xy = np.column_stack((xs, ys))         # shape (N, 2)
        self._ids = projected_nodes.index.to_numpy()        # node ids aligned with rows
        self._kdtree = cKDTree(self._coords_xy)             # fast nearest neighbor

        print("KD-tree built for projected nodes")
    
    def build_ch_network(self, cache_path: str = "sim/DAO/OSMData/montreal_ch_network.h5") -> None:
        """
        Build Contraction Hierarchy network from nodes/edges GeoDataFrames.
        This method should be called explicitly when you want to enable CH routing.
        
        Args:
            cache_path: Path to save/load the preprocessed CH network
        """
        # Check if cached network exists
        if os.path.exists(cache_path):
            print(f"Loading cached CH network from {cache_path}...")
            try:
                self._ch_network = pdna.Network.from_hdf5(cache_path)
                self._load_node_id_mapping()
                print("CH network loaded successfully!")
                return
            except Exception as e:
                print(f"Failed to load cached network: {e}")
                print("Building CH network from scratch...")
        
        print("Building Contraction Hierarchy network...")
        print("This may take 2-5 minutes for Montreal-scale network...")
        
        # Step 1: Create node ID mapping 
        with tqdm(total=5, desc="CH Network Build Progress") as pbar:
            pbar.set_description("Creating node ID mapping")
            self._create_node_id_mapping()
            pbar.update(1)
            
            # Step 2: Prepare nodes DataFrame
            pbar.set_description("Preparing nodes")
            nodes_df = self._nodes.copy()
            nodes_df['node_id'] = nodes_df['id'].map(self._node_id_mapping)
            pbar.update(1)
            
            # Step 3: Prepare edges DataFrame with aggregation for parallel edges
            pbar.set_description("Preparing edges")
            edges_df = self._edges.copy()
            edges_df['from_id'] = edges_df['u'].map(self._node_id_mapping)
            edges_df['to_id'] = edges_df['v'].map(self._node_id_mapping)
            
            # Ensure length column exists
            if 'length' not in edges_df.columns:
                edges_df['length'] = edges_df.geometry.length
            
            # Aggregate parallel edges (take minimum length)
            edges_aggregated = edges_df.groupby(['from_id', 'to_id']).agg({
                'length': 'min'
            }).reset_index()
            pbar.update(1)
            
            # Step 4: Build Pandana network (this is the time-consuming step)
            pbar.set_description("Building CH network (this takes time)")
            self._ch_network = pdna.Network(
                nodes_df['lon'].values,              # x coordinates (longitudes)
                nodes_df['lat'].values,              # y coordinates (latitudes)
                edges_aggregated['from_id'].values,  # source nodes
                edges_aggregated['to_id'].values,    # target nodes
                edges_aggregated[['length']]         # edge weights (DataFrame, not array!)
            )
            pbar.update(1)
            
            # Step 5: Cache the network for future use
            pbar.set_description("Caching CH network")
            try:
                # Ensure directory exists
                os.makedirs(os.path.dirname(cache_path), exist_ok=True)
                self._ch_network.save_hdf5(cache_path)
                self._save_node_id_mapping()
                print(f"CH network cached to {cache_path}")
            except Exception as e:
                print(f"Warning: Could not cache CH network: {e}")
            pbar.update(1)
        
        print("CH network build complete!")
    
    def _create_node_id_mapping(self) -> None:
        """Create mapping between OSM node IDs and contiguous integer IDs for Pandana"""
        unique_node_ids = self._nodes['id'].unique()
        self._node_id_mapping = {old_id: new_id for new_id, old_id in enumerate(unique_node_ids)}
        self._reverse_node_id_mapping = {v: k for k, v in self._node_id_mapping.items()}
    
    def _save_node_id_mapping(self) -> None:
        """Save node ID mapping to disk for future use"""
        mapping_path = "sim/DAO/OSMData/node_id_mapping.npz"
        try:
            # Convert dict to arrays for efficient storage
            osm_ids = np.array(list(self._node_id_mapping.keys()))
            pandana_ids = np.array(list(self._node_id_mapping.values()))
            np.savez_compressed(mapping_path, osm_ids=osm_ids, pandana_ids=pandana_ids)
        except Exception as e:
            print(f"Warning: Could not save node ID mapping: {e}")
    
    def _load_node_id_mapping(self) -> None:
        """Load node ID mapping from disk"""
        mapping_path = "sim/DAO/OSMData/node_id_mapping.npz"
        try:
            data = np.load(mapping_path)
            osm_ids = data['osm_ids']
            pandana_ids = data['pandana_ids']
            self._node_id_mapping = {int(osm): int(pan) for osm, pan in zip(osm_ids, pandana_ids)}
            self._reverse_node_id_mapping = {v: k for k, v in self._node_id_mapping.items()}
        except Exception as e:
            print(f"Warning: Could not load node ID mapping: {e}")
            self._create_node_id_mapping()
    
    def get_ch_network(self) -> Optional[pdna.Network]:
        """Get the CH network, building it if it doesn't exist"""
        if self._ch_network is None:
            print("CH network not built yet. Building now...")
            self.build_ch_network()
        return self._ch_network
            
    def _build_edge_index(self) -> dict:
        if self.edge_index is None:
            self.edge_index = {}
            for idx, row in self._edges.iterrows():
                u, v = row['u'], row['v']
                self.edge_index[(u, v)] = idx
        return self.edge_index
    
    def get_edge_index(self):
        return self.edge_index
    
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
       # Project raw lon/lat → local metric CRS without making a GeoDataFrame
        x, y = self._to_proj.transform(lng, lat)

        # KD-tree nearest neighbor
        dist, idx = self._kdtree.query([x, y], k=1)

        # Map KD-tree index → node id → row in O(1)
        node_id = self._ids[idx]
        return self.nodes_gdf.loc[node_id]

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
        self, source_node: Series, target_node: Series, networkx_graph: Optional[nx.MultiDiGraph] = None, use_ch: bool = True
    ) -> list[int]:
        """
        Compute shortest path between two nodes.
        
        Args:
            source_node: Source node (pandas Series with 'id' field)
            target_node: Target node (pandas Series with 'id' field)
            networkx_graph: NetworkX graph (optional, used when use_ch=False)
            use_ch: If True, use Pandana CH routing (faster); if False, use NetworkX
        
        Returns:
            List of node IDs in the shortest path
        """
        source_node_id = source_node["id"]
        target_node_id = target_node["id"]
        
        if use_ch and self._ch_network is not None:
            # Use Pandana Contraction Hierarchy (3-100x faster)
            try:
                if self._node_id_mapping is None:
                    self._create_node_id_mapping()
                
                # Map OSM node IDs to Pandana integer IDs
                pandana_source = self._node_id_mapping.get(source_node_id)
                pandana_target = self._node_id_mapping.get(target_node_id)
                
                if pandana_source is None or pandana_target is None:
                    raise ValueError("Source or target node not found in node mapping")
                
                # Get path from Pandana (returns Pandana IDs)
                path_pandana = self._ch_network.shortest_path(pandana_source, pandana_target)
                
                # Map back to OSM node IDs
                route = [self._reverse_node_id_mapping[node] for node in path_pandana]
                return route
            except Exception as e:
                print(f"CH routing failed: {e}. Falling back to NetworkX...")
                # Fall back to NetworkX
                use_ch = False
        
        # Use NetworkX routing (fallback or when CH not available)
        if networkx_graph is None:
            # Create NetworkX graph if not provided
            if self._graph.number_of_nodes() == 0:
                self.create_networkx_graph()
            networkx_graph = self._graph
        
        if (
            not self._nodes.empty
            and not self._edges.empty
            and networkx_graph.number_of_nodes() != 0
        ):
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
            raise Exception("Route could not be created between the two nodes")
        else:
            raise Exception(
                "Could not create route with empty nodes, edges or networkx_graph"
            )
    
    def shortest_path_length(self, source_node: Series, target_node: Series, use_ch: bool = True) -> float:
        """
        Compute shortest path length between two nodes.
        
        Args:
            source_node: Source node (pandas Series with 'id' field)
            target_node: Target node (pandas Series with 'id' field)
            use_ch: If True, use Pandana CH routing; if False, use NetworkX
        
        Returns:
            Path length in meters
        """
        source_node_id = source_node["id"]
        target_node_id = target_node["id"]
        
        if use_ch and self._ch_network is not None:
            try:
                if self._node_id_mapping is None:
                    self._create_node_id_mapping()
                
                pandana_source = self._node_id_mapping.get(source_node_id)
                pandana_target = self._node_id_mapping.get(target_node_id)
                
                if pandana_source is None or pandana_target is None:
                    raise ValueError("Source or target node not found in node mapping")
                
                return self._ch_network.shortest_path_length(pandana_source, pandana_target)
            except Exception as e:
                print(f"CH path length calculation failed: {e}. Falling back to NetworkX...")
        
        # NetworkX fallback
        if self._graph.number_of_nodes() == 0:
            self.create_networkx_graph()
        
        return nx.shortest_path_length(self._graph, source_node_id, target_node_id, weight="length")
    
    def batch_shortest_paths(self, sources: list[Series], targets: list[Series]) -> list[list[int]]:
        """
        Vectorized batch routing for multiple origin-destination pairs.
        Much faster than looping with individual queries.
        Requires CH network to be built.
        
        Args:
            sources: List of source nodes (pandas Series with 'id' field)
            targets: List of target nodes (same length as sources)
        
        Returns:
            List of paths (one per OD pair)
        """
        if self._ch_network is None:
            raise Exception("CH network must be built before using batch routing")
        
        if self._node_id_mapping is None:
            self._create_node_id_mapping()
        
        # Convert to Pandana IDs
        pandana_sources = [self._node_id_mapping[s["id"]] for s in sources]
        pandana_targets = [self._node_id_mapping[t["id"]] for t in targets]
        
        # Get paths from Pandana
        paths_pandana = self._ch_network.shortest_paths(pandana_sources, pandana_targets)
        
        # Convert back to OSM IDs
        paths = []
        for path_pandana in paths_pandana:
            path = [self._reverse_node_id_mapping[node] for node in path_pandana]
            paths.append(path)
        
        return paths

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

if __name__ == "__main__":
    print("OSM Connection working")