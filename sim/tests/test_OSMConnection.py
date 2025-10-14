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

import pytest
from unittest.mock import patch, MagicMock
from sim.DAO.OSMConnection import OSMConnection
import geopandas as gpd
import networkx as nx
from pandas import Series
from shapely.geometry import Point, LineString
from typing import Generator


@pytest.fixture(autouse=True)
def reset_singleton() -> Generator[None, None, None]:
    # Reset before each test
    OSMConnection.reset_instance()
    yield
    # Cleanup after test
    OSMConnection.reset_instance()


@patch("os.makedirs")
@patch("os.path.exists")
@patch("sim.DAO.OSMConnection.get_data")
@patch("sim.DAO.OSMConnection.OSM")
@patch("sim.DAO.OSMConnection.OSMConnection._get_drivable_network")
@patch("sim.DAO.OSMConnection.OSMConnection.create_networkx_graph")
def test_osmconnection_initialization_methods_called(
    mock_create_graph: MagicMock,
    mock_get_drivable_network: MagicMock,
    mock_OSM: MagicMock,
    mock_get_data: MagicMock,
    mock_exists: MagicMock,
    mock_makedirs: MagicMock,
) -> None:
    # Arrange
    mock_exists.return_value = False  # mock folder not found
    mock_get_data.return_value = "/mock/path/montreal.osm.pbf"

    # Act
    instance = OSMConnection()

    # Assert
    mock_exists.assert_called_once_with("sim/DAO/OSMData")
    # makedirs called since folder "not found"
    mock_makedirs.assert_called_once_with("sim/DAO/OSMData")
    mock_get_data.assert_called_once_with(
        "Montreal", directory="sim/DAO/OSMData", update=True
    )
    mock_OSM.assert_called_once_with("/mock/path/montreal.osm.pbf")
    assert instance._osm is mock_OSM.return_value

    mock_get_drivable_network.assert_called_once()
    mock_create_graph.assert_called_once()


@patch("os.makedirs")
@patch("os.path.exists")
@patch("sim.DAO.OSMConnection.get_data")
@patch("sim.DAO.OSMConnection.OSM")
@patch("sim.DAO.OSMConnection.OSMConnection._get_drivable_network")
@patch("sim.DAO.OSMConnection.OSMConnection.create_networkx_graph")
def test_osmconnection_initialization_folder_exists(
    mock_create_graph: MagicMock,
    mock_get_drivable_network: MagicMock,
    mock_OSM: MagicMock,
    mock_get_data: MagicMock,
    mock_exists: MagicMock,
    mock_makedirs: MagicMock,
) -> None:
    # Arrange
    mock_exists.return_value = True  # mock folder found
    mock_get_data.return_value = "/mock/path/montreal.osm.pbf"

    # Act
    OSMConnection()

    # Assert
    mock_exists.assert_called_once_with("sim/DAO/OSMData")
    # makedirs not called since folder existed
    mock_makedirs.assert_not_called()
    mock_get_data.assert_called_once_with(
        "Montreal", directory="sim/DAO/OSMData", update=True
    )
    mock_OSM.assert_called_once_with("/mock/path/montreal.osm.pbf")
    mock_get_drivable_network.assert_called_once()
    mock_create_graph.assert_called_once()


@patch("os.path.exists")
@patch("sim.DAO.OSMConnection.get_data")
@patch("sim.DAO.OSMConnection.OSMConnection._get_drivable_network")
@patch("sim.DAO.OSMConnection.OSMConnection.create_networkx_graph")
def test_osmconnection_initialization_get_data_fails(
    mock_create_graph: MagicMock,
    mock_get_drivable_network: MagicMock,
    mock_get_data: MagicMock,
    mock_exists: MagicMock,
) -> None:
    # Arrange
    mock_exists.return_value = True  # mock folder found
    mock_get_data.side_effect = Exception("Failed to download")

    # Act and Assert
    with pytest.raises(
        Exception, match="Error while initializing OSM: Failed to download"
    ):
        OSMConnection()

    mock_get_drivable_network.assert_not_called()
    mock_create_graph.assert_not_called()


@patch("os.path.exists")
@patch("sim.DAO.OSMConnection.get_data")
@patch("sim.DAO.OSMConnection.OSM")
@patch("sim.DAO.OSMConnection.OSMConnection.create_networkx_graph")
def test_get_drivable_network_success(
    mock_create_graph: MagicMock,
    mock_osm: MagicMock,
    mock_get_data: MagicMock,
    mock_exists: MagicMock,
) -> None:
    # Arrange
    mock_exists.return_value = True  # mock folder found
    mock_get_data.return_value = "/mock/path/montreal.osm.pbf"
    mock_osm_instance = MagicMock()
    mock_osm.return_value = mock_osm_instance
    mock_nodes = gpd.GeoDataFrame({"id": [1]}, geometry=[Point(0, 0)])
    mock_edges = gpd.GeoDataFrame({"id": [1]}, geometry=[LineString([(0, 0), (1, 0)])])
    mock_osm_instance.get_network.return_value = (mock_nodes, mock_edges)

    # Act
    OSMConnection()

    # Assert
    mock_create_graph.assert_called_once()
    mock_osm_instance.get_network.assert_called_once_with(
        nodes=True, network_type="driving"
    )


@patch("sim.DAO.OSMConnection.OSMConnection._initialize_osm_data_file")
@patch("sim.DAO.OSMConnection.OSMConnection.create_networkx_graph")
def test_get_drivable_network_fail(
    mock_create_graph: MagicMock,
    mock_init_file: MagicMock,
) -> None:
    # Act and Assert
    with pytest.raises(Exception, match="Could not get network from uninitialized OSM"):
        OSMConnection()

    mock_init_file.assert_called_once()
    mock_create_graph.assert_not_called()


@patch("os.path.exists")
@patch("sim.DAO.OSMConnection.get_data")
@patch("sim.DAO.OSMConnection.OSM")
@patch("sim.DAO.OSMConnection.OSMConnection.create_networkx_graph")
def test_get_drivable_network_fail_from_empty_nodes(
    mock_create_graph: MagicMock,
    mock_osm: MagicMock,
    mock_get_data: MagicMock,
    mock_exists: MagicMock,
) -> None:
    # Arrange
    mock_exists.return_value = True  # mock folder found
    mock_get_data.return_value = "/mock/path/montreal.osm.pbf"
    mock_osm_instance = MagicMock()
    mock_osm.return_value = mock_osm_instance
    mock_nodes = gpd.GeoDataFrame()
    mock_edges = gpd.GeoDataFrame({"id": [1]}, geometry=[LineString([(0, 0), (1, 0)])])
    mock_osm_instance.get_network.return_value = (mock_nodes, mock_edges)

    # Act and Assert
    with pytest.raises(Exception, match="Nodes or edges unavailable"):
        OSMConnection()

    mock_create_graph.assert_not_called()


@patch("sim.DAO.OSMConnection.OSMConnection._initialize_osm_data_file")
@patch("sim.DAO.OSMConnection.OSMConnection._get_drivable_network")
@patch("sim.DAO.OSMConnection.OSMConnection.create_networkx_graph")
def test_getters_nodes_edges_graph(
    mock_create_graph: MagicMock,
    mock_get_drivable_network: MagicMock,
    mock_init_file: MagicMock,
) -> None:
    # Arrange
    instance = OSMConnection()
    mock_init_file.assert_called_once()
    mock_get_drivable_network.assert_called_once()
    mock_create_graph.assert_called_once()

    mock_osm = MagicMock()
    instance._osm = mock_osm
    mock_nodes = gpd.GeoDataFrame({"id": [1]}, geometry=[Point(0, 0)])
    mock_edges = gpd.GeoDataFrame({"id": [1]}, geometry=[LineString([(0, 0), (1, 0)])])
    mock_graph: nx.MultiDiGraph = nx.MultiDiGraph()
    mock_graph.add_node("A")
    mock_graph.add_node("B")
    mock_graph.add_edge("A", "B", key=0, weight=1.0)
    mock_graph.add_edge("A", "B", key=1, weight=2.5)

    instance._nodes = mock_nodes
    instance._edges = mock_edges
    instance._graph = mock_graph

    # Act and Assert
    nodes = instance.get_all_nodes()
    assert nodes.equals(mock_nodes)

    edges = instance.get_all_edges()
    assert edges.equals(mock_edges)

    graph = instance.get_graph()
    assert graph == mock_graph


@patch("sim.DAO.OSMConnection.OSMConnection._initialize_osm_data_file")
@patch("sim.DAO.OSMConnection.OSMConnection._get_drivable_network")
@patch("sim.DAO.OSMConnection.OSMConnection.create_networkx_graph")
def test_setters_nodes_edges(
    mock_create_graph: MagicMock,
    mock_get_drivable_network: MagicMock,
    mock_init_file: MagicMock,
) -> None:
    # Arrange
    instance = OSMConnection()
    mock_init_file.assert_called_once()
    mock_get_drivable_network.assert_called_once()
    mock_create_graph.assert_called_once()

    sample_nodes = gpd.GeoDataFrame({"id": [1]}, geometry=[Point(0, 0)])
    sample_edges = gpd.GeoDataFrame(
        {"id": [1]}, geometry=[LineString([(0, 0), (1, 0)])]
    )

    # Act and Assert
    instance.set_nodes(sample_nodes)
    assert instance._nodes.equals(sample_nodes)

    instance.set_edges(sample_edges)
    assert instance._edges.equals(sample_edges)


@patch("sim.DAO.OSMConnection.OSMConnection._initialize_osm_data_file")
@patch("sim.DAO.OSMConnection.OSMConnection._get_drivable_network")
@patch("sim.DAO.OSMConnection.OSMConnection.create_networkx_graph")
def test_get_node_geometry(
    mock_create_graph: MagicMock,
    mock_get_drivable_network: MagicMock,
    mock_init_file: MagicMock,
) -> None:
    # Arrange
    instance = OSMConnection()
    mock_init_file.assert_called_once()
    mock_get_drivable_network.assert_called_once()
    mock_create_graph.assert_called_once()

    point = Point(-73.591378, 45.591513)
    node_data = {
        "id": "1",
        "lon": -73.591378,
        "lat": 45.591513,
        "timestamp": 0,
        "visible": False,
        "version": 0,
        "tags": None,
        "changeset": 0,
        "geometry": point,
    }
    node = Series(node_data)

    # Act
    geometry = instance.get_node_geometry(node)

    # Assert
    assert isinstance(geometry, Point)
    assert geometry.equals(point)


@patch("sim.DAO.OSMConnection.OSMConnection._initialize_osm_data_file")
@patch("sim.DAO.OSMConnection.OSMConnection._get_drivable_network")
@patch("sim.DAO.OSMConnection.OSMConnection.create_networkx_graph")
@patch("builtins.print")
def test_get_node_by_id_found(
    mock_print: MagicMock,
    mock_create_graph: MagicMock,
    mock_get_drivable_network: MagicMock,
    mock_init_file: MagicMock,
) -> None:
    # Arrange
    instance = OSMConnection()
    mock_init_file.assert_called_once()
    mock_get_drivable_network.assert_called_once()
    mock_create_graph.assert_called_once()

    mock_nodes = gpd.GeoDataFrame({"id": [1]}, geometry=[Point(0, 0)])
    instance._nodes = mock_nodes

    # Act
    node = instance.get_node_by_id(1)

    # Assert
    assert node is not None
    mock_print.assert_not_called()


@patch("sim.DAO.OSMConnection.OSMConnection._initialize_osm_data_file")
@patch("sim.DAO.OSMConnection.OSMConnection._get_drivable_network")
@patch("sim.DAO.OSMConnection.OSMConnection.create_networkx_graph")
@patch("builtins.print")
def test_get_node_by_id_not_found(
    mock_print: MagicMock,
    mock_create_graph: MagicMock,
    mock_get_drivable_network: MagicMock,
    mock_init_file: MagicMock,
) -> None:
    # Arrange
    instance = OSMConnection()
    mock_init_file.assert_called_once()
    mock_get_drivable_network.assert_called_once()
    mock_create_graph.assert_called_once()

    mock_nodes = gpd.GeoDataFrame({"id": [1]}, geometry=[Point(0, 0)])
    instance._nodes = mock_nodes

    # Act
    node = instance.get_node_by_id(2)

    # Assert
    assert node is None
    mock_print.assert_called_once_with("No node could be found")


@patch("sim.DAO.OSMConnection.OSMConnection._initialize_osm_data_file")
@patch("sim.DAO.OSMConnection.OSMConnection._get_drivable_network")
@patch("sim.DAO.OSMConnection.OSMConnection.create_networkx_graph")
def test_get_edge_intersection(
    mock_create_graph: MagicMock,
    mock_get_drivable_network: MagicMock,
    mock_init_file: MagicMock,
) -> None:
    # Arrange
    instance = OSMConnection()
    mock_init_file.assert_called_once()
    mock_get_drivable_network.assert_called_once()
    mock_create_graph.assert_called_once()

    linestring = LineString(
        [[-73.591378, 45.591513], [-73.59159230853888, 45.59260120932741]]
    )
    edge_data = {
        "id": "1",
        "name": "test street",
        "u": 1,
        "v": 2,
        "length": 5,
        "oneway": "yes",
        "maxspeed": 30,
        "geometry": linestring,
    }
    edge = Series(edge_data)

    mock_nodes = gpd.GeoDataFrame({"id": [1, 2]}, geometry=[Point(0, 0), Point(1, 1)])
    instance._nodes = mock_nodes

    # Act
    intersections = instance.get_edge_intersections(edge)

    # Assert
    assert isinstance(intersections, tuple)
    assert not intersections[0].empty


@patch("sim.DAO.OSMConnection.OSMConnection._initialize_osm_data_file")
@patch("sim.DAO.OSMConnection.OSMConnection._get_drivable_network")
@patch("sim.DAO.OSMConnection.OSMConnection.create_networkx_graph")
def test_create_node_success(
    mock_create_graph: MagicMock,
    mock_get_drivable_network: MagicMock,
    mock_init_file: MagicMock,
) -> None:
    # Arrange
    instance = OSMConnection()
    mock_init_file.assert_called_once()
    mock_get_drivable_network.assert_called_once()
    mock_create_graph.assert_called_once()

    point = Point(-73.591378, 45.591513)

    # Act
    node = instance.create_node(1, -73.591378, 45.591513)

    # Assert
    assert isinstance(node, Series)
    assert node.geometry == point


@patch("sim.DAO.OSMConnection.OSMConnection._initialize_osm_data_file")
@patch("sim.DAO.OSMConnection.OSMConnection._get_drivable_network")
@patch("sim.DAO.OSMConnection.OSMConnection.create_networkx_graph")
@patch("sim.DAO.OSMConnection.Point")
@patch("builtins.print")
def test_create_node_fail(
    mock_print: MagicMock,
    mock_point: MagicMock,
    mock_create_graph: MagicMock,
    mock_get_drivable_network: MagicMock,
    mock_init_file: MagicMock,
) -> None:
    # Arrange
    instance = OSMConnection()
    mock_init_file.assert_called_once()
    mock_get_drivable_network.assert_called_once()
    mock_create_graph.assert_called_once()

    mock_point.side_effect = ValueError("Invalid Coordinates")

    # Act
    node = instance.create_node(1, 2.2, 4.2)

    # Assert
    assert node is None
    mock_print.assert_called_once_with("Node creation failed: Invalid Coordinates")


@patch("sim.DAO.OSMConnection.OSMConnection._initialize_osm_data_file")
@patch("sim.DAO.OSMConnection.OSMConnection._get_drivable_network")
@patch("sim.DAO.OSMConnection.OSMConnection.create_networkx_graph")
def test_create_edge_success(
    mock_create_graph: MagicMock,
    mock_get_drivable_network: MagicMock,
    mock_init_file: MagicMock,
) -> None:
    # Arrange
    instance = OSMConnection()
    mock_init_file.assert_called_once()
    mock_get_drivable_network.assert_called_once()
    mock_create_graph.assert_called_once()

    point = Point(-73.591378, 45.591513)
    node_data = {
        "id": 1,
        "lon": -73.591378,
        "lat": 45.591513,
        "timestamp": 0,
        "visible": False,
        "version": 0,
        "tags": None,
        "changeset": 0,
        "geometry": point,
    }
    node1 = Series(node_data)
    node2 = Series(node_data)
    linestring = LineString([[-73.591378, 45.591513], [-73.591378, 45.591513]])

    # Act
    edge = instance.create_edge(1, "test street", node1, node2, 2.8, True, 30)

    # Assert
    assert isinstance(edge, Series)
    assert edge.geometry == linestring


@patch("sim.DAO.OSMConnection.OSMConnection._initialize_osm_data_file")
@patch("sim.DAO.OSMConnection.OSMConnection._get_drivable_network")
@patch("sim.DAO.OSMConnection.OSMConnection.create_networkx_graph")
@patch("sim.DAO.OSMConnection.LineString")
@patch("builtins.print")
def test_create_edge_fail(
    mock_print: MagicMock,
    mock_linestring: MagicMock,
    mock_create_graph: MagicMock,
    mock_get_drivable_network: MagicMock,
    mock_init_file: MagicMock,
) -> None:
    # Arrange
    instance = OSMConnection()
    mock_init_file.assert_called_once()
    mock_get_drivable_network.assert_called_once()
    mock_create_graph.assert_called_once()

    point = Point(-73.591378, 45.591513)
    node_data = {
        "id": 1,
        "lon": 2.2,
        "lat": 5.4,
        "timestamp": 0,
        "visible": False,
        "version": 0,
        "tags": None,
        "changeset": 0,
        "geometry": point,
    }
    node1 = Series(node_data)
    node2 = Series(node_data)

    mock_linestring.side_effect = ValueError("Invalid LineString")

    # Act
    edge = instance.create_edge(1, "Bad Street", node1, node2, 20, False, 30)

    # Assert
    assert edge is None
    mock_print.assert_called_once_with("Edge creation failed: Invalid LineString")


@patch("sim.DAO.OSMConnection.nx.shortest_path")
@patch("sim.DAO.OSMConnection.OSMConnection._initialize_osm_data_file")
@patch("sim.DAO.OSMConnection.OSMConnection._get_drivable_network")
@patch("sim.DAO.OSMConnection.OSMConnection.create_networkx_graph")
def test_shortest_path_success(
    mock_create_graph: MagicMock,
    mock_get_drivable_network: MagicMock,
    mock_init_file: MagicMock,
    mock_shortest_path: MagicMock,
) -> None:
    # Arrange
    instance = OSMConnection()
    mock_init_file.assert_called_once()
    mock_get_drivable_network.assert_called_once()
    mock_create_graph.assert_called_once()

    mock_shortest_path.return_value = [1, 2]

    point = Point(-73.591378, 45.591513)
    node_data = {
        "id": 1,
        "lon": -73.591378,
        "lat": 45.591513,
        "timestamp": 0,
        "visible": False,
        "version": 0,
        "tags": None,
        "changeset": 0,
        "geometry": point,
    }
    node1 = Series(node_data)
    point2 = Point(-73.59159230853888, 45.59260120932741)
    node_data2 = {
        "id": 2,
        "lon": -73.59159230853888,
        "lat": 45.59260120932741,
        "timestamp": 0,
        "visible": False,
        "version": 0,
        "tags": None,
        "changeset": 0,
        "geometry": point2,
    }
    node2 = Series(node_data2)

    instance._edges = gpd.GeoDataFrame(
        {"id": [1]}, geometry=[LineString([(0, 0), (1, 0)])]
    )
    instance._nodes = gpd.GeoDataFrame([node1, node2])
    sample_graph: nx.MultiDiGraph = nx.MultiDiGraph()
    del node_data["id"]
    del node_data2["id"]
    sample_graph.add_node(1, **node_data)
    sample_graph.add_node(2, **node_data2)
    sample_graph.add_edge(1, 2, key=0, weight=1.0)

    # Act
    route = instance.shortest_path(node1, node2, sample_graph)

    # Assert
    mock_shortest_path.assert_called_once_with(sample_graph, 1, 2, weight="length")
    assert route == [1, 2]


@patch("sim.DAO.OSMConnection.OSMConnection._initialize_osm_data_file")
@patch("sim.DAO.OSMConnection.OSMConnection._get_drivable_network")
@patch("sim.DAO.OSMConnection.OSMConnection.create_networkx_graph")
def test_shortest_path_fail_from_empty_graph(
    mock_create_graph: MagicMock,
    mock_get_drivable_network: MagicMock,
    mock_init_file: MagicMock,
) -> None:
    # Arrange
    instance = OSMConnection()
    mock_init_file.assert_called_once()
    mock_get_drivable_network.assert_called_once()
    mock_create_graph.assert_called_once()

    point = Point(-73.591378, 45.591513)
    node_data = {
        "id": 1,
        "lon": -73.591378,
        "lat": 45.591513,
        "timestamp": 0,
        "visible": False,
        "version": 0,
        "tags": None,
        "changeset": 0,
        "geometry": point,
    }
    node1 = Series(node_data)
    point2 = Point(-73.59159230853888, 45.59260120932741)
    node_data2 = {
        "id": 2,
        "lon": -73.59159230853888,
        "lat": 45.59260120932741,
        "timestamp": 0,
        "visible": False,
        "version": 0,
        "tags": None,
        "changeset": 0,
        "geometry": point2,
    }
    node2 = Series(node_data2)
    instance._edges = gpd.GeoDataFrame(
        {"id": [1]}, geometry=[LineString([(0, 0), (1, 0)])]
    )
    instance._nodes = gpd.GeoDataFrame([node1, node2])
    sample_graph: nx.MultiDiGraph = nx.MultiDiGraph()

    # Act and Assert
    with pytest.raises(
        Exception,
        match="Could not create route with empty nodes, edges or networkx_graph",
    ):
        instance.shortest_path(node1, node2, sample_graph)


@patch("sim.DAO.OSMConnection.nx.shortest_path")
@patch("sim.DAO.OSMConnection.OSMConnection._initialize_osm_data_file")
@patch("sim.DAO.OSMConnection.OSMConnection._get_drivable_network")
@patch("sim.DAO.OSMConnection.OSMConnection.create_networkx_graph")
def test_shortest_path_fail_from_missing_id(
    mock_create_graph: MagicMock,
    mock_get_drivable_network: MagicMock,
    mock_init_file: MagicMock,
    mock_shortest_path: MagicMock,
) -> None:
    # Arrange
    instance = OSMConnection()
    mock_init_file.assert_called_once()
    mock_get_drivable_network.assert_called_once()
    mock_create_graph.assert_called_once()

    point = Point(-73.591378, 45.591513)
    node_data = {
        "id": 3,  # Create node with id not in graph
        "lon": -73.591378,
        "lat": 45.591513,
        "timestamp": 0,
        "visible": False,
        "version": 0,
        "tags": None,
        "changeset": 0,
        "geometry": point,
    }
    node1 = Series(node_data)
    point2 = Point(-73.59159230853888, 45.59260120932741)
    node_data2 = {
        "id": 2,
        "lon": -73.59159230853888,
        "lat": 45.59260120932741,
        "timestamp": 0,
        "visible": False,
        "version": 0,
        "tags": None,
        "changeset": 0,
        "geometry": point2,
    }
    node2 = Series(node_data2)

    instance._edges = gpd.GeoDataFrame(
        {"id": [1]}, geometry=[LineString([(0, 0), (1, 0)])]
    )
    instance._nodes = gpd.GeoDataFrame([node1, node2])
    sample_graph: nx.MultiDiGraph = nx.MultiDiGraph()
    del node_data["id"]
    del node_data2["id"]
    sample_graph.add_node(1, **node_data)
    sample_graph.add_node(2, **node_data2)
    sample_graph.add_edge(1, 2, key=0, weight=1.0)

    # Act and Assert
    with pytest.raises(
        Exception, match="Route could not be created between the two nodes"
    ):
        instance.shortest_path(node1, node2, sample_graph)

    mock_shortest_path.assert_not_called()


@patch("builtins.print")
@patch("sim.DAO.OSMConnection.nx.shortest_path")
@patch("sim.DAO.OSMConnection.OSMConnection._initialize_osm_data_file")
@patch("sim.DAO.OSMConnection.OSMConnection._get_drivable_network")
@patch("sim.DAO.OSMConnection.OSMConnection.create_networkx_graph")
def test_shortest_path_fail_from_nx_method_fail(
    mock_create_graph: MagicMock,
    mock_get_drivable_network: MagicMock,
    mock_init_file: MagicMock,
    mock_shortest_path: MagicMock,
    mock_print: MagicMock,
) -> None:
    # Arrange
    instance = OSMConnection()
    mock_init_file.assert_called_once()
    mock_get_drivable_network.assert_called_once()
    mock_create_graph.assert_called_once()

    point = Point(-73.591378, 45.591513)
    node_data = {
        "id": 1,
        "lon": -73.591378,
        "lat": 45.591513,
        "timestamp": 0,
        "visible": False,
        "version": 0,
        "tags": None,
        "changeset": 0,
        "geometry": point,
    }
    node1 = Series(node_data)
    point2 = Point(-73.59159230853888, 45.59260120932741)
    node_data2 = {
        "id": 2,
        "lon": -73.59159230853888,
        "lat": 45.59260120932741,
        "timestamp": 0,
        "visible": False,
        "version": 0,
        "tags": None,
        "changeset": 0,
        "geometry": point2,
    }
    node2 = Series(node_data2)

    instance._edges = gpd.GeoDataFrame(
        {"id": [1]}, geometry=[LineString([(0, 0), (1, 0)])]
    )
    instance._nodes = gpd.GeoDataFrame([node1, node2])
    sample_graph: nx.MultiDiGraph = nx.MultiDiGraph()
    del node_data["id"]
    del node_data2["id"]
    sample_graph.add_node(1, **node_data)
    sample_graph.add_node(2, **node_data2)
    sample_graph.add_edge(1, 2, key=0, weight=1.0)

    mock_shortest_path.side_effect = Exception("Shortest Path Failed")

    # Act and Assert
    with pytest.raises(
        Exception, match="Route could not be created between the two nodes"
    ):
        instance.shortest_path(node1, node2, sample_graph)
    mock_print.assert_called_once_with("Route creation failed: Shortest Path Failed")


@patch("sim.DAO.OSMConnection.OSMConnection._initialize_osm_data_file")
@patch("sim.DAO.OSMConnection.OSMConnection._get_drivable_network")
@patch("sim.DAO.OSMConnection.OSMConnection.create_networkx_graph")
def test_coordinates_to_nearest_node(
    mock_create_graph: MagicMock,
    mock_get_drivable_network: MagicMock,
    mock_init_file: MagicMock,
) -> None:
    # Arrange
    instance = OSMConnection()
    mock_init_file.assert_called_once()
    mock_get_drivable_network.assert_called_once()
    mock_create_graph.assert_called_once()

    point1 = Point(-73.591378, 45.591513)
    point2 = Point(-73.59159230853888, 45.59260120932741)
    mock_nodes = gpd.GeoDataFrame(
        {"id": [1, 2], "lon": [point1.x, point2.x], "lat": [point1.y, point2.y]},
        geometry=[point1, point2],
        crs="EPSG:4326",
    )
    instance._nodes = mock_nodes

    node = instance.coordinates_to_nearest_node(-73.591450, 45.591644)

    assert not node.empty
