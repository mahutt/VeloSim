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

from unittest.mock import Mock
import pytest

from sim.map.route_controller import RouteController
from sim.entities.road import Road
from sim.entities.position import Position
from sim.entities.osrm_result import OSRMSegment, OSRMResult


class TestRouteControllerInitialization:
    """Tests for RouteController initialization."""

    def test_route_controller_init(self) -> None:
        """Test that RouteController initializes with empty data structures."""
        mock_map_controller = Mock()
        controller = RouteController(mock_map_controller)

        assert controller.map_controller == mock_map_controller
        assert len(controller.roads_to_routes) == 0
        assert len(controller.segment_id_to_road) == 0
        assert len(controller.road_id_to_road) == 0
        assert len(controller.routes) == 0

    def test_route_controller_clear(self) -> None:
        """Test that clear() empties all data structures."""
        mock_map_controller = Mock()
        controller = RouteController(mock_map_controller)

        # Add some dummy data
        mock_road = Mock()
        mock_route = Mock()
        controller.roads_to_routes[mock_road] = {mock_route}
        controller.segment_id_to_road[(123, 456)] = mock_road
        controller.road_id_to_road[789] = mock_road
        controller.routes.add(mock_route)

        controller.clear()

        assert len(controller.roads_to_routes) == 0
        assert len(controller.segment_id_to_road) == 0
        assert len(controller.road_id_to_road) == 0
        assert len(controller.routes) == 0


class TestRouteControllerRoadLookup:
    """Tests for road lookup methods."""

    def test_get_road_by_segment_id(self) -> None:
        """Test looking up a road by segment_id."""
        mock_map_controller = Mock()
        controller = RouteController(mock_map_controller)

        # Create a road directly and register it
        road = Road(
            road_id=123,
            name="Test Road",
            pointcollection=[Position([0.0, 0.0]), Position([0.5, 0.5])],
            length=50.0,
            maxspeed=10.0,
            segment_id=(100, 200),
            node_start=100,
            node_end=200,
        )
        controller.segment_id_to_road[(100, 200)] = road
        controller.road_id_to_road[123] = road

        # Lookup by segment_id
        found_road = controller.get_road_by_segment_id((100, 200))
        assert found_road is road

        # Lookup non-existent
        not_found = controller.get_road_by_segment_id((999, 999))
        assert not_found is None

    def test_get_road_by_id(self) -> None:
        """Test looking up a road by hash-based ID."""
        mock_map_controller = Mock()
        controller = RouteController(mock_map_controller)

        # Create a road directly and register it
        road = Road(
            road_id=456,
            name="Test Road",
            pointcollection=[Position([0.0, 0.0]), Position([0.5, 0.5])],
            length=50.0,
            maxspeed=10.0,
            segment_id=(100, 200),
        )
        controller.road_id_to_road[456] = road

        # Lookup by road.id
        found_road = controller.get_road_by_id(road.id)
        assert found_road is road


class TestRouteControllerRouteRegistration:
    """Tests for route registration and unregistration."""

    def test_register_road_to_route(self) -> None:
        """Test registering a road-to-route mapping."""
        mock_map_controller = Mock()

        controller = RouteController(mock_map_controller)

        mock_road = Mock()
        mock_road.id = 123
        mock_route = Mock()

        controller._register_road_to_route(mock_road, mock_route)

        assert mock_road in controller.roads_to_routes
        assert mock_route in controller.roads_to_routes[mock_road]

    def test_unregister_road_from_route(self) -> None:
        """Test unregistering a road from a route."""
        mock_map_controller = Mock()

        controller = RouteController(mock_map_controller)

        # Create a road with specific properties
        mock_road = Mock()
        mock_road.id = 123
        mock_road.segment_id = (100, 200)
        mock_route = Mock()

        # Register the road first
        controller._register_road_to_route(mock_road, mock_route)
        controller.segment_id_to_road[(100, 200)] = mock_road
        controller.road_id_to_road[123] = mock_road

        # Unregister it
        controller.unregister_road_from_route(mock_road, mock_route)

        # Road should be deallocated since no routes reference it
        assert mock_road not in controller.roads_to_routes
        assert (100, 200) not in controller.segment_id_to_road
        assert 123 not in controller.road_id_to_road

    def test_unregister_route(self) -> None:
        """Test unregistering a route from all its roads."""
        mock_map_controller = Mock()
        controller = RouteController(mock_map_controller)

        mock_road1 = Mock()
        mock_road1.id = 1
        mock_road1.segment_id = (10, 20)
        mock_road2 = Mock()
        mock_road2.id = 2
        mock_road2.segment_id = (20, 30)
        mock_route = Mock()

        controller.routes.add(mock_route)
        controller._register_road_to_route(mock_road1, mock_route)
        controller._register_road_to_route(mock_road2, mock_route)
        controller.segment_id_to_road[(10, 20)] = mock_road1
        controller.segment_id_to_road[(20, 30)] = mock_road2
        controller.road_id_to_road[1] = mock_road1
        controller.road_id_to_road[2] = mock_road2

        controller.unregister_route(mock_route)

        assert mock_route not in controller.routes
        # Roads should be deallocated since no routes reference them
        assert mock_road1 not in controller.roads_to_routes
        assert mock_road2 not in controller.roads_to_routes


class TestRouteControllerQueryMethods:
    """Tests for query methods."""

    def test_get_routes_for_road(self) -> None:
        """Test getting routes that use a specific road."""
        mock_map_controller = Mock()
        controller = RouteController(mock_map_controller)

        mock_road = Mock()
        mock_road.id = 1
        mock_route1 = Mock()
        mock_route2 = Mock()

        controller._register_road_to_route(mock_road, mock_route1)
        controller._register_road_to_route(mock_road, mock_route2)

        routes = controller.get_routes_for_road(mock_road)

        assert len(routes) == 2
        assert mock_route1 in routes
        assert mock_route2 in routes

    def test_get_routes_for_segment_id(self) -> None:
        """Test getting routes by segment_id."""
        mock_map_controller = Mock()
        controller = RouteController(mock_map_controller)

        # Create a road directly and register it
        road = Road(
            road_id=123,
            name="Test Road",
            pointcollection=[Position([0.0, 0.0]), Position([0.5, 0.5])],
            length=50.0,
            maxspeed=10.0,
            segment_id=(100, 200),
        )
        controller.segment_id_to_road[(100, 200)] = road

        mock_route = Mock()
        controller._register_road_to_route(road, mock_route)

        routes = controller.get_routes_for_segment_id((100, 200))

        assert len(routes) == 1
        assert mock_route in routes

    def test_get_all_active_roads(self) -> None:
        """Test getting all active roads."""
        mock_map_controller = Mock()
        controller = RouteController(mock_map_controller)

        mock_road1 = Mock()
        mock_road1.id = 1
        mock_road2 = Mock()
        mock_road2.id = 2
        mock_route = Mock()

        controller._register_road_to_route(mock_road1, mock_route)
        controller._register_road_to_route(mock_road2, mock_route)

        active_roads = controller.get_all_active_roads()

        assert len(active_roads) == 2
        assert mock_road1 in active_roads
        assert mock_road2 in active_roads

    def test_get_active_counts(self) -> None:
        """Test getting active route and road counts."""
        mock_map_controller = Mock()
        controller = RouteController(mock_map_controller)

        mock_road = Mock()
        mock_road.id = 1
        mock_route = Mock()

        controller.routes.add(mock_route)
        controller._register_road_to_route(mock_road, mock_route)

        assert controller.get_active_route_count() == 1
        assert controller.get_active_road_count() == 1


class TestRoadSegmentId:
    """Tests for Road class segment_id support."""

    def test_road_with_segment_id(self) -> None:
        """Test Road creation with segment_id."""
        road = Road(
            road_id=123,
            name="Test Road",
            pointcollection=[Position([0.0, 0.0]), Position([1.0, 1.0])],
            length=100.0,
            maxspeed=13.89,
            segment_id=(100, 200),
            node_start=100,
            node_end=200,
        )

        assert road.segment_id == (100, 200)
        assert road.node_start == 100
        assert road.node_end == 200
        assert road.get_segment_id() == (100, 200)

    def test_road_segment_id_from_nodes(self) -> None:
        """Test Road segment_id constructed from node_start/node_end."""
        road = Road(
            road_id=123,
            name="Test Road",
            pointcollection=[Position([0.0, 0.0]), Position([1.0, 1.0])],
            length=100.0,
            maxspeed=13.89,
            node_start=300,
            node_end=400,
        )

        assert road.segment_id == (300, 400)

    def test_road_without_segment_id(self) -> None:
        """Test Road without segment_id (legacy behavior)."""
        road = Road(
            road_id=123,
            name="Test Road",
            pointcollection=[Position([0.0, 0.0]), Position([1.0, 1.0])],
            length=100.0,
            maxspeed=13.89,
        )

        assert road.segment_id is None
        assert road.get_segment_id() is None

    def test_road_hash_with_segment_id(self) -> None:
        """Test Road hash based on segment_id."""
        road1 = Road(
            road_id=1,
            name="Road 1",
            pointcollection=[Position([0.0, 0.0])],
            length=100.0,
            maxspeed=13.89,
            segment_id=(100, 200),
        )

        road2 = Road(
            road_id=2,  # Different ID
            name="Road 2",  # Different name
            pointcollection=[Position([1.0, 1.0])],  # Different coords
            length=200.0,  # Different length
            maxspeed=20.0,  # Different speed
            segment_id=(100, 200),  # Same segment_id
        )

        # Same hash because same segment_id
        assert hash(road1) == hash(road2)

    def test_road_equality_with_segment_id(self) -> None:
        """Test Road equality based on segment_id."""
        road1 = Road(
            road_id=1,
            name="Road 1",
            pointcollection=[Position([0.0, 0.0])],
            length=100.0,
            maxspeed=13.89,
            segment_id=(100, 200),
        )

        road2 = Road(
            road_id=2,
            name="Road 2",
            pointcollection=[Position([1.0, 1.0])],
            length=200.0,
            maxspeed=20.0,
            segment_id=(100, 200),
        )

        road3 = Road(
            road_id=3,
            name="Road 3",
            pointcollection=[Position([2.0, 2.0])],
            length=300.0,
            maxspeed=25.0,
            segment_id=(300, 400),  # Different segment_id
        )

        assert road1 == road2  # Same segment_id
        assert road1 != road3  # Different segment_id

    def test_road_equality_fallback_to_id(self) -> None:
        """Test Road equality falls back to ID when no segment_id."""
        road1 = Road(
            road_id=123,
            name="Road 1",
            pointcollection=[Position([0.0, 0.0])],
            length=100.0,
            maxspeed=13.89,
        )

        road2 = Road(
            road_id=123,
            name="Road 2",
            pointcollection=[Position([1.0, 1.0])],
            length=200.0,
            maxspeed=20.0,
        )

        road3 = Road(
            road_id=456,
            name="Road 3",
            pointcollection=[Position([2.0, 2.0])],
            length=300.0,
            maxspeed=25.0,
        )

        assert road1 == road2  # Same ID
        assert road1 != road3  # Different ID


class TestOSRMSegment:
    """Tests for OSRMSegment dataclass."""

    def test_osrm_segment_creation(self) -> None:
        """Test OSRMSegment creation."""
        segment = OSRMSegment(
            node_start=100,
            node_end=200,
            distance=50.0,
            duration=5.0,
            geometry=[[0.0, 0.0], [1.0, 1.0]],
            road_name="Test Street",
        )

        assert segment.node_start == 100
        assert segment.node_end == 200
        assert segment.distance == 50.0
        assert segment.duration == 5.0
        assert len(segment.geometry) == 2
        assert segment.road_name == "Test Street"

    def test_osrm_segment_get_segment_id(self) -> None:
        """Test OSRMSegment.get_segment_id() method."""
        segment = OSRMSegment(
            node_start=123,
            node_end=456,
            distance=100.0,
            duration=10.0,
            geometry=[],
        )

        assert segment.get_segment_id() == (123, 456)

    def test_osrm_segment_from_annotation_data(self) -> None:
        """Test OSRMSegment.from_annotation_data() factory method."""
        segment = OSRMSegment.from_annotation_data(
            node_start=111,
            node_end=222,
            distance=75.0,
            duration=7.5,
            geometry=[[0.0, 0.0], [0.5, 0.5], [1.0, 1.0]],
            road_name="Annotation Road",
        )

        assert segment.node_start == 111
        assert segment.node_end == 222
        assert segment.distance == 75.0
        assert segment.duration == 7.5
        assert len(segment.geometry) == 3
        assert segment.road_name == "Annotation Road"


class TestRouteControllerPointGeneration:
    """Tests for _generate_point_collection method."""

    def test_generate_point_collection_empty_geometry(self) -> None:
        """Test point generation with empty geometry."""
        mock_map_controller = Mock()
        controller = RouteController(mock_map_controller)

        result = controller._generate_point_collection([], 100.0, 10.0)

        assert result == []

    def test_generate_point_collection_invalid_speed(self) -> None:
        """Test point generation with zero/negative speed."""
        mock_map_controller = Mock()
        controller = RouteController(mock_map_controller)

        geometry = [[0.0, 0.0], [1.0, 1.0]]

        # Zero speed should return edge points
        result = controller._generate_point_collection(geometry, 100.0, 0.0)

        assert len(result) == 2
        assert result[0].get_position() == [0.0, 0.0]
        assert result[1].get_position() == [1.0, 1.0]

    def test_generate_point_collection_invalid_length(self) -> None:
        """Test point generation with zero/negative length."""
        mock_map_controller = Mock()
        controller = RouteController(mock_map_controller)

        geometry = [[0.0, 0.0], [1.0, 1.0]]

        # Zero length should return edge points
        result = controller._generate_point_collection(geometry, 0.0, 10.0)

        assert len(result) == 2
        assert result[0].get_position() == [0.0, 0.0]
        assert result[1].get_position() == [1.0, 1.0]

    def test_generate_point_collection_normal_case(self) -> None:
        """Test normal point generation with valid inputs."""
        mock_map_controller = Mock()
        controller = RouteController(mock_map_controller)

        geometry = [[0.0, 0.0], [100.0, 0.0]]

        # 100m length at 10m/s = 10 seconds
        result = controller._generate_point_collection(geometry, 100.0, 10.0)

        # Should have multiple interpolated points
        assert len(result) > 1

    def test_generate_point_collection_final_segment(self) -> None:
        """Test point generation for final segment includes endpoint."""
        mock_map_controller = Mock()
        controller = RouteController(mock_map_controller)

        geometry = [[0.0, 0.0], [100.0, 0.0]]

        result = controller._generate_point_collection(
            geometry, 100.0, 10.0, is_final_segment=True
        )

        # Final point should be included
        assert len(result) > 0


class TestRouteControllerRouteCreation:
    """Tests for route creation from OSRM results."""

    def test_get_route_from_positions_no_route(self) -> None:
        """Test get_route_from_positions when no route is found."""
        mock_map_controller = Mock()
        controller = RouteController(mock_map_controller)

        mock_osrm = Mock()
        mock_osrm.shortest_path_coords.return_value = None

        start = Position([0.0, 0.0])
        end = Position([1.0, 1.0])

        with pytest.raises(ValueError, match="No route found"):
            controller.get_route_from_positions(start, end, mock_osrm, {})

    def test_get_route_from_positions_success(self) -> None:
        """Test successful route creation from positions."""
        mock_map_controller = Mock()
        controller = RouteController(mock_map_controller)

        mock_osrm = Mock()
        # Return the processed format that OSRMResult.from_dict expects
        mock_osrm.shortest_path_coords.return_value = {
            "coordinates": [[0.0, 0.0], [1.0, 1.0]],
            "distance": 100.0,
            "duration": 10.0,
            "steps": [
                {
                    "geometry": [[0.0, 0.0], [1.0, 1.0]],
                    "distance": 100.0,
                    "duration": 10.0,
                    "name": "Test Road",
                    "mode": "driving",
                    "maneuver": "depart",
                }
            ],
            "segments": [],
        }

        start = Position([0.0, 0.0])
        end = Position([1.0, 1.0])

        route = controller.get_route_from_positions(start, end, mock_osrm, {})

        assert route is not None
        assert route in controller.routes

    def test_create_route_empty_steps(self) -> None:
        """Test create_route with empty steps."""
        mock_map_controller = Mock()
        controller = RouteController(mock_map_controller)

        mock_osrm = Mock()

        osrm_result = OSRMResult(
            coordinates=[[0.0, 0.0], [1.0, 1.0]],
            distance=100.0,
            duration=10.0,
            steps=[],
        )

        route = controller.create_route(osrm_result, mock_osrm, {})

        assert route is not None
        assert len(route.roads) == 0


class TestRouteControllerStepToSegmentMapping:
    """Tests for _map_step_to_segment_ids method."""

    def test_map_step_to_segment_ids_empty(self) -> None:
        """Test mapping with empty inputs."""
        mock_map_controller = Mock()
        controller = RouteController(mock_map_controller)

        result = controller._map_step_to_segment_ids([], [])

        assert result == (None, None)

    def test_map_step_to_segment_ids_no_match(self) -> None:
        """Test mapping when no segments match."""
        mock_map_controller = Mock()
        controller = RouteController(mock_map_controller)

        step_geometry = [[0.0, 0.0], [1.0, 1.0]]
        segments = [
            OSRMSegment(
                node_start=100,
                node_end=200,
                distance=50.0,
                duration=5.0,
                geometry=[[10.0, 10.0], [11.0, 11.0]],  # Different coords
            )
        ]

        result = controller._map_step_to_segment_ids(step_geometry, segments)

        assert result == (None, None)

    def test_map_step_to_segment_ids_with_match(self) -> None:
        """Test mapping with matching segments."""
        mock_map_controller = Mock()
        controller = RouteController(mock_map_controller)

        step_geometry = [[0.0, 0.0], [1.0, 1.0]]
        segments = [
            OSRMSegment(
                node_start=100,
                node_end=200,
                distance=50.0,
                duration=5.0,
                geometry=[[0.0, 0.0], [0.5, 0.5]],  # Start matches
            ),
            OSRMSegment(
                node_start=200,
                node_end=300,
                distance=50.0,
                duration=5.0,
                geometry=[[0.5, 0.5], [1.0, 1.0]],  # End matches
            ),
        ]

        result = controller._map_step_to_segment_ids(step_geometry, segments)

        assert result == (100, 300)


class TestRoadEquality:
    """Additional tests for Road equality edge cases."""

    def test_road_eq_with_non_road(self) -> None:
        """Test Road equality with non-Road object."""
        road = Road(
            road_id=123,
            name="Test Road",
            pointcollection=[Position([0.0, 0.0])],
            length=100.0,
            maxspeed=13.89,
        )

        result = road.__eq__("not a road")

        assert result is NotImplemented

    def test_road_hash_fallback_to_id(self) -> None:
        """Test Road hash falls back to ID when no segment_id."""
        road = Road(
            road_id=123,
            name="Test Road",
            pointcollection=[Position([0.0, 0.0])],
            length=100.0,
            maxspeed=13.89,
            segment_id=None,
        )

        assert hash(road) == hash(123)
