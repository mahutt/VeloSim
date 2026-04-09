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

from typing import Dict, List, Set, TYPE_CHECKING

from sim.entities.position import Position
from sim.entities.road import Road

if TYPE_CHECKING:
    from sim.map.position_registry import PositionRegistry


STOP_SIGN_MATCH_TOLERANCE_DEGREES = 0.00015
STOP_SIGN_INTERSECTION_CLUSTER_TOLERANCE_DEGREES = 0.00015


class StopSignController:
    """Registers stop-sign positions and maps them to roads by geometry overlap."""

    def __init__(self, registry: "PositionRegistry") -> None:
        self._registry = registry
        self._all_stop_signs: Set[Position] = set()
        self._road_to_stop_signs: Dict[Road, Set[Position]] = {}
        self._road_sign_trigger_points: Dict[Road, Dict[Position, Position]] = {}

    def _compute_trigger_point_for_sign(
        self, road: Road, sign: Position
    ) -> Position | None:
        """Pick the route point that best represents "on top of" the stop sign.

        Uses the nearest point in the road's default sampled points.
        """
        points = road.pointcollection
        if not points:
            return None

        sign_lon, sign_lat = sign.get_position()
        best_idx = -1
        best_dist_sq = float("inf")

        for idx, point in enumerate(points):
            pt_lon, pt_lat = point.get_position()
            dx = pt_lon - sign_lon
            dy = pt_lat - sign_lat
            dist_sq = (dx * dx) + (dy * dy)

            # This triggers stops BEFORE entering intersection, not on exit
            if dist_sq < best_dist_sq:
                best_dist_sq = dist_sq
                best_idx = idx

        return points[best_idx] if best_idx >= 0 else None

    def _distance_sq_sign_to_road(self, road: Road, sign: Position) -> float:
        """Return squared distance from sign to nearest sampled road point."""
        sign_lon, sign_lat = sign.get_position()
        best_dist_sq = float("inf")

        for point in road.pointcollection:
            pt_lon, pt_lat = point.get_position()
            dx = pt_lon - sign_lon
            dy = pt_lat - sign_lat
            dist_sq = (dx * dx) + (dy * dy)
            if dist_sq < best_dist_sq:
                best_dist_sq = dist_sq

        return best_dist_sq

    def register_stop_signs(self, stop_sign_positions: List[Position]) -> None:
        """Register stop-sign positions and attach them to intersecting roads.

        Args:
            stop_sign_positions: Candidate stop-sign positions from routing metadata.

        Returns:
            None
        """
        for pos in stop_sign_positions:
            self._all_stop_signs.add(pos)
            roads = self._registry.find_roads_at_position(pos)
            if not roads:
                roads = self._registry.find_roads_near_position(
                    pos, STOP_SIGN_MATCH_TOLERANCE_DEGREES
                )
            if not roads:
                continue

            # Assign each stop sign to the single best matching road so we do not
            # stop on perpendicular roads at intersections.
            best_road = min(
                roads, key=lambda road: self._distance_sq_sign_to_road(road, pos)
            )

            trigger = self._compute_trigger_point_for_sign(best_road, pos)
            if trigger is None:
                continue

            existing_triggers = self._road_sign_trigger_points.get(
                best_road, {}
            ).values()
            cluster_tol_sq = (
                STOP_SIGN_INTERSECTION_CLUSTER_TOLERANCE_DEGREES
                * STOP_SIGN_INTERSECTION_CLUSTER_TOLERANCE_DEGREES
            )

            # If another stop sign on this road would trigger at nearly the same
            # point (typical at intersection sign clusters), keep only one stop.
            should_skip_sign = False
            trig_lon, trig_lat = trigger.get_position()
            for existing_trigger in existing_triggers:
                ex_lon, ex_lat = existing_trigger.get_position()
                dx = ex_lon - trig_lon
                dy = ex_lat - trig_lat
                if (dx * dx) + (dy * dy) <= cluster_tol_sq:
                    should_skip_sign = True
                    break

            if should_skip_sign:
                continue

            if best_road not in self._road_to_stop_signs:
                self._road_to_stop_signs[best_road] = set()
            self._road_to_stop_signs[best_road].add(pos)
            if best_road not in self._road_sign_trigger_points:
                self._road_sign_trigger_points[best_road] = {}
            self._road_sign_trigger_points[best_road][pos] = trigger

    def unregister_road(self, road: Road) -> None:
        """Drop stop-sign associations for a road that is being deallocated.

        Args:
            road: Road being deallocated.

        Returns:
            None
        """
        self._road_to_stop_signs.pop(road, None)
        self._road_sign_trigger_points.pop(road, None)

    def has_stop_sign(self, road: Road) -> bool:
        """Return True if a road has at least one registered stop sign.

        Args:
            road: Road to check.

        Returns:
            bool: True when at least one stop sign is associated with the road.
        """
        return bool(self._road_to_stop_signs.get(road))

    def get_stop_signs_for_road(self, road: Road) -> List[Position]:
        """Return stop-sign positions associated with a road.

        Args:
            road: Road whose stop signs should be returned.

        Returns:
            List[Position]: Stop-sign positions mapped to the road.
        """
        return list(self._road_to_stop_signs.get(road, set()))

    def get_matching_stop_sign_at_position(
        self, road: Road, position: Position
    ) -> Position | None:
        """Return the matching stop sign for a road-point pair, if any.

        Args:
            road: Road to inspect.
            position: Position candidate on that road.

        Returns:
            Position | None: Matching stop-sign position, or None.
        """
        road_signs = self._road_to_stop_signs.get(road, set())
        if not road_signs:
            return None

        target_lon, target_lat = position.get_position()
        trigger_map = self._road_sign_trigger_points.get(road, {})
        trigger_tol_sq = (
            STOP_SIGN_MATCH_TOLERANCE_DEGREES * STOP_SIGN_MATCH_TOLERANCE_DEGREES
        )

        for sign in road_signs:
            trigger = trigger_map.get(sign)
            if trigger is None:
                continue
            trig_lon, trig_lat = trigger.get_position()
            dx = trig_lon - target_lon
            dy = trig_lat - target_lat
            dist_sq = (dx * dx) + (dy * dy)

            if dist_sq <= trigger_tol_sq:
                return sign

        return None

    def is_stop_sign_at_position(self, road: Road, position: Position) -> bool:
        """Return True if the given road-position pair is a registered stop sign.

        Args:
            road: Road to inspect.
            position: Position candidate on that road.

        Returns:
            bool: True when the position matches a registered trigger point.
        """
        return self.get_matching_stop_sign_at_position(road, position) is not None

    def get_all_stop_signs(self) -> List[Position]:
        """Return all registered stop-sign positions.

        Returns:
            List[Position]: All known stop-sign positions tracked by the controller.
        """
        return list(self._all_stop_signs)
