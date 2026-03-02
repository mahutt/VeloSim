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

"""
Dynamic Traffic Demo — VeloSim

Three-pass demo that validates the full traffic pipeline end-to-end:

  Pass 1 (Direct): Generates a route, picks a target road, and applies traffic
      directly via road.apply_traffic_for_overlap() — the existing behavior.

  Pass 2 (Pipeline): Writes a traffic CSV from discovered segment keys, creates
      a fresh MapController wired with that CSV + SimPy env, generates the same
      route, and steps SimPy tick-by-tick so the state machine processes the event
      through the full pipeline (TrafficParser → TrafficController → PositionRegistry
      → road.apply_traffic_for_overlap()).

  Pass 3 (Routing Provider): Verifies that the TrafficController's
      _update_routing_provider() call stores traffic state in the OSRMAdapter's
      TrafficStateStore (no longer raises NotImplementedError). Checks set, get,
      expiry cleanup, and close() cleanup.

  Outputs a traffic CSV + scenario JSON importable into the scenario editor, plus
  a GeoJSON preview for https://geojson.io.

Usage:
    python scripts/dynamic_traffic_demo.py [--multiplier 0.3] [--target 0.5]
    python scripts/dynamic_traffic_demo.py --skip-pipeline   # quick run
    python scripts/dynamic_traffic_demo.py --verbose          # DEBUG logging
"""

import argparse
import csv
import json
import sys
import traceback
from pathlib import Path

# Load environment variables from .env file
try:
    from dotenv import load_dotenv

    project_root = Path(__file__).parent.parent
    env_path = project_root / ".env"
    if env_path.exists():
        load_dotenv(env_path)
except ImportError:
    pass

import simpy

from sim.entities.map_payload import MapPayload, TrafficConfig
from sim.entities.position import Position
from sim.entities.traffic_event_state import TrafficEventState
from sim.map.map_controller import MapController
from grafana_logging.logger import get_logger
try:
    from sim.osm.traffic_state_store import traffic_state_store
except ImportError:
    traffic_state_store = None

logger = get_logger(__name__)


# ─── Helper Functions ────────────────────────────────────────────────────────


def format_segment_key_for_csv(segment_key):
    """Format a SegmentKey tuple as a string for TrafficParser's ast.literal_eval().

    Args:
        segment_key: ((lon1, lat1), (lon2, lat2))

    Returns:
        String like "((lon1,lat1),(lon2,lat2))"
    """
    (lon1, lat1), (lon2, lat2) = segment_key
    return f"(({lon1},{lat1}),({lon2},{lat2}))"


def get_event_segment_key(road):
    """Extract the best segment_key for CSV from a road.

    Prefers road.geometry endpoints (registered in PositionRegistry by
    RouteController) over road.segment_key (derived from interpolated
    pointcollection). The geometry endpoints share Position objects with
    the routing provider's output, ensuring the PositionRegistry finds
    overlaps during the pipeline pass.

    Args:
        road: Road object.

    Returns:
        SegmentKey tuple: ((lon1, lat1), (lon2, lat2))
    """
    if road.geometry and len(road.geometry) >= 2:
        start = road.geometry[0].get_position()
        end = road.geometry[-1].get_position()
        return ((start[0], start[1]), (end[0], end[1]))
    return road.segment_key


def generate_traffic_csv(path, segment_key, tick_start, duration, weight, name):
    """Write a valid traffic CSV matching TrafficParser format.

    Args:
        path: Output file path.
        segment_key: ((lon1, lat1), (lon2, lat2))
        tick_start: Simulation tick when event triggers.
        duration: How many ticks the event lasts.
        weight: Speed multiplier (0.0-1.0).
        name: Human-readable event name.
    """
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["TYPE", "tick_start", "segment_key", "name", "duration", "weight"])
        writer.writerow([
            "local_traffic",
            tick_start,
            format_segment_key_for_csv(segment_key),
            name,
            duration,
            weight,
        ])


def generate_scenario_json(json_path, csv_path, start_pos, end_pos):
    """Write a full scenario JSON importable into the scenario editor.

    The scenario places a vehicle at start_pos (IKEA) with a driver on shift,
    and a station at end_pos (Concordia) with 1 initial task. This causes
    the driver to be dispatched along the route that passes through the
    target traffic segment.

    Args:
        json_path: Output JSON file path.
        csv_path: Path to the traffic CSV (absolute path).
        start_pos: Start Position (vehicle/depot location).
        end_pos: End Position (task destination).
    """
    start_lon, start_lat = start_pos.get_position()
    end_lon, end_lat = end_pos.get_position()

    scenario = {
        "content": {
            "start_time": "day1:08:00",
            "end_time": "day1:09:00",
            "vehicle_battery_capacity": 50,
            "stations": [
                {
                    "name": "IKEA Depot",
                    "position": [start_lon, start_lat],
                    "initial_task_count": 0,
                    "scheduled_tasks": [],
                },
                {
                    "name": "Concordia Station",
                    "position": [end_lon, end_lat],
                    "initial_task_count": 1,
                    "scheduled_tasks": [],
                },
            ],
            "drivers": [
                {
                    "name": "Demo Driver",
                    "shift": {
                        "start_time": "day1:08:00",
                        "end_time": "day1:12:00",
                    },
                }
            ],
            "vehicles": [
                {
                    "name": "Demo Bike",
                    "position": [start_lon, start_lat],
                    "battery_count": 20,
                }
            ],
            "traffic": {
                "traffic_path": str(Path(csv_path).resolve()),
            },
        }
    }
    with open(json_path, "w") as f:
        json.dump(scenario, f, indent=2)


def simulate_traversal_with_pipeline(route, target_road, env, tc):
    """SimPy-driven traversal: advance env tick-by-tick then call route.next().

    The SimPy environment is stepped to tick+1 before each route.next() call,
    so the TrafficController's _process_event generators fire at their scheduled
    tick_start and traffic is applied to roads before the route reads them.

    Args:
        route: Route object to traverse.
        target_road: The target Road to track.
        env: SimPy Environment to step.
        tc: TrafficController (for logging event states).

    Returns:
        Tuple of (positions_list, stats_dict)
    """
    positions = []
    tick = 0

    ticks_before_traffic = 0
    ticks_after_traffic = 0
    ticks_after_expired = 0
    entered_target_tick = None
    left_target_tick = None
    traffic_expired_tick = None
    on_target = False

    # Track whether traffic has been applied to the target road
    traffic_applied = False
    traffic_expired = False

    while not route.is_finished:
        # Advance SimPy clock to current tick (fires scheduled events)
        env.run(until=tick + 1)

        # Check if traffic has been applied to the target road
        if not traffic_applied and target_road.traffic_multiplier < 1.0:
            traffic_applied = True
            new_points = len(target_road.active_pointcollection)
            print(
                f"    [tick {tick:>5}] PIPELINE TRAFFIC APPLIED — "
                f"multiplier={target_road.traffic_multiplier:.2f}, "
                f"points now={new_points}"
            )

        # Detect traffic removal (event expired)
        if traffic_applied and not traffic_expired and target_road.traffic_multiplier >= 1.0:
            traffic_expired = True
            traffic_expired_tick = tick
            print(f"    [tick {tick:>5}] PIPELINE TRAFFIC EXPIRED — speed restored")

        # Log state machine transitions for traffic events
        for event in tc.get_traffic_events():
            if event.state == TrafficEventState.TRIGGERED and tick == event.tick_start:
                logger.debug(
                    f"    [tick {tick}] Event '{event.name}' state: {event.state}"
                )

        pos = route.next()
        if pos is None:
            break

        coords = pos.get_position()

        road_idx = route.current_road_index
        if road_idx < len(route.roads):
            current_road = route.roads[road_idx]
            speed_kmh = current_road.current_speed * 3.6
            mult = current_road.traffic_multiplier
        else:
            current_road = None
            speed_kmh = 0.0
            mult = 1.0

        is_on_target = current_road is not None and current_road is target_road
        if is_on_target and not on_target:
            on_target = True
            entered_target_tick = tick
            print(
                f"    [tick {tick:>5}] ENTERED target road "
                f"(speed={speed_kmh:.1f} km/h)"
            )
        elif not is_on_target and on_target:
            on_target = False
            left_target_tick = tick
            print(f"    [tick {tick:>5}] LEFT target road")

        if is_on_target:
            if traffic_expired:
                ticks_after_expired += 1
            elif traffic_applied:
                ticks_after_traffic += 1
            else:
                ticks_before_traffic += 1

        positions.append({
            "tick": tick,
            "lon": coords[0],
            "lat": coords[1],
            "speed_kmh": speed_kmh,
            "multiplier": mult,
            "road_idx": road_idx,
            "on_target": is_on_target,
        })

        tick += 1

    stats = {
        "total_ticks": tick,
        "ticks_before_traffic": ticks_before_traffic,
        "ticks_after_traffic": ticks_after_traffic,
        "ticks_after_expired": ticks_after_expired,
        "total_on_target": ticks_before_traffic + ticks_after_traffic + ticks_after_expired,
        "entered_target_tick": entered_target_tick,
        "left_target_tick": left_target_tick,
        "traffic_expired_tick": traffic_expired_tick,
    }
    return positions, stats


def compare_results(stats_direct, stats_pipeline, original_points):
    """Print side-by-side comparison of direct vs pipeline results.

    Args:
        stats_direct: Stats dict from direct simulation.
        stats_pipeline: Stats dict from pipeline simulation.
        original_points: Original point count on target road (no traffic).
    """
    print(f"\n   {'Metric':<30} {'Direct':>10} {'Pipeline':>10}")
    print(f"   {'—'*30} {'—'*10} {'—'*10}")

    rows = [
        ("Total ticks", stats_direct["total_ticks"], stats_pipeline["total_ticks"]),
        ("Ticks on target", stats_direct["total_on_target"], stats_pipeline["total_on_target"]),
        ("  Before traffic", stats_direct["ticks_before_traffic"], stats_pipeline["ticks_before_traffic"]),
        ("  After traffic", stats_direct["ticks_after_traffic"], stats_pipeline["ticks_after_traffic"]),
        ("  After expired", stats_direct.get("ticks_after_expired", "—"), stats_pipeline.get("ticks_after_expired", "—")),
        ("Entered target @", stats_direct["entered_target_tick"], stats_pipeline["entered_target_tick"]),
        ("Left target @", stats_direct["left_target_tick"], stats_pipeline["left_target_tick"]),
        ("Traffic expired @", stats_direct.get("traffic_expired_tick", "—"), stats_pipeline.get("traffic_expired_tick", "—")),
    ]

    for label, val_d, val_p in rows:
        d_str = str(val_d) if val_d is not None else "—"
        p_str = str(val_p) if val_p is not None else "—"
        print(f"   {label:<30} {d_str:>10} {p_str:>10}")

    # Slowdown comparison
    if original_points > 0:
        d_slow = (stats_direct["total_on_target"] / original_points - 1) * 100 if stats_direct["total_on_target"] > 0 else 0
        p_slow = (stats_pipeline["total_on_target"] / original_points - 1) * 100 if stats_pipeline["total_on_target"] > 0 else 0
        print(f"   {'Slowdown %':<30} {d_slow:>9.1f}% {p_slow:>9.1f}%")

    # Verdict
    d_has_slowdown = stats_direct["total_on_target"] > original_points
    p_has_slowdown = stats_pipeline["total_on_target"] > original_points
    if d_has_slowdown and p_has_slowdown:
        print("\n   PASS: Both passes produced slowdown on target road")
    elif d_has_slowdown and not p_has_slowdown:
        print("\n   PARTIAL: Direct showed slowdown, pipeline did not")
    elif not d_has_slowdown and p_has_slowdown:
        print("\n   PARTIAL: Pipeline showed slowdown, direct did not")
    else:
        print("\n   NOTE: Neither pass showed slowdown (check timing/target)")


# ─── Original helpers (unchanged) ────────────────────────────────────────────


def analyze_route(route):
    """Analyze a route's road segments and calculate arrival ticks.

    Each road's pointcollection has 1 point per simulation tick (1pt/sec),
    so the number of points equals the traversal time in ticks.

    Returns:
        List of dicts with road metadata and cumulative arrival ticks.
    """
    cumulative_ticks = 0
    road_info = []

    for i, road in enumerate(route.roads):
        points = len(road.active_pointcollection)
        arrival_tick = cumulative_ticks
        road_info.append({
            "index": i,
            "road": road,
            "name": road.name or "Unnamed",
            "length_m": road.length,
            "maxspeed_ms": road.maxspeed,
            "speed_kmh": road.maxspeed * 3.6,
            "points": points,
            "arrival_tick": arrival_tick,
            "segment_key": road.segment_key,
        })
        cumulative_ticks += points

    return road_info


def print_road_table(road_info):
    """Print a formatted table of road segments."""
    header = (
        f"  {'#':>3} {'Name':<30} {'Length':>8} {'Speed':>8} "
        f"{'Points':>7} {'Arrive@':>8}"
    )
    print(header)
    print(f"  {'—'*3} {'—'*30} {'—'*8} {'—'*8} {'—'*7} {'—'*8}")
    for info in road_info:
        print(
            f"  {info['index']:>3} {info['name']:<30} "
            f"{info['length_m']:>7.0f}m {info['speed_kmh']:>6.1f}kph "
            f"{info['points']:>6}p  t={info['arrival_tick']:>5}"
        )


def simulate_traversal(route, target_road, traffic_tick, multiplier):
    """Simulate route traversal, applying traffic at the specified tick.

    Walks through the route tick-by-tick using route.next(). At the
    scheduled tick, applies traffic directly to the target road.
    Tracks speed and position for GeoJSON output.

    Returns:
        Tuple of (positions_list, stats_dict)
    """
    positions = []
    tick = 0
    traffic_applied = False

    # Tracking for target road
    ticks_before_traffic = 0
    ticks_after_traffic = 0
    entered_target_tick = None
    left_target_tick = None
    on_target = False

    while not route.is_finished:
        # Apply traffic at the scheduled tick
        if tick == traffic_tick and not traffic_applied:
            target_road.apply_traffic_for_overlap(
                list(target_road.geometry) if target_road.geometry else list(target_road.pointcollection),
                multiplier,
                target_road.segment_key,
            )
            traffic_applied = True
            new_points = len(target_road.active_pointcollection)
            print(
                f"    [tick {tick:>5}] TRAFFIC APPLIED — "
                f"multiplier={multiplier}, "
                f"points now={new_points}"
            )

        pos = route.next()
        if pos is None:
            break

        coords = pos.get_position()

        # Determine current road context
        road_idx = route.current_road_index
        if road_idx < len(route.roads):
            current_road = route.roads[road_idx]
            speed_kmh = current_road.current_speed * 3.6
            mult = current_road.traffic_multiplier
        else:
            current_road = None
            speed_kmh = 0.0
            mult = 1.0

        # Track target road entry/exit
        is_on_target = current_road is not None and current_road is target_road
        if is_on_target and not on_target:
            on_target = True
            entered_target_tick = tick
            print(
                f"    [tick {tick:>5}] ENTERED target road "
                f"(speed={speed_kmh:.1f} km/h)"
            )
        elif not is_on_target and on_target:
            on_target = False
            left_target_tick = tick
            print(f"    [tick {tick:>5}] LEFT target road")

        if is_on_target:
            if traffic_applied:
                ticks_after_traffic += 1
            else:
                ticks_before_traffic += 1

        positions.append({
            "tick": tick,
            "lon": coords[0],
            "lat": coords[1],
            "speed_kmh": speed_kmh,
            "multiplier": mult,
            "road_idx": road_idx,
            "on_target": is_on_target,
        })

        tick += 1

    stats = {
        "total_ticks": tick,
        "ticks_before_traffic": ticks_before_traffic,
        "ticks_after_traffic": ticks_after_traffic,
        "total_on_target": ticks_before_traffic + ticks_after_traffic,
        "entered_target_tick": entered_target_tick,
        "left_target_tick": left_target_tick,
    }
    return positions, stats


def generate_geojson(positions, road_info, target_idx, traffic_tick, event_duration, stats):
    """Generate GeoJSON FeatureCollection for visualization.

    Includes:
      - Each road segment as a labeled polyline (green = normal, red = traffic)
      - Vehicle traversal path (thin blue)
      - Traffic zone highlight (thick red overlay)
      - Start/end markers
      - Traffic applied marker (where on the route traffic kicked in)
      - Traffic expired marker (where on the route traffic lifted)
      - Vehicle enters/exits traffic zone markers
      - Speed-colored waypoints (every 30 ticks)
    """
    features = []
    target = road_info[target_idx]
    target_road = target["road"]

    # ── Per-road-segment polylines ────────────────────────────────────────
    for info in road_info:
        road = info["road"]
        road_coords = [pos.get_position() for pos in road.active_pointcollection]
        if len(road_coords) < 2:
            continue

        is_target = info["index"] == target_idx
        color = "#F44336" if is_target else "#4CAF50"
        width = 5 if is_target else 3
        opacity = 0.9 if is_target else 0.6

        features.append({
            "type": "Feature",
            "properties": {
                "name": f"[{info['index']}] {info['name']}",
                "description": (
                    f"Length: {info['length_m']:.0f}m, "
                    f"Speed: {info['speed_kmh']:.1f} km/h, "
                    f"Points: {info['points']}, "
                    f"Arrive @ tick {info['arrival_tick']}"
                ),
                "stroke": color,
                "stroke-width": width,
                "stroke-opacity": opacity,
            },
            "geometry": {
                "type": "LineString",
                "coordinates": road_coords,
            },
        })

    # ── Vehicle traversal path (thin blue overlay) ────────────────────────
    route_coords = [[p["lon"], p["lat"]] for p in positions]
    features.append({
        "type": "Feature",
        "properties": {
            "name": "Vehicle Traversal Path",
            "description": f"Total ticks: {len(positions)}",
            "stroke": "#2196F3",
            "stroke-width": 2,
            "stroke-opacity": 0.5,
        },
        "geometry": {
            "type": "LineString",
            "coordinates": route_coords,
        },
    })

    # ── Start & End markers ───────────────────────────────────────────────
    if positions:
        features.append({
            "type": "Feature",
            "properties": {
                "name": "Start (tick 0)",
                "marker-color": "#4CAF50",
                "marker-symbol": "car",
                "marker-size": "large",
            },
            "geometry": {
                "type": "Point",
                "coordinates": [positions[0]["lon"], positions[0]["lat"]],
            },
        })
        features.append({
            "type": "Feature",
            "properties": {
                "name": f"End (tick {positions[-1]['tick']})",
                "marker-color": "#9C27B0",
                "marker-symbol": "flag",
                "marker-size": "large",
            },
            "geometry": {
                "type": "Point",
                "coordinates": [positions[-1]["lon"], positions[-1]["lat"]],
            },
        })

    # ── Traffic applied marker ────────────────────────────────────────────
    if traffic_tick < len(positions):
        p = positions[traffic_tick]
        features.append({
            "type": "Feature",
            "properties": {
                "name": f"Traffic APPLIED (tick {traffic_tick})",
                "description": (
                    f"Traffic event starts here. "
                    f"Speed drops to {target['speed_kmh'] * target_road.traffic_multiplier:.1f} km/h"
                ),
                "marker-color": "#F44336",
                "marker-symbol": "danger",
                "marker-size": "large",
            },
            "geometry": {
                "type": "Point",
                "coordinates": [p["lon"], p["lat"]],
            },
        })

    # ── Traffic expired marker ────────────────────────────────────────────
    expiry_tick = traffic_tick + event_duration
    if expiry_tick < len(positions):
        p = positions[expiry_tick]
        features.append({
            "type": "Feature",
            "properties": {
                "name": f"Traffic EXPIRED (tick {expiry_tick})",
                "description": (
                    f"Traffic event ends here. "
                    f"Speed restored to {target['speed_kmh']:.1f} km/h"
                ),
                "marker-color": "#FF9800",
                "marker-symbol": "circle-stroked",
                "marker-size": "large",
            },
            "geometry": {
                "type": "Point",
                "coordinates": [p["lon"], p["lat"]],
            },
        })

    # ── Vehicle enters traffic zone marker ────────────────────────────────
    entered_tick = stats.get("entered_target_tick")
    if entered_tick is not None and entered_tick < len(positions):
        p = positions[entered_tick]
        features.append({
            "type": "Feature",
            "properties": {
                "name": f"Vehicle ENTERS traffic zone (tick {entered_tick})",
                "description": f"Speed: {p['speed_kmh']:.1f} km/h",
                "marker-color": "#FF5722",
                "marker-symbol": "triangle",
                "marker-size": "medium",
            },
            "geometry": {
                "type": "Point",
                "coordinates": [p["lon"], p["lat"]],
            },
        })

    # ── Vehicle exits traffic zone marker ─────────────────────────────────
    left_tick = stats.get("left_target_tick")
    if left_tick is not None and left_tick < len(positions):
        p = positions[left_tick]
        features.append({
            "type": "Feature",
            "properties": {
                "name": f"Vehicle EXITS traffic zone (tick {left_tick})",
                "description": f"Speed: {p['speed_kmh']:.1f} km/h",
                "marker-color": "#8BC34A",
                "marker-symbol": "triangle-stroked",
                "marker-size": "medium",
            },
            "geometry": {
                "type": "Point",
                "coordinates": [p["lon"], p["lat"]],
            },
        })

    # ── Speed-colored waypoints (every 30th tick) ─────────────────────────
    for p in positions[::30]:
        if p["multiplier"] >= 0.9:
            color = "#4CAF50"  # green — free flow
        elif p["multiplier"] >= 0.5:
            color = "#FF9800"  # orange — moderate
        else:
            color = "#F44336"  # red — severe
        features.append({
            "type": "Feature",
            "properties": {
                "name": f"t={p['tick']}: {p['speed_kmh']:.0f} km/h",
                "marker-color": color,
                "marker-size": "small",
            },
            "geometry": {
                "type": "Point",
                "coordinates": [p["lon"], p["lat"]],
            },
        })

    return {"type": "FeatureCollection", "features": features}


# ─── CLI ──────────────────────────────────────────────────────────────────────


def parse_args():
    parser = argparse.ArgumentParser(
        description="VeloSim Dynamic Traffic Demo"
    )
    parser.add_argument(
        "--multiplier", type=float, default=0.3,
        help="Traffic speed multiplier 0.01-1.0 (default: 0.3 = 30%% speed)",
    )
    parser.add_argument(
        "--target", type=float, default=0.5,
        help="Target road position as fraction of route 0.0-1.0 (default: 0.5)",
    )
    parser.add_argument(
        "--advance", type=int, default=50,
        help="Apply traffic N ticks before vehicle arrives (default: 50)",
    )
    parser.add_argument(
        "--start-lon", type=float, default=-73.691993,
        help="Start longitude (default: IKEA)",
    )
    parser.add_argument(
        "--start-lat", type=float, default=45.490198,
        help="Start latitude (default: IKEA)",
    )
    parser.add_argument(
        "--end-lon", type=float, default=-73.577797,
        help="End longitude (default: Concordia)",
    )
    parser.add_argument(
        "--end-lat", type=float, default=45.495009,
        help="End latitude (default: Concordia)",
    )
    parser.add_argument(
        "--skip-pipeline", action="store_true",
        help="Skip pass 2 (pipeline simulation) for quick runs",
    )
    parser.add_argument(
        "--verbose", action="store_true",
        help="Enable DEBUG logging for traffic pipeline",
    )
    return parser.parse_args()


# ─── Main ─────────────────────────────────────────────────────────────────────


def main():
    args = parse_args()

    if args.verbose:
        logger.setLevel("DEBUG")
    else:
        logger.setLevel("WARNING")

    print("=" * 70)
    print("VeloSim — Dynamic Traffic Demo (Two-Pass)")
    print("=" * 70)

    try:
        start_pos = Position([args.start_lon, args.start_lat])
        end_pos = Position([args.end_lon, args.end_lat])
        multiplier = max(0.01, min(1.0, args.multiplier))
        target_frac = max(0.0, min(1.0, args.target))
        advance_ticks = args.advance

        # ── Phase 1: Initialize & Generate Route ─────────────────────────
        print("\n1. Initializing simulation environment...")
        env = simpy.Environment()
        map_payload = MapPayload(env=env)
        mc = MapController(map_payload)
        print("   SimPy env ready, PositionRegistry active")

        print("\n2. Generating route via OSRM...")
        print(f"   Start: ({start_pos.get_position()})")
        print(f"   End:   ({end_pos.get_position()})")
        route = mc.get_route(start_pos, end_pos)
        print(f"   Route {route.id}: {len(route.roads)} road segments, "
              f"{route.distance:.0f}m, ~{route.duration:.0f}s")

        # ── Phase 1 cont: Analyze road segments ──────────────────────────
        print("\n3. Road segment analysis:")
        road_info = analyze_route(route)
        print_road_table(road_info)

        if not road_info:
            print("\n   ERROR: No road segments in route")
            sys.exit(1)

        total_ticks = sum(r["points"] for r in road_info)
        print(f"\n   Total estimated ticks: {total_ticks}")

        # ── Phase 2: Pick Target & Plan Scenario ─────────────────────────
        target_idx = int(len(road_info) * target_frac)
        target_idx = max(1, min(target_idx, len(road_info) - 2))
        target = road_info[target_idx]
        target_road = target["road"]

        traffic_tick = max(0, target["arrival_tick"] - advance_ticks)

        # Extract event_segment_key (geometry-based for pipeline compatibility)
        event_segment_key = get_event_segment_key(target_road)

        print(f"\n4. Traffic scenario:")
        print(f"   Target road:  #{target_idx} '{target['name']}'")
        print(f"   segment_key (pointcollection): {target['segment_key']}")
        print(f"   segment_key (geometry/CSV):    {event_segment_key}")
        print(f"   Vehicle arrives: tick {target['arrival_tick']}")
        print(f"   Traffic applies: tick {traffic_tick} "
              f"({advance_ticks} ticks early)")
        print(f"   Multiplier:   {multiplier} "
              f"({multiplier*100:.0f}% of normal speed)")
        print(f"   Normal speed: {target['speed_kmh']:.1f} km/h")
        print(f"   Expect speed: {target['speed_kmh'] * multiplier:.1f} km/h")
        original_points = target["points"]
        expected_points = int(original_points / max(multiplier, 0.01))
        print(f"   Original traversal: {original_points} ticks")
        print(f"   Expected traversal: ~{expected_points} ticks "
              f"(+{expected_points - original_points} ticks)")

        # ── Phase 3: Direct Application Simulation ───────────────────────
        print(f"\n5. Pass 1 — Direct application simulation...")
        positions, stats_direct = simulate_traversal(
            route, target_road, traffic_tick, multiplier
        )

        print(f"\n   Direct simulation complete:")
        print(f"   Total ticks traversed: {stats_direct['total_ticks']}")
        print(f"   Ticks on target road:  {stats_direct['total_on_target']}")
        if stats_direct["ticks_before_traffic"] > 0:
            print(f"     Before traffic: {stats_direct['ticks_before_traffic']} ticks "
                  f"@ {target['speed_kmh']:.1f} km/h")
        if stats_direct["ticks_after_traffic"] > 0:
            print(f"     After traffic:  {stats_direct['ticks_after_traffic']} ticks "
                  f"@ {target['speed_kmh'] * multiplier:.1f} km/h")
        if original_points > 0 and stats_direct["total_on_target"] > 0:
            slowdown = (stats_direct["total_on_target"] / original_points - 1) * 100
            print(f"   Slowdown effect: +{slowdown:.1f}% longer on segment")

        # ── Phase 4: Generate Traffic CSV & Scenario JSON ────────────────
        scripts_dir = Path(__file__).parent
        csv_path = scripts_dir / "dynamic_traffic_output.csv"
        json_path = scripts_dir / "dynamic_traffic_scenario.json"

        # Compute event duration so it expires ~60% through the slowed traversal.
        # This lets the driver experience traffic then see it lifted mid-segment.
        entered = stats_direct.get("entered_target_tick") or target["arrival_tick"]
        left = stats_direct.get("left_target_tick") or (entered + target["points"])
        slowed_traversal = left - entered
        event_duration = (entered - traffic_tick) + int(slowed_traversal * 0.6)
        # Ensure minimum viable duration
        event_duration = max(event_duration, advance_ticks + 10)

        print(f"\n6. Generating traffic CSV & scenario JSON...")
        print(f"   Event duration: {event_duration} ticks "
              f"(expires at tick ~{traffic_tick + event_duration})")
        print(f"   Driver on segment: tick {entered}–{left} (under traffic)")
        print(f"   Event expires: ~60% through traversal → driver speeds up")
        generate_traffic_csv(
            csv_path, event_segment_key, traffic_tick, event_duration, multiplier, "demo_traffic"
        )
        generate_scenario_json(json_path, csv_path, start_pos, end_pos)
        print(f"   CSV:      {csv_path}")
        print(f"   Scenario: {json_path}")

        # ── Phase 5: Pipeline Simulation ─────────────────────────────────
        stats_pipeline = None
        if not args.skip_pipeline:
            print(f"\n7. Pass 2 — Pipeline simulation (CSV → TrafficController)...")

            # Create fresh SimPy env + MapController with traffic config
            env2 = simpy.Environment()
            traffic_config = TrafficConfig(traffic_path=str(csv_path))
            map_payload2 = MapPayload(env=env2, traffic=traffic_config)
            mc2 = MapController(map_payload2)

            # Log loaded events
            tc2 = mc2.traffic_controller
            events = tc2.get_traffic_events()
            print(f"   Loaded {len(events)} traffic event(s) from CSV")
            for i, evt in enumerate(events):
                print(f"     [{i}] {evt.name}: tick_start={evt.tick_start}, "
                      f"weight={evt.weight}, duration={evt.duration}, "
                      f"state={evt.state}")

            # Generate the same route (same OSRM endpoints = same roads)
            print(f"   Generating same route via OSRM...")
            route2 = mc2.get_route(start_pos, end_pos)
            print(f"   Route {route2.id}: {len(route2.roads)} road segments")

            # Find the matching target road in the new route
            target_road2 = None
            for road in route2.roads:
                road_geom_key = get_event_segment_key(road)
                if road_geom_key == event_segment_key:
                    target_road2 = road
                    break

            if target_road2 is None:
                # Fallback: match by index
                if target_idx < len(route2.roads):
                    target_road2 = route2.roads[target_idx]
                    print(f"   WARNING: Exact geometry match not found, "
                          f"using index {target_idx}")
                else:
                    print(f"   ERROR: Could not find matching target road in pass 2")
                    mc2.close()
                    sys.exit(1)

            print(f"   Target road: '{target_road2.name or 'Unnamed'}' "
                  f"(multiplier={target_road2.traffic_multiplier:.2f})")

            # Run pipeline simulation
            positions_pipeline, stats_pipeline = simulate_traversal_with_pipeline(
                route2, target_road2, env2, tc2
            )
            road_info2 = analyze_route(route2)

            print(f"\n   Pipeline simulation complete:")
            print(f"   Total ticks traversed: {stats_pipeline['total_ticks']}")
            print(f"   Ticks on target road:  {stats_pipeline['total_on_target']}")
            if stats_pipeline["ticks_before_traffic"] > 0:
                print(f"     Before traffic: {stats_pipeline['ticks_before_traffic']} ticks")
            if stats_pipeline["ticks_after_traffic"] > 0:
                print(f"     Under traffic:  {stats_pipeline['ticks_after_traffic']} ticks")
            if stats_pipeline.get("ticks_after_expired", 0) > 0:
                print(f"     After expired:  {stats_pipeline['ticks_after_expired']} ticks (normal speed)")
            if stats_pipeline.get("traffic_expired_tick") is not None:
                print(f"   Traffic expired at tick: {stats_pipeline['traffic_expired_tick']}")

            # Log final event states
            remaining_events = tc2.get_traffic_events()
            print(f"\n   Final event states:")
            if remaining_events:
                for evt in remaining_events:
                    print(f"     '{evt.name}': {evt.state}")
            else:
                print(f"     (all events completed and cleaned up)")

            # ── Phase 6: Compare Results ─────────────────────────────────
            print(f"\n8. Comparison (Direct vs Pipeline):")
            compare_results(stats_direct, stats_pipeline, original_points)

            mc2.close()
        else:
            print(f"\n7. Pipeline simulation skipped (--skip-pipeline)")

        # ── Phase 5b: Routing Provider Traffic Verification ──────────────
        rp_step = 9 if not args.skip_pipeline else 8
        if traffic_state_store is None:
            print(f"\n{rp_step}. Pass 3 — SKIPPED (traffic_state_store not available)")
        else:
            print(f"\n{rp_step}. Pass 3 — Routing provider traffic store verification...")

            # Create a fresh MapController wired with the same traffic CSV
            # but this time we inspect the TrafficStateStore that OSRMAdapter
            # delegates to, proving the CRUD methods work end-to-end.
            traffic_state_store._reset()  # start clean

            env3 = simpy.Environment()
            traffic_config3 = TrafficConfig(traffic_path=str(csv_path))
            map_payload3 = MapPayload(env=env3, traffic=traffic_config3)
            mc3 = MapController(map_payload3)

            tc3 = mc3.traffic_controller
            rp3 = mc3.routing_provider
            events3 = tc3.get_traffic_events()
            print(f"   Loaded {len(events3)} traffic event(s)")

            # Generate a route so roads exist and PositionRegistry has data
            route3 = mc3.get_route(start_pos, end_pos)
            print(f"   Route {route3.id}: {len(route3.roads)} road segments")

            # Step SimPy past the event's tick_start so the state machine fires
            # PENDING → TRIGGERED → APPLIED, which calls _update_routing_provider()
            if events3:
                evt = events3[0]
                # After TRIGGERED, the routing provider update is delayed by
                # GPS_SYNC_DELAY (10 ticks), so advance past that.
                trigger_tick = evt.tick_start + 15
                print(f"   Advancing SimPy to tick {trigger_tick} "
                      f"(event tick_start={evt.tick_start})...")
                env3.run(until=trigger_tick)

                # Build EdgeIdentifier from the event's segment_key so the
                # store key is constructed via Position (same path the adapter
                # uses internally). Using evt.segment_key directly would fail
                # due to float precision differences from CSV parsing.
                from sim.map.routing_provider import EdgeIdentifier
                start_coords, end_coords = evt.segment_key
                edge_id = EdgeIdentifier(
                    start_position=Position([start_coords[0], start_coords[1]]),
                    end_position=Position([end_coords[0], end_coords[1]]),
                )
                store_key = edge_id.segment_key

                # Check that the routing provider now has the traffic state.
                # The adapter's sim_id defaults to "" (empty string).
                sim_id = ""
                stored_factor = traffic_state_store.get(sim_id, store_key)

                print(f"   Checking TrafficStateStore for segment_key...")
                if stored_factor is not None:
                    print(f"   PASS: Routing provider stored speed_factor={stored_factor:.2f} "
                          f"for event '{evt.name}'")
                else:
                    print(f"   FAIL: No traffic state found in routing provider store")
                    print(f"         Expected speed_factor={evt.weight} "
                          f"for segment_key={store_key}")

                # Also verify via the adapter's get_edge_traffic method directly
                adapter_result = rp3.get_edge_traffic(edge_id)
                if adapter_result is not None:
                    print(f"   PASS: adapter.get_edge_traffic() returned {adapter_result:.2f}")
                else:
                    print(f"   FAIL: adapter.get_edge_traffic() returned None")

                # Now advance past expiry and verify cleanup.
                # After EXPIRED, the remove sync path is:
                #   WaitUntilServed → ResetSim → GPS_SYNC_DELAY(10) → ResetRP
                # So we need at least +12 ticks past expiry for the full
                # removal to complete (sync acquisition + delay + clear).
                expiry_tick = evt.tick_start + evt.duration + 15
                print(f"\n   Advancing SimPy to tick {expiry_tick} "
                      f"(past event expiry at tick {evt.tick_start + evt.duration})...")
                env3.run(until=expiry_tick)

                stored_after = traffic_state_store.get(sim_id, store_key)
                adapter_after = rp3.get_edge_traffic(edge_id)
                if stored_after is None and adapter_after is None:
                    print(f"   PASS: Traffic state cleared after event expired")
                else:
                    print(f"   INFO: Traffic state after expiry: "
                          f"store={stored_after}, adapter={adapter_after}")
                    print(f"   (clear_edge_traffic is called on expiry — "
                          f"state should be None)")

                # Verify close() cleans up the sim's store partition
                print(f"\n   Calling mc3.close() to verify cleanup...")
                mc3.close()
                final_check = traffic_state_store.get(sim_id, store_key)
                if final_check is None:
                    print(f"   PASS: close() cleaned up traffic state store")
                else:
                    print(f"   FAIL: close() did not clean up (value={final_check})")
            else:
                print(f"   SKIP: No traffic events loaded")
                mc3.close()

        # ── Phase 7: GeoJSON Output ──────────────────────────────────────
        # Prefer pipeline data (has proper expiry) over direct (never expires)
        step_num = rp_step + 1
        print(f"\n{step_num}. Generating GeoJSON preview...")
        if stats_pipeline is not None:
            print(f"   Using Pass 2 (pipeline) data — includes traffic expiry")
            geojson = generate_geojson(
                positions_pipeline, road_info2, target_idx,
                traffic_tick, event_duration, stats_pipeline,
            )
        else:
            print(f"   Using Pass 1 (direct) data — no traffic expiry")
            geojson = generate_geojson(
                positions, road_info, target_idx,
                traffic_tick, event_duration, stats_direct,
            )

        output_path = scripts_dir / "dynamic_traffic_output.geojson"
        with open(output_path, "w") as f:
            json.dump(geojson, f, indent=2)
        print(f"   Written to: {output_path}")
        print(f"   Visualize at: https://geojson.io")

        # ── Cleanup ──────────────────────────────────────────────────────
        mc.close()

        print(f"\n{'='*70}")
        print("Demo complete!")
        if not args.skip_pipeline:
            print("Output files:")
            print(f"  CSV:      {csv_path}")
            print(f"  Scenario: {json_path}")
            print(f"  GeoJSON:  {output_path}")
        print(f"{'='*70}")

    except Exception as e:
        print(f"\nError: {e}")
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
