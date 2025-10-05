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

from unittest.mock import patch, MagicMock
from sim.DAO.OSMConnection import OSMConnection
import geopandas as gpd
import networkx as nx
from pandas import Series
from shapely.geometry import Point, LineString


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

    # Assert <-
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

    # Assert <-
    mock_exists.assert_called_once_with("sim/DAO/OSMData")
    # makedirs not called since folder existed
    mock_makedirs.assert_not_called()
    mock_get_data.assert_called_once_with(
        "Montreal", directory="sim/DAO/OSMData", update=True
    )
    mock_OSM.assert_called_once_with("/mock/path/montreal.osm.pbf")
    mock_get_drivable_network.assert_called_once()
    mock_create_graph.assert_called_once()


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
def test_create_edge(
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
    node1 = Series(node_data)
    node2 = Series(node_data)
    linestring = LineString([[-73.591378, 45.591513], [-73.591378, 45.591513]])

    # Act
    edge = instance.create_edge(1, "test street", node1, node2, 2.8, True, 30)

    # Assert
    assert isinstance(edge, Series)
    assert edge.geometry == linestring
