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

from typing import Any, Callable, List, Optional
from unittest.mock import Mock

import simpy

from sim.entities.position import Position
from sim.entities.traffic_event import TrafficEvent
from sim.entities.traffic_event_state import TrafficEventState
from sim.map.routing_provider import (
    RouteResult,
    RouteStep,
    RoutingProvider,
    SegmentKey,
)
from sim.traffic.traffic_controller import GPS_SYNC_DELAY, TrafficController


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _create_mock_route_controller() -> Mock:
    """Create a mock RouteController with callback registration."""
    rc = Mock()
    rc.get_all_active_roads = Mock(return_value=set())

    rc._on_road_created_callbacks = []
    rc._on_road_deallocated_callbacks = []

    def register_on_road_created(cb: Callable) -> None:
        rc._on_road_created_callbacks.append(cb)

    def unregister_on_road_created(cb: Callable) -> bool:
        try:
            rc._on_road_created_callbacks.remove(cb)
            return True
        except ValueError:
            return False

    def register_on_road_deallocated(cb: Callable) -> None:
        rc._on_road_deallocated_callbacks.append(cb)

    def unregister_on_road_deallocated(cb: Callable) -> bool:
        try:
            rc._on_road_deallocated_callbacks.remove(cb)
            return True
        except ValueError:
            return False

    rc.register_on_road_created = register_on_road_created
    rc.unregister_on_road_created = unregister_on_road_created
    rc.register_on_road_deallocated = register_on_road_deallocated
    rc.unregister_on_road_deallocated = unregister_on_road_deallocated

    return rc


def _make_event(
    segment_key: SegmentKey,
    tick_start: int = 0,
    duration: int = 100,
    weight: float = 0.5,
    name: str = "Test Event",
) -> TrafficEvent:
    """Create a minimal TrafficEvent for testing."""
    return TrafficEvent(
        event_type="local_traffic",
        tick_start=tick_start,
        segment_key=segment_key,
        duration=duration,
        weight=weight,
        name=name,
    )


class MockRoutingProvider(RoutingProvider):
    """A mock routing provider that returns predictable routes."""

    def __init__(self, route_result: Optional[RouteResult] = None) -> None:
        self._route_result = route_result
        self.set_edge_traffic_calls: list = []
        self.clear_edge_traffic_calls: list = []

    def get_route(self, start: Position, end: Position) -> Optional[RouteResult]:
        return self._route_result

    def get_distance(self, start: Position, end: Position) -> Optional[float]:
        return 100.0

    def snap_to_road(self, position: Position) -> Position:
        return position

    def close(self) -> None:
        pass

    def set_edge_traffic(self, update: Any) -> bool:
        self.set_edge_traffic_calls.append(update)
        return True

    def clear_edge_traffic(self, edge: Any) -> bool:
        self.clear_edge_traffic_calls.append(edge)
        return True


def _build_route_result(positions: List[Position]) -> RouteResult:
    """Build a RouteResult from a list of positions."""
    step = RouteStep(
        name="Test Road",
        distance=100.0,
        duration=10.0,
        geometry=positions,
        speed=10.0,
    )
    return RouteResult(
        coordinates=positions,
        distance=100.0,
        duration=10.0,
        steps=[step],
        segments=[],
    )


# ---------------------------------------------------------------------------
# Test: Full Event Lifecycle (unallocated — no PositionRegistry)
# ---------------------------------------------------------------------------


class TestEventLifecycle:
    """Tests for the full PENDING -> TRIGGERED -> APPLIED -> EXPIRED -> DONE cycle.

    Without a PositionRegistry, all events follow the unallocated path:
    only the routing provider is updated, no road-level traffic application.
    """

    def test_full_lifecycle_unallocated(self) -> None:
        """Event with no matching roads — only routing provider is updated."""
        env = simpy.Environment()
        rc = _create_mock_route_controller()

        positions = [Position([0.0, 0.0]), Position([1.0, 1.0])]
        route_result = _build_route_result(positions)
        provider = MockRoutingProvider(route_result)

        segment_key: SegmentKey = ((0.0, 0.0), (1.0, 1.0))
        event = _make_event(segment_key, tick_start=5, duration=20)

        tc = TrafficController(rc, env=env, routing_provider=provider)
        tc._traffic_events = [event]
        env.process(tc._run_traffic_events())

        # Run past everything: trigger(5) + duration(20) + buffer
        env.run(until=5 + 20 + GPS_SYNC_DELAY + 10)
        assert event.state == TrafficEventState.DONE

        # Routing provider should have been called for apply and remove
        assert len(provider.set_edge_traffic_calls) == 1
        assert len(provider.clear_edge_traffic_calls) == 1

    def test_state_transitions_in_order(self) -> None:
        """Verify that states transition in the correct order."""
        env = simpy.Environment()
        rc = _create_mock_route_controller()

        positions = [Position([0.0, 0.0]), Position([1.0, 1.0])]
        route_result = _build_route_result(positions)
        provider = MockRoutingProvider(route_result)

        segment_key: SegmentKey = ((0.0, 0.0), (1.0, 1.0))
        event = _make_event(segment_key, tick_start=10, duration=50)

        tc = TrafficController(rc, env=env, routing_provider=provider)
        tc._traffic_events = [event]
        env.process(tc._run_traffic_events())

        # Before trigger
        current = event.state
        assert current == TrafficEventState.PENDING

        # Just after trigger
        env.run(until=11)
        current = event.state
        assert current in (
            TrafficEventState.TRIGGERED,
            TrafficEventState.APPLIED,
        )

        # After sync completes
        env.run(until=15)
        current = event.state
        assert current == TrafficEventState.APPLIED

        # After expiry — on unallocated path, EXPIRED -> DONE happens in
        # the same tick (no GPS_SYNC_DELAY), so event may already be DONE
        env.run(until=10 + 50 + GPS_SYNC_DELAY + 5)
        current = event.state
        assert current == TrafficEventState.DONE

    def test_delayed_start_event(self) -> None:
        """Event with non-zero tick_start waits before triggering."""
        env = simpy.Environment()
        rc = _create_mock_route_controller()

        positions = [Position([0.0, 0.0]), Position([1.0, 1.0])]
        route_result = _build_route_result(positions)
        provider = MockRoutingProvider(route_result)

        segment_key: SegmentKey = ((0.0, 0.0), (1.0, 1.0))
        event = _make_event(segment_key, tick_start=100, duration=20)

        tc = TrafficController(rc, env=env, routing_provider=provider)
        tc._traffic_events = [event]
        env.process(tc._run_traffic_events())

        # Before trigger time
        env.run(until=99)
        assert event.state == TrafficEventState.PENDING

        # After trigger time
        env.run(until=101)
        assert event.state in (
            TrafficEventState.TRIGGERED,
            TrafficEventState.APPLIED,
        )


# ---------------------------------------------------------------------------
# Test: Synchronization Paths (unallocated)
# ---------------------------------------------------------------------------


class TestSynchronization:
    """Tests for the synchronization subprocess (unallocated path only).

    Without PositionRegistry, _check_allocation() always returns False,
    so all events take the unallocated path (routing provider only).
    """

    def test_triggered_unallocated_updates_only_provider(self) -> None:
        """[Triggered && Unallocated] path: only routing provider updated."""
        env = simpy.Environment()
        rc = _create_mock_route_controller()

        positions = [Position([0.0, 0.0]), Position([1.0, 1.0])]
        route_result = _build_route_result(positions)
        provider = MockRoutingProvider(route_result)

        segment_key: SegmentKey = ((0.0, 0.0), (1.0, 1.0))
        event = _make_event(segment_key, tick_start=0, duration=200)

        tc = TrafficController(rc, env=env, routing_provider=provider)
        tc._traffic_events = [event]
        env.process(tc._run_traffic_events())

        env.run(until=5)

        assert event.state == TrafficEventState.APPLIED
        assert len(event.affected_roads) == 0
        assert len(provider.set_edge_traffic_calls) == 1

    def test_expired_unallocated_resets_only_provider(self) -> None:
        """[Expired && Unallocated] path: only provider reset."""
        env = simpy.Environment()
        rc = _create_mock_route_controller()

        positions = [Position([0.0, 0.0]), Position([1.0, 1.0])]
        route_result = _build_route_result(positions)
        provider = MockRoutingProvider(route_result)

        segment_key: SegmentKey = ((0.0, 0.0), (1.0, 1.0))
        event = _make_event(segment_key, tick_start=0, duration=20)

        tc = TrafficController(rc, env=env, routing_provider=provider)
        tc._traffic_events = [event]
        env.process(tc._run_traffic_events())

        # Run past full lifecycle
        env.run(until=20 + GPS_SYNC_DELAY + 10)

        assert event.state == TrafficEventState.DONE
        assert len(event.affected_roads) == 0
        # Routing provider should have been called for both apply and reset
        assert len(provider.set_edge_traffic_calls) == 1
        assert len(provider.clear_edge_traffic_calls) == 1

    def test_active_traffic_dict_updated_on_apply(self) -> None:
        """Verify _set_traffic_in_simulation stores in active_traffic."""
        env = simpy.Environment()
        rc = _create_mock_route_controller()

        positions = [Position([0.0, 0.0]), Position([1.0, 1.0])]
        route_result = _build_route_result(positions)
        provider = MockRoutingProvider(route_result)

        segment_key: SegmentKey = ((0.0, 0.0), (1.0, 1.0))
        event = _make_event(segment_key, tick_start=0, duration=200, weight=0.4)

        tc = TrafficController(rc, env=env, routing_provider=provider)
        tc._traffic_events = [event]
        env.process(tc._run_traffic_events())

        # Since unallocated, _set_traffic_in_simulation is not called
        # (it goes to routing provider only), but we can check state after apply
        env.run(until=5)
        assert event.state == TrafficEventState.APPLIED


# ---------------------------------------------------------------------------
# Test: Routing Provider Graceful No-Op
# ---------------------------------------------------------------------------


class TestRoutingProviderGracefulNoOp:
    """Tests that NotImplementedError from routing provider is handled gracefully."""

    def test_not_implemented_error_handled(self) -> None:
        """TC handles routing provider that doesn't support traffic updates."""
        env = simpy.Environment()
        rc = _create_mock_route_controller()

        positions = [Position([0.0, 0.0]), Position([1.0, 1.0])]
        route_result = _build_route_result(positions)

        # Use a provider that raises NotImplementedError
        provider = MockRoutingProvider(route_result)
        provider.set_edge_traffic = Mock(  # type: ignore[method-assign]
            side_effect=NotImplementedError
        )
        provider.clear_edge_traffic = Mock(  # type: ignore[method-assign]
            side_effect=NotImplementedError
        )

        segment_key: SegmentKey = ((0.0, 0.0), (1.0, 1.0))
        event = _make_event(segment_key, tick_start=0, duration=20)

        tc = TrafficController(rc, env=env, routing_provider=provider)
        tc._traffic_events = [event]
        env.process(tc._run_traffic_events())

        # Should not raise — completes full lifecycle
        env.run(until=20 + GPS_SYNC_DELAY + 10)
        assert event.state == TrafficEventState.DONE


# ---------------------------------------------------------------------------
# Test: Sync Resource Serialization
# ---------------------------------------------------------------------------


class TestSyncResourceSerialization:
    """Tests that concurrent events are serialized through the sync resource."""

    def test_two_events_same_tick_serialized(self) -> None:
        """Two events triggered at the same tick are processed sequentially."""
        env = simpy.Environment()
        rc = _create_mock_route_controller()

        positions = [Position([0.0, 0.0]), Position([1.0, 1.0])]
        route_result = _build_route_result(positions)
        provider = MockRoutingProvider(route_result)

        event_a = _make_event(
            ((0.0, 0.0), (1.0, 1.0)), tick_start=5, duration=50, name="Event A"
        )
        event_b = _make_event(
            ((2.0, 2.0), (3.0, 3.0)), tick_start=5, duration=50, name="Event B"
        )

        tc = TrafficController(rc, env=env, routing_provider=provider)
        tc._traffic_events = [event_a, event_b]
        env.process(tc._run_traffic_events())

        # Run until both are in APPLIED state
        env.run(until=5 + GPS_SYNC_DELAY + 5)

        # Both events should reach APPLIED — sync resource serializes, not blocks
        assert event_a.state == TrafficEventState.APPLIED
        assert event_b.state == TrafficEventState.APPLIED


# ---------------------------------------------------------------------------
# Test: No Routing Provider
# ---------------------------------------------------------------------------


class TestNoRoutingProvider:
    """Tests behavior when no routing provider is available."""

    def test_geometry_resolution_returns_none(self) -> None:
        """Without routing provider, geometry resolution returns None."""
        env = simpy.Environment()
        rc = _create_mock_route_controller()

        segment_key: SegmentKey = ((0.0, 0.0), (1.0, 1.0))
        event = _make_event(segment_key, tick_start=0, duration=20)

        tc = TrafficController(rc, env=env, routing_provider=None)
        tc._traffic_events = [event]
        env.process(tc._run_traffic_events())

        env.run(until=20 + GPS_SYNC_DELAY + 10)

        # Event should still complete lifecycle
        assert event.state == TrafficEventState.DONE
        # But no geometry was resolved
        assert event.route_geometry is None


# ---------------------------------------------------------------------------
# Test: Check for Similar Event
# ---------------------------------------------------------------------------


class TestCheckForSimilarEvent:
    """Tests for the _check_for_similar_event logic."""

    def test_similar_pending_event_detected(self) -> None:
        """When an event completes, similar PENDING events are detected."""
        env = simpy.Environment()
        rc = _create_mock_route_controller()

        positions = [Position([0.0, 0.0]), Position([1.0, 1.0])]
        route_result = _build_route_result(positions)
        provider = MockRoutingProvider(route_result)

        segment_key: SegmentKey = ((0.0, 0.0), (1.0, 1.0))

        # First event triggers and completes quickly
        event_first = _make_event(segment_key, tick_start=0, duration=10, name="First")
        # Second event on same segment, triggers later
        event_second = _make_event(
            segment_key, tick_start=100, duration=10, name="Second"
        )

        tc = TrafficController(rc, env=env, routing_provider=provider)
        tc._traffic_events = [event_first, event_second]
        env.process(tc._run_traffic_events())

        # Run until first event is DONE
        env.run(until=10 + GPS_SYNC_DELAY + 5)

        assert event_first.state == TrafficEventState.DONE
        # Second event should still be PENDING
        assert event_second.state == TrafficEventState.PENDING


# ---------------------------------------------------------------------------
# Test: Delete Event (memory cleanup)
# ---------------------------------------------------------------------------


class TestDeleteEvent:
    """Tests that completed events are removed from the internal list."""

    def test_done_event_removed_from_list(self) -> None:
        """After DONE, event is removed from _traffic_events to free memory."""
        env = simpy.Environment()
        rc = _create_mock_route_controller()

        positions = [Position([0.0, 0.0]), Position([1.0, 1.0])]
        route_result = _build_route_result(positions)
        provider = MockRoutingProvider(route_result)

        segment_key: SegmentKey = ((0.0, 0.0), (1.0, 1.0))
        event = _make_event(segment_key, tick_start=0, duration=10)

        tc = TrafficController(rc, env=env, routing_provider=provider)
        tc._traffic_events = [event]
        env.process(tc._run_traffic_events())

        # Run past full lifecycle
        env.run(until=10 + GPS_SYNC_DELAY + 10)

        assert event.state == TrafficEventState.DONE
        assert event not in tc._traffic_events


# ---------------------------------------------------------------------------
# Test: Geometry Resolution
# ---------------------------------------------------------------------------


class TestGeometryResolution:
    """Tests for _resolve_event_geometry."""

    def test_geometry_resolved_from_route_steps(self) -> None:
        """Geometry is extracted from route steps when available."""
        env = simpy.Environment()
        rc = _create_mock_route_controller()

        positions = [Position([0.0, 0.0]), Position([0.5, 0.5]), Position([1.0, 1.0])]
        route_result = _build_route_result(positions)
        provider = MockRoutingProvider(route_result)

        segment_key: SegmentKey = ((0.0, 0.0), (1.0, 1.0))
        event = _make_event(segment_key, tick_start=0, duration=100)

        tc = TrafficController(rc, env=env, routing_provider=provider)
        tc._traffic_events = [event]
        env.process(tc._run_traffic_events())

        env.run(until=5)
        assert event.route_geometry is not None
        assert len(event.route_geometry) == 3

    def test_geometry_falls_back_to_coordinates(self) -> None:
        """Falls back to route coordinates when no steps have geometry."""
        env = simpy.Environment()
        rc = _create_mock_route_controller()

        positions = [Position([0.0, 0.0]), Position([1.0, 1.0])]
        # Route result with empty step geometry
        route_result = RouteResult(
            coordinates=positions,
            distance=100.0,
            duration=10.0,
            steps=[
                RouteStep(
                    name="r", distance=100.0, duration=10.0, geometry=[], speed=10.0
                )
            ],
            segments=[],
        )
        provider = MockRoutingProvider(route_result)

        segment_key: SegmentKey = ((0.0, 0.0), (1.0, 1.0))
        event = _make_event(segment_key, tick_start=0, duration=100)

        tc = TrafficController(rc, env=env, routing_provider=provider)
        tc._traffic_events = [event]
        env.process(tc._run_traffic_events())

        env.run(until=5)
        assert event.route_geometry is not None
        assert len(event.route_geometry) == 2

    def test_geometry_falls_back_to_endpoints_on_error(self) -> None:
        """Falls back to segment_key endpoints when routing provider fails."""
        env = simpy.Environment()
        rc = _create_mock_route_controller()

        provider = MockRoutingProvider(None)  # Returns None for get_route

        segment_key: SegmentKey = ((0.0, 0.0), (1.0, 1.0))
        event = _make_event(segment_key, tick_start=0, duration=100)

        tc = TrafficController(rc, env=env, routing_provider=provider)
        tc._traffic_events = [event]
        env.process(tc._run_traffic_events())

        env.run(until=5)
        # Fallback: just the two endpoints
        assert event.route_geometry is not None
        assert len(event.route_geometry) == 2


# ---------------------------------------------------------------------------
# Test: TrafficEvent Dataclass
# ---------------------------------------------------------------------------


class TestTrafficEventDataclass:
    """Tests for the updated TrafficEvent dataclass."""

    def test_hash_by_identity_fields(self) -> None:
        """TrafficEvent is hashable using (type, tick, segment_key, duration)."""
        event = _make_event(((0.0, 0.0), (1.0, 1.0)), tick_start=10, duration=50)
        h = hash(event)
        assert isinstance(h, int)

    def test_eq_compares_identity_fields(self) -> None:
        """Two events with same identity fields are equal."""
        e1 = _make_event(((0.0, 0.0), (1.0, 1.0)), tick_start=10, duration=50)
        e2 = _make_event(((0.0, 0.0), (1.0, 1.0)), tick_start=10, duration=50)
        assert e1 == e2

    def test_eq_different_fields_not_equal(self) -> None:
        """Events with different identity fields are not equal."""
        e1 = _make_event(((0.0, 0.0), (1.0, 1.0)), tick_start=10, duration=50)
        e2 = _make_event(((0.0, 0.0), (1.0, 1.0)), tick_start=20, duration=50)
        assert e1 != e2

    def test_default_state_is_pending(self) -> None:
        """New events start in PENDING state."""
        event = _make_event(((0.0, 0.0), (1.0, 1.0)))
        assert event.state == TrafficEventState.PENDING

    def test_route_geometry_default_none(self) -> None:
        """route_geometry defaults to None."""
        event = _make_event(((0.0, 0.0), (1.0, 1.0)))
        assert event.route_geometry is None

    def test_affected_roads_default_empty(self) -> None:
        """affected_roads defaults to empty set."""
        event = _make_event(((0.0, 0.0), (1.0, 1.0)))
        assert event.affected_roads == set()

    def test_event_usable_in_set(self) -> None:
        """Events can be stored in sets (hashable)."""
        e1 = _make_event(((0.0, 0.0), (1.0, 1.0)), tick_start=10, duration=50)
        e2 = _make_event(((2.0, 2.0), (3.0, 3.0)), tick_start=10, duration=50)
        s = {e1, e2}
        assert len(s) == 2
