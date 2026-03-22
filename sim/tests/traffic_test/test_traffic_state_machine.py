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
from sim.entities.road import Road
from sim.entities.traffic_event import TrafficEvent
from sim.entities.traffic_event_state import TrafficEventState
from sim.map.routing_provider import (
    RouteResult,
    RouteStep,
    RoutingProvider,
    SegmentKey,
)
from sim.map.position_registry import PositionRegistry
from sim.traffic.traffic_controller import TrafficController


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _create_mock_route_controller() -> Mock:
    """Create a mock RouteController with callback registration."""
    rc = Mock()
    rc.get_all_active_roads = Mock(return_value=set())
    rc.get_routes_for_road = Mock(return_value=set())

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


def _make_road(road_id: int, positions: List[Position]) -> Road:
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
        self.gps_sync_delay: int = 10

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

    def get_gps_sync_delay(self) -> int:
        return self.gps_sync_delay


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


def _simulate_road_creation(rc: Mock, road: Road) -> None:
    """Simulate road creation by firing all registered callbacks."""
    for cb in rc._on_road_created_callbacks:
        cb(road)


def _simulate_road_deallocation(rc: Mock, road: Road) -> None:
    """Simulate road deallocation by firing all registered callbacks."""
    for cb in rc._on_road_deallocated_callbacks:
        cb(road)


# ---------------------------------------------------------------------------
# Test: Full Event Lifecycle
# ---------------------------------------------------------------------------


class TestEventLifecycle:
    """Tests for the full PENDING -> TRIGGERED -> APPLIED -> EXPIRED -> DONE cycle."""

    def test_full_lifecycle_allocated(self) -> None:
        """Event with matching road goes through full state machine."""
        env = simpy.Environment()
        rc = _create_mock_route_controller()
        registry = PositionRegistry()

        # Shared position between road and event
        shared = Position([1.0, 1.0])
        positions = [Position([0.0, 0.0]), shared, Position([2.0, 2.0])]

        route_result = _build_route_result(positions)
        provider = MockRoutingProvider(route_result)

        segment_key: SegmentKey = ((0.0, 0.0), (2.0, 2.0))
        event = _make_event(segment_key, tick_start=10, duration=50)

        # Create road and register in registry
        road = _make_road(1, positions)
        registry.register_road(road, positions)

        # Create TC — event is injected manually
        tc = TrafficController(
            rc, env=env, routing_provider=provider, registry=registry
        )
        tc._traffic_events = [event]
        env.process(tc._run_traffic_events())

        # Run until just after trigger (tick 10)
        env.run(until=11)
        assert event.state in (
            TrafficEventState.TRIGGERED,
            TrafficEventState.APPLIED,
        )

        # Run past sync delay: tick_start(10) + GPS_SYNC_DELAY(10) + 1
        gps_sync_delay = provider.get_gps_sync_delay()
        env.run(until=10 + gps_sync_delay + 1)
        current = event.state
        assert current == TrafficEventState.APPLIED

        # Run until expiry: tick + duration + GPS_SYNC_DELAY + 1
        gps_sync_delay = provider.get_gps_sync_delay()
        env.run(until=10 + 50 + gps_sync_delay + 1)
        current = event.state
        assert current == TrafficEventState.DONE

    def test_full_lifecycle_unallocated(self) -> None:
        """Event with no matching roads — only routing provider is updated."""
        env = simpy.Environment()
        rc = _create_mock_route_controller()
        registry = PositionRegistry()

        positions = [Position([0.0, 0.0]), Position([1.0, 1.0])]
        route_result = _build_route_result(positions)
        provider = MockRoutingProvider(route_result)

        segment_key: SegmentKey = ((0.0, 0.0), (1.0, 1.0))
        event = _make_event(segment_key, tick_start=5, duration=20)

        tc = TrafficController(
            rc, env=env, routing_provider=provider, registry=registry
        )
        tc._traffic_events = [event]
        env.process(tc._run_traffic_events())

        # Run past everything: trigger(5) + duration(20) + buffer
        gps_sync_delay = provider.get_gps_sync_delay()

        env.run(until=5 + 20 + gps_sync_delay + 10)
        assert event.state == TrafficEventState.DONE

        # Routing provider should have been called for apply and remove
        assert len(provider.set_edge_traffic_calls) == 1
        assert len(provider.clear_edge_traffic_calls) == 1


# ---------------------------------------------------------------------------
# Test: Synchronization Paths
# ---------------------------------------------------------------------------


class TestSynchronization:
    """Tests for the 4-path synchronization subprocess."""

    def test_triggered_allocated_applies_to_road(self) -> None:
        """[Triggered && Allocated] path: applies to road + provider."""
        env = simpy.Environment()
        rc = _create_mock_route_controller()
        registry = PositionRegistry()

        shared = Position([1.0, 1.0])
        positions = [Position([0.0, 0.0]), shared, Position([2.0, 2.0])]
        route_result = _build_route_result(positions)
        provider = MockRoutingProvider(route_result)

        segment_key: SegmentKey = ((0.0, 0.0), (2.0, 2.0))
        event = _make_event(segment_key, tick_start=0, duration=200, weight=0.4)

        road = _make_road(1, positions)
        registry.register_road(road, positions)

        tc = TrafficController(
            rc, env=env, routing_provider=provider, registry=registry
        )
        tc._traffic_events = [event]
        env.process(tc._run_traffic_events())

        # Run past sync delay to ensure APPLIED
        gps_sync_delay = provider.get_gps_sync_delay()
        env.run(until=gps_sync_delay + 5)

        assert event.state == TrafficEventState.APPLIED
        assert road in event.affected_roads
        # Routing provider should have received the traffic update
        assert len(provider.set_edge_traffic_calls) == 1

    def test_triggered_unallocated_updates_only_provider(self) -> None:
        """[Triggered && Unallocated] path: only routing provider updated."""
        env = simpy.Environment()
        rc = _create_mock_route_controller()
        registry = PositionRegistry()

        positions = [Position([0.0, 0.0]), Position([1.0, 1.0])]
        route_result = _build_route_result(positions)
        provider = MockRoutingProvider(route_result)

        segment_key: SegmentKey = ((0.0, 0.0), (1.0, 1.0))
        event = _make_event(segment_key, tick_start=0, duration=200)

        # No road registered — event is unallocated

        tc = TrafficController(
            rc, env=env, routing_provider=provider, registry=registry
        )
        tc._traffic_events = [event]
        env.process(tc._run_traffic_events())

        env.run(until=5)

        assert event.state == TrafficEventState.APPLIED
        assert len(event.affected_roads) == 0
        assert len(provider.set_edge_traffic_calls) == 1

    def test_expired_allocated_removes_from_road(self) -> None:
        """[Expired && Allocated] path: traffic removed from road."""
        env = simpy.Environment()
        rc = _create_mock_route_controller()
        registry = PositionRegistry()

        shared = Position([1.0, 1.0])
        positions = [Position([0.0, 0.0]), shared, Position([2.0, 2.0])]
        route_result = _build_route_result(positions)
        provider = MockRoutingProvider(route_result)

        segment_key: SegmentKey = ((0.0, 0.0), (2.0, 2.0))
        event = _make_event(segment_key, tick_start=0, duration=30, weight=0.3)

        road = _make_road(1, positions)
        registry.register_road(road, positions)

        tc = TrafficController(
            rc, env=env, routing_provider=provider, registry=registry
        )
        tc._traffic_events = [event]
        env.process(tc._run_traffic_events())

        # Run past full lifecycle: duration(30) + GPS_SYNC_DELAY(10) + buffer
        gps_sync_delay = provider.get_gps_sync_delay()
        env.run(until=30 + gps_sync_delay * 2 + 10)

        assert event.state == TrafficEventState.DONE
        assert len(event.affected_roads) == 0
        assert len(provider.clear_edge_traffic_calls) == 1

    def test_expired_unallocated_resets_only_provider(self) -> None:
        """[Expired && Unallocated] path: only provider reset."""
        env = simpy.Environment()
        rc = _create_mock_route_controller()
        registry = PositionRegistry()

        positions = [Position([0.0, 0.0]), Position([1.0, 1.0])]
        route_result = _build_route_result(positions)
        provider = MockRoutingProvider(route_result)

        segment_key: SegmentKey = ((0.0, 0.0), (1.0, 1.0))
        event = _make_event(segment_key, tick_start=0, duration=20)

        # No road registered — event stays unallocated throughout

        tc = TrafficController(
            rc, env=env, routing_provider=provider, registry=registry
        )
        tc._traffic_events = [event]
        env.process(tc._run_traffic_events())

        # Run past full lifecycle
        gps_sync_delay = provider.get_gps_sync_delay()
        env.run(until=20 + gps_sync_delay * 2 + 10)

        assert event.state == TrafficEventState.DONE
        assert len(event.affected_roads) == 0
        # Routing provider should have been called for both apply and reset
        assert len(provider.set_edge_traffic_calls) == 1
        assert len(provider.clear_edge_traffic_calls) == 1


# ---------------------------------------------------------------------------
# Test: GPS Sync Delay
# ---------------------------------------------------------------------------


class TestGPSSyncDelay:
    """Verify the 10-tick delay between sim and routing provider updates."""

    def test_delay_between_sim_and_routing_provider(self) -> None:
        """Sim update happens first, routing provider after GPS_SYNC_DELAY ticks."""
        env = simpy.Environment()
        rc = _create_mock_route_controller()
        registry = PositionRegistry()

        shared = Position([1.0, 1.0])
        positions = [Position([0.0, 0.0]), shared, Position([2.0, 2.0])]
        route_result = _build_route_result(positions)
        provider = MockRoutingProvider(route_result)

        segment_key: SegmentKey = ((0.0, 0.0), (2.0, 2.0))
        event = _make_event(segment_key, tick_start=0, duration=500)

        road = _make_road(1, positions)
        registry.register_road(road, positions)

        tc = TrafficController(
            rc, env=env, routing_provider=provider, registry=registry
        )
        tc._traffic_events = [event]
        env.process(tc._run_traffic_events())

        # Run just past trigger but before GPS delay completes
        gps_sync_delay = provider.get_gps_sync_delay()
        env.run(until=gps_sync_delay - 1)

        # Road should already have traffic (sim update first in allocated path)
        assert road in event.affected_roads
        # But routing provider should NOT have been called yet
        assert len(provider.set_edge_traffic_calls) == 0

        # Now run past the GPS delay
        gps_sync_delay
        env.run(until=gps_sync_delay + 1)

        # Routing provider should now have been called
        assert len(provider.set_edge_traffic_calls) == 1

    def test_expiry_delay_sim_before_routing_provider(self) -> None:
        """On expiry, sim cleanup happens first, routing provider after GPS_SYNC_DELAY.

        Per the state diagram: [Expired&&Allocated] path is
        Sim -> DelayTransition -> RoutingProvider (symmetric with trigger path).
        """
        env = simpy.Environment()
        rc = _create_mock_route_controller()
        registry = PositionRegistry()

        shared = Position([1.0, 1.0])
        positions = [Position([0.0, 0.0]), shared, Position([2.0, 2.0])]
        route_result = _build_route_result(positions)
        provider = MockRoutingProvider(route_result)

        segment_key: SegmentKey = ((0.0, 0.0), (2.0, 2.0))
        event = _make_event(segment_key, tick_start=0, duration=50)

        road = _make_road(1, positions)
        registry.register_road(road, positions)

        tc = TrafficController(
            rc, env=env, routing_provider=provider, registry=registry
        )
        tc._traffic_events = [event]
        env.process(tc._run_traffic_events())

        # Get to APPLIED state
        gps_sync_delay = provider.get_gps_sync_delay()
        env.run(until=gps_sync_delay + 5)
        assert event.state == TrafficEventState.APPLIED
        assert road in event.affected_roads

        # Run to just after expiry but before the GPS delay completes
        # Expiry at tick 50, sim cleanup immediate, RP reset after GPS_SYNC_DELAY
        env.run(until=50 + gps_sync_delay - 1)

        # Sim should already be cleaned up (affected_roads cleared)
        assert len(event.affected_roads) == 0
        assert road.traffic_multiplier == 1.0
        # But routing provider should NOT have been called for clear yet
        assert len(provider.clear_edge_traffic_calls) == 0

        # Now run past the GPS delay
        env.run(until=50 + gps_sync_delay + 1)

        # Routing provider should now have been called for clear
        assert len(provider.clear_edge_traffic_calls) == 1


# ---------------------------------------------------------------------------
# Test: Road Lifecycle Callbacks During APPLIED State
# ---------------------------------------------------------------------------


class TestRoadLifecycleDuringApplied:
    """Tests for dynamic road creation/deallocation during the APPLIED state."""

    def test_new_road_gets_traffic_during_applied_state(self) -> None:
        """Road created after event is APPLIED gets traffic via callback."""
        env = simpy.Environment()
        rc = _create_mock_route_controller()
        registry = PositionRegistry()

        shared = Position([1.0, 1.0])
        event_positions = [Position([0.0, 0.0]), shared, Position([2.0, 2.0])]
        route_result = _build_route_result(event_positions)
        provider = MockRoutingProvider(route_result)

        segment_key: SegmentKey = ((0.0, 0.0), (2.0, 2.0))
        event = _make_event(segment_key, tick_start=0, duration=200, weight=0.4)

        # No road initially — event starts unallocated

        tc = TrafficController(
            rc, env=env, routing_provider=provider, registry=registry
        )
        tc._traffic_events = [event]
        env.process(tc._run_traffic_events())

        # Advance past trigger to APPLIED state
        env.run(until=5)
        assert event.state == TrafficEventState.APPLIED

        # Now create a road that shares geometry with the event
        road = _make_road(1, [Position([0.0, 0.0]), shared, Position([2.0, 2.0])])
        registry.register_road(
            road, [Position([0.0, 0.0]), shared, Position([2.0, 2.0])]
        )

        # Simulate road creation callback (fires TC._on_road_created)
        _simulate_road_creation(rc, road)

        # Road should now be in affected_roads (Unallocated -> Allocated)
        assert road in event.affected_roads

    def test_road_deallocation_during_applied_cleans_up(self) -> None:
        """Road deallocated during APPLIED state is removed from affected_roads."""
        env = simpy.Environment()
        rc = _create_mock_route_controller()
        registry = PositionRegistry()

        shared = Position([1.0, 1.0])
        positions = [Position([0.0, 0.0]), shared, Position([2.0, 2.0])]
        route_result = _build_route_result(positions)
        provider = MockRoutingProvider(route_result)

        segment_key: SegmentKey = ((0.0, 0.0), (2.0, 2.0))
        event = _make_event(segment_key, tick_start=0, duration=200, weight=0.4)

        road = _make_road(1, positions)
        registry.register_road(road, positions)

        tc = TrafficController(
            rc, env=env, routing_provider=provider, registry=registry
        )
        tc._traffic_events = [event]
        env.process(tc._run_traffic_events())

        # Advance to APPLIED state
        gps_sync_delay = provider.get_gps_sync_delay()
        env.run(until=gps_sync_delay + 5)
        assert event.state == TrafficEventState.APPLIED
        assert road in event.affected_roads

        # Deallocate the road
        _simulate_road_deallocation(rc, road)

        # Road should be removed from affected_roads (Allocated -> Unallocated)
        assert road not in event.affected_roads


# ---------------------------------------------------------------------------
# Test: Allocated -> Unallocated Transition & Cleanup
# ---------------------------------------------------------------------------


class TestAllocatedToUnallocatedTransition:
    """Tests for the Allocated -> Unallocated transition when roads are deallocated.

    Verifies that when all intersecting roads are deallocated during the APPLIED
    state, the event correctly transitions to unallocated and expiry cleanup
    takes the routing-provider-only path.
    """

    def test_multi_road_deallocation_clears_affected_roads(self) -> None:
        """3 roads allocated, all deallocated one by one -> affected_roads empty."""
        env = simpy.Environment()
        rc = _create_mock_route_controller()
        registry = PositionRegistry()

        # Shared positions across 3 roads and the event
        p0 = Position([0.0, 0.0])
        p1 = Position([1.0, 1.0])
        p2 = Position([2.0, 2.0])
        p3 = Position([3.0, 3.0])
        p4 = Position([4.0, 4.0])

        # Event covers p0 -> p4
        event_positions = [p0, p1, p2, p3, p4]
        route_result = _build_route_result(event_positions)
        provider = MockRoutingProvider(route_result)

        segment_key: SegmentKey = ((0.0, 0.0), (4.0, 4.0))
        event = _make_event(segment_key, tick_start=0, duration=500, weight=0.3)

        # 3 roads, each sharing some positions with the event
        road_a = _make_road(1, [p0, p1])
        road_b = _make_road(2, [p1, p2, p3])
        road_c = _make_road(3, [p3, p4])

        registry.register_road(road_a, [p0, p1])
        registry.register_road(road_b, [p1, p2, p3])
        registry.register_road(road_c, [p3, p4])

        tc = TrafficController(
            rc, env=env, routing_provider=provider, registry=registry
        )
        tc._traffic_events = [event]
        env.process(tc._run_traffic_events())

        # Run to APPLIED
        gps_sync_delay = provider.get_gps_sync_delay()
        env.run(until=gps_sync_delay + 5)
        assert event.state == TrafficEventState.APPLIED
        assert road_a in event.affected_roads
        assert road_b in event.affected_roads
        assert road_c in event.affected_roads
        assert len(event.affected_roads) == 3

        # Deallocate roads one by one (simulating vehicle traversal)
        # Real flow: callbacks fire first, then registry.unregister_road()
        _simulate_road_deallocation(rc, road_a)
        registry.unregister_road(road_a)
        assert road_a not in event.affected_roads
        assert len(event.affected_roads) == 2

        _simulate_road_deallocation(rc, road_b)
        registry.unregister_road(road_b)
        assert road_b not in event.affected_roads
        assert len(event.affected_roads) == 1

        _simulate_road_deallocation(rc, road_c)
        registry.unregister_road(road_c)
        assert road_c not in event.affected_roads
        assert len(event.affected_roads) == 0

        # Event is now unallocated
        assert not registry.is_event_allocated(event)

    def test_allocated_to_unallocated_expiry_uses_provider_only_path(self) -> None:
        """Event starts allocated, all roads deallocated, expires via unallocated path.

        The key behavior: at expiry, _check_allocation() returns False because
        roads were already removed from registry. So the Expired && Unallocated
        path fires (routing provider only), and _reset_traffic_in_simulation()
        is NOT called (no roads to clean up).
        """
        env = simpy.Environment()
        rc = _create_mock_route_controller()
        registry = PositionRegistry()

        p0 = Position([0.0, 0.0])
        p1 = Position([1.0, 1.0])
        p2 = Position([2.0, 2.0])

        event_positions = [p0, p1, p2]
        route_result = _build_route_result(event_positions)
        provider = MockRoutingProvider(route_result)

        segment_key: SegmentKey = ((0.0, 0.0), (2.0, 2.0))
        event = _make_event(segment_key, tick_start=0, duration=50, weight=0.4)

        road = _make_road(1, [p0, p1, p2])
        registry.register_road(road, [p0, p1, p2])

        tc = TrafficController(
            rc, env=env, routing_provider=provider, registry=registry
        )
        tc._traffic_events = [event]
        env.process(tc._run_traffic_events())

        # Run to APPLIED — allocated path (sim + provider)
        gps_sync_delay = provider.get_gps_sync_delay()
        env.run(until=gps_sync_delay + 5)
        assert TrafficEventState(event.state) == TrafficEventState.APPLIED
        assert road in event.affected_roads
        assert len(provider.set_edge_traffic_calls) == 1

        # Deallocate the road mid-lifecycle (vehicle drove past it)
        # Real flow: callbacks fire first, then registry.unregister_road()
        _simulate_road_deallocation(rc, road)
        registry.unregister_road(road)
        assert len(event.affected_roads) == 0

        # Run past expiry — unallocated path (provider only, no GPS delay)
        env.run(until=50 + gps_sync_delay + 5)
        assert TrafficEventState(event.state) == TrafficEventState.DONE

        # Provider should have received both set + clear
        assert len(provider.set_edge_traffic_calls) == 1
        assert len(provider.clear_edge_traffic_calls) == 1

    def test_partial_deallocation_stays_allocated_at_expiry(self) -> None:
        """Only some roads deallocated — event stays allocated at expiry.

        When 2 of 3 roads are deallocated but 1 remains, the event is still
        allocated at expiry and takes the Expired && Allocated path
        (provider reset -> GPS delay -> sim cleanup).
        """
        env = simpy.Environment()
        rc = _create_mock_route_controller()
        registry = PositionRegistry()

        p0 = Position([0.0, 0.0])
        p1 = Position([1.0, 1.0])
        p2 = Position([2.0, 2.0])
        p3 = Position([3.0, 3.0])

        event_positions = [p0, p1, p2, p3]
        route_result = _build_route_result(event_positions)
        provider = MockRoutingProvider(route_result)

        segment_key: SegmentKey = ((0.0, 0.0), (3.0, 3.0))
        event = _make_event(segment_key, tick_start=0, duration=50, weight=0.3)

        road_a = _make_road(1, [p0, p1])
        road_b = _make_road(2, [p1, p2])
        road_c = _make_road(3, [p2, p3])

        registry.register_road(road_a, [p0, p1])
        registry.register_road(road_b, [p1, p2])
        registry.register_road(road_c, [p2, p3])

        tc = TrafficController(
            rc, env=env, routing_provider=provider, registry=registry
        )
        tc._traffic_events = [event]
        env.process(tc._run_traffic_events())

        # Run to APPLIED
        gps_sync_delay = provider.get_gps_sync_delay()
        env.run(until=gps_sync_delay + 5)
        assert TrafficEventState(event.state) == TrafficEventState.APPLIED
        assert len(event.affected_roads) == 3

        # Deallocate 2 of 3 roads
        _simulate_road_deallocation(rc, road_a)
        registry.unregister_road(road_a)
        _simulate_road_deallocation(rc, road_b)
        registry.unregister_road(road_b)

        assert len(event.affected_roads) == 1
        assert road_c in event.affected_roads

        # Still allocated (road_c shares p2, p3 with event)
        assert registry.is_event_allocated(event)

        # Run past expiry — allocated path (provider -> delay -> sim cleanup)
        env.run(until=50 + gps_sync_delay * 2 + 10)
        assert TrafficEventState(event.state) == TrafficEventState.DONE

        # affected_roads should be cleaned up by _reset_traffic_in_simulation
        assert len(event.affected_roads) == 0

        # road_c should have its traffic removed
        assert road_c.traffic_multiplier == 1.0

    def test_unallocated_to_allocated_to_unallocated_full_cycle(self) -> None:
        """Event starts unallocated, road arrives, road leaves, expires unallocated.

        Full cycle: unallocated at trigger -> road created (allocated) ->
        road deallocated (unallocated again) -> expires via unallocated path.
        """
        env = simpy.Environment()
        rc = _create_mock_route_controller()
        registry = PositionRegistry()

        p0 = Position([0.0, 0.0])
        p1 = Position([1.0, 1.0])
        p2 = Position([2.0, 2.0])

        event_positions = [p0, p1, p2]
        route_result = _build_route_result(event_positions)
        provider = MockRoutingProvider(route_result)

        segment_key: SegmentKey = ((0.0, 0.0), (2.0, 2.0))
        event = _make_event(segment_key, tick_start=0, duration=200, weight=0.5)

        # No roads initially — event starts unallocated

        tc = TrafficController(
            rc, env=env, routing_provider=provider, registry=registry
        )
        tc._traffic_events = [event]
        env.process(tc._run_traffic_events())

        # Run to APPLIED (unallocated — no GPS delay for trigger)
        env.run(until=5)
        assert TrafficEventState(event.state) == TrafficEventState.APPLIED
        assert len(event.affected_roads) == 0
        # Provider was updated via unallocated trigger path
        assert len(provider.set_edge_traffic_calls) == 1

        # Road arrives mid-lifecycle (Unallocated -> Allocated)
        road = _make_road(1, [p0, p1, p2])
        registry.register_road(road, [p0, p1, p2])
        _simulate_road_creation(rc, road)

        assert road in event.affected_roads
        assert road.traffic_multiplier < 1.0  # traffic was applied

        # Road leaves (Allocated -> Unallocated)
        _simulate_road_deallocation(rc, road)
        registry.unregister_road(road)

        assert len(event.affected_roads) == 0
        assert not registry.is_event_allocated(event)

        # Event expires — unallocated path (provider only)
        gps_sync_delay = provider.get_gps_sync_delay()
        env.run(until=200 + gps_sync_delay + 5)
        assert TrafficEventState(event.state) == TrafficEventState.DONE
        assert len(provider.clear_edge_traffic_calls) == 1

    def test_road_traffic_state_cleaned_on_deallocation(self) -> None:
        """Verify that affected_roads tracking is consistent after deallocation.

        When a road is deallocated, it's discarded from event.affected_roads.
        If the event later expires, _reset_traffic_in_simulation only iterates
        over remaining affected_roads — the deallocated road is not touched.
        """
        env = simpy.Environment()
        rc = _create_mock_route_controller()
        registry = PositionRegistry()

        p0 = Position([0.0, 0.0])
        p1 = Position([1.0, 1.0])
        p2 = Position([2.0, 2.0])
        p3 = Position([3.0, 3.0])

        event_positions = [p0, p1, p2, p3]
        route_result = _build_route_result(event_positions)
        provider = MockRoutingProvider(route_result)

        segment_key: SegmentKey = ((0.0, 0.0), (3.0, 3.0))
        event = _make_event(segment_key, tick_start=0, duration=50, weight=0.3)

        road_a = _make_road(1, [p0, p1, p2])
        road_b = _make_road(2, [p2, p3])

        registry.register_road(road_a, [p0, p1, p2])
        registry.register_road(road_b, [p2, p3])

        tc = TrafficController(
            rc, env=env, routing_provider=provider, registry=registry
        )
        tc._traffic_events = [event]
        env.process(tc._run_traffic_events())

        # Run to APPLIED
        gps_sync_delay = provider.get_gps_sync_delay()
        env.run(until=gps_sync_delay + 5)
        assert TrafficEventState(event.state) == TrafficEventState.APPLIED
        assert road_a in event.affected_roads
        assert road_b in event.affected_roads

        # Road A still has traffic applied
        assert road_a.traffic_multiplier < 1.0

        # Deallocate road_a (simulating vehicle passing through)
        # Real flow: callbacks fire first, then registry.unregister_road()
        _simulate_road_deallocation(rc, road_a)
        registry.unregister_road(road_a)

        # road_a is removed from tracking but still holds its traffic_ranges
        # (deallocation callback doesn't call road.remove_traffic — the road
        # is going away entirely, so cleanup is just the affected_roads set)
        assert road_a not in event.affected_roads
        assert road_b in event.affected_roads

        # Run to expiry — road_b still there, so allocated path
        env.run(until=50 + gps_sync_delay * 2 + 10)
        assert TrafficEventState(event.state) == TrafficEventState.DONE

        # road_b was cleaned up via _reset_traffic_in_simulation
        assert road_b.traffic_multiplier == 1.0
        assert len(event.affected_roads) == 0


# ---------------------------------------------------------------------------
# Test: Routing Provider Graceful No-Op
# ---------------------------------------------------------------------------


class TestRoutingProviderGracefulNoOp:
    """Tests that NotImplementedError from routing provider is handled gracefully."""

    def test_not_implemented_error_handled(self) -> None:
        """TC handles routing provider that doesn't support traffic updates."""
        env = simpy.Environment()
        rc = _create_mock_route_controller()
        registry = PositionRegistry()

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

        tc = TrafficController(
            rc, env=env, routing_provider=provider, registry=registry
        )
        tc._traffic_events = [event]
        env.process(tc._run_traffic_events())

        # Should not raise — completes full lifecycle
        gps_sync_delay = provider.get_gps_sync_delay()

        env.run(until=20 + gps_sync_delay + 10)
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
        registry = PositionRegistry()

        positions = [Position([0.0, 0.0]), Position([1.0, 1.0])]
        route_result = _build_route_result(positions)
        provider = MockRoutingProvider(route_result)

        event_a = _make_event(
            ((0.0, 0.0), (1.0, 1.0)), tick_start=5, duration=50, name="Event A"
        )
        event_b = _make_event(
            ((2.0, 2.0), (3.0, 3.0)), tick_start=5, duration=50, name="Event B"
        )

        tc = TrafficController(
            rc, env=env, routing_provider=provider, registry=registry
        )
        tc._traffic_events = [event_a, event_b]
        env.process(tc._run_traffic_events())

        # Run until both are in APPLIED state
        gps_sync_delay = provider.get_gps_sync_delay()
        env.run(until=5 + gps_sync_delay + 5)

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
        registry = PositionRegistry()

        segment_key: SegmentKey = ((0.0, 0.0), (1.0, 1.0))
        event = _make_event(segment_key, tick_start=0, duration=20)

        tc = TrafficController(rc, env=env, routing_provider=None, registry=registry)
        tc._traffic_events = [event]
        env.process(tc._run_traffic_events())

        env.run(until=20 + 10 + 10)

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
        registry = PositionRegistry()

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

        tc = TrafficController(
            rc, env=env, routing_provider=provider, registry=registry
        )
        tc._traffic_events = [event_first, event_second]
        env.process(tc._run_traffic_events())

        # Run until first event is DONE
        env.run(until=10 + 10 + 5)

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
        registry = PositionRegistry()

        positions = [Position([0.0, 0.0]), Position([1.0, 1.0])]
        route_result = _build_route_result(positions)
        provider = MockRoutingProvider(route_result)

        segment_key: SegmentKey = ((0.0, 0.0), (1.0, 1.0))
        event = _make_event(segment_key, tick_start=0, duration=10)

        tc = TrafficController(
            rc, env=env, routing_provider=provider, registry=registry
        )
        tc._traffic_events = [event]
        env.process(tc._run_traffic_events())

        # Run past full lifecycle
        env.run(until=10 + 10 + 10)

        assert event.state == TrafficEventState.DONE
        assert event not in tc._traffic_events
