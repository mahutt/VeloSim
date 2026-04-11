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

from grafana_logging.logger import get_logger
from typing import Dict, Generator, List, Optional, Set, TYPE_CHECKING

import simpy

from sim.entities.map_payload import TrafficConfig
from sim.entities.position import Position
from sim.entities.road import Road
from sim.entities.traffic_data import RoadTrafficState, TrafficData
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

if TYPE_CHECKING:
    from sim.map.position_registry import PositionRegistry

logger = get_logger(__name__)


class TrafficController:
    """Manages traffic event lifecycle and road traffic state.

    Implements the traffic event state machine:
    PENDING -> TRIGGERED -> APPLIED -> EXPIRED -> DONE

    Uses a PositionRegistry for bidirectional geometry-based matching between
    roads and traffic events, and SimPy processes for tick-based scheduling.
    """

    def __init__(
        self,
        route_controller: RouteController,
        registry: "PositionRegistry",
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
            registry: PositionRegistry for bidirectional geometry
                matching between roads and traffic events.
        """
        self._route_controller = route_controller
        self._env = env
        self._routing_provider = routing_provider
        self._registry = registry
        self.traffic_config = traffic_config

        self._active_traffic: Dict[SegmentKey, RoadTrafficState] = {}
        self._active_zero_weight_segments: Dict[SegmentKey, List[Position]] = {}
        self._traffic_events: List[TrafficEvent] = []

        # Sync resource serializes event processing through synchronization
        # ("WaitUntilServed" from state machine diagram)
        self._sync_resource: Optional[simpy.Resource] = None
        if env:
            self._sync_resource = simpy.Resource(env, capacity=1)

        # Register for road lifecycle events
        self._route_controller.register_on_road_created(self._on_road_created)
        self._route_controller.register_on_road_deallocated(self._on_road_deallocated)

        # Parse traffic events if config provided
        if traffic_config and traffic_config.traffic_level:
            parser = TrafficParser(traffic_config)
            self._traffic_events = parser.parse()
            logger.info(f"Loaded {len(self._traffic_events)} traffic event(s)")
            for i, event in enumerate(self._traffic_events):
                logger.debug(f"  [{i}] {event}")

        # Start SimPy traffic event processing if env is available
        if self._env and self._traffic_events:
            self._env.process(self._run_traffic_events())

        # Start SimPy processes for global multipliers if available
        if self._env and traffic_config and traffic_config.global_schedule:
            self._env.process(self._setup_global_traffic_schedules())

        self._current_global_multiplier = 1.0
        if traffic_config:
            self.gps_sync_delay = traffic_config.gps_sync_delay
        else:
            self.gps_sync_delay = 10

    # =========================================================================
    # Road Lifecycle Callbacks
    # =========================================================================

    def _on_road_created(self, road: Road) -> None:
        """Handle new road creation.

        If registry exists, checks for active traffic events that intersect
        the new road and applies their traffic. Otherwise uses legacy path.
        Sets current global multiplier to it if any.

        Args:
            road: The newly created road.
        """
        self.sync_road_state(road)

    def sync_road_state(self, road: Road) -> None:
        """Updates a road's state to match current conditions.

        Args:
            road: The road to update

        Returns:
            None
        """
        # Apply current global multiplier to road
        if self._current_global_multiplier != 1.0:
            road.set_global_traffic_multiplier(self._current_global_multiplier)

        self._handle_road_created_for_active_events(road)

        # To ensure the global multiplier on the road is affecting routes
        if road.traffic_multiplier != 1.0:
            self._notify_routes_for_road(road)

    def _handle_road_created_for_active_events(self, road: Road) -> None:
        """Apply traffic from any active events that intersect this new road.

        Handles the [Unallocated -> Allocated] transition from "Listening for
        Change" state in the state machine.

        Args:
            road: The newly created road.
        """
        events = self._registry.find_events_for_road(road)
        for event in events:
            if event.state in (
                TrafficEventState.APPLIED,
                TrafficEventState.TRIGGERED,
            ):
                overlap = self._registry.get_overlap_positions(road, event)
                if overlap:
                    if event.weight == 0.0:
                        # Zero-weight events are already occupancy-tracked
                        # for their full geometry; road registration will
                        # inherit occupied flags from the registry.
                        pass
                    else:
                        road.apply_traffic_for_overlap(
                            list(overlap), event.weight, event.segment_key
                        )
                        strategy = TrafficStateFactory.get_strategy(event.event_type)
                        road.set_point_strategy(strategy)
                    event.affected_roads.add(road)
                    self._notify_routes_for_road(road)
                    logger.debug(f"Applied event '{event.name}' to new road {road.id}")

    def _on_road_deallocated(self, road: Road) -> None:
        """Handle road deallocation.

        If registry exists, removes road from active events' affected_roads.
        Handles [Allocated -> Unallocated] transition (clearOrphans).

        Args:
            road: The road being deallocated.
        """
        events = self._registry.find_events_for_road(road)
        for event in events:
            event.affected_roads.discard(road)

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

        Follows the state machine from the wiki:
        https://github.com/vinishamanek/VeloSim/wiki/Overall-Architecture-and-Class-Diagrams#traffic-state-machine
        PENDING -> TRIGGERED -> (sync apply) -> APPLIED -> (wait) ->
        EXPIRED -> (sync remove) -> DONE
        """
        assert self._env is not None
        assert self._sync_resource is not None
        # -- PENDING: WaitUntilTriggered --
        if self._env.now < event.tick_start:
            yield self._env.timeout(event.tick_start - self._env.now)

        # -- TRIGGERED: resolve geometry, register in registry --
        event.state = TrafficEventState.TRIGGERED
        logger.info(f"Event '{event.name}' TRIGGERED at tick {int(self._env.now)}")

        event.route_geometry = self._resolve_event_geometry(event)
        if event.route_geometry:
            self._registry.register_event(event, event.route_geometry)
            logger.info(
                f"Event '{event.name}': resolved {len(event.route_geometry)} "
                f"geometry positions"
            )
        else:
            logger.warning(
                f"Event '{event.name}': geometry resolution failed — "
                f"event will not match any roads"
            )

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

        # Save affected roads before sync clears them — needed to notify
        # routes after the GPS delay so the overlay persists until DONE
        roads_to_notify = set(event.affected_roads)

        # -- WaitUntilServed again for removal --
        with self._sync_resource.request() as req:
            yield req
            # -- SYNCHRONIZATION (remove) --
            yield from self._synchronize(event, is_apply=False)

        # -- DONE: checkForSimilarEvent, deleteEvent --
        event.state = TrafficEventState.DONE
        logger.info(f"Event '{event.name}' DONE at tick {int(self._env.now)}")

        # Now clear the traffic overlay — after GPS delay has passed
        for road in roads_to_notify:
            self._notify_routes_for_road(road)

        self._check_for_similar_event(event)
        self._delete_event(event)

    def _setup_global_traffic_schedules(self) -> Generator[simpy.Event, None, None]:
        """Spawns processes for every entry in the global multiplier list."""
        assert self._env is not None
        if self.traffic_config and self.traffic_config.global_schedule:
            for event in self.traffic_config.global_schedule:
                start_tick = event["start_time"]
                end_tick = event["end_time"]
                multiplier = event["multiplier"]

                # Schedule start of the global multiplier event
                self._env.process(self._apply_global_multiplier(start_tick, multiplier))

                # Schedule reset to 1.0 (free flow) before the end_tick to ensure no
                # overlap with a new event starting at end_tick
                reset_tick = max(start_tick, end_tick - 1)
                self._env.process(self._apply_global_multiplier(reset_tick, 1.0))

            yield self._env.timeout(0)

    def _apply_global_multiplier(
        self, tick: int, multiplier: float
    ) -> Generator[simpy.Event, None, None]:
        """
        Applies global multiplier to all roads at scheduled tick and
        notifies all routes.
        """
        assert self._env is not None
        delay = max(0, tick - self._env.now)
        yield self._env.timeout(delay)

        # Store the new multiplier for future roads
        self._current_global_multiplier = multiplier
        logger.info(
            f"Global traffic multiplier updated to {multiplier} at "
            f"tick {int(self._env.now)}"
        )

        # Notify all active roads to recalculate routes
        for road in self._route_controller.get_all_active_roads():
            road.set_global_traffic_multiplier(multiplier)
            self._notify_routes_for_road(road)

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
        logger.info(
            f"Event '{event.name}': allocation check = {is_allocated} "
            f"(apply={is_apply})"
        )

        if is_apply:
            if event.weight == 0.0:
                self._set_traffic_in_simulation(event)
            if is_allocated:
                # [Triggered && Allocated]: Sim -> Delay -> RoutingProvider
                # Traffic affects the road immediately (car slows down),
                # but route notification is delayed until after GPS_SYNC_DELAY
                # so the driver visually slows before traffic colors appear.
                # This mirrors the removal path (overlay persists through delay).
                if event.weight != 0.0:
                    self._set_traffic_in_simulation(event)
                yield self._env.timeout(self.gps_sync_delay)
                self._set_traffic_in_routing_provider(event)
                for road in event.affected_roads:
                    self._notify_routes_for_road(road)
            else:
                # [Triggered && Unallocated]: RoutingProvider only
                logger.warning(
                    f"Event '{event.name}': no roads overlap event geometry — "
                    f"traffic will only affect routing provider, not simulation"
                )
                self._set_traffic_in_routing_provider(event)
        else:
            if event.weight == 0.0:
                self._reset_traffic_in_simulation(event)
            if is_allocated:
                # [Expired && Allocated]: Sim -> Delay -> RoutingProvider
                if event.weight != 0.0:
                    self._reset_traffic_in_simulation(event)
                yield self._env.timeout(self.gps_sync_delay)
                self._reset_traffic_in_routing_provider(event)
            else:
                # [Expired && Unallocated]: RoutingProvider only
                self._reset_traffic_in_routing_provider(event)

    # =========================================================================
    # Synchronization Helpers
    # =========================================================================

    def _check_allocation(self, event: TrafficEvent) -> bool:
        """Check if any roads intersect the event's geometry."""
        return self._registry.is_event_allocated(event)

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
        """Apply traffic to simulation roads.

        For each road intersecting the event, computes overlap positions and
        calls road.apply_traffic_for_overlap(). Also injects the appropriate
        point generation strategy from the factory.

        Args:
            event: The traffic event to apply.
        """
        if event.weight == 0.0:
            occupied_positions = event.route_geometry or []
            self._registry.occupy_positions(occupied_positions)
            self._active_zero_weight_segments[event.segment_key] = list(
                occupied_positions
            )
            logger.debug(
                f"Event '{event.name}': marked {len(occupied_positions)} "
                f"occupied position(s)"
            )
            return

        strategy = TrafficStateFactory.get_strategy(event.event_type)

        affected_roads = self._registry.find_roads_for_event(event)
        for road in affected_roads:
            overlap = self._registry.get_overlap_positions(road, event)
            if overlap:
                if road.apply_traffic_for_overlap(
                    list(overlap), event.weight, event.segment_key
                ):
                    road.set_point_strategy(strategy)
                    event.affected_roads.add(road)

        # Store in _active_traffic so future roads also get this traffic
        clamped = max(0.0, event.weight)
        state = TrafficStateFactory.create(
            multiplier=clamped,
            traffic_points=[],
            source=event.name,
            tick=int(self._env.now) if self._env else 0,
        )
        self._active_traffic[event.segment_key] = state

        logger.debug(
            f"Event '{event.name}': applied to {len(affected_roads)} road(s) "
            f"in simulation"
        )

    def _set_traffic_in_routing_provider(self, event: TrafficEvent) -> None:
        """Set speed penalty in the routing provider."""
        self._update_routing_provider(event, apply=True)

    def _reset_traffic_in_simulation(self, event: TrafficEvent) -> None:
        """Remove traffic from simulation roads and clean up.

        Does NOT notify routes here — the traffic overlay should persist
        through the GPS_SYNC_DELAY to model the real-world lag between
        actual road conditions and GPS/map data. Routes are notified
        later when the event reaches DONE state.
        """
        if event.weight == 0.0:
            occupied_positions = self._active_zero_weight_segments.pop(
                event.segment_key, []
            )
            self._registry.release_positions(occupied_positions)
        else:
            for road in event.affected_roads:
                road.remove_traffic(event.segment_key)
                if not road._traffic_ranges:
                    road.set_point_strategy(None)

        self._active_traffic.pop(event.segment_key, None)
        event.affected_roads.clear()

        self._registry.unregister_event(event)

        logger.debug(f"Event '{event.name}': removed from simulation roads")

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
        traffic_data = TrafficData(
            segment_key=event.segment_key,
            speed_factor=event.weight,
            source_event=event.name,
        )

        start_pos = Position([start_coords[0], start_coords[1]])
        end_pos = Position([end_coords[0], end_coords[1]])
        edge = EdgeIdentifier(start_position=start_pos, end_position=end_pos)

        try:
            if apply:
                update = TrafficUpdate(
                    edge=edge, speed_factor=traffic_data.speed_factor
                )
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

    def _notify_routes_for_road(self, road: Road) -> None:
        """Notify all routes using this road to rebuild their traffic triples."""
        for route in self._route_controller.get_routes_for_road(road):
            route.notify_traffic_changed()

    # =========================================================================
    # Legacy / Manual Traffic API (backward compatible)
    # =========================================================================

    def _find_affected_roads(self, segment_key: SegmentKey) -> Set[Road]:
        """Find all roads that contain nodes from the segment_key.

        Uses PositionRegistry for O(1) position-based lookup.

        Args:
            segment_key: ((start_lon, start_lat), (end_lon, end_lat))

        Returns:
            Set of roads containing at least one of the segment's positions.
        """
        start_coords, end_coords = segment_key
        start_pos = Position([start_coords[0], start_coords[1]])
        end_pos = Position([end_coords[0], end_coords[1]])

        affected: Set[Road] = set()
        affected |= self._registry.find_roads_at_position(start_pos)
        affected |= self._registry.find_roads_at_position(end_pos)
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
            multiplier: Speed factor (0.0-1.0), 1.0 = free flow.
            source: Optional source identifier for tracking.

        Returns:
            True if traffic was applied to at least one active road.
        """
        clamped = max(0.0, min(1.0, multiplier))

        state = TrafficStateFactory.create(
            multiplier=clamped,
            traffic_points=[],
            source=source,
        )

        # Always store traffic state (for current and future roads)
        self._active_traffic[segment_key] = state

        # Find affected roads via registry
        affected_roads = self._find_affected_roads(segment_key)

        # Compute overlap positions and apply traffic to each affected road
        start_coords, end_coords = segment_key
        start_pos = Position([start_coords[0], start_coords[1]])
        end_pos = Position([end_coords[0], end_coords[1]])
        segment_positions = {start_pos, end_pos}

        for road in affected_roads:
            road_geom_set = set(road.geometry) if road.geometry else set()
            overlap = list(segment_positions & road_geom_set)
            if overlap:
                if road.apply_traffic_for_overlap(overlap, clamped, segment_key):
                    self._notify_routes_for_road(road)

        return bool(affected_roads)

    def clear_traffic(self, segment_key: SegmentKey) -> bool:
        """Clear traffic state for a road segment.

        Args:
            segment_key: Geometry-based segment identifier.

        Returns:
            True if traffic was cleared from at least one road.
        """
        affected_roads = self._find_affected_roads(segment_key)

        updated: Set[Road] = set()
        for road in affected_roads:
            if road.remove_traffic(segment_key):
                updated.add(road)
                self._notify_routes_for_road(road)

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

    def get_zero_weight_event_linestrings(self) -> List[List[List[float]]]:
        """Return route geometries for active zero-weight events.

        Returns:
            A list of linestring coordinate lists. Each linestring is a list
            of [longitude, latitude] pairs.
        """
        linestrings: List[List[List[float]]] = []
        for geometry in self._active_zero_weight_segments.values():
            if geometry:
                linestrings.append([pos.get_position() for pos in geometry])
        return linestrings

    def cleanup(self) -> None:
        """Clean up TrafficController resources.

        Unregisters callbacks to prevent memory leaks.

        Returns:
            None.
        """
        self._route_controller.unregister_on_road_created(self._on_road_created)
        self._route_controller.unregister_on_road_deallocated(self._on_road_deallocated)
        for geometry in self._active_zero_weight_segments.values():
            self._registry.release_positions(geometry)
        self._active_zero_weight_segments.clear()
        self._active_traffic.clear()
