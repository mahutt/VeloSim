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

import math
from enum import Enum
from typing import Dict, List, Set, TYPE_CHECKING, Tuple

from sim.entities.position import Position
from sim.entities.road import Road

if TYPE_CHECKING:
    from sim.map.position_registry import PositionRegistry


TRAFFIC_LIGHT_MATCH_TOLERANCE_DEGREES = 0.00012
TRAFFIC_LIGHT_INTERSECTION_CLUSTER_TOLERANCE_DEGREES = 0.00008
TRAFFIC_LIGHT_MIN_TRIGGER_INDEX = 2
TRAFFIC_LIGHT_TRIGGER_BACKOFF_POINTS = 2
DEFAULT_RED_LIGHT_TICKS = 5
DEFAULT_GREEN_LIGHT_TICKS = 5


class TrafficLightState(str, Enum):
    """Discrete state for traffic-light simulation."""

    RED = "red"
    GREEN = "green"


class StopLightController:
    """Registers traffic lights and exposes deterministic state per tick."""

    def __init__(
        self,
        registry: "PositionRegistry",
        red_ticks: int = DEFAULT_RED_LIGHT_TICKS,
        green_ticks: int = DEFAULT_GREEN_LIGHT_TICKS,
    ) -> None:
        self._registry = registry
        self._all_traffic_lights: Set[Position] = set()
        self._road_to_traffic_lights: Dict[Road, Set[Position]] = {}
        self._road_light_trigger_points: Dict[Road, Dict[Position, Position]] = {}
        self._road_light_trigger_index: Dict[Road, Dict[Position, int]] = {}
        self._road_light_phase_group: Dict[Road, Dict[Position, int]] = {}
        self._road_light_intersection_key: Dict[
            Road, Dict[Position, Tuple[int, int]]
        ] = {}
        self._intersection_axis_bearing: Dict[Tuple[int, int], float] = {}
        self._intersection_tick_offsets: Dict[Tuple[int, int], int] = {}
        self._red_ticks = max(int(red_ticks), 1)
        self._green_ticks = max(int(green_ticks), 1)

    @property
    def cycle_ticks(self) -> int:
        """Return full red+green cycle duration in ticks.

        Returns:
            int: Combined red and green cycle length.
        """
        return self._red_ticks + self._green_ticks

    def _compute_trigger_point_for_light(
        self, road: Road, light: Position
    ) -> tuple[Position, int, Position, int] | None:
        points = road.pointcollection
        if not points:
            return None

        light_lon, light_lat = light.get_position()
        best_idx = -1
        best_dist_sq = float("inf")

        for idx, point in enumerate(points):
            pt_lon, pt_lat = point.get_position()
            dx = pt_lon - light_lon
            dy = pt_lat - light_lat
            dist_sq = (dx * dx) + (dy * dy)
            if dist_sq <= best_dist_sq:
                best_dist_sq = dist_sq
                best_idx = idx

        if best_idx < 0:
            return None

        anchor_point = points[best_idx]
        anchor_idx = best_idx

        # Trigger slightly before the physical light so vehicles decide before
        # entering/intersecting the conflict zone.
        if len(points) <= 2:
            trigger_idx = best_idx
        else:
            trigger_idx = max(best_idx - TRAFFIC_LIGHT_TRIGGER_BACKOFF_POINTS, 0)
        return (points[trigger_idx], trigger_idx, anchor_point, anchor_idx)

    def _distance_sq_light_to_road(self, road: Road, light: Position) -> float:
        light_lon, light_lat = light.get_position()
        best_dist_sq = float("inf")

        for point in road.pointcollection:
            pt_lon, pt_lat = point.get_position()
            dx = pt_lon - light_lon
            dy = pt_lat - light_lat
            dist_sq = (dx * dx) + (dy * dy)
            if dist_sq < best_dist_sq:
                best_dist_sq = dist_sq

        return best_dist_sq

    def _intersection_key(self, light: Position) -> Tuple[int, int]:
        lon, lat = light.get_position()
        tol = TRAFFIC_LIGHT_INTERSECTION_CLUSTER_TOLERANCE_DEGREES
        return (int(round(lon / tol)), int(round(lat / tol)))

    def _light_intersection_key(self, road: Road, light: Position) -> Tuple[int, int]:
        stored = self._road_light_intersection_key.get(road, {}).get(light)
        if stored is not None:
            return stored

        computed = self._intersection_key(light)
        if road not in self._road_light_intersection_key:
            self._road_light_intersection_key[road] = {}
        self._road_light_intersection_key[road][light] = computed
        return computed

    def _intersection_tick_offset(self, intersection_key: Tuple[int, int]) -> int:
        """Return deterministic phase offset for an intersection key.

        Offsets desynchronize intersections globally while keeping behavior
        stable and reproducible for a given map.
        """
        existing = self._intersection_tick_offsets.get(intersection_key)
        if existing is not None:
            return existing

        cycle = self.cycle_ticks
        if cycle <= 1:
            self._intersection_tick_offsets[intersection_key] = 0
            return 0

        # Deterministic spatial hash; abs() avoids negative modulo ambiguity.
        key_hash = abs(
            (intersection_key[0] * 73856093) ^ (intersection_key[1] * 19349663)
        )
        offset = key_hash % cycle
        self._intersection_tick_offsets[intersection_key] = offset
        return offset

    def _road_axis_bearing(self, road: Road, trigger: Position) -> float | None:
        points = road.pointcollection
        if len(points) < 2:
            return None

        trigger_idx = -1
        for idx, point in enumerate(points):
            if point == trigger:
                trigger_idx = idx
                break

        if trigger_idx < 0:
            return None

        if trigger_idx == 0:
            p1 = points[0]
            p2 = points[1]
        elif trigger_idx >= len(points) - 1:
            p1 = points[-2]
            p2 = points[-1]
        else:
            p1 = points[trigger_idx - 1]
            p2 = points[trigger_idx + 1]

        lon1, lat1 = p1.get_position()
        lon2, lat2 = p2.get_position()
        dx = lon2 - lon1
        dy = lat2 - lat1
        if abs(dx) < 1e-14 and abs(dy) < 1e-14:
            return None

        bearing = math.degrees(math.atan2(dy, dx)) % 180.0
        return bearing

    def _phase_group_for_intersection(
        self, intersection_key: Tuple[int, int], axis_bearing: float | None
    ) -> int:
        if axis_bearing is None:
            return 0

        base_axis = self._intersection_axis_bearing.get(intersection_key)
        if base_axis is None:
            self._intersection_axis_bearing[intersection_key] = axis_bearing
            return 0

        delta = abs(((axis_bearing - base_axis + 90.0) % 180.0) - 90.0)
        return 1 if delta >= 45.0 else 0

    def _is_trigger_too_close_for_road(self, road: Road, trigger: Position) -> bool:
        existing_triggers = self._road_light_trigger_points.get(road, {}).values()
        cluster_tol_sq = (
            TRAFFIC_LIGHT_INTERSECTION_CLUSTER_TOLERANCE_DEGREES
            * TRAFFIC_LIGHT_INTERSECTION_CLUSTER_TOLERANCE_DEGREES
        )
        trig_lon, trig_lat = trigger.get_position()
        for existing_trigger in existing_triggers:
            ex_lon, ex_lat = existing_trigger.get_position()
            dx = ex_lon - trig_lon
            dy = ex_lat - trig_lat
            if (dx * dx) + (dy * dy) <= cluster_tol_sq:
                return True
        return False

    def _is_light_ahead_of_trigger(
        self, road: Road, trigger_idx: int, light: Position
    ) -> bool:
        """Return True when light is in front of travel direction at trigger.

        This prevents mapping the opposite-direction signal head on corridors
        where two signal nodes exist around the same intersection.
        """
        points = road.pointcollection
        if len(points) < 2:
            return True

        if trigger_idx < len(points) - 1:
            base = points[trigger_idx]
            nxt = points[trigger_idx + 1]
            dir_x = nxt.get_position()[0] - base.get_position()[0]
            dir_y = nxt.get_position()[1] - base.get_position()[1]
        else:
            base = points[trigger_idx]
            prev = points[trigger_idx - 1]
            dir_x = base.get_position()[0] - prev.get_position()[0]
            dir_y = base.get_position()[1] - prev.get_position()[1]

        base_lon, base_lat = base.get_position()
        light_lon, light_lat = light.get_position()
        to_light_x = light_lon - base_lon
        to_light_y = light_lat - base_lat

        dot = (dir_x * to_light_x) + (dir_y * to_light_y)
        return dot >= 0

    def _remove_road_light_mapping(self, road: Road, light: Position) -> None:
        lights = self._road_to_traffic_lights.get(road)
        if lights is not None:
            lights.discard(light)

        trigger_points = self._road_light_trigger_points.get(road)
        if trigger_points is not None:
            trigger_points.pop(light, None)

        trigger_indices = self._road_light_trigger_index.get(road)
        if trigger_indices is not None:
            trigger_indices.pop(light, None)

        phase_groups = self._road_light_phase_group.get(road)
        if phase_groups is not None:
            phase_groups.pop(light, None)

        intersection_keys = self._road_light_intersection_key.get(road)
        if intersection_keys is not None:
            intersection_keys.pop(light, None)

    def register_traffic_lights(self, traffic_light_positions: List[Position]) -> None:
        """Register traffic-light positions and map each light to nearby roads.

        Args:
            traffic_light_positions: Traffic-light positions to register.

        Returns:
            None
        """
        for pos in traffic_light_positions:
            self._all_traffic_lights.add(pos)
            roads = self._registry.find_roads_at_position(pos)
            if not roads:
                roads = self._registry.find_roads_near_position(
                    pos, TRAFFIC_LIGHT_MATCH_TOLERANCE_DEGREES
                )
            if not roads:
                continue

            ranked_roads = sorted(
                roads, key=lambda road: self._distance_sq_light_to_road(road, pos)
            )
            for road in ranked_roads:
                trigger_result = self._compute_trigger_point_for_light(road, pos)
                if trigger_result is None:
                    continue
                trigger, trigger_idx, anchor_point, anchor_idx = trigger_result

                # Avoid stopping after a vehicle has already entered an intersection
                # and is turning into a new road where the light sits near road start.
                if (
                    len(road.pointcollection) > (TRAFFIC_LIGHT_MIN_TRIGGER_INDEX + 1)
                    and anchor_idx < TRAFFIC_LIGHT_MIN_TRIGGER_INDEX
                ):
                    continue

                if not self._is_light_ahead_of_trigger(road, trigger_idx, pos):
                    continue

                if self._is_trigger_too_close_for_road(road, trigger):
                    continue

                axis_bearing = self._road_axis_bearing(road, trigger)
                intersection_key = self._intersection_key(anchor_point)

                # Keep a single stop trigger per road/intersection; if multiple
                # lights map to the same approach, retain the earliest trigger.
                existing_lights_same_intersection = [
                    light
                    for light, key in self._road_light_intersection_key.get(
                        road, {}
                    ).items()
                    if key == intersection_key
                ]
                if existing_lights_same_intersection:
                    existing_indices = self._road_light_trigger_index.get(road, {})
                    earliest_existing_idx = min(
                        existing_indices.get(light, 10**9)
                        for light in existing_lights_same_intersection
                    )
                    if trigger_idx >= earliest_existing_idx:
                        continue
                    for existing_light in existing_lights_same_intersection:
                        self._remove_road_light_mapping(road, existing_light)

                phase_group = self._phase_group_for_intersection(
                    intersection_key, axis_bearing
                )

                if road not in self._road_to_traffic_lights:
                    self._road_to_traffic_lights[road] = set()
                self._road_to_traffic_lights[road].add(pos)

                if road not in self._road_light_trigger_points:
                    self._road_light_trigger_points[road] = {}
                self._road_light_trigger_points[road][pos] = trigger

                if road not in self._road_light_trigger_index:
                    self._road_light_trigger_index[road] = {}
                self._road_light_trigger_index[road][pos] = trigger_idx

                if road not in self._road_light_phase_group:
                    self._road_light_phase_group[road] = {}
                self._road_light_phase_group[road][pos] = phase_group

                if road not in self._road_light_intersection_key:
                    self._road_light_intersection_key[road] = {}
                self._road_light_intersection_key[road][pos] = intersection_key

    def unregister_road(self, road: Road) -> None:
        """Drop traffic-light associations for a deallocated road.

        Args:
            road: Road being deallocated.

        Returns:
            None
        """
        self._road_to_traffic_lights.pop(road, None)
        self._road_light_trigger_points.pop(road, None)
        self._road_light_trigger_index.pop(road, None)
        self._road_light_phase_group.pop(road, None)
        self._road_light_intersection_key.pop(road, None)

    def has_traffic_light(self, road: Road) -> bool:
        """Return True if a road has at least one registered traffic light.

        Args:
            road: Road to inspect.

        Returns:
            bool: True when at least one traffic light is mapped to the road.
        """
        return bool(self._road_to_traffic_lights.get(road))

    def get_traffic_lights_for_road(self, road: Road) -> List[Position]:
        """Return traffic-light positions associated with a road.

        Args:
            road: Road to inspect.

        Returns:
            List[Position]: Traffic lights mapped to the road.
        """
        return list(self._road_to_traffic_lights.get(road, set()))

    def get_matching_traffic_light_at_position(
        self, road: Road, position: Position
    ) -> Position | None:
        """Return the matching traffic light for a road-point pair, if any.

        Args:
            road: Road to inspect.
            position: Candidate position on the road.

        Returns:
            Position | None: Matched traffic-light position, or None.
        """
        road_lights = self._road_to_traffic_lights.get(road, set())
        if not road_lights:
            return None

        target_lon, target_lat = position.get_position()
        trigger_map = self._road_light_trigger_points.get(road, {})
        trigger_tol_sq = 1e-14

        for light in road_lights:
            trigger = trigger_map.get(light)
            if trigger is None:
                continue
            trig_lon, trig_lat = trigger.get_position()
            dx = trig_lon - target_lon
            dy = trig_lat - target_lat
            if (dx * dx) + (dy * dy) <= trigger_tol_sq:
                return light

        return None

    def get_state(self, simulation_tick: int) -> TrafficLightState:
        """Return traffic-light state for the given simulation tick.

        Args:
            simulation_tick: Current simulation tick.

        Returns:
            TrafficLightState: Red or green state at the tick.
        """
        tick = max(int(simulation_tick), 0)
        phase = tick % self.cycle_ticks
        if phase < self._red_ticks:
            return TrafficLightState.RED
        return TrafficLightState.GREEN

    def get_next_transition_tick(self, simulation_tick: int) -> int:
        """Return the next tick when state flips from current state.

        Args:
            simulation_tick: Current simulation tick.

        Returns:
            int: Next tick where light state changes.
        """
        tick = max(int(simulation_tick), 0)
        phase = tick % self.cycle_ticks
        cycle_start = tick - phase

        if phase < self._red_ticks:
            return cycle_start + self._red_ticks
        return cycle_start + self.cycle_ticks

    def _invert_state(self, state: TrafficLightState) -> TrafficLightState:
        """Invert a traffic-light state between RED and GREEN."""
        return (
            TrafficLightState.GREEN
            if state == TrafficLightState.RED
            else TrafficLightState.RED
        )

    def _state_for_phase_group(
        self,
        phase_group: int,
        simulation_tick: int,
        intersection_key: Tuple[int, int],
    ) -> TrafficLightState:
        """Resolve state for one phase group at an intersection and tick."""
        offset_tick = simulation_tick + self._intersection_tick_offset(intersection_key)
        base_state = self.get_state(offset_tick)
        if phase_group % 2 == 1:
            return self._invert_state(base_state)
        return base_state

    def _bearing_delta_degrees(
        self, bearing_a: float | None, bearing_b: float | None
    ) -> float | None:
        """Return smallest absolute angular delta between two axis bearings."""
        if bearing_a is None or bearing_b is None:
            return None
        return abs(((bearing_a - bearing_b + 90.0) % 180.0) - 90.0)

    def _iter_intersection_light_mappings(
        self, intersection_key: Tuple[int, int]
    ) -> List[Tuple[Road, Position, int, float | None]]:
        """Collect all road/light mappings for a single intersection key."""
        mappings: List[Tuple[Road, Position, int, float | None]] = []
        for road, light_to_group in self._road_light_phase_group.items():
            trigger_map = self._road_light_trigger_points.get(road, {})
            for light, phase_group in light_to_group.items():
                if self._light_intersection_key(road, light) != intersection_key:
                    continue
                trigger = trigger_map.get(light)
                axis_bearing = (
                    self._road_axis_bearing(road, trigger)
                    if trigger is not None
                    else None
                )
                mappings.append((road, light, phase_group, axis_bearing))
        return mappings

    def _resolve_conflicting_green(
        self,
        road: Road,
        light: Position,
        simulation_tick: int,
        computed_state: TrafficLightState,
    ) -> TrafficLightState:
        """Prevent conflicting intersection approaches from both being green."""
        if computed_state != TrafficLightState.GREEN:
            return computed_state

        intersection_key = self._light_intersection_key(road, light)
        trigger = self._road_light_trigger_points.get(road, {}).get(light)
        this_bearing = (
            self._road_axis_bearing(road, trigger) if trigger is not None else None
        )

        for (
            other_road,
            other_light,
            other_phase_group,
            other_bearing,
        ) in self._iter_intersection_light_mappings(intersection_key):
            if other_road == road and other_light == light:
                continue

            other_key = self._light_intersection_key(other_road, other_light)
            other_state = self._state_for_phase_group(
                other_phase_group, simulation_tick, other_key
            )
            if other_state != TrafficLightState.GREEN:
                continue

            delta = self._bearing_delta_degrees(this_bearing, other_bearing)
            is_conflicting = delta is None or delta >= 45.0
            if not is_conflicting:
                continue

            # Deterministic tie-break so conflicting approaches cannot both be green.
            if road.id > other_road.id:
                return TrafficLightState.RED

        return computed_state

    def get_state_for_road_light(
        self, road: Road, light: Position, simulation_tick: int
    ) -> TrafficLightState:
        """Return state for a specific road/light pair at a simulation tick.

        Args:
            road: Road associated with the light.
            light: Traffic-light position.
            simulation_tick: Current simulation tick.

        Returns:
            TrafficLightState: Resolved state for that road/light mapping.
        """
        intersection_key = self._light_intersection_key(road, light)
        phase_group = self._road_light_phase_group.get(road, {}).get(light, 0)
        computed_state = self._state_for_phase_group(
            phase_group, simulation_tick, intersection_key
        )
        return self._resolve_conflicting_green(
            road, light, simulation_tick, computed_state
        )

    def get_light_signals_for_road(
        self, road: Road, simulation_tick: int
    ) -> List[Tuple[Position, TrafficLightState]]:
        """Return road traffic lights paired with their current state.

        Args:
            road: Road to inspect.
            simulation_tick: Current simulation tick.

        Returns:
            List[Tuple[Position, TrafficLightState]]: Light/state pairs.
        """
        signals: List[Tuple[Position, TrafficLightState]] = []
        for light in self._road_to_traffic_lights.get(road, set()):
            signals.append(
                (light, self.get_state_for_road_light(road, light, simulation_tick))
            )
        return signals

    def is_red_light_at_position(
        self, road: Road, position: Position, simulation_tick: int
    ) -> bool:
        """Return True if the road-position pair maps to a red traffic light.

        Args:
            road: Road to inspect.
            position: Candidate position on the road.
            simulation_tick: Current simulation tick.

        Returns:
            bool: True when matched traffic light resolves to red.
        """
        matched = self.get_matching_traffic_light_at_position(road, position)
        if matched is None:
            return False
        return (
            self.get_state_for_road_light(road, matched, simulation_tick)
            == TrafficLightState.RED
        )

    def get_all_traffic_lights(self) -> List[Position]:
        """Return all registered traffic-light positions.

        Returns:
            List[Position]: All traffic-light positions known by the controller.
        """
        return list(self._all_traffic_lights)
