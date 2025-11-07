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
import numpy as np
from typing import Generator


@pytest.fixture(autouse=True)
def reset_singleton() -> Generator[None, None, None]:
    OSMConnection.reset_instance()
    yield
    OSMConnection.reset_instance()


class TestBuildCHNetwork:
    """Tests for build_ch_network method"""

    @patch("sim.DAO.OSMConnection.OSMConnection._initialize_osm_data_file")
    @patch("sim.DAO.OSMConnection.OSMConnection._get_drivable_network")
    @patch("sim.DAO.OSMConnection.OSMConnection.create_networkx_graph")
    @patch("os.path.abspath")
    @patch("os.path.exists")
    @patch("sim.DAO.OSMConnection.pdna.Network.from_hdf5")
    def test_build_ch_network_loads_from_cache(
        self,
        mock_from_hdf5: MagicMock,
        mock_exists: MagicMock,
        mock_abspath: MagicMock,
        mock_create_graph: MagicMock,
        mock_get_drivable: MagicMock,
        mock_init_file: MagicMock,
    ) -> None:
        """Test that CH network loads from cache if available"""
        instance = OSMConnection()

        # Mock absolute path resolution
        mock_abspath.return_value = "/absolute/path/to/sim/DAO/OSMConnection.py"

        # Mock cache exists
        mock_exists.return_value = True
        mock_network = MagicMock()
        mock_from_hdf5.return_value = mock_network

        # Mock node ID mapping
        with patch.object(instance, "_load_node_id_mapping") as mock_load_mapping:
            instance.build_ch_network()

            mock_from_hdf5.assert_called_once()
            mock_load_mapping.assert_called_once()
            assert instance._ch_network == mock_network

    @patch("sim.DAO.OSMConnection.OSMConnection._initialize_osm_data_file")
    @patch("sim.DAO.OSMConnection.OSMConnection._get_drivable_network")
    @patch("sim.DAO.OSMConnection.OSMConnection.create_networkx_graph")
    @patch("os.path.abspath")
    @patch("builtins.print")
    def test_build_ch_network_fallback_on_cache_load_failure(
        self,
        mock_print: MagicMock,
        mock_abspath: MagicMock,
        mock_create_graph: MagicMock,
        mock_get_drivable: MagicMock,
        mock_init_file: MagicMock,
    ) -> None:
        """Test that CH network builds from scratch if cache load fails"""
        instance = OSMConnection()
        mock_print.reset_mock()

        # Mock absolute path resolution
        mock_abspath.return_value = "/absolute/path/to/sim/DAO/OSMConnection.py"

        # Set up nodes and edges
        nodes = gpd.GeoDataFrame(
            {
                "id": [1, 2, 3],
                "lon": [-73.5, -73.6, -73.7],
                "lat": [45.5, 45.6, 45.7],
            },
            geometry=[Point(-73.5, 45.5), Point(-73.6, 45.6), Point(-73.7, 45.7)],
        )
        edges = gpd.GeoDataFrame(
            {
                "u": [1, 2],
                "v": [2, 3],
                "length": [100.0, 150.0],
            },
            geometry=[
                LineString([(-73.5, 45.5), (-73.6, 45.6)]),
                LineString([(-73.6, 45.6), (-73.7, 45.7)]),
            ],
        )
        instance._nodes = nodes
        instance._edges = edges

        # Cache file doesn't exist, so will build from scratch
        with patch("os.path.exists", return_value=False):
            with patch("sim.DAO.OSMConnection.pdna.Network") as mock_pdna_network:
                with patch("os.makedirs"):
                    mock_network = MagicMock()
                    mock_pdna_network.return_value = mock_network

                    instance.build_ch_network()

                    # Should build from scratch
                    mock_pdna_network.assert_called_once()
                    assert instance._ch_network == mock_network

    @patch("sim.DAO.OSMConnection.OSMConnection._initialize_osm_data_file")
    @patch("sim.DAO.OSMConnection.OSMConnection._get_drivable_network")
    @patch("sim.DAO.OSMConnection.OSMConnection.create_networkx_graph")
    @patch("os.path.abspath")
    @patch("os.path.exists")
    @patch("sim.DAO.OSMConnection.pdna.Network")
    @patch("os.makedirs")
    def test_build_ch_network_from_scratch(
        self,
        mock_makedirs: MagicMock,
        mock_pdna_network: MagicMock,
        mock_exists: MagicMock,
        mock_abspath: MagicMock,
        mock_create_graph: MagicMock,
        mock_get_drivable: MagicMock,
        mock_init_file: MagicMock,
    ) -> None:
        """Test building CH network from scratch"""
        instance = OSMConnection()

        # Mock absolute path resolution
        mock_abspath.return_value = "/absolute/path/to/sim/DAO/OSMConnection.py"

        # No cache available
        mock_exists.return_value = False

        # Set up test data
        nodes = gpd.GeoDataFrame(
            {
                "id": [1, 2, 3],
                "lon": [-73.5, -73.6, -73.7],
                "lat": [45.5, 45.6, 45.7],
            },
            geometry=[Point(-73.5, 45.5), Point(-73.6, 45.6), Point(-73.7, 45.7)],
        )
        edges = gpd.GeoDataFrame(
            {
                "u": [1, 2],
                "v": [2, 3],
                "length": [100.0, 150.0],
            },
            geometry=[
                LineString([(-73.5, 45.5), (-73.6, 45.6)]),
                LineString([(-73.6, 45.6), (-73.7, 45.7)]),
            ],
        )
        instance._nodes = nodes
        instance._edges = edges

        mock_network = MagicMock()
        mock_pdna_network.return_value = mock_network

        instance.build_ch_network()

        # Verify pandana.Network was called with correct parameters
        assert mock_pdna_network.called
        assert instance._ch_network == mock_network
        assert instance._node_id_mapping is not None

    @patch("sim.DAO.OSMConnection.OSMConnection._initialize_osm_data_file")
    @patch("sim.DAO.OSMConnection.OSMConnection._get_drivable_network")
    @patch("sim.DAO.OSMConnection.OSMConnection.create_networkx_graph")
    @patch("os.path.abspath")
    @patch("os.path.exists")
    @patch("sim.DAO.OSMConnection.pdna.Network")
    @patch("os.makedirs")
    def test_build_ch_network_handles_parallel_edges(
        self,
        mock_makedirs: MagicMock,
        mock_pdna_network: MagicMock,
        mock_exists: MagicMock,
        mock_abspath: MagicMock,
        mock_create_graph: MagicMock,
        mock_get_drivable: MagicMock,
        mock_init_file: MagicMock,
    ) -> None:
        """Test that parallel edges are aggregated correctly"""
        instance = OSMConnection()

        # Mock absolute path resolution
        mock_abspath.return_value = "/absolute/path/to/sim/DAO/OSMConnection.py"
        mock_exists.return_value = False

        # Create edges with parallel edges (same u,v pairs)
        nodes = gpd.GeoDataFrame(
            {
                "id": [1, 2],
                "lon": [-73.5, -73.6],
                "lat": [45.5, 45.6],
            },
            geometry=[Point(-73.5, 45.5), Point(-73.6, 45.6)],
        )
        edges = gpd.GeoDataFrame(
            {
                "u": [1, 1, 1],
                "v": [2, 2, 2],
                "length": [100.0, 80.0, 120.0],  # Should take min (80.0)
            },
            geometry=[
                LineString([(-73.5, 45.5), (-73.6, 45.6)]),
                LineString([(-73.5, 45.5), (-73.6, 45.6)]),
                LineString([(-73.5, 45.5), (-73.6, 45.6)]),
            ],
        )
        instance._nodes = nodes
        instance._edges = edges

        mock_network = MagicMock()
        mock_pdna_network.return_value = mock_network

        instance.build_ch_network()

        # Verify aggregation happened (should have only 1 edge after aggregation)
        call_args = mock_pdna_network.call_args
        edge_lengths = call_args[0][4]  # 5th positional arg
        # Should have aggregated to single edge with min length
        assert len(edge_lengths) == 1


class TestNodeIDMapping:
    """Tests for node ID mapping methods"""

    @patch("sim.DAO.OSMConnection.OSMConnection._initialize_osm_data_file")
    @patch("sim.DAO.OSMConnection.OSMConnection._get_drivable_network")
    @patch("sim.DAO.OSMConnection.OSMConnection.create_networkx_graph")
    def test_create_node_id_mapping(
        self,
        mock_create_graph: MagicMock,
        mock_get_drivable: MagicMock,
        mock_init_file: MagicMock,
    ) -> None:
        """Test creation of node ID mapping"""
        instance = OSMConnection()

        nodes = gpd.GeoDataFrame(
            {"id": [100, 200, 300]},
            geometry=[Point(0, 0), Point(1, 1), Point(2, 2)],
        )
        instance._nodes = nodes

        instance._create_node_id_mapping()

        assert instance._node_id_mapping is not None
        assert len(instance._node_id_mapping) == 3
        assert 100 in instance._node_id_mapping
        assert 200 in instance._node_id_mapping
        assert 300 in instance._node_id_mapping

        # Check reverse mapping
        assert instance._reverse_node_id_mapping is not None
        assert len(instance._reverse_node_id_mapping) == 3

    @patch("sim.DAO.OSMConnection.OSMConnection._initialize_osm_data_file")
    @patch("sim.DAO.OSMConnection.OSMConnection._get_drivable_network")
    @patch("sim.DAO.OSMConnection.OSMConnection.create_networkx_graph")
    @patch("numpy.savez_compressed")
    def test_save_node_id_mapping(
        self,
        mock_savez: MagicMock,
        mock_create_graph: MagicMock,
        mock_get_drivable: MagicMock,
        mock_init_file: MagicMock,
    ) -> None:
        """Test saving node ID mapping to disk"""
        instance = OSMConnection()

        instance._node_id_mapping = {100: 0, 200: 1, 300: 2}

        instance._save_node_id_mapping()

        mock_savez.assert_called_once()
        call_args = mock_savez.call_args
        assert "osm_ids" in call_args[1]
        assert "pandana_ids" in call_args[1]

    @patch("sim.DAO.OSMConnection.OSMConnection._initialize_osm_data_file")
    @patch("sim.DAO.OSMConnection.OSMConnection._get_drivable_network")
    @patch("sim.DAO.OSMConnection.OSMConnection.create_networkx_graph")
    @patch("numpy.savez_compressed")
    @patch("builtins.print")
    def test_save_node_id_mapping_fails_gracefully(
        self,
        mock_print: MagicMock,
        mock_savez: MagicMock,
        mock_create_graph: MagicMock,
        mock_get_drivable: MagicMock,
        mock_init_file: MagicMock,
    ) -> None:
        """Test that save_node_id_mapping handles errors gracefully"""
        instance = OSMConnection()
        mock_print.reset_mock()

        instance._node_id_mapping = {100: 0, 200: 1}
        mock_savez.side_effect = Exception("Disk full")

        instance._save_node_id_mapping()

        # Should print warning but not crash
        assert any(
            "Warning: Could not save node ID mapping" in str(msg)
            for msg in mock_print.call_args_list
        )

    @patch("sim.DAO.OSMConnection.OSMConnection._initialize_osm_data_file")
    @patch("sim.DAO.OSMConnection.OSMConnection._get_drivable_network")
    @patch("sim.DAO.OSMConnection.OSMConnection.create_networkx_graph")
    @patch("numpy.load")
    def test_load_node_id_mapping(
        self,
        mock_load: MagicMock,
        mock_create_graph: MagicMock,
        mock_get_drivable: MagicMock,
        mock_init_file: MagicMock,
    ) -> None:
        """Test loading node ID mapping from disk"""
        instance = OSMConnection()

        mock_data = {
            "osm_ids": np.array([100, 200, 300]),
            "pandana_ids": np.array([0, 1, 2]),
        }
        mock_load.return_value = mock_data

        instance._load_node_id_mapping()

        assert instance._node_id_mapping is not None
        assert instance._node_id_mapping[100] == 0
        assert instance._node_id_mapping[200] == 1
        assert instance._node_id_mapping[300] == 2

        assert instance._reverse_node_id_mapping is not None
        assert instance._reverse_node_id_mapping[0] == 100

    @patch("sim.DAO.OSMConnection.OSMConnection._initialize_osm_data_file")
    @patch("sim.DAO.OSMConnection.OSMConnection._get_drivable_network")
    @patch("sim.DAO.OSMConnection.OSMConnection.create_networkx_graph")
    @patch("numpy.load")
    @patch("builtins.print")
    def test_load_node_id_mapping_fallback_on_error(
        self,
        mock_print: MagicMock,
        mock_load: MagicMock,
        mock_create_graph: MagicMock,
        mock_get_drivable: MagicMock,
        mock_init_file: MagicMock,
    ) -> None:
        """Test that load falls back to create on error"""
        instance = OSMConnection()
        mock_print.reset_mock()

        nodes = gpd.GeoDataFrame({"id": [1, 2]}, geometry=[Point(0, 0), Point(1, 1)])
        instance._nodes = nodes

        mock_load.side_effect = Exception("File not found")

        instance._load_node_id_mapping()

        # Should print warning and create new mapping
        assert any(
            "Warning: Could not load node ID mapping" in str(msg)
            for msg in mock_print.call_args_list
        )
        assert instance._node_id_mapping is not None


class TestGetCHNetwork:
    """Tests for get_ch_network method"""

    @patch("sim.DAO.OSMConnection.OSMConnection._initialize_osm_data_file")
    @patch("sim.DAO.OSMConnection.OSMConnection._get_drivable_network")
    @patch("sim.DAO.OSMConnection.OSMConnection.create_networkx_graph")
    def test_get_ch_network_returns_existing(
        self,
        mock_create_graph: MagicMock,
        mock_get_drivable: MagicMock,
        mock_init_file: MagicMock,
    ) -> None:
        """Test that get_ch_network returns existing network"""
        instance = OSMConnection()

        mock_network = MagicMock()
        instance._ch_network = mock_network

        result = instance.get_ch_network()

        assert result == mock_network

    @patch("sim.DAO.OSMConnection.OSMConnection._initialize_osm_data_file")
    @patch("sim.DAO.OSMConnection.OSMConnection._get_drivable_network")
    @patch("sim.DAO.OSMConnection.OSMConnection.create_networkx_graph")
    def test_get_ch_network_builds_if_none(
        self,
        mock_create_graph: MagicMock,
        mock_get_drivable: MagicMock,
        mock_init_file: MagicMock,
    ) -> None:
        """Test that get_ch_network builds if not exists"""
        instance = OSMConnection()
        instance._ch_network = None

        with patch.object(instance, "build_ch_network") as mock_build:
            mock_network = MagicMock()

            def set_network() -> None:
                instance._ch_network = mock_network

            mock_build.side_effect = set_network

            result = instance.get_ch_network()

            mock_build.assert_called_once()
            assert result == mock_network


class TestShortestPathWithCH:
    """Tests for shortest_path with CH routing"""

    @patch("sim.DAO.OSMConnection.OSMConnection._initialize_osm_data_file")
    @patch("sim.DAO.OSMConnection.OSMConnection._get_drivable_network")
    @patch("sim.DAO.OSMConnection.OSMConnection.create_networkx_graph")
    def test_shortest_path_with_ch_success(
        self,
        mock_create_graph: MagicMock,
        mock_get_drivable: MagicMock,
        mock_init_file: MagicMock,
    ) -> None:
        """Test shortest_path using CH network"""
        instance = OSMConnection()

        # Set up CH network
        mock_ch_network = MagicMock()
        mock_ch_network.shortest_path.return_value = [0, 1, 2]
        instance._ch_network = mock_ch_network

        instance._node_id_mapping = {100: 0, 200: 1, 300: 2}
        instance._reverse_node_id_mapping = {0: 100, 1: 200, 2: 300}

        source = Series({"id": 100})
        target = Series({"id": 300})

        # Set up nodes and edges for fallback
        instance._nodes = gpd.GeoDataFrame(
            {"id": [100, 200, 300]},
            geometry=[Point(0, 0), Point(1, 1), Point(2, 2)],
        )
        instance._edges = gpd.GeoDataFrame(
            {"id": [1]}, geometry=[LineString([(0, 0), (1, 1)])]
        )

        path = instance.shortest_path(source, target, use_ch=True)

        assert path == [100, 200, 300]
        mock_ch_network.shortest_path.assert_called_once_with(0, 2)

    @patch("sim.DAO.OSMConnection.OSMConnection._initialize_osm_data_file")
    @patch("sim.DAO.OSMConnection.OSMConnection._get_drivable_network")
    @patch("sim.DAO.OSMConnection.OSMConnection.create_networkx_graph")
    @patch("builtins.print")
    def test_shortest_path_ch_fallback_to_networkx(
        self,
        mock_print: MagicMock,
        mock_create_graph: MagicMock,
        mock_get_drivable: MagicMock,
        mock_init_file: MagicMock,
    ) -> None:
        """Test shortest_path falls back to NetworkX if CH fails"""
        instance = OSMConnection()
        mock_print.reset_mock()

        # Set up CH network that will fail
        mock_ch_network = MagicMock()
        mock_ch_network.shortest_path.side_effect = Exception("CH error")
        instance._ch_network = mock_ch_network

        instance._node_id_mapping = {100: 0, 200: 1}
        instance._reverse_node_id_mapping = {0: 100, 1: 200}

        source = Series({"id": 100})
        target = Series({"id": 200})

        # Set up NetworkX graph
        instance._nodes = gpd.GeoDataFrame(
            {"id": [100, 200]}, geometry=[Point(0, 0), Point(1, 1)]
        )
        instance._edges = gpd.GeoDataFrame(
            {"id": [1], "u": [100], "v": [200], "length": [1.0]},
            geometry=[LineString([(0, 0), (1, 1)])],
        )

        graph: nx.MultiDiGraph = nx.MultiDiGraph()
        graph.add_edge(100, 200, length=1.0)
        instance._graph = graph

        path = instance.shortest_path(source, target, use_ch=True)

        # Should fall back to NetworkX
        assert "CH routing failed" in str(mock_print.call_args_list)
        assert path == [100, 200]

    @patch("sim.DAO.OSMConnection.OSMConnection._initialize_osm_data_file")
    @patch("sim.DAO.OSMConnection.OSMConnection._get_drivable_network")
    @patch("sim.DAO.OSMConnection.OSMConnection.create_networkx_graph")
    def test_shortest_path_ch_node_not_in_mapping(
        self,
        mock_create_graph: MagicMock,
        mock_get_drivable: MagicMock,
        mock_init_file: MagicMock,
    ) -> None:
        """Test shortest_path handles missing node in mapping"""
        instance = OSMConnection()

        mock_ch_network = MagicMock()
        instance._ch_network = mock_ch_network
        instance._node_id_mapping = {100: 0}  # Missing node 200

        source = Series({"id": 100})
        target = Series({"id": 200})  # Not in mapping

        # Set up fallback graph
        instance._nodes = gpd.GeoDataFrame(
            {"id": [100, 200]}, geometry=[Point(0, 0), Point(1, 1)]
        )
        instance._edges = gpd.GeoDataFrame(
            {"id": [1], "u": [100], "v": [200], "length": [1.0]},
            geometry=[LineString([(0, 0), (1, 1)])],
        )
        graph: nx.MultiDiGraph = nx.MultiDiGraph()
        graph.add_edge(100, 200, length=1.0)
        instance._graph = graph

        path = instance.shortest_path(source, target, use_ch=True)

        # Should fall back to NetworkX
        assert path == [100, 200]


class TestShortestPathLength:
    """Tests for shortest_path_length method"""

    @patch("sim.DAO.OSMConnection.OSMConnection._initialize_osm_data_file")
    @patch("sim.DAO.OSMConnection.OSMConnection._get_drivable_network")
    @patch("sim.DAO.OSMConnection.OSMConnection.create_networkx_graph")
    def test_shortest_path_length_with_ch(
        self,
        mock_create_graph: MagicMock,
        mock_get_drivable: MagicMock,
        mock_init_file: MagicMock,
    ) -> None:
        """Test shortest_path_length using CH network"""
        instance = OSMConnection()

        mock_ch_network = MagicMock()
        mock_ch_network.shortest_path_length.return_value = 150.5
        instance._ch_network = mock_ch_network

        instance._node_id_mapping = {100: 0, 200: 1}
        instance._reverse_node_id_mapping = {0: 100, 1: 200}

        source = Series({"id": 100})
        target = Series({"id": 200})

        length = instance.shortest_path_length(source, target, use_ch=True)

        assert length == 150.5
        mock_ch_network.shortest_path_length.assert_called_once_with(0, 1)

    @patch("sim.DAO.OSMConnection.OSMConnection._initialize_osm_data_file")
    @patch("sim.DAO.OSMConnection.OSMConnection._get_drivable_network")
    @patch("sim.DAO.OSMConnection.OSMConnection.create_networkx_graph")
    @patch("networkx.shortest_path_length")
    def test_shortest_path_length_with_networkx(
        self,
        mock_nx_length: MagicMock,
        mock_create_graph: MagicMock,
        mock_get_drivable: MagicMock,
        mock_init_file: MagicMock,
    ) -> None:
        """Test shortest_path_length using NetworkX"""
        instance = OSMConnection()

        source = Series({"id": 100})
        target = Series({"id": 200})

        # Set up graph
        graph: nx.MultiDiGraph = nx.MultiDiGraph()
        graph.add_edge(100, 200, length=100.0)
        instance._graph = graph

        mock_nx_length.return_value = 100.0

        length = instance.shortest_path_length(source, target, use_ch=False)

        mock_nx_length.assert_called_once_with(graph, 100, 200, weight="length")
        assert length == 100.0

    @patch("sim.DAO.OSMConnection.OSMConnection._initialize_osm_data_file")
    @patch("sim.DAO.OSMConnection.OSMConnection._get_drivable_network")
    @patch("sim.DAO.OSMConnection.OSMConnection.create_networkx_graph")
    @patch("builtins.print")
    def test_shortest_path_length_ch_fallback(
        self,
        mock_print: MagicMock,
        mock_create_graph: MagicMock,
        mock_get_drivable: MagicMock,
        mock_init_file: MagicMock,
    ) -> None:
        """Test shortest_path_length falls back on CH error"""
        instance = OSMConnection()
        mock_print.reset_mock()

        mock_ch_network = MagicMock()
        mock_ch_network.shortest_path_length.side_effect = Exception("CH error")
        instance._ch_network = mock_ch_network

        instance._node_id_mapping = {100: 0, 200: 1}

        source = Series({"id": 100})
        target = Series({"id": 200})

        graph: nx.MultiDiGraph = nx.MultiDiGraph()
        graph.add_edge(100, 200, length=100.0)
        instance._graph = graph

        with patch("networkx.shortest_path_length") as mock_nx:
            mock_nx.return_value = 100.0
            length = instance.shortest_path_length(source, target, use_ch=True)

            assert "CH path length calculation failed" in str(mock_print.call_args_list)
            assert length == 100.0


class TestBatchShortestPaths:
    """Tests for batch_shortest_paths method"""

    @patch("sim.DAO.OSMConnection.OSMConnection._initialize_osm_data_file")
    @patch("sim.DAO.OSMConnection.OSMConnection._get_drivable_network")
    @patch("sim.DAO.OSMConnection.OSMConnection.create_networkx_graph")
    def test_batch_shortest_paths_success(
        self,
        mock_create_graph: MagicMock,
        mock_get_drivable: MagicMock,
        mock_init_file: MagicMock,
    ) -> None:
        """Test batch_shortest_paths with multiple OD pairs"""
        instance = OSMConnection()

        mock_ch_network = MagicMock()
        mock_ch_network.shortest_paths.return_value = [[0, 1], [1, 2]]
        instance._ch_network = mock_ch_network

        instance._node_id_mapping = {100: 0, 200: 1, 300: 2}
        instance._reverse_node_id_mapping = {0: 100, 1: 200, 2: 300}

        sources = [Series({"id": 100}), Series({"id": 200})]
        targets = [Series({"id": 200}), Series({"id": 300})]

        paths = instance.batch_shortest_paths(sources, targets)

        assert len(paths) == 2
        assert paths[0] == [100, 200]
        assert paths[1] == [200, 300]

    @patch("sim.DAO.OSMConnection.OSMConnection._initialize_osm_data_file")
    @patch("sim.DAO.OSMConnection.OSMConnection._get_drivable_network")
    @patch("sim.DAO.OSMConnection.OSMConnection.create_networkx_graph")
    def test_batch_shortest_paths_no_ch_network(
        self,
        mock_create_graph: MagicMock,
        mock_get_drivable: MagicMock,
        mock_init_file: MagicMock,
    ) -> None:
        """Test batch_shortest_paths raises error without CH network"""
        instance = OSMConnection()
        instance._ch_network = None

        sources = [Series({"id": 100})]
        targets = [Series({"id": 200})]

        with pytest.raises(
            Exception, match="CH network must be built before using batch routing"
        ):
            instance.batch_shortest_paths(sources, targets)

    @patch("sim.DAO.OSMConnection.OSMConnection._initialize_osm_data_file")
    @patch("sim.DAO.OSMConnection.OSMConnection._get_drivable_network")
    @patch("sim.DAO.OSMConnection.OSMConnection.create_networkx_graph")
    def test_batch_shortest_paths_no_mapping(
        self,
        mock_create_graph: MagicMock,
        mock_get_drivable: MagicMock,
        mock_init_file: MagicMock,
    ) -> None:
        """Test batch_shortest_paths creates mapping if missing"""
        instance = OSMConnection()

        mock_ch_network = MagicMock()
        instance._ch_network = mock_ch_network
        instance._node_id_mapping = None

        nodes = gpd.GeoDataFrame(
            {"id": [100, 200]}, geometry=[Point(0, 0), Point(1, 1)]
        )
        instance._nodes = nodes

        sources = [Series({"id": 100})]
        targets = [Series({"id": 200})]

        mock_ch_network.shortest_paths.return_value = [[0, 1]]

        paths = instance.batch_shortest_paths(sources, targets)

        # Should have created mapping
        assert instance._node_id_mapping is not None
        assert len(paths) == 1  # type: ignore[unreachable]


class TestSetProjectedNodes:
    """Tests for _set_projected_nodes edge cases"""

    @patch("sim.DAO.OSMConnection.OSMConnection._initialize_osm_data_file")
    @patch("sim.DAO.OSMConnection.OSMConnection._get_drivable_network")
    @patch("sim.DAO.OSMConnection.OSMConnection.create_networkx_graph")
    def test_set_projected_nodes_with_empty_nodes(
        self,
        mock_create_graph: MagicMock,
        mock_get_drivable: MagicMock,
        mock_init_file: MagicMock,
    ) -> None:
        """Test _set_projected_nodes handles empty nodes"""
        instance = OSMConnection()

        instance._nodes = gpd.GeoDataFrame()
        instance._set_projected_nodes()

        assert instance.nodes_gdf.empty
        assert instance._kdtree is None
        assert len(instance._ids) == 0

    @patch("sim.DAO.OSMConnection.OSMConnection._initialize_osm_data_file")
    @patch("sim.DAO.OSMConnection.OSMConnection._get_drivable_network")
    @patch("sim.DAO.OSMConnection.OSMConnection.create_networkx_graph")
    def test_set_projected_nodes_without_lon_lat(
        self,
        mock_create_graph: MagicMock,
        mock_get_drivable: MagicMock,
        mock_init_file: MagicMock,
    ) -> None:
        """Test _set_projected_nodes with geometry but no lon/lat columns"""
        instance = OSMConnection()

        # Nodes with geometry but missing lon/lat columns
        nodes = gpd.GeoDataFrame(
            {"id": [1, 2]},
            geometry=[Point(-73.5, 45.5), Point(-73.6, 45.6)],
            crs="EPSG:4326",
        )
        instance._nodes = nodes

        instance._set_projected_nodes()

        assert not instance.nodes_gdf.empty
        assert instance._kdtree is not None


class TestCoordinatesToNearestNode:
    """Tests for coordinates_to_nearest_node edge cases"""

    @patch("sim.DAO.OSMConnection.OSMConnection._initialize_osm_data_file")
    @patch("sim.DAO.OSMConnection.OSMConnection._get_drivable_network")
    @patch("sim.DAO.OSMConnection.OSMConnection.create_networkx_graph")
    def test_coordinates_to_nearest_node_rebuilds_cache(
        self,
        mock_create_graph: MagicMock,
        mock_get_drivable: MagicMock,
        mock_init_file: MagicMock,
    ) -> None:
        """Test that coordinates_to_nearest_node rebuilds cache if needed"""
        instance = OSMConnection()

        # Set nodes but invalidate cache
        nodes = gpd.GeoDataFrame(
            {
                "id": [1, 2],
                "lon": [-73.5, -73.6],
                "lat": [45.5, 45.6],
            },
            geometry=[Point(-73.5, 45.5), Point(-73.6, 45.6)],
            crs="EPSG:4326",
        )
        instance._nodes = nodes
        instance.nodes_gdf = None  # type: ignore[assignment]  # Invalidate cache

        node = instance.coordinates_to_nearest_node(-73.55, 45.55)

        assert not node.empty
        assert instance.nodes_gdf is not None

    @patch("sim.DAO.OSMConnection.OSMConnection._initialize_osm_data_file")
    @patch("sim.DAO.OSMConnection.OSMConnection._get_drivable_network")
    @patch("sim.DAO.OSMConnection.OSMConnection.create_networkx_graph")
    def test_coordinates_to_nearest_node_no_nodes_error(
        self,
        mock_create_graph: MagicMock,
        mock_get_drivable: MagicMock,
        mock_init_file: MagicMock,
    ) -> None:
        """Test coordinates_to_nearest_node raises error with no nodes"""
        instance = OSMConnection()

        instance._nodes = gpd.GeoDataFrame()
        instance._set_projected_nodes()

        with pytest.raises(Exception, match="No nodes available"):
            instance.coordinates_to_nearest_node(-73.5, 45.5)


class TestBuildEdgeIndex:
    """Tests for _build_edge_index edge cases"""

    @patch("sim.DAO.OSMConnection.OSMConnection._initialize_osm_data_file")
    @patch("sim.DAO.OSMConnection.OSMConnection._get_drivable_network")
    @patch("sim.DAO.OSMConnection.OSMConnection.create_networkx_graph")
    def test_build_edge_index_without_u_v_columns(
        self,
        mock_create_graph: MagicMock,
        mock_get_drivable: MagicMock,
        mock_init_file: MagicMock,
    ) -> None:
        """Test _build_edge_index skips if u/v columns missing"""
        instance = OSMConnection()

        # Edges without u/v columns
        instance._edges = gpd.GeoDataFrame(
            {"id": [1, 2]},
            geometry=[
                LineString([(0, 0), (1, 1)]),
                LineString([(1, 1), (2, 2)]),
            ],
        )
        instance.edge_index = None

        result = instance._build_edge_index()

        # Should return empty dict since u/v columns missing
        assert isinstance(result, dict)
        assert result == {}

    @patch("sim.DAO.OSMConnection.OSMConnection._initialize_osm_data_file")
    @patch("sim.DAO.OSMConnection.OSMConnection._get_drivable_network")
    @patch("sim.DAO.OSMConnection.OSMConnection.create_networkx_graph")
    def test_build_edge_index_with_valid_edges(
        self,
        mock_create_graph: MagicMock,
        mock_get_drivable: MagicMock,
        mock_init_file: MagicMock,
    ) -> None:
        """Test _build_edge_index creates correct index"""
        instance = OSMConnection()

        instance._edges = gpd.GeoDataFrame(
            {
                "id": [10, 20],
                "u": [1, 2],
                "v": [2, 3],
            },
            geometry=[
                LineString([(0, 0), (1, 1)]),
                LineString([(1, 1), (2, 2)]),
            ],
        )
        instance.edge_index = None

        result = instance._build_edge_index()

        assert isinstance(result, dict)
        assert (1, 2) in result
        assert (2, 3) in result


class TestCreateNetworkXGraph:
    """Tests for create_networkx_graph edge cases"""

    @patch("sim.DAO.OSMConnection.OSMConnection._initialize_osm_data_file")
    @patch("sim.DAO.OSMConnection.OSMConnection._get_drivable_network")
    @patch("sim.DAO.OSMConnection.OSMConnection.create_networkx_graph")
    def test_create_networkx_graph_called_during_init(
        self,
        mock_create_graph: MagicMock,
        mock_get_drivable: MagicMock,
        mock_init_file: MagicMock,
    ) -> None:
        """Test create_networkx_graph is called during initialization"""
        OSMConnection()

        # Verify it was called during __init__
        mock_create_graph.assert_called_once()
