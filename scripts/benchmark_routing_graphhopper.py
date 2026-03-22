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
Routing Benchmark (GraphHopper) — VeloSim
=========================================
Measures wall-clock latency of adapter.get_route() across four scenarios.
All timings include real HTTP round-trips to the routing engine; adapter
init and traffic preloading are excluded from timed sections.

Scenario 1 — Baseline (no traffic)
    Single-sim, IKEA → Concordia, free-flow.

Scenario 2 — Heavy traffic (varying event count)
    Single-sim, 10 / 50 / 100 / 250 / 500 / 1000 congestion events on the
    route. Events cycle across real segment keys extracted from the baseline
    route so the adapter performs GraphHopper's two-pass routing flow.

Scenario 3 — Concurrent simulations, no traffic
    N independent simulations (each with its own session & sim_id) all
    calling get_route() through a threading.Barrier so requests overlap.

Scenario 4 — Concurrent simulations, unique per-sim traffic
    Same as Scenario 3 but each sim has its own distinct traffic state
    injected before the barrier fires.

Usage
-----
    python scripts/benchmark_routing_graphhopper.py
    python scripts/benchmark_routing_graphhopper.py --reps 10
    python scripts/benchmark_routing_graphhopper.py --concurrent 2 4 8 16
    python scripts/benchmark_routing_graphhopper.py --output results/benchmark.csv
    python scripts/benchmark_routing_graphhopper.py --verbose
    python scripts/benchmark_routing_graphhopper.py --traffic-events 10 50 100 250 500 1000
    ROUTING_PROVIDER=graphhopper python scripts/benchmark_routing_graphhopper.py

Prerequisites
-------------
    GraphHopper running: npm run graphhopper:up
    (or set GRAPHHOPPER_URL env var to a remote instance)
"""

import argparse
import csv
import itertools
import logging
import os
import statistics
import sys
import threading
import time
from pathlib import Path
from typing import Dict, List, Optional

# ── env / path setup ────────────────────────────────────────────────────────
try:
    from dotenv import load_dotenv

    _root = Path(__file__).parent.parent
    _env = _root / ".env"
    if _env.exists():
        load_dotenv(_env)
except ImportError:
    pass

sys.path.insert(0, str(Path(__file__).parent.parent))

from sim.entities.position import Position
from sim.map.routing_provider import SegmentKey
from sim.osm.graphhopper_connection import GraphHopperConnection
from sim.osm.graphhopper_adapter import GraphHopperAdapter
from sim.osm.traffic_state_store import traffic_state_store

logger = logging.getLogger(__name__)

# ── Fixed benchmark endpoints (IKEA Montréal → Concordia SGW) ───────────────
START = Position([-73.691993, 45.490198])
END = Position([-73.577797, 45.495009])

GRAPHHOPPER_PROFILE = os.getenv("GRAPHHOPPER_COSTING", "car")
DEFAULT_TRAFFIC_COUNTS = [10, 50, 100, 250, 500, 1000]
DEFAULT_CONCURRENT = [2, 4, 8]
HEAVY_TRAFFIC_FACTOR = 0.1
DEFAULT_REPS = 5


def _percentile(sorted_data: List[float], pct: float) -> float:
    if not sorted_data:
        return float("nan")
    n = len(sorted_data)
    idx = (n - 1) * pct / 100.0
    lo = int(idx)
    hi = lo + 1
    if hi >= n:
        return sorted_data[-1]
    frac = idx - lo
    return sorted_data[lo] * (1 - frac) + sorted_data[hi] * frac


def compute_stats(times_s: List[float]) -> Dict[str, float]:
    sorted_t = sorted(times_s)
    n = len(sorted_t)
    mean = statistics.mean(sorted_t)
    return {
        "n": n,
        "mean_ms": mean * 1000,
        "median_ms": statistics.median(sorted_t) * 1000,
        "min_ms": sorted_t[0] * 1000,
        "max_ms": sorted_t[-1] * 1000,
        "p95_ms": _percentile(sorted_t, 95) * 1000,
        "p99_ms": _percentile(sorted_t, 99) * 1000,
        "stdev_ms": (statistics.stdev(sorted_t) * 1000 if n > 1 else 0.0),
    }


def extract_segment_keys(graphhopper_url: Optional[str] = None) -> List[SegmentKey]:
    logger.info("Extracting segment keys from baseline route …")
    try:
        conn = GraphHopperConnection(graphhopper_url=graphhopper_url)
        start_lon, start_lat = START.get_position()
        end_lon, end_lat = END.get_position()
        result = conn.shortest_path_coords(
            start_lon,
            start_lat,
            end_lon,
            end_lat,
            profile=GRAPHHOPPER_PROFILE,
        )
        conn.close()
    except Exception as exc:
        logger.error(f"Failed to extract segment keys: {exc}")
        return []

    if not result or not result.segments:
        logger.warning("No segments in baseline result – traffic matching will be empty")
        return []

    keys: List[SegmentKey] = []
    for seg in result.segments:
        if seg.geometry and len(seg.geometry) >= 2:
            start_coord = (float(seg.geometry[0][0]), float(seg.geometry[0][1]))
            end_coord = (float(seg.geometry[-1][0]), float(seg.geometry[-1][1]))
            keys.append((start_coord, end_coord))

    logger.info(f"Extracted {len(keys)} real segment keys from baseline route")
    return keys


def _load_traffic(
    sim_id: str,
    segment_keys: List[SegmentKey],
    n_events: int,
    speed_factor: float = HEAVY_TRAFFIC_FACTOR,
) -> None:
    if not segment_keys:
        return
    key_cycle = itertools.cycle(segment_keys)
    for _ in range(n_events):
        key = next(key_cycle)
        traffic_state_store.set(sim_id, key, speed_factor)


def scenario_1_baseline(reps: int, graphhopper_url: Optional[str]) -> Dict:
    print("\n── Scenario 1: Baseline (no traffic) ──────────────────────────────")
    sim_id = "bench_s1"
    try:
        adapter = GraphHopperAdapter(
            graphhopper_url=graphhopper_url,
            sim_id=sim_id,
            profile=GRAPHHOPPER_PROFILE,
        )
    except Exception as exc:
        print(f"  SKIP — cannot connect to GraphHopper: {exc}")
        return {}

    adapter.get_route(START, END)

    times: List[float] = []
    for i in range(reps):
        t0 = time.perf_counter()
        result = adapter.get_route(START, END)
        elapsed = time.perf_counter() - t0
        times.append(elapsed)
        status = "OK" if result else "FAIL"
        print(f"  rep {i + 1:>2}/{reps}  {elapsed * 1000:>7.1f} ms  [{status}]")

    adapter.close()
    stats = compute_stats(times)
    _print_stats(stats)
    return {
        "scenario": "1_baseline",
        "traffic_events": 0,
        "concurrent_sims": 1,
        **stats,
    }


def scenario_2_heavy_traffic(
    reps: int,
    segment_keys: List[SegmentKey],
    event_counts: List[int],
    graphhopper_url: Optional[str],
) -> List[Dict]:
    print("\n── Scenario 2: Heavy traffic (varying event counts) ────────────────")
    rows: List[Dict] = []

    if not segment_keys:
        print("  SKIP — no segment keys available (baseline route failed)")
        return rows

    for n_events in event_counts:
        sim_id = f"bench_s2_{n_events}"
        try:
            adapter = GraphHopperAdapter(
                graphhopper_url=graphhopper_url,
                sim_id=sim_id,
                profile=GRAPHHOPPER_PROFILE,
            )
        except Exception as exc:
            print(f"  n={n_events:>5}  SKIP — {exc}")
            continue

        _load_traffic(sim_id, segment_keys, n_events)
        adapter.get_route(START, END)

        times: List[float] = []
        for i in range(reps):
            t0 = time.perf_counter()
            result = adapter.get_route(START, END)
            elapsed = time.perf_counter() - t0
            times.append(elapsed)
            status = "OK" if result else "FAIL"
            print(
                f"  n={n_events:>5}  rep {i + 1:>2}/{reps}"
                f"  {elapsed * 1000:>7.1f} ms  [{status}]"
            )

        adapter.close()
        stats = compute_stats(times)
        _print_stats(stats, prefix=f"  n={n_events:<5} → ")
        rows.append(
            {
                "scenario": "2_heavy_traffic",
                "traffic_events": n_events,
                "concurrent_sims": 1,
                **stats,
            }
        )

    return rows


def scenario_3_concurrent_no_traffic(
    reps: int,
    concurrent_counts: List[int],
    graphhopper_url: Optional[str],
) -> List[Dict]:
    print("\n── Scenario 3: Concurrent simulations (no traffic) ─────────────────")
    rows: List[Dict] = []

    for n_sims in concurrent_counts:
        print(f"\n  {n_sims} concurrent simulation(s):")

        adapters: List[GraphHopperAdapter] = []
        for i in range(n_sims):
            try:
                adapters.append(
                    GraphHopperAdapter(
                        graphhopper_url=graphhopper_url,
                        sim_id=f"bench_s3_{n_sims}_{i}",
                        profile=GRAPHHOPPER_PROFILE,
                    )
                )
            except Exception as exc:
                print(f"    SKIP — cannot create adapter {i}: {exc}")
                for a in adapters:
                    a.close()
                adapters = []
                break

        if not adapters:
            continue

        for adapter in adapters:
            adapter.get_route(START, END)

        per_sim_times: Dict[int, List[float]] = {i: [] for i in range(n_sims)}

        for rep in range(reps):
            barrier = threading.Barrier(n_sims)
            thread_results: List[Optional[float]] = [None] * n_sims

            def _worker(idx: int, adapter: GraphHopperAdapter) -> None:
                barrier.wait()
                t0 = time.perf_counter()
                adapter.get_route(START, END)
                thread_results[idx] = time.perf_counter() - t0

            threads = [
                threading.Thread(target=_worker, args=(i, adapters[i]))
                for i in range(n_sims)
            ]
            wall_t0 = time.perf_counter()
            for t in threads:
                t.start()
            for t in threads:
                t.join()
            wall_elapsed = time.perf_counter() - wall_t0

            for i, t in enumerate(thread_results):
                if t is not None:
                    per_sim_times[i].append(t)

            sim_ms = [f"{(thread_results[i] or 0) * 1000:.1f}" for i in range(n_sims)]
            print(
                f"    rep {rep + 1:>2}/{reps}  wall={wall_elapsed * 1000:>7.1f} ms"
                f"  sim_ms=[{', '.join(sim_ms)}]"
            )

        all_times = [t for ts in per_sim_times.values() for t in ts]
        stats = compute_stats(all_times)
        throughput = n_sims / (stats["mean_ms"] / 1000)
        _print_stats(stats, prefix=f"  n_sims={n_sims} → ")
        print(f"    throughput ≈ {throughput:.1f} route-calls / s")

        for adapter in adapters:
            adapter.close()

        rows.append(
            {
                "scenario": "3_concurrent_no_traffic",
                "traffic_events": 0,
                "concurrent_sims": n_sims,
                "throughput_rps": round(throughput, 2),
                **stats,
            }
        )

    return rows


def scenario_4_concurrent_with_traffic(
    reps: int,
    segment_keys: List[SegmentKey],
    concurrent_counts: List[int],
    graphhopper_url: Optional[str],
    n_events_per_sim: int = 100,
) -> List[Dict]:
    print(
        "\n── Scenario 4: Concurrent simulations with per-sim traffic ──────────"
        f"\n   (each sim: {n_events_per_sim} traffic events, speed_factor varies per sim)"
    )
    rows: List[Dict] = []

    if not segment_keys:
        print("  SKIP — no segment keys (baseline route failed)")
        return rows

    for n_sims in concurrent_counts:
        print(f"\n  {n_sims} concurrent simulation(s) + {n_events_per_sim} events each:")

        adapters: List[GraphHopperAdapter] = []
        for i in range(n_sims):
            try:
                sim_id = f"bench_s4_{n_sims}_{i}"
                adapter = GraphHopperAdapter(
                    graphhopper_url=graphhopper_url,
                    sim_id=sim_id,
                    profile=GRAPHHOPPER_PROFILE,
                )
                speed_factor = max(0.05, 0.5 / (i + 1))
                _load_traffic(sim_id, segment_keys, n_events_per_sim, speed_factor)
                adapters.append(adapter)
            except Exception as exc:
                print(f"    SKIP — cannot create adapter {i}: {exc}")
                for a in adapters:
                    a.close()
                adapters = []
                break

        if not adapters:
            continue

        for adapter in adapters:
            adapter.get_route(START, END)

        per_sim_times: Dict[int, List[float]] = {i: [] for i in range(n_sims)}

        for rep in range(reps):
            barrier = threading.Barrier(n_sims)
            thread_results: List[Optional[float]] = [None] * n_sims

            def _worker(idx: int, adapter: GraphHopperAdapter) -> None:
                barrier.wait()
                t0 = time.perf_counter()
                adapter.get_route(START, END)
                thread_results[idx] = time.perf_counter() - t0

            threads = [
                threading.Thread(target=_worker, args=(i, adapters[i]))
                for i in range(n_sims)
            ]
            wall_t0 = time.perf_counter()
            for t in threads:
                t.start()
            for t in threads:
                t.join()
            wall_elapsed = time.perf_counter() - wall_t0

            for i, t in enumerate(thread_results):
                if t is not None:
                    per_sim_times[i].append(t)

            sim_ms = [f"{(thread_results[i] or 0) * 1000:.1f}" for i in range(n_sims)]
            print(
                f"    rep {rep + 1:>2}/{reps}  wall={wall_elapsed * 1000:>7.1f} ms"
                f"  sim_ms=[{', '.join(sim_ms)}]"
            )

        all_times = [t for ts in per_sim_times.values() for t in ts]
        stats = compute_stats(all_times)
        throughput = n_sims / (stats["mean_ms"] / 1000)
        _print_stats(stats, prefix=f"  n_sims={n_sims} → ")
        print(f"    throughput ≈ {throughput:.1f} route-calls / s")

        for adapter in adapters:
            adapter.close()

        rows.append(
            {
                "scenario": "4_concurrent_with_traffic",
                "traffic_events": n_events_per_sim,
                "concurrent_sims": n_sims,
                "throughput_rps": round(throughput, 2),
                **stats,
            }
        )

    return rows


def _print_stats(stats: Dict, prefix: str = "  ") -> None:
    if not stats:
        return
    print(
        f"{prefix}n={stats['n']}"
        f"  mean={stats['mean_ms']:.1f} ms"
        f"  median={stats['median_ms']:.1f} ms"
        f"  p95={stats['p95_ms']:.1f} ms"
        f"  stdev={stats['stdev_ms']:.1f} ms"
        f"  min={stats['min_ms']:.1f} ms"
        f"  max={stats['max_ms']:.1f} ms"
    )


def print_summary_table(rows: List[Dict]) -> None:
    if not rows:
        return

    headers = ["Scenario", "Events", "Sims", "mean ms", "p95 ms", "max ms", "stdev ms", "RPS"]
    col_w = [30, 7, 5, 9, 9, 9, 9, 8]

    def _row(cells: List[str]) -> str:
        return "  ".join(str(c).ljust(w) for c, w in zip(cells, col_w))

    print("\n" + "=" * 100)
    print("BENCHMARK SUMMARY  —  IKEA Montréal → Concordia SGW")
    print("=" * 100)
    print(_row(headers))
    print("─" * 100)
    for r in rows:
        print(
            _row(
                [
                    r.get("scenario", ""),
                    str(r.get("traffic_events", 0)),
                    str(r.get("concurrent_sims", 1)),
                    f"{r['mean_ms']:.1f}",
                    f"{r['p95_ms']:.1f}",
                    f"{r['max_ms']:.1f}",
                    f"{r['stdev_ms']:.1f}",
                    str(r.get("throughput_rps", "—")),
                ]
            )
        )
    print("=" * 100)


def write_csv(rows: List[Dict], output_path: str) -> None:
    if not rows:
        return
    seen: dict = {}
    for row in rows:
        seen.update(row)
    fieldnames = list(seen.keys())
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    print(f"\nResults written to: {path.resolve()}")


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="VeloSim routing benchmark (GraphHopper, IKEA → Concordia)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("--reps", type=int, default=DEFAULT_REPS, help=f"Timed repetitions per scenario cell (default: {DEFAULT_REPS})")
    p.add_argument(
        "--concurrent",
        type=int,
        nargs="+",
        default=DEFAULT_CONCURRENT,
        metavar="N",
        help=f"Concurrent-sim counts for Scenarios 3 & 4 (default: {DEFAULT_CONCURRENT})",
    )
    p.add_argument(
        "--traffic-events",
        type=int,
        nargs="+",
        default=DEFAULT_TRAFFIC_COUNTS,
        metavar="N",
        help=f"Event counts for Scenario 2 (default: {DEFAULT_TRAFFIC_COUNTS})",
    )
    p.add_argument("--traffic-per-sim", type=int, default=100, metavar="N", help="Traffic events per sim in Scenario 4 (default: 100)")
    p.add_argument("--output", default="scripts/benchmark_outputs/benchmark_graphhopper_results.csv", help="CSV output path")
    p.add_argument("--skip", type=int, nargs="*", default=[], metavar="N", help="Scenario numbers to skip (e.g. --skip 2 4)")
    p.add_argument("--verbose", action="store_true", help="Enable DEBUG logging")
    return p.parse_args()


def main() -> None:
    args = _parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.WARNING,
        format="%(levelname)s %(name)s: %(message)s",
    )

    provider = os.getenv("ROUTING_PROVIDER", "graphhopper").lower()
    graphhopper_url = os.getenv("GRAPHHOPPER_URL")

    print("=" * 70)
    print("VeloSim Routing Benchmark (GraphHopper)")
    print("=" * 70)
    print(f"  Routing provider   : {provider.upper()}")
    print(f"  GraphHopper URL    : {graphhopper_url or '(auto-detect from env / default)'}")
    print(f"  GraphHopper profile: {GRAPHHOPPER_PROFILE}")
    print("  Route              : IKEA Montréal → Concordia SGW")
    print(f"  Repetitions        : {args.reps}")
    print(f"  Concurrent sims    : {args.concurrent}")
    print(f"  Traffic events     : {args.traffic_events}")
    print(f"  Traffic/sim (S4)   : {args.traffic_per_sim}")
    if args.skip:
        print(f"  Skipping           : scenarios {args.skip}")
    print()

    if provider != "graphhopper":
        print(
            "WARNING: ROUTING_PROVIDER is not 'graphhopper'. "
            "This benchmark targets the GraphHopper adapter."
        )

    segment_keys: List[SegmentKey] = []
    if set(args.skip).isdisjoint({2, 4}):
        print("Extracting route segment keys for traffic injection …")
        try:
            segment_keys = extract_segment_keys(graphhopper_url)
            if not segment_keys:
                print(
                    "  WARNING: no segment keys found – "
                    "Scenarios 2 & 4 will run without matched traffic.\n"
                    "  Ensure GraphHopper is running and the route is reachable."
                )
        except Exception as exc:
            print(f"  ERROR: {exc}")
            print("  Scenarios 2 & 4 will be skipped.")
            args.skip = list(set(args.skip) | {2, 4})

    all_rows: List[Dict] = []

    if 1 not in args.skip:
        row = scenario_1_baseline(args.reps, graphhopper_url)
        if row:
            all_rows.append(row)

    if 2 not in args.skip:
        all_rows.extend(
            scenario_2_heavy_traffic(
                args.reps,
                segment_keys,
                args.traffic_events,
                graphhopper_url,
            )
        )

    if 3 not in args.skip:
        all_rows.extend(
            scenario_3_concurrent_no_traffic(
                args.reps,
                args.concurrent,
                graphhopper_url,
            )
        )

    if 4 not in args.skip:
        all_rows.extend(
            scenario_4_concurrent_with_traffic(
                args.reps,
                segment_keys,
                args.concurrent,
                graphhopper_url,
                args.traffic_per_sim,
            )
        )

    if all_rows:
        print_summary_table(all_rows)
        write_csv(all_rows, args.output)
    else:
        print("\nNo results collected — ensure GraphHopper is running and reachable.")
        print("Start with:  npm run graphhopper:up")


if __name__ == "__main__":
    main()
