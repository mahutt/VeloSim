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
from sim.entities.road import Road
from sim.map.position_registry import PositionRegistry
from sim.map.stop_light_controller import StopLightController, TrafficLightState


def test_register_traffic_lights_maps_to_road_and_trigger_point() -> None:
    registry = PositionRegistry()
    road_geometry = [Position([0.0, 0.0]), Position([1.0, 1.0])]
    road = Road(
        road_id=1,
        name="Road",
        pointcollection=[Position([0.0, 0.0]), Position([1.0, 1.0])],
        length=100.0,
        maxspeed=10.0,
        geometry=road_geometry,
    )
    registry.register_road(road, road_geometry)

    controller = StopLightController(registry)
    light = Position([1.0, 1.0])

    controller.register_traffic_lights([light])

    assert controller.has_traffic_light(road)
    assert controller.get_matching_traffic_light_at_position(road, Position([1.0, 1.0]))


def test_light_state_machine_and_transition_tick() -> None:
    controller = StopLightController(PositionRegistry(), red_ticks=3, green_ticks=2)

    assert controller.get_state(0) == TrafficLightState.RED
    assert controller.get_state(2) == TrafficLightState.RED
    assert controller.get_state(3) == TrafficLightState.GREEN
    assert controller.get_state(4) == TrafficLightState.GREEN
    assert controller.get_state(5) == TrafficLightState.RED

    assert controller.get_next_transition_tick(1) == 3
    assert controller.get_next_transition_tick(3) == 5


def test_perpendicular_roads_are_in_opposite_phases() -> None:
    registry = PositionRegistry()
    east_west_geometry = [
        Position([-1.0, 0.0]),
        Position([0.0, 0.0]),
        Position([1.0, 0.0]),
    ]
    north_south_geometry = [
        Position([0.0, -1.0]),
        Position([0.0, 0.0]),
        Position([0.0, 1.0]),
    ]

    east_west_road = Road(
        road_id=10,
        name="East-West",
        pointcollection=east_west_geometry,
        length=100.0,
        maxspeed=10.0,
        geometry=east_west_geometry,
    )
    north_south_road = Road(
        road_id=20,
        name="North-South",
        pointcollection=north_south_geometry,
        length=100.0,
        maxspeed=10.0,
        geometry=north_south_geometry,
    )
    registry.register_road(east_west_road, east_west_geometry)
    registry.register_road(north_south_road, north_south_geometry)

    controller = StopLightController(registry, red_ticks=3, green_ticks=2)
    controller.register_traffic_lights([Position([0.0, 0.0])])

    ew_lights = controller.get_traffic_lights_for_road(east_west_road)
    ns_lights = controller.get_traffic_lights_for_road(north_south_road)

    assert ew_lights
    assert ns_lights

    ew_state = controller.get_state_for_road_light(east_west_road, ew_lights[0], 3)
    ns_state = controller.get_state_for_road_light(north_south_road, ns_lights[0], 3)

    assert ew_state != ns_state
    assert not (
        ew_state == TrafficLightState.GREEN and ns_state == TrafficLightState.GREEN
    )


def test_ambiguous_axis_still_prevents_conflicting_green() -> None:
    registry = PositionRegistry()

    ambiguous_geometry = [Position([0.0, 0.0])]
    north_south_geometry = [
        Position([0.0, -1.0]),
        Position([0.0, 0.0]),
        Position([0.0, 1.0]),
    ]

    ambiguous_road = Road(
        road_id=1,
        name="Ambiguous",
        pointcollection=ambiguous_geometry,
        length=10.0,
        maxspeed=10.0,
        geometry=ambiguous_geometry,
    )
    north_south_road = Road(
        road_id=2,
        name="North-South",
        pointcollection=north_south_geometry,
        length=100.0,
        maxspeed=10.0,
        geometry=north_south_geometry,
    )

    registry.register_road(ambiguous_road, ambiguous_geometry)
    registry.register_road(north_south_road, north_south_geometry)

    controller = StopLightController(registry, red_ticks=2, green_ticks=2)
    controller.register_traffic_lights([Position([0.0, 0.0])])

    ambiguous_light = controller.get_traffic_lights_for_road(ambiguous_road)[0]
    north_south_light = controller.get_traffic_lights_for_road(north_south_road)[0]

    ambiguous_state = controller.get_state_for_road_light(
        ambiguous_road, ambiguous_light, 2
    )
    north_south_state = controller.get_state_for_road_light(
        north_south_road, north_south_light, 2
    )

    assert not (
        ambiguous_state == TrafficLightState.GREEN
        and north_south_state == TrafficLightState.GREEN
    )


def test_light_near_road_start_is_not_mapped_to_entry_road() -> None:
    registry = PositionRegistry()
    road_geometry = [
        Position([0.0, 0.0]),
        Position([0.0, 1.0]),
        Position([0.0, 2.0]),
        Position([0.0, 3.0]),
    ]
    road = Road(
        road_id=30,
        name="Turn Entry Road",
        pointcollection=road_geometry,
        length=120.0,
        maxspeed=10.0,
        geometry=road_geometry,
    )
    registry.register_road(road, road_geometry)

    controller = StopLightController(registry)
    # Light sits at the very beginning of this road; driver should have
    # already decided before entering, so do not map trigger on this road.
    controller.register_traffic_lights([Position([0.0, 0.0])])

    assert not controller.has_traffic_light(road)


def test_offset_lights_same_intersection_use_opposite_phases() -> None:
    registry = PositionRegistry()
    east_west_geometry = [
        Position([-1.0, 0.0]),
        Position([0.0, 0.0]),
        Position([1.0, 0.0]),
    ]
    north_south_geometry = [
        Position([0.0, -1.0]),
        Position([0.0, 0.0]),
        Position([0.0, 1.0]),
    ]

    east_west_road = Road(
        road_id=40,
        name="East-West Offset",
        pointcollection=east_west_geometry,
        length=100.0,
        maxspeed=10.0,
        geometry=east_west_geometry,
    )
    north_south_road = Road(
        road_id=50,
        name="North-South Offset",
        pointcollection=north_south_geometry,
        length=100.0,
        maxspeed=10.0,
        geometry=north_south_geometry,
    )
    registry.register_road(east_west_road, east_west_geometry)
    registry.register_road(north_south_road, north_south_geometry)

    controller = StopLightController(registry, red_ticks=3, green_ticks=2)

    # Lights are offset around the same intersection and not co-located.
    controller.register_traffic_lights(
        [
            Position([0.00009, 0.0]),
            Position([0.0, 0.00009]),
        ]
    )

    ew_lights = controller.get_traffic_lights_for_road(east_west_road)
    ns_lights = controller.get_traffic_lights_for_road(north_south_road)
    assert ew_lights
    assert ns_lights

    ew_state = controller.get_state_for_road_light(east_west_road, ew_lights[0], 3)
    ns_state = controller.get_state_for_road_light(north_south_road, ns_lights[0], 3)

    assert ew_state != ns_state


def test_same_road_same_intersection_keeps_earliest_trigger_only() -> None:
    registry = PositionRegistry()
    road_points = [
        Position([0.0, 0.0]),
        Position([1.0, 0.0]),
        Position([2.0, 0.0]),
        Position([3.0, 0.0]),
        Position([4.0, 0.0]),
        Position([5.0, 0.0]),
    ]
    road = Road(
        road_id=60,
        name="Main",
        pointcollection=road_points,
        length=150.0,
        maxspeed=10.0,
        geometry=road_points,
    )
    registry.register_road(road, road_points)

    controller = StopLightController(registry)

    # Two nearby lights on the same intersection/approach. Only the earliest
    # trigger should be retained so the vehicle does not stop twice.
    controller.register_traffic_lights(
        [
            Position([4.0, 0.00001]),
            Position([4.00003, -0.00001]),
        ]
    )

    mapped_lights = controller.get_traffic_lights_for_road(road)
    assert len(mapped_lights) == 1


def test_different_intersections_are_not_globally_synchronized() -> None:
    registry = PositionRegistry()

    road_a_points = [
        Position([-1.0, 0.0]),
        Position([0.0, 0.0]),
        Position([1.0, 0.0]),
    ]
    road_b_points = [
        Position([9.0, 10.0]),
        Position([10.0, 10.0]),
        Position([11.0, 10.0]),
    ]

    road_a = Road(
        road_id=70,
        name="Intersection A",
        pointcollection=road_a_points,
        length=100.0,
        maxspeed=10.0,
        geometry=road_a_points,
    )
    road_b = Road(
        road_id=80,
        name="Intersection B",
        pointcollection=road_b_points,
        length=100.0,
        maxspeed=10.0,
        geometry=road_b_points,
    )
    registry.register_road(road_a, road_a_points)
    registry.register_road(road_b, road_b_points)

    controller = StopLightController(registry, red_ticks=3, green_ticks=2)
    controller.register_traffic_lights(
        [
            Position([0.0, 0.0]),
            Position([10.0, 10.0]),
        ]
    )

    light_a = controller.get_traffic_lights_for_road(road_a)[0]
    light_b = controller.get_traffic_lights_for_road(road_b)[0]

    any_diff = False
    for tick in range(controller.cycle_ticks * 3):
        state_a = controller.get_state_for_road_light(road_a, light_a, tick)
        state_b = controller.get_state_for_road_light(road_b, light_b, tick)
        if state_a != state_b:
            any_diff = True
            break

    assert any_diff


def test_opposite_direction_light_is_filtered_for_road_direction() -> None:
    registry = PositionRegistry()
    road_points = [
        Position([0.0, 0.0]),
        Position([0.0, 0.0001]),
        Position([0.0, 0.0002]),
        Position([0.0, 0.0003]),
    ]
    road = Road(
        road_id=90,
        name="Northbound",
        pointcollection=road_points,
        length=100.0,
        maxspeed=10.0,
        geometry=road_points,
    )
    registry.register_road(road, road_points)

    controller = StopLightController(registry)

    # One light ahead in travel direction, one behind (opposite-direction head).
    controller.register_traffic_lights(
        [
            Position([0.0, 0.00028]),
            Position([0.0, 0.00002]),
        ]
    )

    mapped = controller.get_traffic_lights_for_road(road)
    assert len(mapped) == 1
    assert mapped[0].get_position() == [0.0, 0.00028]
