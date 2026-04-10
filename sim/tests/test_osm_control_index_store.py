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

import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from sim.osm.osm_control_index_store import ControlKind, OSMControlIndexStore


def test_get_control_coordinates_uses_valid_disk_cache(tmp_path: Path) -> None:
    pbf_path = tmp_path / "city.osm.pbf"
    pbf_path.write_bytes(b"pbf")

    stat = pbf_path.stat()
    cache_file = pbf_path.with_suffix(".control_points_cache.json")
    cache_file.write_text(
        json.dumps(
            {
                "pbf_path": str(pbf_path.resolve()),
                "pbf_mtime_ns": stat.st_mtime_ns,
                "pbf_size": stat.st_size,
                "stop": [[-73.57, 45.5]],
                "traffic_signals": [[-73.58, 45.51]],
            }
        ),
        encoding="utf-8",
    )

    store = OSMControlIndexStore()

    def _unexpected_load(
        pbf_path: Path,
    ) -> dict[ControlKind, list[list[float]]]:
        del pbf_path
        raise AssertionError("PBF loader should not run when disk cache is valid")

    store._load_from_pbf = _unexpected_load  # type: ignore[method-assign]

    result = store.get_control_coordinates(pbf_path, "stop")

    assert result == [[-73.57, 45.5]]


def test_get_control_coordinates_rebuilds_stale_cache(tmp_path: Path) -> None:
    pbf_path = tmp_path / "city.osm.pbf"
    pbf_path.write_bytes(b"pbf")

    cache_file = pbf_path.with_suffix(".control_points_cache.json")
    cache_file.write_text(
        json.dumps(
            {
                "pbf_path": str(pbf_path.resolve()),
                "pbf_mtime_ns": 0,
                "pbf_size": 0,
                "stop": [],
                "traffic_signals": [],
            }
        ),
        encoding="utf-8",
    )

    store = OSMControlIndexStore()
    loader_calls: list[Path] = []

    def _fake_load(pbf_path: Path) -> dict[ControlKind, list[list[float]]]:
        loader_calls.append(pbf_path)
        return {
            "stop": [[-73.571, 45.501]],
            "traffic_signals": [[-73.572, 45.502]],
        }

    store._load_from_pbf = _fake_load  # type: ignore[method-assign]

    result = store.get_control_coordinates(pbf_path, "traffic_signals")

    assert result == [[-73.572, 45.502]]
    assert loader_calls == [pbf_path.resolve()]

    payload = json.loads(cache_file.read_text(encoding="utf-8"))
    assert payload["stop"] == [[-73.571, 45.501]]
    assert payload["traffic_signals"] == [[-73.572, 45.502]]


def test_load_from_pbf_extracts_only_supported_valid_nodes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    class _FakeLocation:
        def __init__(self, lon: float, lat: float, is_valid: bool) -> None:
            self.lon = lon
            self.lat = lat
            self._is_valid = is_valid

        def valid(self) -> bool:
            return self._is_valid

    class _FakeNode:
        def __init__(
            self, highway: str, lon: float, lat: float, is_valid: bool
        ) -> None:
            self.tags = {"highway": highway}
            self.location = _FakeLocation(lon, lat, is_valid)

    class _FakeSimpleHandler:
        def node(self, _: _FakeNode) -> None:
            """Placeholder; overridden by _ControlHandler in the SUT."""

        def apply_file(self, _: str) -> None:
            nodes = [
                _FakeNode("stop", -73.57, 45.5, True),
                _FakeNode("traffic_signals", -73.58, 45.51, True),
                _FakeNode("traffic_signals", -73.58, 45.51, True),
                _FakeNode("stop", -73.59, 45.52, False),
                _FakeNode("crossing", -73.6, 45.53, True),
            ]
            for node in nodes:
                self.node(node)

    fake_osmium = SimpleNamespace(
        SimpleHandler=_FakeSimpleHandler,
        osm=SimpleNamespace(Node=_FakeNode),
    )

    monkeypatch.setitem(sys.modules, "osmium", fake_osmium)

    pbf_path = tmp_path / "city.osm.pbf"
    pbf_path.write_bytes(b"pbf")

    store = OSMControlIndexStore()
    result = store._load_from_pbf(pbf_path)

    assert set(tuple(coord) for coord in result["stop"]) == {(-73.57, 45.5)}
    assert set(tuple(coord) for coord in result["traffic_signals"]) == {(-73.58, 45.51)}
