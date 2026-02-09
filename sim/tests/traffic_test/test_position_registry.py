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
from sim.entities.traffic_event import TrafficEvent
from sim.map.position_registry import PositionRegistry


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_road(road_id: int, positions: list[Position]) -> Road:
    """Create a minimal Road for testing."""
    return Road(
        road_id=road_id,
        name=f"Road {road_id}",
        pointcollection=positions,
        length=100.0,
        maxspeed=10.0,
        geometry=positions,
    )


def _make_event(
    segment_key: tuple, tick_start: int = 0, duration: int = 100
) -> TrafficEvent:
    """Create a minimal TrafficEvent for testing."""
    return TrafficEvent(
        event_type="local_traffic",
        tick_start=tick_start,
        segment_key=segment_key,
        duration=duration,
        weight=0.5,
        name="Test Event",
    )


# ---------------------------------------------------------------------------
# Test: Register / Unregister Roads
# ---------------------------------------------------------------------------


class TestRegisterRoad:
    def test_register_road_single(self) -> None:
        registry = PositionRegistry()
        p1 = Position([0.0, 0.0])
        p2 = Position([1.0, 1.0])
        road = _make_road(1, [p1, p2])

        registry.register_road(road, [p1, p2])

        assert registry.find_roads_at_position(p1) == {road}
        assert registry.find_roads_at_position(p2) == {road}

    def test_register_road_empty_geometry(self) -> None:
        registry = PositionRegistry()
        road = _make_road(1, [Position([0.0, 0.0])])

        registry.register_road(road, [])

        # No positions should be indexed
        assert registry.find_roads_at_position(Position([0.0, 0.0])) == set()

    def test_unregister_road_removes_all_positions(self) -> None:
        registry = PositionRegistry()
        p1 = Position([0.0, 0.0])
        p2 = Position([1.0, 1.0])
        road = _make_road(1, [p1, p2])

        registry.register_road(road, [p1, p2])
        registry.unregister_road(road)

        assert registry.find_roads_at_position(p1) == set()
        assert registry.find_roads_at_position(p2) == set()

    def test_unregister_road_not_registered(self) -> None:
        """Unregistering a road that was never registered should not raise."""
        registry = PositionRegistry()
        road = _make_road(99, [Position([5.0, 5.0])])

        registry.unregister_road(road)  # Should be a no-op

    def test_multiple_roads_share_position(self) -> None:
        registry = PositionRegistry()
        shared = Position([1.0, 1.0])
        road_a = _make_road(1, [Position([0.0, 0.0]), shared])
        road_b = _make_road(2, [shared, Position([2.0, 2.0])])

        registry.register_road(road_a, [Position([0.0, 0.0]), shared])
        registry.register_road(road_b, [shared, Position([2.0, 2.0])])

        assert registry.find_roads_at_position(shared) == {road_a, road_b}

    def test_unregister_one_road_keeps_other(self) -> None:
        registry = PositionRegistry()
        shared = Position([1.0, 1.0])
        road_a = _make_road(1, [Position([0.0, 0.0]), shared])
        road_b = _make_road(2, [shared, Position([2.0, 2.0])])

        registry.register_road(road_a, [Position([0.0, 0.0]), shared])
        registry.register_road(road_b, [shared, Position([2.0, 2.0])])
        registry.unregister_road(road_a)

        assert registry.find_roads_at_position(shared) == {road_b}


# ---------------------------------------------------------------------------
# Test: Register / Unregister Events
# ---------------------------------------------------------------------------


class TestRegisterEvent:
    def test_register_event_single(self) -> None:
        registry = PositionRegistry()
        p1 = Position([0.0, 0.0])
        p2 = Position([1.0, 1.0])
        event = _make_event(((0.0, 0.0), (1.0, 1.0)))

        registry.register_event(event, [p1, p2])

        # Event should be findable via its positions
        assert event in registry._geom_to_events.get(p1, set())
        assert event in registry._geom_to_events.get(p2, set())

    def test_register_event_empty_geometry(self) -> None:
        registry = PositionRegistry()
        event = _make_event(((0.0, 0.0), (1.0, 1.0)))

        registry.register_event(event, [])

        assert registry._event_positions.get(event) is None

    def test_unregister_event_removes_all_positions(self) -> None:
        registry = PositionRegistry()
        p1 = Position([0.0, 0.0])
        p2 = Position([1.0, 1.0])
        event = _make_event(((0.0, 0.0), (1.0, 1.0)))

        registry.register_event(event, [p1, p2])
        registry.unregister_event(event)

        assert p1 not in registry._geom_to_events
        assert p2 not in registry._geom_to_events

    def test_unregister_event_not_registered(self) -> None:
        registry = PositionRegistry()
        event = _make_event(((5.0, 5.0), (6.0, 6.0)))

        registry.unregister_event(event)  # Should be a no-op


# ---------------------------------------------------------------------------
# Test: find_roads_for_event
# ---------------------------------------------------------------------------


class TestFindRoadsForEvent:
    def test_matching_positions(self) -> None:
        registry = PositionRegistry()
        shared = Position([1.0, 1.0])

        road = _make_road(1, [Position([0.0, 0.0]), shared, Position([2.0, 2.0])])
        event = _make_event(((1.0, 1.0), (3.0, 3.0)))

        registry.register_road(
            road, [Position([0.0, 0.0]), shared, Position([2.0, 2.0])]
        )
        registry.register_event(event, [shared, Position([3.0, 3.0])])

        result = registry.find_roads_for_event(event)
        assert result == {road}

    def test_no_matching_positions(self) -> None:
        registry = PositionRegistry()

        road = _make_road(1, [Position([0.0, 0.0]), Position([1.0, 1.0])])
        event = _make_event(((5.0, 5.0), (6.0, 6.0)))

        registry.register_road(road, [Position([0.0, 0.0]), Position([1.0, 1.0])])
        registry.register_event(event, [Position([5.0, 5.0]), Position([6.0, 6.0])])

        result = registry.find_roads_for_event(event)
        assert result == set()

    def test_multiple_roads_matching(self) -> None:
        registry = PositionRegistry()
        shared = Position([1.0, 1.0])

        road_a = _make_road(1, [Position([0.0, 0.0]), shared])
        road_b = _make_road(2, [shared, Position([2.0, 2.0])])
        event = _make_event(((1.0, 1.0), (3.0, 3.0)))

        registry.register_road(road_a, [Position([0.0, 0.0]), shared])
        registry.register_road(road_b, [shared, Position([2.0, 2.0])])
        registry.register_event(event, [shared, Position([3.0, 3.0])])

        result = registry.find_roads_for_event(event)
        assert result == {road_a, road_b}

    def test_event_not_registered(self) -> None:
        registry = PositionRegistry()
        event = _make_event(((0.0, 0.0), (1.0, 1.0)))

        # Event never registered -> should return empty set
        result = registry.find_roads_for_event(event)
        assert result == set()


# ---------------------------------------------------------------------------
# Test: find_events_for_road
# ---------------------------------------------------------------------------


class TestFindEventsForRoad:
    def test_matching_event(self) -> None:
        registry = PositionRegistry()
        shared = Position([1.0, 1.0])

        road = _make_road(1, [Position([0.0, 0.0]), shared])
        event = _make_event(((1.0, 1.0), (2.0, 2.0)))

        registry.register_road(road, [Position([0.0, 0.0]), shared])
        registry.register_event(event, [shared, Position([2.0, 2.0])])

        result = registry.find_events_for_road(road)
        assert result == {event}

    def test_no_matching_event(self) -> None:
        registry = PositionRegistry()

        road = _make_road(1, [Position([0.0, 0.0]), Position([1.0, 1.0])])
        event = _make_event(((5.0, 5.0), (6.0, 6.0)))

        registry.register_road(road, [Position([0.0, 0.0]), Position([1.0, 1.0])])
        registry.register_event(event, [Position([5.0, 5.0]), Position([6.0, 6.0])])

        result = registry.find_events_for_road(road)
        assert result == set()

    def test_road_not_registered(self) -> None:
        registry = PositionRegistry()
        road = _make_road(1, [Position([0.0, 0.0])])

        result = registry.find_events_for_road(road)
        assert result == set()


# ---------------------------------------------------------------------------
# Test: get_overlap_positions
# ---------------------------------------------------------------------------


class TestGetOverlapPositions:
    def test_overlap_exists(self) -> None:
        registry = PositionRegistry()
        shared = Position([1.0, 1.0])

        road = _make_road(1, [Position([0.0, 0.0]), shared, Position([2.0, 2.0])])
        event = _make_event(((1.0, 1.0), (3.0, 3.0)))

        registry.register_road(
            road, [Position([0.0, 0.0]), shared, Position([2.0, 2.0])]
        )
        registry.register_event(event, [shared, Position([3.0, 3.0])])

        overlap = registry.get_overlap_positions(road, event)
        assert overlap == {shared}

    def test_no_overlap(self) -> None:
        registry = PositionRegistry()

        road = _make_road(1, [Position([0.0, 0.0]), Position([1.0, 1.0])])
        event = _make_event(((5.0, 5.0), (6.0, 6.0)))

        registry.register_road(road, [Position([0.0, 0.0]), Position([1.0, 1.0])])
        registry.register_event(event, [Position([5.0, 5.0]), Position([6.0, 6.0])])

        overlap = registry.get_overlap_positions(road, event)
        assert overlap == set()

    def test_multiple_shared_positions(self) -> None:
        registry = PositionRegistry()
        p1 = Position([1.0, 1.0])
        p2 = Position([2.0, 2.0])

        road = _make_road(1, [Position([0.0, 0.0]), p1, p2, Position([3.0, 3.0])])
        event = _make_event(((1.0, 1.0), (2.0, 2.0)))

        registry.register_road(
            road, [Position([0.0, 0.0]), p1, p2, Position([3.0, 3.0])]
        )
        registry.register_event(event, [p1, p2])

        overlap = registry.get_overlap_positions(road, event)
        assert overlap == {p1, p2}


# ---------------------------------------------------------------------------
# Test: is_event_allocated
# ---------------------------------------------------------------------------


class TestIsEventAllocated:
    def test_allocated_when_roads_intersect(self) -> None:
        registry = PositionRegistry()
        shared = Position([1.0, 1.0])

        road = _make_road(1, [Position([0.0, 0.0]), shared])
        event = _make_event(((1.0, 1.0), (2.0, 2.0)))

        registry.register_road(road, [Position([0.0, 0.0]), shared])
        registry.register_event(event, [shared, Position([2.0, 2.0])])

        assert registry.is_event_allocated(event) is True

    def test_unallocated_when_no_roads(self) -> None:
        registry = PositionRegistry()
        event = _make_event(((5.0, 5.0), (6.0, 6.0)))

        registry.register_event(event, [Position([5.0, 5.0]), Position([6.0, 6.0])])

        assert registry.is_event_allocated(event) is False

    def test_unallocated_after_road_removed(self) -> None:
        registry = PositionRegistry()
        shared = Position([1.0, 1.0])

        road = _make_road(1, [Position([0.0, 0.0]), shared])
        event = _make_event(((1.0, 1.0), (2.0, 2.0)))

        registry.register_road(road, [Position([0.0, 0.0]), shared])
        registry.register_event(event, [shared, Position([2.0, 2.0])])

        assert registry.is_event_allocated(event) is True

        registry.unregister_road(road)

        assert registry.is_event_allocated(event) is False


# ---------------------------------------------------------------------------
# Test: Double Registration Guard
# ---------------------------------------------------------------------------


class TestDoubleRegistration:
    def test_double_register_road_cleans_stale_entries(self) -> None:
        """Re-registering a road with different geometry cleans up old entries."""
        registry = PositionRegistry()
        p_old = Position([0.0, 0.0])
        p_new = Position([5.0, 5.0])
        p_shared = Position([1.0, 1.0])

        road = _make_road(1, [p_old, p_shared])
        registry.register_road(road, [p_old, p_shared])
        assert registry.find_roads_at_position(p_old) == {road}

        # Re-register with different geometry
        registry.register_road(road, [p_new, p_shared])
        assert registry.find_roads_at_position(p_old) == set()
        assert registry.find_roads_at_position(p_new) == {road}
        assert registry.find_roads_at_position(p_shared) == {road}

    def test_double_register_event_cleans_stale_entries(self) -> None:
        """Re-registering an event with different geometry cleans up old entries."""
        registry = PositionRegistry()
        p_old = Position([0.0, 0.0])
        p_new = Position([5.0, 5.0])

        event = _make_event(((0.0, 0.0), (1.0, 1.0)))
        registry.register_event(event, [p_old])
        assert event in registry._geom_to_events.get(p_old, set())

        # Re-register with different geometry
        registry.register_event(event, [p_new])
        assert p_old not in registry._geom_to_events
        assert event in registry._geom_to_events.get(p_new, set())
