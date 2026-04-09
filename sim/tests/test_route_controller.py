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

from sim.map import route_controller as route_controller_module
from sim.map.route_controller import RouteController
from sim.map.position_registry import PositionRegistry
from sim.entities.map_payload import MapPayload
from sim.entities.road import Road
from sim.entities.position import Position
from sim.map.routing_provider import RouteSegment, RouteResult, RouteStep


class TestRouteControllerInitialization:
    """Tests for RouteController initialization."""

    def test_route_controller_init(self) -> None:
        """Test that RouteController initializes with empty data structures."""
        mock_map_controller = Mock()
        controller = RouteController(mock_map_controller, PositionRegistry())

        assert controller.map_controller == mock_map_controller
        assert len(controller.roads_to_routes) == 0
        assert len(controller.segment_key_to_road) == 0
        assert len(controller.road_id_to_road) == 0
        assert len(controller.routes) == 0

    def test_route_controller_init_logs_when_report_missing(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Missing SimulationReport is logged because metrics will use fallback mode."""
        mock_map_controller = Mock()
        warning = Mock()
        monkeypatch.setattr(route_controller_module.logger, "warning", warning)

        RouteController(mock_map_controller, PositionRegistry())

        warning.assert_called_once()
        assert "using internal vehicle-distance tracking" in warning.call_args[0][0]

    def test_route_controller_clear(self) -> None:
        """Test that clear() empties all data structures."""
        mock_map_controller = Mock()
        controller = RouteController(mock_map_controller, PositionRegistry())

        # Add some dummy data
        mock_road = Mock()
        mock_route = Mock()
        segment_key = ((0.0, 0.0), (1.0, 1.0))
        controller.roads_to_routes[mock_road] = {mock_route}
        controller.segment_key_to_road[segment_key] = mock_road
        controller.road_id_to_road[789] = mock_road
        controller.routes.add(mock_route)

        controller.clear()

        assert len(controller.roads_to_routes) == 0
        assert len(controller.segment_key_to_road) == 0
        assert len(controller.road_id_to_road) == 0
        assert len(controller.routes) == 0

    def test_route_controller_uses_map_payload_for_route_interval(self) -> None:
        """Route interval should be resolved from MapPayload runtime settings."""
        mock_map_controller = Mock()
        map_payload = MapPayload(route_recalculation_interval_minutes=1)

        controller = RouteController(
            mock_map_controller,
            PositionRegistry(),
            map_payload=map_payload,
        )

        mock_routing_provider = Mock()
        route_result = RouteResult(
            coordinates=[Position([0.0, 0.0]), Position([1.0, 1.0])],
            distance=100.0,
            duration=10.0,
            steps=[],
            segments=[],
        )

        first_route = controller.create_route(
            route_result,
            mock_routing_provider,
            {"simulation": {"route_recalculation_interval_minutes": 999}},
        )

        assert first_route._route_recalculation_interval_seconds == 60

    def test_route_controller_defaults_interval_when_payload_missing(self) -> None:
        """Route interval should default to 30 minutes when payload is absent."""
        mock_map_controller = Mock()
        controller = RouteController(mock_map_controller, PositionRegistry())

        mock_routing_provider = Mock()
        route_result = RouteResult(
            coordinates=[Position([0.0, 0.0]), Position([1.0, 1.0])],
            distance=100.0,
            duration=10.0,
            steps=[],
            segments=[],
        )

        route = controller.create_route(route_result, mock_routing_provider, {})

        assert route._route_recalculation_interval_seconds == 1800


class TestRouteControllerRoadLookup:
    """Tests for road lookup methods."""

    def test_get_road_by_segment_key(self) -> None:
        """Test looking up a road by segment_key (geometry endpoints)."""
        mock_map_controller = Mock()
        controller = RouteController(mock_map_controller, PositionRegistry())

        # Create a road directly and register it
        road = Road(
            road_id=123,
            name="Test Road",
            pointcollection=[Position([0.0, 0.0]), Position([0.5, 0.5])],
            length=50.0,
            maxspeed=10.0,
        )
        segment_key = road.segment_key  # ((0.0, 0.0), (0.5, 0.5))
        controller.segment_key_to_road[segment_key] = road
        controller.road_id_to_road[123] = road

        # Lookup by segment_key
        found_road = controller.get_road_by_segment_key(segment_key)
        assert found_road is road

        # Lookup non-existent
        not_found = controller.get_road_by_segment_key(((999.0, 999.0), (888.0, 888.0)))
        assert not_found is None

    def test_get_road_by_id(self) -> None:
        """Test looking up a road by hash-based ID."""
        mock_map_controller = Mock()
        controller = RouteController(mock_map_controller, PositionRegistry())

        # Create a road directly and register it
        road = Road(
            road_id=456,
            name="Test Road",
            pointcollection=[Position([0.0, 0.0]), Position([0.5, 0.5])],
            length=50.0,
            maxspeed=10.0,
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

        controller = RouteController(mock_map_controller, PositionRegistry())

        mock_road = Mock()
        mock_road.id = 123
        mock_route = Mock()

        controller._register_road_to_route(mock_road, mock_route)

        assert mock_road in controller.roads_to_routes
        assert mock_route in controller.roads_to_routes[mock_road]

    def test_unregister_road_from_route(self) -> None:
        """Test unregistering a road from a route."""
        mock_map_controller = Mock()

        controller = RouteController(mock_map_controller, PositionRegistry())

        # Create a road with specific properties (geometry-based segment_key)
        mock_road = Mock()
        mock_road.id = 123
        mock_road.segment_key = ((0.0, 0.0), (1.0, 1.0))
        mock_road.nodes = []  # Empty list for mock road
        mock_route = Mock()

        # Register the road first
        controller._register_road_to_route(mock_road, mock_route)
        controller.segment_key_to_road[((0.0, 0.0), (1.0, 1.0))] = mock_road
        controller.road_id_to_road[123] = mock_road

        # Unregister it
        controller.unregister_road_from_route(mock_road, mock_route)

        # Road should be deallocated since no routes reference it
        assert mock_road not in controller.roads_to_routes
        assert ((0.0, 0.0), (1.0, 1.0)) not in controller.segment_key_to_road
        assert 123 not in controller.road_id_to_road

    def test_unregister_route(self) -> None:
        """Test unregistering a route from all its roads."""
        mock_map_controller = Mock()
        controller = RouteController(mock_map_controller, PositionRegistry())

        mock_road1 = Mock()
        mock_road1.id = 1
        mock_road1.segment_key = ((0.0, 0.0), (1.0, 1.0))
        mock_road1.nodes = []  # Empty list for mock road
        mock_road2 = Mock()
        mock_road2.id = 2
        mock_road2.segment_key = ((1.0, 1.0), (2.0, 2.0))
        mock_road2.nodes = []  # Empty list for mock road
        mock_route = Mock()
        mock_route.get_distance_traveled.return_value = 0.0

        controller.routes.add(mock_route)
        controller._register_road_to_route(mock_road1, mock_route)
        controller._register_road_to_route(mock_road2, mock_route)
        controller.segment_key_to_road[((0.0, 0.0), (1.0, 1.0))] = mock_road1
        controller.segment_key_to_road[((1.0, 1.0), (2.0, 2.0))] = mock_road2
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
        controller = RouteController(mock_map_controller, PositionRegistry())

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

    def test_get_routes_for_segment_key(self) -> None:
        """Test getting routes by segment_key (geometry endpoints)."""
        mock_map_controller = Mock()
        controller = RouteController(mock_map_controller, PositionRegistry())

        # Create a road directly and register it
        road = Road(
            road_id=123,
            name="Test Road",
            pointcollection=[Position([0.0, 0.0]), Position([0.5, 0.5])],
            length=50.0,
            maxspeed=10.0,
        )
        segment_key = road.segment_key  # ((0.0, 0.0), (0.5, 0.5))
        controller.segment_key_to_road[segment_key] = road

        mock_route = Mock()
        controller._register_road_to_route(road, mock_route)

        routes = controller.get_routes_for_segment_key(segment_key)

        assert len(routes) == 1
        assert mock_route in routes

    def test_get_all_active_roads(self) -> None:
        """Test getting all active roads."""
        mock_map_controller = Mock()
        controller = RouteController(mock_map_controller, PositionRegistry())

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
        controller = RouteController(mock_map_controller, PositionRegistry())

        mock_road = Mock()
        mock_road.id = 1
        mock_route = Mock()

        controller.routes.add(mock_route)
        controller._register_road_to_route(mock_road, mock_route)

        assert controller.get_active_route_count() == 1
        assert controller.get_active_road_count() == 1


class TestRoadSegmentKey:
    """Tests for Road class segment_key (geometry-based identification)."""

    def test_road_segment_key_property(self) -> None:
        """Test Road segment_key derived from geometry endpoints."""
        road = Road(
            road_id=123,
            name="Test Road",
            pointcollection=[Position([0.0, 0.0]), Position([1.0, 1.0])],
            length=100.0,
            maxspeed=13.89,
        )

        # segment_key is based on start/end coordinates
        expected_key = ((0.0, 0.0), (1.0, 1.0))
        assert road.segment_key == expected_key

    def test_road_segment_key_multipoint(self) -> None:
        """Test Road segment_key with multiple intermediate points."""
        road = Road(
            road_id=123,
            name="Test Road",
            pointcollection=[
                Position([0.0, 0.0]),
                Position([0.5, 0.5]),  # Intermediate point
                Position([0.7, 0.8]),  # Another intermediate
                Position([1.0, 1.0]),
            ],
            length=100.0,
            maxspeed=13.89,
        )

        # segment_key only uses first and last points
        expected_key = ((0.0, 0.0), (1.0, 1.0))
        assert road.segment_key == expected_key

    def test_road_hash_based_on_segment_key(self) -> None:
        """Test Road hash based on segment_key (geometry endpoints)."""
        road1 = Road(
            road_id=1,
            name="Road 1",
            pointcollection=[Position([0.0, 0.0]), Position([1.0, 1.0])],
            length=100.0,
            maxspeed=13.89,
        )

        road2 = Road(
            road_id=2,  # Different ID
            name="Road 2",  # Different name
            pointcollection=[
                Position([0.0, 0.0]),
                Position([1.0, 1.0]),
            ],  # Same endpoints
            length=200.0,  # Different length
            maxspeed=20.0,  # Different speed
        )

        # Same hash because same segment_key (start/end coords)
        assert hash(road1) == hash(road2)

    def test_road_equality_based_on_segment_key(self) -> None:
        """Test Road equality based on segment_key (geometry endpoints)."""
        road1 = Road(
            road_id=1,
            name="Road 1",
            pointcollection=[Position([0.0, 0.0]), Position([1.0, 1.0])],
            length=100.0,
            maxspeed=13.89,
        )

        road2 = Road(
            road_id=2,
            name="Road 2",
            pointcollection=[
                Position([0.0, 0.0]),
                Position([1.0, 1.0]),
            ],  # Same endpoints
            length=200.0,
            maxspeed=20.0,
        )

        road3 = Road(
            road_id=3,
            name="Road 3",
            pointcollection=[
                Position([2.0, 2.0]),
                Position([3.0, 3.0]),
            ],  # Different endpoints
            length=300.0,
            maxspeed=25.0,
        )

        assert road1 == road2  # Same segment_key
        assert road1 != road3  # Different segment_key

    def test_road_different_intermediate_points_same_key(self) -> None:
        """Test roads with different intermediates but same endpoints are equal."""
        road1 = Road(
            road_id=1,
            name="Road 1",
            pointcollection=[
                Position([0.0, 0.0]),
                Position([0.25, 0.25]),  # Different intermediates
                Position([1.0, 1.0]),
            ],
            length=100.0,
            maxspeed=13.89,
        )

        road2 = Road(
            road_id=2,
            name="Road 2",
            pointcollection=[
                Position([0.0, 0.0]),
                Position([0.5, 0.5]),  # Different intermediates
                Position([0.75, 0.75]),
                Position([1.0, 1.0]),
            ],
            length=150.0,
            maxspeed=15.0,
        )

        # Same segment_key because same start/end points
        assert road1.segment_key == road2.segment_key
        assert road1 == road2
        assert hash(road1) == hash(road2)


class TestRouteSegment:
    """Tests for RouteSegment dataclass."""

    def test_route_segment_creation(self) -> None:
        """Test RouteSegment creation (provider-neutral, geometry-based)."""
        segment = RouteSegment(
            distance=50.0,
            duration=5.0,
            geometry=[Position([0.0, 0.0]), Position([1.0, 1.0])],
            road_name="Test Street",
            maxspeed=10.0,
        )

        assert segment.distance == 50.0
        assert segment.duration == 5.0
        assert len(segment.geometry) == 2
        assert segment.road_name == "Test Street"
        assert segment.maxspeed == 10.0

    def test_route_segment_segment_key(self) -> None:
        """Test RouteSegment segment_key property (geometry-based identification)."""
        segment = RouteSegment(
            distance=50.0,
            duration=5.0,
            geometry=[Position([0.0, 0.0]), Position([0.5, 0.5]), Position([1.0, 1.0])],
        )

        # segment_key is based on start/end coordinates
        expected_key = ((0.0, 0.0), (1.0, 1.0))
        assert segment.segment_key == expected_key

    def test_route_segment_default_values(self) -> None:
        """Test RouteSegment with default values."""
        segment = RouteSegment(
            distance=100.0,
            duration=10.0,
            geometry=[Position([0.0, 0.0]), Position([1.0, 1.0])],
        )

        assert segment.road_name is None
        assert segment.maxspeed is None


class TestRouteControllerPointGeneration:
    """Tests for generate_point_collection method."""

    def test_generate_point_collection_empty_geometry(self) -> None:
        """Test point generation with empty geometry."""
        mock_map_controller = Mock()
        controller = RouteController(mock_map_controller, PositionRegistry())

        result = controller.generate_point_collection([], 100.0, 10.0)

        assert result == []

    def test_generate_point_collection_invalid_speed(self) -> None:
        """Test point generation with zero/negative speed."""
        mock_map_controller = Mock()
        controller = RouteController(mock_map_controller, PositionRegistry())

        geometry = [Position([0.0, 0.0]), Position([1.0, 1.0])]

        # Zero speed should return edge points
        result = controller.generate_point_collection(geometry, 100.0, 0.0)

        assert len(result) == 2
        assert result[0].get_position() == [0.0, 0.0]
        assert result[1].get_position() == [1.0, 1.0]

    def test_generate_point_collection_invalid_length(self) -> None:
        """Test point generation with zero/negative length."""
        mock_map_controller = Mock()
        controller = RouteController(mock_map_controller, PositionRegistry())

        geometry = [Position([0.0, 0.0]), Position([1.0, 1.0])]

        # Zero length should return edge points
        result = controller.generate_point_collection(geometry, 0.0, 10.0)

        assert len(result) == 2
        assert result[0].get_position() == [0.0, 0.0]
        assert result[1].get_position() == [1.0, 1.0]

    def test_generate_point_collection_normal_case(self) -> None:
        """Test normal point generation with valid inputs."""
        mock_map_controller = Mock()
        controller = RouteController(mock_map_controller, PositionRegistry())

        geometry = [Position([0.0, 0.0]), Position([100.0, 0.0])]

        # 100m length at 10m/s = 10 seconds
        result = controller.generate_point_collection(geometry, 100.0, 10.0)

        # Should have multiple interpolated points
        assert len(result) > 1

    def test_generate_point_collection_final_segment(self) -> None:
        """Test point generation for final segment includes endpoint."""
        mock_map_controller = Mock()
        controller = RouteController(mock_map_controller, PositionRegistry())

        geometry = [Position([0.0, 0.0]), Position([100.0, 0.0])]

        result = controller.generate_point_collection(
            geometry, 100.0, 10.0, is_final_segment=True
        )

        # Final point should be included
        assert len(result) > 0


class TestRouteControllerRouteCreation:
    """Tests for route creation from routing results."""

    def test_get_route_from_positions_no_route(self) -> None:
        """Test get_route_from_positions when no route is found."""
        mock_map_controller = Mock()
        controller = RouteController(mock_map_controller, PositionRegistry())

        mock_routing_provider = Mock()
        mock_routing_provider.get_route.return_value = None

        start = Position([0.0, 0.0])
        end = Position([1.0, 1.0])

        with pytest.raises(ValueError, match="No route found"):
            controller.get_route_from_positions(start, end, mock_routing_provider, {})

    def test_get_route_from_positions_success(self) -> None:
        """Test successful route creation from positions."""
        mock_map_controller = Mock()
        controller = RouteController(mock_map_controller, PositionRegistry())

        mock_routing_provider = Mock()
        # Return a RouteResult object
        mock_routing_provider.get_route.return_value = RouteResult(
            coordinates=[Position([0.0, 0.0]), Position([1.0, 1.0])],
            distance=100.0,
            duration=10.0,
            steps=[
                RouteStep(
                    name="Test Road",
                    distance=100.0,
                    duration=10.0,
                    geometry=[Position([0.0, 0.0]), Position([1.0, 1.0])],
                )
            ],
            segments=[],
        )

        start = Position([0.0, 0.0])
        end = Position([1.0, 1.0])

        route = controller.get_route_from_positions(
            start, end, mock_routing_provider, {}
        )

        assert route is not None
        assert route in controller.routes

    def test_create_route_empty_steps(self) -> None:
        """Test create_route with empty steps."""
        mock_map_controller = Mock()
        controller = RouteController(mock_map_controller, PositionRegistry())

        mock_routing_provider = Mock()

        route_result = RouteResult(
            coordinates=[Position([0.0, 0.0]), Position([1.0, 1.0])],
            distance=100.0,
            duration=10.0,
            steps=[],
            segments=[],
        )

        route = controller.create_route(route_result, mock_routing_provider, {})

        assert route is not None
        assert len(route.roads) == 0

    def test_create_route_registers_stop_signs_for_road(self) -> None:
        """Stop signs from route metadata should be associated to overlapping roads."""
        mock_map_controller = Mock()
        controller = RouteController(mock_map_controller, PositionRegistry())

        mock_routing_provider = Mock()
        stop_sign_pos = Position([1.0, 1.0])

        route_result = RouteResult(
            coordinates=[Position([0.0, 0.0]), Position([1.0, 1.0])],
            distance=100.0,
            duration=10.0,
            steps=[
                RouteStep(
                    name="Test Road",
                    distance=100.0,
                    duration=10.0,
                    geometry=[Position([0.0, 0.0]), stop_sign_pos],
                )
            ],
            segments=[],
            stop_sign_positions=[stop_sign_pos],
        )

        route = controller.create_route(route_result, mock_routing_provider, {})

        assert route.roads
        road = route.roads[0]
        assert controller.has_stop_sign_for_road(road)
        signs = controller.get_stop_signs_for_road(road)
        assert any(p.get_position() == stop_sign_pos.get_position() for p in signs)

    def test_create_route_registers_nearby_stop_signs_for_road(self) -> None:
        """Nearby stop-sign positions should map to roads even when not exact."""
        mock_map_controller = Mock()
        controller = RouteController(mock_map_controller, PositionRegistry())

        mock_routing_provider = Mock()
        road_endpoint = Position([1.0, 1.0])
        nearby_stop_sign = Position([1.00005, 1.00005])

        route_result = RouteResult(
            coordinates=[Position([0.0, 0.0]), road_endpoint],
            distance=100.0,
            duration=10.0,
            steps=[
                RouteStep(
                    name="Test Road",
                    distance=100.0,
                    duration=10.0,
                    geometry=[Position([0.0, 0.0]), road_endpoint],
                )
            ],
            segments=[],
            stop_sign_positions=[nearby_stop_sign],
        )

        route = controller.create_route(route_result, mock_routing_provider, {})

        assert route.roads
        road = route.roads[0]
        assert controller.has_stop_sign_for_road(road)
        assert controller.is_stop_sign_at_position(road, road_endpoint)

    def test_create_route_registers_traffic_lights_for_road(self) -> None:
        """Traffic lights from route metadata should be associated to roads."""
        mock_map_controller = Mock()
        controller = RouteController(mock_map_controller, PositionRegistry())

        mock_routing_provider = Mock()
        traffic_light_pos = Position([1.0, 1.0])

        route_result = RouteResult(
            coordinates=[Position([0.0, 0.0]), Position([1.0, 1.0])],
            distance=100.0,
            duration=10.0,
            steps=[
                RouteStep(
                    name="Test Road",
                    distance=100.0,
                    duration=10.0,
                    geometry=[Position([0.0, 0.0]), traffic_light_pos],
                )
            ],
            segments=[],
            traffic_light_positions=[traffic_light_pos],
        )

        route = controller.create_route(route_result, mock_routing_provider, {})

        assert route.roads
        road = route.roads[0]
        assert controller.has_traffic_light_for_road(road)
        lights = controller.get_traffic_lights_for_road(road)
        assert any(p.get_position() == traffic_light_pos.get_position() for p in lights)

    def test_clusters_nearby_stop_signs_on_same_road(self) -> None:
        """Very close stop signs on the same approach should produce one stop event."""
        mock_map_controller = Mock()
        controller = RouteController(mock_map_controller, PositionRegistry())

        mock_routing_provider = Mock()
        route_result = RouteResult(
            coordinates=[Position([0.0, 0.0]), Position([0.001, 0.0])],
            distance=100.0,
            duration=10.0,
            steps=[
                RouteStep(
                    name="Approach Road",
                    distance=100.0,
                    duration=10.0,
                    geometry=[Position([0.0, 0.0]), Position([0.001, 0.0])],
                )
            ],
            segments=[],
            stop_sign_positions=[
                Position([0.00101, 0.00001]),
                Position([0.001015, 0.00001]),
            ],
        )

        route = controller.create_route(route_result, mock_routing_provider, {})
        road = route.roads[0]

        assert controller.has_stop_sign_for_road(road)
        assert len(controller.get_stop_signs_for_road(road)) == 1

    def test_near_intersection_stop_sign_maps_to_best_matching_road(self) -> None:
        """Stop signs near intersections should not attach to perpendicular roads."""
        mock_map_controller = Mock()
        controller = RouteController(mock_map_controller, PositionRegistry())

        mock_routing_provider = Mock()
        horizontal_intersection = Position([0.0, 0.0])
        vertical_stop_sign = Position([0.0, 0.00009])

        route_result = RouteResult(
            coordinates=[Position([-0.0002, 0.0]), Position([0.0002, 0.0])],
            distance=200.0,
            duration=20.0,
            steps=[
                RouteStep(
                    name="Horizontal Road",
                    distance=100.0,
                    duration=10.0,
                    geometry=[
                        Position([-0.0002, 0.0]),
                        horizontal_intersection,
                        Position([0.0002, 0.0]),
                    ],
                ),
                RouteStep(
                    name="Vertical Road",
                    distance=100.0,
                    duration=10.0,
                    geometry=[
                        Position([0.0, -0.0002]),
                        horizontal_intersection,
                        Position([0.0, 0.0002]),
                    ],
                ),
            ],
            segments=[],
            stop_sign_positions=[vertical_stop_sign],
        )

        route = controller.create_route(route_result, mock_routing_provider, {})

        horizontal_road = route.roads[0]
        vertical_road = route.roads[1]

        assert not controller.has_stop_sign_for_road(horizontal_road)
        assert controller.has_stop_sign_for_road(vertical_road)

    def test_stop_sign_mapping_cleared_on_road_deallocation(self) -> None:
        """Stop-sign associations should be removed when a road is deallocated."""
        mock_map_controller = Mock()
        controller = RouteController(mock_map_controller, PositionRegistry())

        mock_routing_provider = Mock()
        stop_sign_pos = Position([1.0, 1.0])

        route_result = RouteResult(
            coordinates=[Position([0.0, 0.0]), Position([1.0, 1.0])],
            distance=100.0,
            duration=10.0,
            steps=[
                RouteStep(
                    name="Test Road",
                    distance=100.0,
                    duration=10.0,
                    geometry=[Position([0.0, 0.0]), stop_sign_pos],
                )
            ],
            segments=[],
            stop_sign_positions=[stop_sign_pos],
        )

        route = controller.create_route(route_result, mock_routing_provider, {})
        road = route.roads[0]

        assert controller.has_stop_sign_for_road(road)

        controller.unregister_route(route)

        assert not controller.has_stop_sign_for_road(road)


class TestRoadEquality:
    """Additional tests for Road equality edge cases."""

    def test_road_eq_with_non_road(self) -> None:
        """Test Road equality with non-Road object."""
        road = Road(
            road_id=123,
            name="Test Road",
            pointcollection=[Position([0.0, 0.0]), Position([1.0, 1.0])],
            length=100.0,
            maxspeed=13.89,
        )

        result = road.__eq__("not a road")

        assert result is NotImplemented

    def test_road_hash_uses_segment_key(self) -> None:
        """Test Road hash is based on segment_key (geometry endpoints)."""
        road = Road(
            road_id=123,
            name="Test Road",
            pointcollection=[Position([0.0, 0.0]), Position([1.0, 1.0])],
            length=100.0,
            maxspeed=13.89,
        )

        # Hash is based on segment_key
        expected_key = ((0.0, 0.0), (1.0, 1.0))
        assert hash(road) == hash(expected_key)


class TestRoadDeallocationCallbacks:
    """Tests for road deallocation callback mechanism."""

    def test_register_on_road_deallocated_callback(self) -> None:
        """Test that callbacks are registered and called on deallocation."""
        mock_map_controller = Mock()
        controller = RouteController(mock_map_controller, PositionRegistry())

        # Track callback invocations
        callback_calls: list[Road] = []

        def on_dealloc(road: Road) -> None:
            callback_calls.append(road)

        controller.register_on_road_deallocated(on_dealloc)

        # Create and register a road
        mock_road = Mock()
        mock_road.id = 123
        mock_road.segment_key = ((0.0, 0.0), (1.0, 1.0))
        mock_road.nodes = []  # Empty list for mock road
        mock_route = Mock()

        controller._register_road_to_route(mock_road, mock_route)
        controller.segment_key_to_road[mock_road.segment_key] = mock_road
        controller.road_id_to_road[mock_road.id] = mock_road

        # Unregister to trigger deallocation
        controller.unregister_road_from_route(mock_road, mock_route)

        # Callback should have been called with the road
        assert len(callback_calls) == 1
        assert callback_calls[0] is mock_road

    def test_multiple_callbacks_called_on_deallocation(self) -> None:
        """Test that multiple registered callbacks are all called."""
        mock_map_controller = Mock()
        controller = RouteController(mock_map_controller, PositionRegistry())

        callback1_calls: list[Road] = []
        callback2_calls: list[Road] = []

        controller.register_on_road_deallocated(lambda r: callback1_calls.append(r))
        controller.register_on_road_deallocated(lambda r: callback2_calls.append(r))

        mock_road = Mock()
        mock_road.id = 1
        mock_road.segment_key = ((0.0, 0.0), (1.0, 1.0))
        mock_road.nodes = []  # Empty list for mock road
        mock_route = Mock()

        controller._register_road_to_route(mock_road, mock_route)
        controller.segment_key_to_road[mock_road.segment_key] = mock_road
        controller.road_id_to_road[mock_road.id] = mock_road

        controller.unregister_road_from_route(mock_road, mock_route)

        assert len(callback1_calls) == 1
        assert len(callback2_calls) == 1

    def test_unregister_on_road_deallocated_success(self) -> None:
        """Test that unregister_on_road_deallocated removes a callback."""
        mock_map_controller = Mock()
        controller = RouteController(mock_map_controller, PositionRegistry())

        callback_calls: list[Road] = []

        def on_dealloc(road: Road) -> None:
            callback_calls.append(road)

        controller.register_on_road_deallocated(on_dealloc)

        # Unregister the callback
        result = controller.unregister_on_road_deallocated(on_dealloc)

        assert result is True

        # Create and deallocate a road - callback should NOT be called
        mock_road = Mock()
        mock_road.id = 123
        mock_road.segment_key = ((0.0, 0.0), (1.0, 1.0))
        mock_road.nodes = []  # Empty list for mock road
        mock_route = Mock()

        controller._register_road_to_route(mock_road, mock_route)
        controller.segment_key_to_road[mock_road.segment_key] = mock_road
        controller.road_id_to_road[mock_road.id] = mock_road

        controller.unregister_road_from_route(mock_road, mock_route)

        # Callback should NOT have been called since it was unregistered
        assert len(callback_calls) == 0

    def test_unregister_on_road_deallocated_not_found(self) -> None:
        """Test that unregister returns False for non-existent callback."""
        mock_map_controller = Mock()
        controller = RouteController(mock_map_controller, PositionRegistry())

        def some_callback(road: Road) -> None:
            pass

        # Try to unregister a callback that was never registered
        result = controller.unregister_on_road_deallocated(some_callback)

        assert result is False

    def test_clear_removes_all_callbacks(self) -> None:
        """Test that clear() removes all registered callbacks."""
        mock_map_controller = Mock()
        controller = RouteController(mock_map_controller, PositionRegistry())

        callback_calls: list[Road] = []

        def on_dealloc(road: Road) -> None:
            callback_calls.append(road)

        controller.register_on_road_deallocated(on_dealloc)

        # Clear the controller
        controller.clear()

        # Verify callbacks list is empty by trying to unregister
        result = controller.unregister_on_road_deallocated(on_dealloc)
        assert result is False  # Callback no longer exists


class TestTotalVehicleDistance:
    """Tests for get_total_vehicle_distance() aggregation."""

    def _make_controller(self) -> RouteController:
        return RouteController(Mock(), PositionRegistry())

    def test_initial_distance_is_zero(self) -> None:
        """Total distance is 0.0 on a fresh controller."""
        controller = self._make_controller()
        assert controller.get_total_vehicle_distance() == 0.0

    def test_fallback_distance_path_logs_once(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Fallback aggregation path logs once for missing report-backed metrics."""
        warning = Mock()
        monkeypatch.setattr(route_controller_module.logger, "warning", warning)
        controller = self._make_controller()

        assert controller.get_total_vehicle_distance() == 0.0
        assert controller.get_total_vehicle_distance() == 0.0

        assert warning.call_count == 2
        assert (
            "using internal vehicle-distance tracking"
            in warning.call_args_list[0][0][0]
        )
        assert (
            "returning distance from internal route tracking"
            in warning.call_args_list[1][0][0]
        )

    def test_active_routes_contribute_distance(self) -> None:
        """Active routes' get_distance_traveled() is summed."""
        controller = self._make_controller()

        route1 = Mock()
        route1.get_distance_traveled.return_value = 150.0
        route2 = Mock()
        route2.get_distance_traveled.return_value = 250.0

        controller.routes.add(route1)
        controller.routes.add(route2)

        assert controller.get_total_vehicle_distance() == 400.0

    def test_completed_route_distance_preserved_after_unregister(self) -> None:
        """Distance from an unregistered route is retained."""
        controller = self._make_controller()

        route = Mock()
        route.get_distance_traveled.return_value = 300.0
        controller.routes.add(route)

        # Unregister captures distance
        controller.unregister_route(route)

        assert route not in controller.routes
        assert controller.get_total_vehicle_distance() == 300.0

    def test_mix_of_active_and_completed(self) -> None:
        """Combines completed route distance with active route distance."""
        controller = self._make_controller()

        # First route: completes with 200m
        completed_route = Mock()
        completed_route.get_distance_traveled.return_value = 200.0
        controller.routes.add(completed_route)
        controller.unregister_route(completed_route)

        # Second route: still active at 120m
        active_route = Mock()
        active_route.get_distance_traveled.return_value = 120.0
        controller.routes.add(active_route)

        assert controller.get_total_vehicle_distance() == 320.0

    def test_multiple_completed_routes_accumulate(self) -> None:
        """Multiple unregistered routes accumulate distance."""
        controller = self._make_controller()

        for dist in [100.0, 200.0, 300.0]:
            route = Mock()
            route.get_distance_traveled.return_value = dist
            controller.routes.add(route)
            controller.unregister_route(route)

        assert controller.get_total_vehicle_distance() == 600.0

    def test_clear_resets_total_distance(self) -> None:
        """clear() resets accumulated completed distance to zero."""
        controller = self._make_controller()

        route = Mock()
        route.get_distance_traveled.return_value = 500.0
        controller.routes.add(route)
        controller.unregister_route(route)

        controller.clear()

        assert controller.get_total_vehicle_distance() == 0.0

    def test_unregister_nonexistent_route_no_effect(self) -> None:
        """Unregistering a route not in the set doesn't change distance."""
        controller = self._make_controller()

        route = Mock()
        route.get_distance_traveled.return_value = 999.0

        # Route was never registered
        controller.unregister_route(route)

        assert controller.get_total_vehicle_distance() == 0.0
