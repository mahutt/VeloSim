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

import logging
from typing import Dict, Generator, List, Optional, Set

import simpy

from sim.entities.map_payload import TrafficConfig
from sim.entities.position import Position
from sim.entities.road import Road
from sim.entities.traffic_data import RoadTrafficState
from sim.entities.traffic_event import TrafficEvent
from sim.entities.traffic_event_state import TrafficEventState
from sim.map.route_controller import RouteController
from sim.map.routing_provider import (
    EdgeIdentifier,
    RoutingProvider,
    SegmentKey,
    TrafficUpdate,
)
from sim.traffic.traffic_parser import TrafficParser
from sim.traffic.traffic_state_factory import TrafficStateFactory

logger = logging.getLogger(__name__)

# Hardcoded GPS sync delay in ticks between sim and routing provider updates
GPS_SYNC_DELAY = 10


class TrafficController:
    """Manages traffic event lifecycle and road traffic state.

    Implements the traffic event state machine:
    PENDING -> TRIGGERED -> APPLIED -> EXPIRED -> DONE

    Uses SimPy processes for tick-based scheduling. Road-level traffic
    application (via PositionRegistry) is added by the traffic mapper layer.
    """

    def __init__(
        self,
        route_controller: RouteController,
        traffic_config: Optional[TrafficConfig] = None,
        env: Optional[simpy.Environment] = None,
        routing_provider: Optional[RoutingProvider] = None,
    ) -> None:
        """Initialize TrafficController.

        Args:
            route_controller: RouteController for road lookups.
            traffic_config: Optional TrafficConfig with traffic settings.
            env: Optional SimPy environment for tick-based scheduling.
            routing_provider: Optional RoutingProvider for geometry resolution
                and traffic weight updates.
        """
        self._route_controller = route_controller
        self._env = env
        self._routing_provider = routing_provider

        self._active_traffic: Dict[SegmentKey, RoadTrafficState] = {}
        self._traffic_events: List[TrafficEvent] = []

        # Reverse index: Position -> set of roads containing that node
        self._node_to_roads: Dict[Position, Set[Road]] = {}

        # Sync resource serializes event processing through synchronization
        # ("WaitUntilServed" from state machine diagram)
        self._sync_resource: Optional[simpy.Resource] = None
        if env:
            self._sync_resource = simpy.Resource(env, capacity=1)

        # Register for road lifecycle events
        self._route_controller.register_on_road_created(self._on_road_created)
        self._route_controller.register_on_road_deallocated(self._on_road_deallocated)

        # Parse traffic events from CSV if config provided
        if traffic_config and traffic_config.traffic_path:
            parser = TrafficParser(traffic_config.traffic_path)
            self._traffic_events = parser.parse()
            logger.info(f"Loaded {len(self._traffic_events)} traffic event(s)")
            for i, event in enumerate(self._traffic_events):
                logger.debug(f"  [{i}] {event}")

        # Start SimPy traffic event processing if env is available
        if self._env and self._traffic_events:
            self._env.process(self._run_traffic_events())

    # =========================================================================
    # Road Lifecycle Callbacks
    # =========================================================================

    def _on_road_created(self, road: Road) -> None:
        """Handle new road creation.

        Registers the road's nodes in the reverse index and applies any
        existing active traffic to the new road.

        Args:
            road: The newly created road.
        """
        # Register nodes in reverse index
        for node in road.nodes:
            if node not in self._node_to_roads:
                self._node_to_roads[node] = set()
            self._node_to_roads[node].add(road)

        # Apply any existing active traffic to this new road
        self._apply_existing_traffic_to_road(road)

    def _apply_existing_traffic_to_road(self, road: Road) -> None:
        """Apply all existing active traffic states to a road if applicable.

        Args:
            road: The road to apply traffic to.
        """
        for segment_key, state in self._active_traffic.items():
            road.add_traffic_range(segment_key, state.multiplier)

    def _on_road_deallocated(self, road: Road) -> None:
        """Handle road deallocation.

        Removes the road from the node index and cleans up traffic state.

        Args:
            road: The road being deallocated.
        """
        # Remove from node index
        for node in road.nodes:
            if node in self._node_to_roads:
                self._node_to_roads[node].discard(road)
                if not self._node_to_roads[node]:
                    del self._node_to_roads[node]

        # Clean up traffic state
        self._active_traffic.pop(road.segment_key, None)

    # =========================================================================
    # SimPy Event Scheduling
    # =========================================================================

    def _run_traffic_events(self) -> Generator[simpy.Event, None, None]:
        """Main SimPy generator: spawns a process per traffic event."""
        assert self._env is not None
        sorted_events = sorted(self._traffic_events, key=lambda e: e.tick_start)
        for event in sorted_events:
            self._env.process(self._process_event(event))
        yield self._env.timeout(0)

    def _process_event(self, event: TrafficEvent) -> Generator[simpy.Event, None, None]:
        """SimPy generator: full lifecycle for one traffic event.

        Follows the state machine:
        PENDING -> TRIGGERED -> (sync apply) -> APPLIED -> (wait) ->
        EXPIRED -> (sync remove) -> DONE
        """
        assert self._env is not None
        assert self._sync_resource is not None
        # -- PENDING: WaitUntilTriggered --
        if self._env.now < event.tick_start:
            yield self._env.timeout(event.tick_start - self._env.now)

        # -- TRIGGERED: resolve geometry --
        event.state = TrafficEventState.TRIGGERED
        logger.info(f"Event '{event.name}' TRIGGERED at tick {int(self._env.now)}")

        event.route_geometry = self._resolve_event_geometry(event)

        # -- TRIGGERED: WaitUntilServed (acquire sync resource) --
        with self._sync_resource.request() as req:
            yield req
            # -- SYNCHRONIZATION (apply) --
            yield from self._synchronize(event, is_apply=True)

        # -- ACTIVE: Listening for Change --
        event.state = TrafficEventState.APPLIED
        logger.info(f"Event '{event.name}' APPLIED at tick {int(self._env.now)}")

        # Road lifecycle changes handled via callbacks
        expiry_tick = event.tick_start + event.duration
        remaining = max(0, expiry_tick - self._env.now)
        if remaining > 0:
            yield self._env.timeout(remaining)

        # -- EXPIRED --
        event.state = TrafficEventState.EXPIRED
        logger.info(f"Event '{event.name}' EXPIRED at tick {int(self._env.now)}")

        # -- WaitUntilServed again for removal --
        with self._sync_resource.request() as req:
            yield req
            # -- SYNCHRONIZATION (remove) --
            yield from self._synchronize(event, is_apply=False)

        # -- DONE: checkForSimilarEvent, deleteEvent --
        event.state = TrafficEventState.DONE
        logger.info(f"Event '{event.name}' DONE at tick {int(self._env.now)}")
        self._check_for_similar_event(event)
        self._delete_event(event)

    # =========================================================================
    # Synchronization Subprocess
    # =========================================================================

    def _synchronize(
        self, event: TrafficEvent, is_apply: bool
    ) -> Generator[simpy.Event, None, None]:
        """Synchronization subprocess from the state machine diagram.

        Has 4 paths based on (Triggered/Expired) x (Allocated/Unallocated):
        - Triggered && Allocated: Sim -> Delay -> RoutingProvider
        - Triggered && Unallocated: RoutingProvider only
        - Expired && Allocated: Sim -> Delay -> RoutingProvider
        - Expired && Unallocated: RoutingProvider only

        Args:
            event: The traffic event being synchronized.
            is_apply: True for apply (Triggered), False for remove (Expired).
        """
        assert self._env is not None
        is_allocated = self._check_allocation(event)

        if is_apply:
            if is_allocated:
                # [Triggered && Allocated]: Sim -> Delay -> RoutingProvider
                self._set_traffic_in_simulation(event)
                yield self._env.timeout(GPS_SYNC_DELAY)
                self._set_traffic_in_routing_provider(event)
            else:
                # [Triggered && Unallocated]: RoutingProvider only
                self._set_traffic_in_routing_provider(event)
        else:
            if is_allocated:
                # [Expired && Allocated]: Sim -> Delay -> RoutingProvider
                self._reset_traffic_in_simulation(event)
                yield self._env.timeout(GPS_SYNC_DELAY)
                self._reset_traffic_in_routing_provider(event)
            else:
                # [Expired && Unallocated]: RoutingProvider only
                self._reset_traffic_in_routing_provider(event)

    # =========================================================================
    # Synchronization Helpers
    # =========================================================================

    def _check_allocation(self, event: TrafficEvent) -> bool:
        """Check if any roads intersect the event's geometry.

        Without a PositionRegistry, no road-level intersection is possible,
        so this always returns False. The traffic mapper layer upgrades this.
        """
        return False

    def _resolve_event_geometry(self, event: TrafficEvent) -> Optional[List[Position]]:
        """Resolve the full route geometry for a traffic event's segment_key.

        Calls the routing provider with the segment_key endpoints to get the
        actual road geometry between those points.

        Args:
            event: The traffic event to resolve geometry for.

        Returns:
            List of Position objects from the route, or fallback to endpoints.
        """
        if not self._routing_provider:
            return None

        start_coords, end_coords = event.segment_key
        start_pos = Position([start_coords[0], start_coords[1]])
        end_pos = Position([end_coords[0], end_coords[1]])

        try:
            route_result = self._routing_provider.get_route(start_pos, end_pos)
            if route_result and route_result.steps:
                # Collect all geometry positions from steps
                all_positions: List[Position] = []
                for step in route_result.steps:
                    if step.geometry:
                        all_positions.extend(step.geometry)
                if all_positions:
                    return all_positions
            if route_result and route_result.coordinates:
                return route_result.coordinates
        except Exception as e:
            logger.warning(f"Failed to resolve geometry for event '{event.name}': {e}")

        # Fallback: use just the endpoints
        return [start_pos, end_pos]

    def _set_traffic_in_simulation(self, event: TrafficEvent) -> None:
        """Store traffic in the active_traffic dict.

        Without a PositionRegistry, road-level application is not possible.
        This stores the traffic state so the routing provider path and any
        future road creation callbacks can pick it up.

        Args:
            event: The traffic event to apply.
        """
        clamped = max(0.01, event.weight)
        state = TrafficStateFactory.create(
            multiplier=clamped,
            traffic_points=[],
            source=event.name,
            tick=int(self._env.now) if self._env else 0,
        )
        self._active_traffic[event.segment_key] = state

        logger.debug(f"Event '{event.name}': stored in active_traffic dict")

    def _set_traffic_in_routing_provider(self, event: TrafficEvent) -> None:
        """Set speed penalty in the routing provider."""
        self._update_routing_provider(event, apply=True)

    def _reset_traffic_in_simulation(self, event: TrafficEvent) -> None:
        """Remove traffic from the active_traffic dict."""
        self._active_traffic.pop(event.segment_key, None)
        event.affected_roads.clear()

        logger.debug(f"Event '{event.name}': removed from active_traffic dict")

    def _reset_traffic_in_routing_provider(self, event: TrafficEvent) -> None:
        """Reset speed penalty in the routing provider."""
        self._update_routing_provider(event, apply=False)

    def _update_routing_provider(self, event: TrafficEvent, apply: bool) -> None:
        """Update routing provider traffic state. Handles NotImplementedError.

        Corresponds to the "Setting SegmentKey Routing Provider" (apply=True)
        and "Resetting SegmentKey in Routing Provider" (apply=False) states
        in the state machine diagram.

        Args:
            event: The traffic event to apply or remove.
            apply: True to set the speed factor on the edge, False to clear it.
        """
        if not self._routing_provider:
            return

        start_coords, end_coords = event.segment_key
        start_pos = Position([start_coords[0], start_coords[1]])
        end_pos = Position([end_coords[0], end_coords[1]])
        edge = EdgeIdentifier(start_position=start_pos, end_position=end_pos)

        try:
            if apply:
                update = TrafficUpdate(edge=edge, speed_factor=event.weight)
                self._routing_provider.set_edge_traffic(update)
            else:
                self._routing_provider.clear_edge_traffic(edge)
        except NotImplementedError:
            logger.debug(
                f"Routing provider does not support traffic updates "
                f"(event '{event.name}', apply={apply})"
            )

    def _check_for_similar_event(self, event: TrafficEvent) -> None:
        """Check if any other PENDING events share the same segment_key."""
        similar = [
            e
            for e in self._traffic_events
            if e is not event
            and e.segment_key == event.segment_key
            and e.state == TrafficEventState.PENDING
        ]
        if similar:
            logger.info(
                f"Event '{event.name}': {len(similar)} similar PENDING "
                f"event(s) on same segment_key"
            )

    def _delete_event(self, event: TrafficEvent) -> None:
        """Remove a completed event from the internal list to free memory."""
        try:
            self._traffic_events.remove(event)
        except ValueError:
            pass

    # =========================================================================
    # Legacy / Manual Traffic API (backward compatible)
    # =========================================================================

    def _find_affected_roads(self, segment_key: SegmentKey) -> Set[Road]:
        """Find all roads that contain nodes from the segment_key.

        Args:
            segment_key: ((start_lon, start_lat), (end_lon, end_lat))

        Returns:
            Set of roads containing at least one of the segment's nodes.
        """
        start_coords, end_coords = segment_key

        # Convert tuple coordinates to Position for lookup
        start_pos = Position([start_coords[0], start_coords[1]])
        end_pos = Position([end_coords[0], end_coords[1]])

        affected: Set[Road] = set()
        if start_pos in self._node_to_roads:
            affected |= self._node_to_roads[start_pos]
        if end_pos in self._node_to_roads:
            affected |= self._node_to_roads[end_pos]

        return affected

    def set_traffic(
        self,
        segment_key: SegmentKey,
        multiplier: float,
        source: Optional[str] = None,
    ) -> bool:
        """Set traffic state for a road segment.

        Uses reverse index to find affected roads and applies traffic ranges.
        Traffic state is always stored so it can be applied to roads created
        later.

        Args:
            segment_key: Geometry-based segment identifier.
            multiplier: Speed factor (0.01-1.0), 1.0 = free flow.
            source: Optional source identifier for tracking.

        Returns:
            True if traffic was applied to at least one active road, False if
            traffic was only stored in memory (no active roads affected).
        """
        clamped = max(0.01, min(1.0, multiplier))

        state = TrafficStateFactory.create(
            multiplier=clamped,
            traffic_points=[],
            source=source,
        )

        # Always store traffic state (for current and future roads)
        self._active_traffic[segment_key] = state

        # Find affected roads via reverse index
        affected_roads = self._find_affected_roads(segment_key)

        # Apply traffic to each affected road
        for road in affected_roads:
            road.add_traffic_range(segment_key, clamped)

        return bool(affected_roads)

    def clear_traffic(self, segment_key: SegmentKey) -> bool:
        """Clear traffic state for a road segment.

        Args:
            segment_key: Geometry-based segment identifier.

        Returns:
            True if traffic was cleared from at least one road, False if no
            roads were affected (traffic state is still removed from internal
            tracking).
        """
        affected_roads = self._find_affected_roads(segment_key)

        updated: Set[Road] = set()
        for road in affected_roads:
            if road.remove_traffic(segment_key):
                updated.add(road)

        self._active_traffic.pop(segment_key, None)
        return bool(updated)

    def clear_all_traffic(self) -> None:
        """Clear traffic state from all active roads.

        Returns:
            None.
        """
        for road in self._route_controller.get_all_active_roads():
            road.clear_traffic()
        self._active_traffic.clear()

    def get_traffic_state(self, segment_key: SegmentKey) -> Optional[RoadTrafficState]:
        """Get traffic state for a segment.

        Args:
            segment_key: Geometry-based segment identifier.

        Returns:
            RoadTrafficState if found, None otherwise.
        """
        return self._active_traffic.get(segment_key)

    def get_traffic_events(self) -> List[TrafficEvent]:
        """Get the list of parsed traffic events.

        Returns:
            List of TrafficEvent objects parsed from the traffic CSV.
        """
        return self._traffic_events

    def cleanup(self) -> None:
        """Clean up TrafficController resources.

        Unregisters callbacks to prevent memory leaks.

        Returns:
            None.
        """
        self._route_controller.unregister_on_road_created(self._on_road_created)
        self._route_controller.unregister_on_road_deallocated(self._on_road_deallocated)
        self._active_traffic.clear()
        self._node_to_roads.clear()
