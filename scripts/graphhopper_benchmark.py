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

import argparse
import csv
import os
import statistics
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Optional, Sequence, Tuple

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
from sim.map.MapController import MapController


@dataclass(frozen=True)
class Scenario:
    name: str
    traffic_events: int
    concurrent_sims: int
    runs: int


def format_segment_key_for_csv(segment_key: Tuple[Tuple[float, float], Tuple[float, float]]) -> str:
    (lon1, lat1), (lon2, lat2) = segment_key
    return f"(({lon1},{lat1}),({lon2},{lat2}))"


def get_event_segment_key(road) -> Tuple[Tuple[float, float], Tuple[float, float]]:
    if road.geometry and len(road.geometry) >= 2:
        start = road.geometry[0].get_position()
        end = road.geometry[-1].get_position()
        return ((start[0], start[1]), (end[0], end[1]))
    return road.segment_key


def generate_traffic_csv(path: Path, rows: Iterable[Tuple[str, int, str, int, float]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["TYPE", "tick_start", "segment_key", "name", "duration", "weight"])
        for name, tick_start, segment_key, duration, weight in rows:
            writer.writerow([
                "local_traffic",
                tick_start,
                segment_key,
                name,
                duration,
                weight,
            ])


def percentile(values: Sequence[float], pct: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    if pct <= 0:
        return ordered[0]
    if pct >= 100:
        return ordered[-1]
    k = (len(ordered) - 1) * (pct / 100.0)
    f = int(k)
    c = min(f + 1, len(ordered) - 1)
    if f == c:
        return ordered[f]
    return ordered[f] + (ordered[c] - ordered[f]) * (k - f)


def build_events(
    road_info: List[dict],
    event_count: int,
    multiplier: float,
    advance_ticks: int,
) -> List[Tuple[str, int, str, int, float]]:
    if event_count <= 0:
        return []

    segments = [get_event_segment_key(info["road"]) for info in road_info]
    if not segments:
        return []

    rows: List[Tuple[str, int, str, int, float]] = []
    for i in range(event_count):
        idx = i % len(road_info)
        info = road_info[idx]
        points = info["points"]
        arrival_tick = info["arrival_tick"]
        tick_start = max(0, arrival_tick - advance_ticks)
        duration = max(advance_ticks + 10, int(points / max(multiplier, 0.01) * 0.6))
        segment_key = format_segment_key_for_csv(segments[idx])
        rows.append((f"bench_{i}", tick_start, segment_key, duration, multiplier))
    return rows


def analyze_route(route) -> List[dict]:
    cumulative_ticks = 0
    road_info = []

    for road in route.roads:
        points = len(road.active_pointcollection)
        road_info.append({
            "road": road,
            "points": points,
            "arrival_tick": cumulative_ticks,
        })
        cumulative_ticks += points

    return road_info


def traverse_route(env: simpy.Environment, route) -> None:
    tick = 0
    while not route.is_finished:
        env.run(until=tick + 1)
        pos = route.next()
        if pos is None:
            break
        tick += 1


def run_single(
    traffic_events: int,
    multiplier: float,
    advance_ticks: int,
    start_pos: Position,
    end_pos: Position,
    output_dir: Path,
) -> float:
    env0 = simpy.Environment()
    base_payload = MapPayload(env=env0)
    mc0 = MapController(base_payload)
    route0 = mc0.get_route(start_pos, end_pos)
    road_info = analyze_route(route0)
    mc0.close()

    csv_path = output_dir / "traffic.csv"
    if traffic_events > 0:
        rows = build_events(road_info, traffic_events, multiplier, advance_ticks)
        generate_traffic_csv(csv_path, rows)
        traffic_config = TrafficConfig(traffic_path=str(csv_path))
    else:
        traffic_config = None

    env = simpy.Environment()
    map_payload = MapPayload(env=env, traffic=traffic_config)

    start = time.perf_counter()
    mc = MapController(map_payload)
    route = mc.get_route(start_pos, end_pos)
    traverse_route(env, route)
    mc.close()
    end = time.perf_counter()

    return (end - start) * 1000.0


def run_scenario(
    scenario: Scenario,
    multiplier: float,
    advance_ticks: int,
    start_pos: Position,
    end_pos: Position,
    output_dir: Path,
) -> Tuple[Scenario, List[float], Optional[float]]:
    durations: List[float] = []
    scenario_dir = output_dir / scenario.name
    scenario_dir.mkdir(parents=True, exist_ok=True)

    start = time.perf_counter()
    with ThreadPoolExecutor(max_workers=scenario.concurrent_sims) as executor:
        futures = [
            executor.submit(
                run_single,
                scenario.traffic_events,
                multiplier,
                advance_ticks,
                start_pos,
                end_pos,
                scenario_dir / f"run_{i}",
            )
            for i in range(scenario.runs)
        ]
        for future in as_completed(futures):
            durations.append(future.result())
    end = time.perf_counter()

    throughput = None
    if scenario.concurrent_sims > 1:
        total_time = end - start
        if total_time > 0:
            throughput = scenario.runs / total_time

    return scenario, durations, throughput


def scenario_table() -> List[Scenario]:
    return [
        Scenario("1_baseline", 0, 1, 5),
        Scenario("2_heavy_traffic", 10, 1, 5),
        Scenario("2_heavy_traffic", 50, 1, 5),
        Scenario("2_heavy_traffic", 100, 1, 5),
        Scenario("2_heavy_traffic", 250, 1, 5),
        Scenario("2_heavy_traffic", 500, 1, 5),
        Scenario("2_heavy_traffic", 1000, 1, 5),
        Scenario("3_concurrent_no_traffic", 0, 2, 10),
        Scenario("3_concurrent_no_traffic", 0, 4, 20),
        Scenario("3_concurrent_no_traffic", 0, 8, 40),
        Scenario("4_concurrent_with_traffic", 100, 2, 10),
        Scenario("4_concurrent_with_traffic", 100, 4, 20),
        Scenario("4_concurrent_with_traffic", 100, 8, 40),
    ]


def print_results(scenarios: List[Tuple[Scenario, List[float], Optional[float]]]) -> None:
    header = [
        "Scenario",
        "Traffic Events",
        "Concurrent Sims",
        "n",
        "Mean (ms)",
        "Median (ms)",
        "Min (ms)",
        "Max (ms)",
        "p95 (ms)",
        "p99 (ms)",
        "Stdev (ms)",
        "Throughput (RPS)",
    ]
    print("| " + " | ".join(header) + " |")
    print("|" + "|".join(["---"] * len(header)) + "|")
    for scenario, durations, throughput in scenarios:
        mean = statistics.mean(durations) if durations else 0.0
        median = statistics.median(durations) if durations else 0.0
        min_v = min(durations) if durations else 0.0
        max_v = max(durations) if durations else 0.0
        p95 = percentile(durations, 95)
        p99 = percentile(durations, 99)
        stdev = statistics.pstdev(durations) if len(durations) > 1 else 0.0
        throughput_str = f"{throughput:.2f}" if throughput is not None else "—"

        row = [
            scenario.name,
            str(scenario.traffic_events),
            str(scenario.concurrent_sims),
            str(scenario.runs),
            f"{mean:.1f}",
            f"{median:.1f}",
            f"{min_v:.1f}",
            f"{max_v:.1f}",
            f"{p95:.1f}",
            f"{p99:.1f}",
            f"{stdev:.1f}",
            throughput_str,
        ]
        print("| " + " | ".join(row) + " |")


def write_csv(
    csv_path: Path,
    scenarios: List[Tuple[Scenario, List[float], Optional[float]]],
) -> None:
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "Scenario",
            "Traffic Events",
            "Concurrent Sims",
            "n",
            "Mean (ms)",
            "Median (ms)",
            "Min (ms)",
            "Max (ms)",
            "p95 (ms)",
            "p99 (ms)",
            "Stdev (ms)",
            "Throughput (RPS)",
        ])
        for scenario, durations, throughput in scenarios:
            mean = statistics.mean(durations) if durations else 0.0
            median = statistics.median(durations) if durations else 0.0
            min_v = min(durations) if durations else 0.0
            max_v = max(durations) if durations else 0.0
            p95 = percentile(durations, 95)
            p99 = percentile(durations, 99)
            stdev = statistics.pstdev(durations) if len(durations) > 1 else 0.0
            throughput_val = f"{throughput:.2f}" if throughput is not None else ""
            writer.writerow([
                scenario.name,
                scenario.traffic_events,
                scenario.concurrent_sims,
                scenario.runs,
                f"{mean:.1f}",
                f"{median:.1f}",
                f"{min_v:.1f}",
                f"{max_v:.1f}",
                f"{p95:.1f}",
                f"{p99:.1f}",
                f"{stdev:.1f}",
                throughput_val,
            ])


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="GraphHopper traffic benchmark")
    parser.add_argument(
        "--provider",
        default="graphhopper",
        help="Routing provider to use (default: graphhopper)",
    )
    parser.add_argument(
        "--multiplier",
        type=float,
        default=0.3,
        help="Traffic speed multiplier (default: 0.3)",
    )
    parser.add_argument(
        "--advance",
        type=int,
        default=50,
        help="Apply traffic N ticks before vehicle arrives (default: 50)",
    )
    parser.add_argument(
        "--start-lon",
        type=float,
        default=-73.691993,
        help="Start longitude (default: IKEA)",
    )
    parser.add_argument(
        "--start-lat",
        type=float,
        default=45.490198,
        help="Start latitude (default: IKEA)",
    )
    parser.add_argument(
        "--end-lon",
        type=float,
        default=-73.577797,
        help="End longitude (default: Concordia)",
    )
    parser.add_argument(
        "--end-lat",
        type=float,
        default=45.495009,
        help="End latitude (default: Concordia)",
    )
    parser.add_argument(
        "--output",
        default=str(Path("scripts") / "benchmark_outputs" / "graphhopper_benchmark_results.csv"),
        help="CSV output path",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    os.environ["ROUTING_PROVIDER"] = args.provider

    start_pos = Position([args.start_lon, args.start_lat])
    end_pos = Position([args.end_lon, args.end_lat])

    scenarios = scenario_table()
    output_dir = Path(args.output).parent

    results: List[Tuple[Scenario, List[float], Optional[float]]] = []
    for scenario in scenarios:
        results.append(
            run_scenario(
                scenario,
                multiplier=max(0.01, min(1.0, args.multiplier)),
                advance_ticks=args.advance,
                start_pos=start_pos,
                end_pos=end_pos,
                output_dir=output_dir,
            )
        )

    print_results(results)
    write_csv(Path(args.output), results)


if __name__ == "__main__":
    main()
