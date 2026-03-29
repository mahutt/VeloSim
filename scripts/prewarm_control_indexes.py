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

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from sim.osm.osm_control_index_store import get_osm_control_coordinates


def _resolve_pbf_path(cli_pbf_path: str | None) -> Path | None:
    if cli_pbf_path:
        candidate = Path(cli_pbf_path).expanduser().resolve()
        return candidate if candidate.exists() else None

    for env_key in (
        "OSM_PBF_PATH",
        "TRAFFIC_LIGHT_PBF_PATH",
        "STOP_SIGN_PBF_PATH",
    ):
        env_value = os.getenv(env_key)
        if not env_value:
            continue
        candidate = Path(env_value).expanduser().resolve()
        if candidate.exists():
            return candidate

    repo_root = Path(__file__).resolve().parents[1]
    default_candidates = [
        repo_root / "graphhopper-data" / "montreal-latest.osm.pbf",
        repo_root / "osrm-data" / "montreal.osm.pbf",
    ]
    for candidate in default_candidates:
        if candidate.exists():
            return candidate

    return None


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Precompute stop-sign/traffic-light cache from an OSM PBF"
    )
    parser.add_argument(
        "--pbf",
        type=str,
        default=None,
        help="Path to OSM PBF file. If omitted, uses env vars/default locations.",
    )
    args = parser.parse_args()

    pbf_path = _resolve_pbf_path(args.pbf)
    if pbf_path is None:
        print(
            "ERROR: Could not locate OSM PBF. Provide --pbf or set OSM_PBF_PATH/STOP_SIGN_PBF_PATH/TRAFFIC_LIGHT_PBF_PATH.",
            file=sys.stderr,
        )
        return 1

    # Keep all runtime env keys aligned with the chosen PBF path.
    os.environ["OSM_PBF_PATH"] = str(pbf_path)
    os.environ["STOP_SIGN_PBF_PATH"] = str(pbf_path)
    os.environ["TRAFFIC_LIGHT_PBF_PATH"] = str(pbf_path)

    stop_points = get_osm_control_coordinates(pbf_path, "stop")
    traffic_lights = get_osm_control_coordinates(pbf_path, "traffic_signals")

    cache_file = pbf_path.with_suffix(".control_points_cache.json")
    print(f"PBF: {pbf_path}")
    print(f"Cache file: {cache_file}")
    print(f"Stop signs: {len(stop_points)}")
    print(f"Traffic lights: {len(traffic_lights)}")
    print("Prewarm complete.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
