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

from typing import Generator
from unittest.mock import Mock, patch

import pytest

from sim.entities.position import Position
from sim.map.routing_provider import EdgeIdentifier, TrafficUpdate
from sim.osm.graphhopper_adapter import GraphHopperAdapter, ToleranceKey
from sim.osm.graphhopper_result import (
    GraphHopperInstruction,
    GraphHopperResult,
    GraphHopperSegment,
)
from sim.osm.graphhopper_segment_mapper import graphhopper_segment_mapper
from sim.osm.traffic_state_store import traffic_state_store


@pytest.fixture(autouse=True)
def _reset_traffic_state() -> Generator[None, None, None]:
    traffic_state_store._reset()
    graphhopper_segment_mapper.clear_sim("test-sim")
    yield
    traffic_state_store._reset()
    graphhopper_segment_mapper.clear_sim("test-sim")


def _make_result(distance: float = 100.0, duration: float = 10.0) -> GraphHopperResult:
    instruction = GraphHopperInstruction(
        text="Continue",
        distance=distance,
        time=duration * 1000.0,
        interval=[0, 1],
        street_name="Main Street",
    )
    segment = GraphHopperSegment(
        distance=distance,
        duration=duration,
        geometry=[[-73.5673, 45.5017], [-73.5533, 45.5017]],
        road_name="Main Street",
    )
    return GraphHopperResult(
        coordinates=[[-73.5673, 45.5017], [-73.5533, 45.5017]],
        distance=distance,
        duration=duration,
        instructions=[instruction],
        segments=[segment],
    )


def _make_adapter(
    sim_id: str = "test-sim", profile: str = "car"
) -> tuple[GraphHopperAdapter, Mock]:
    with patch("sim.osm.graphhopper_adapter.GraphHopperConnection") as connection_cls:
        mock_connection = Mock()
        connection_cls.return_value = mock_connection
        adapter = GraphHopperAdapter(
            graphhopper_url="http://graphhopper:8989",
            sim_id=sim_id,
            profile=profile,
        )
    return adapter, mock_connection


def _edge(
    start: tuple[float, float] = (-73.5673, 45.5017),
    end: tuple[float, float] = (-73.5533, 45.5017),
) -> EdgeIdentifier:
    return EdgeIdentifier(
        start_position=Position([start[0], start[1]]),
        end_position=Position([end[0], end[1]]),
    )


class TestGraphHopperAdapterRouting:
    def test_get_route_returns_none_when_baseline_fails(self) -> None:
        adapter, connection = _make_adapter(profile="bike")
        connection.shortest_path_coords.return_value = None

        result = adapter.get_route(
            Position([-73.5673, 45.5017]),
            Position([-73.5533, 45.5017]),
        )

        assert result is None
        assert connection.shortest_path_coords.call_count == 1
        kwargs = connection.shortest_path_coords.call_args.kwargs
        assert kwargs["profile"] == "bike"
        assert kwargs["custom_model"] is None

    def test_get_route_uses_baseline_when_no_custom_model(self) -> None:
        adapter, connection = _make_adapter()
        baseline = _make_result(distance=123.0)
        connection.shortest_path_coords.return_value = baseline

        with patch.object(adapter, "_build_custom_model_for_route", return_value=None):
            result = adapter.get_route(
                Position([-73.5673, 45.5017]),
                Position([-73.5533, 45.5017]),
            )

        assert result is not None
        assert result.distance == 123.0
        assert connection.shortest_path_coords.call_count == 1

    def test_get_route_falls_back_to_baseline_when_traffic_route_fails(self) -> None:
        adapter, connection = _make_adapter(profile="car")
        baseline = _make_result(distance=200.0)
        connection.shortest_path_coords.side_effect = [baseline, None]
        custom_model = {
            "areas": {"seg_1": {"type": "Feature"}},
            "speed": [{"if": "in_seg_1", "multiply_by": 0.5}],
        }

        with patch.object(
            adapter,
            "_build_custom_model_for_route",
            return_value=custom_model,
        ):
            result = adapter.get_route(
                Position([-73.5673, 45.5017]),
                Position([-73.5533, 45.5017]),
            )

        assert result is not None
        assert result.distance == 200.0
        assert connection.shortest_path_coords.call_count == 2
        second_call_kwargs = connection.shortest_path_coords.call_args_list[1].kwargs
        assert second_call_kwargs["custom_model"] == custom_model

    def test_get_route_prefers_traffic_result_when_available(self) -> None:
        adapter, connection = _make_adapter()
        baseline = _make_result(distance=200.0)
        traffic = _make_result(distance=90.0)
        connection.shortest_path_coords.side_effect = [baseline, traffic]

        with patch.object(
            adapter,
            "_build_custom_model_for_route",
            return_value={"areas": {"seg_1": {}}, "speed": [{"if": "true"}]},
        ):
            result = adapter.get_route(
                Position([-73.5673, 45.5017]),
                Position([-73.5533, 45.5017]),
            )

        assert result is not None
        assert result.distance == 90.0


class TestGraphHopperAdapterDistanceAndSnap:
    def test_get_distance_returns_route_distance(self) -> None:
        adapter, _ = _make_adapter()

        with patch.object(adapter, "get_route", return_value=Mock(distance=321.5)):
            distance = adapter.get_distance(
                Position([-73.5673, 45.5017]),
                Position([-73.5533, 45.5017]),
            )

        assert distance == 321.5

    def test_get_distance_returns_none_when_no_route(self) -> None:
        adapter, _ = _make_adapter()

        with patch.object(adapter, "get_route", return_value=None):
            distance = adapter.get_distance(
                Position([-73.5673, 45.5017]),
                Position([-73.5533, 45.5017]),
            )

        assert distance is None

    def test_snap_to_road_delegates_and_wraps_result(self) -> None:
        adapter, connection = _make_adapter(profile="bike")
        connection.snap_to_road.return_value = (-73.5600, 45.5050)

        snapped = adapter.snap_to_road(Position([-73.5673, 45.5017]))

        assert snapped == Position([-73.5600, 45.5050])
        connection.snap_to_road.assert_called_once_with(
            -73.5673,
            45.5017,
            profile="bike",
        )


class TestGraphHopperAdapterTrafficCRUD:
    def test_close_cleans_up_sim_state_and_connection(self) -> None:
        adapter, connection = _make_adapter(sim_id="test-sim")

        with (
            patch(
                "sim.osm.graphhopper_adapter.traffic_state_store.cleanup_sim"
            ) as cleanup_sim,
            patch(
                "sim.osm.graphhopper_adapter.graphhopper_segment_mapper.clear_sim"
            ) as clear_sim,
        ):
            adapter.close()

        cleanup_sim.assert_called_once_with("test-sim")
        clear_sim.assert_called_once_with("test-sim")
        connection.close.assert_called_once()

    def test_single_edge_traffic_crud(self) -> None:
        adapter, _ = _make_adapter(sim_id="test-sim")
        edge = _edge()
        update = TrafficUpdate(edge=edge, speed_factor=0.4)

        assert adapter.set_edge_traffic(update) is True
        assert adapter.get_edge_traffic(edge) == 0.4
        assert adapter.clear_edge_traffic(edge) is True
        assert adapter.get_edge_traffic(edge) is None

    def test_set_edges_traffic_sets_all_updates(self) -> None:
        adapter, _ = _make_adapter(sim_id="test-sim")
        updates = [
            TrafficUpdate(edge=_edge((-73.0, 45.0), (-73.1, 45.1)), speed_factor=0.1),
            TrafficUpdate(edge=_edge((-73.2, 45.2), (-73.3, 45.3)), speed_factor=0.9),
        ]

        assert adapter.set_edges_traffic(updates) is True

        e1 = _edge((-73.0, 45.0), (-73.1, 45.1))
        e2 = _edge((-73.2, 45.2), (-73.3, 45.3))
        assert adapter.get_edge_traffic(e1) == 0.1
        assert adapter.get_edge_traffic(e2) == 0.9

    def test_clear_all_traffic_clears_sim_data(self) -> None:
        adapter, _ = _make_adapter(sim_id="test-sim")
        edge = _edge()

        adapter.set_edge_traffic(TrafficUpdate(edge=edge, speed_factor=0.5))

        assert adapter.clear_all_traffic() is True
        assert adapter.get_edge_traffic(edge) is None


class TestGraphHopperAdapterMatchingHelpers:
    def test_find_traffic_for_segment_matches_forward_direction(self) -> None:
        adapter, _ = _make_adapter()
        key = ((-73.5673, 45.5017), (-73.5533, 45.5017))
        sim_traffic = {key: 0.35}

        factor = adapter._find_traffic_for_segment(
            (-73.5673, 45.5017),
            (-73.5533, 45.5017),
            sim_traffic,
        )

        assert factor == 0.35

    def test_find_traffic_for_segment_matches_reverse_direction(self) -> None:
        adapter, _ = _make_adapter()
        key = ((-73.5673, 45.5017), (-73.5533, 45.5017))
        sim_traffic = {key: 0.65}

        factor = adapter._find_traffic_for_segment(
            (-73.5533, 45.5017),
            (-73.5673, 45.5017),
            sim_traffic,
        )

        assert factor == 0.65

    def test_find_traffic_for_segment_returns_none_when_not_found(self) -> None:
        adapter, _ = _make_adapter()

        factor = adapter._find_traffic_for_segment(
            (-73.0, 45.0),
            (-73.1, 45.1),
            {},
        )

        assert factor is None


class TestGraphHopperAdapterCustomModel:
    def test_build_custom_model_returns_none_when_no_traffic(self) -> None:
        adapter, _ = _make_adapter(sim_id="test-sim")

        model = adapter._build_custom_model_for_route(_make_result())

        assert model is None

    def test_build_custom_model_returns_none_when_no_segments_match(self) -> None:
        adapter, _ = _make_adapter(sim_id="test-sim")
        result = _make_result()
        result.segments = [
            GraphHopperSegment(
                distance=10.0,
                duration=1.0,
                geometry=[[-73.0, 45.0]],
                road_name="Short",
            )
        ]
        traffic_state_store.set(
            "test-sim",
            ToleranceKey(((-73.5673, 45.5017), (-73.5533, 45.5017))).store_key(),
            0.5,
        )

        model = adapter._build_custom_model_for_route(result)

        assert model is None

    def test_build_custom_model_skips_segment_without_matching_factor(self) -> None:
        adapter, _ = _make_adapter(sim_id="test-sim")
        result = _make_result()
        traffic_state_store.set(
            "test-sim",
            ToleranceKey(((-73.0, 45.0), (-73.1, 45.1))).store_key(),
            0.5,
        )

        model = adapter._build_custom_model_for_route(result)

        assert model is None

    def test_build_custom_model_builds_areas_and_clamps_speed_factors(self) -> None:
        adapter, _ = _make_adapter(sim_id="test-sim")
        result = _make_result()
        segment_key = ((-73.5673, 45.5017), (-73.5533, 45.5017))
        traffic_state_store.set("test-sim", ToleranceKey(segment_key).store_key(), 0.0)

        with patch(
            "sim.osm.graphhopper_adapter.graphhopper_segment_mapper.get_or_create_area",
            return_value=(
                "seg_test",
                {
                    "type": "Feature",
                    "geometry": {"type": "Polygon", "coordinates": [[]]},
                    "properties": {},
                },
            ),
        ):
            model = adapter._build_custom_model_for_route(result)

        assert model is not None
        assert "areas" in model
        assert "seg_test" in model["areas"]
        assert model["speed"][0]["if"] == "in_seg_test"
        assert model["speed"][0]["multiply_by"] == pytest.approx(0.01)


class TestGraphHopperAdapterGeometryAndConnection:
    def test_geometry_for_interval_empty_coordinates_returns_empty(self) -> None:
        geometry = GraphHopperAdapter._geometry_for_interval([], [0, 1])

        assert geometry == []

    def test_geometry_for_interval_invalid_interval_returns_empty(self) -> None:
        geometry = GraphHopperAdapter._geometry_for_interval(
            [[-73.5673, 45.5017], [-73.5533, 45.5017]],
            [2, 0],
        )

        assert geometry == []

    def test_connection_property_exposes_underlying_connection(self) -> None:
        adapter, connection = _make_adapter()

        assert adapter.connection is connection
