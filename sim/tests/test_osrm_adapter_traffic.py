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

from typing import Generator
from unittest.mock import patch

import pytest

from sim.entities.position import Position
from sim.map.routing_provider import EdgeIdentifier, TrafficUpdate
from sim.osm.osrm_adapter import OSRMAdapter
from sim.osm.traffic_state_store import traffic_state_store


@pytest.fixture(autouse=True)
def _reset_store() -> Generator[None, None, None]:
    """Reset the singleton store before each test."""
    traffic_state_store._reset()
    yield
    traffic_state_store._reset()


def _make_adapter(sim_id: str = "test-sim") -> OSRMAdapter:
    """Create an OSRMAdapter with a mocked OSRMConnection."""
    with patch("sim.osm.osrm_adapter.OSRMConnection"):
        return OSRMAdapter(sim_id=sim_id)


def _edge(
    start: tuple[float, float] = (-73.567, 45.501),
    end: tuple[float, float] = (-73.568, 45.502),
) -> EdgeIdentifier:
    return EdgeIdentifier(
        start_position=Position(list(start)),
        end_position=Position(list(end)),
    )


def _update(
    factor: float = 0.5,
    start: tuple[float, float] = (-73.567, 45.501),
    end: tuple[float, float] = (-73.568, 45.502),
) -> TrafficUpdate:
    return TrafficUpdate(edge=_edge(start, end), speed_factor=factor)


class TestOSRMAdapterTrafficCRUD:
    """OSRMAdapter traffic CRUD delegates to TrafficStateStore."""

    def test_set_edge_traffic(self) -> None:
        adapter = _make_adapter()
        assert adapter.set_edge_traffic(_update(0.3)) is True
        assert traffic_state_store.get("test-sim", _edge().segment_key) == 0.3

    def test_set_edges_traffic(self) -> None:
        adapter = _make_adapter()
        updates = [
            _update(0.1, (-73.0, 45.0), (-73.1, 45.1)),
            _update(0.9, (-73.2, 45.2), (-73.3, 45.3)),
        ]
        assert adapter.set_edges_traffic(updates) is True

        e1 = _edge((-73.0, 45.0), (-73.1, 45.1))
        e2 = _edge((-73.2, 45.2), (-73.3, 45.3))
        assert traffic_state_store.get("test-sim", e1.segment_key) == 0.1
        assert traffic_state_store.get("test-sim", e2.segment_key) == 0.9

    def test_get_edge_traffic(self) -> None:
        adapter = _make_adapter()
        assert adapter.get_edge_traffic(_edge()) is None
        adapter.set_edge_traffic(_update(0.7))
        assert adapter.get_edge_traffic(_edge()) == 0.7

    def test_clear_edge_traffic(self) -> None:
        adapter = _make_adapter()
        adapter.set_edge_traffic(_update(0.4))
        assert adapter.clear_edge_traffic(_edge()) is True
        assert adapter.get_edge_traffic(_edge()) is None

    def test_clear_edge_traffic_missing(self) -> None:
        adapter = _make_adapter()
        assert adapter.clear_edge_traffic(_edge()) is False

    def test_clear_all_traffic(self) -> None:
        adapter = _make_adapter()
        adapter.set_edge_traffic(_update(0.2))
        assert adapter.clear_all_traffic() is True
        assert adapter.get_edge_traffic(_edge()) is None

    def test_close_cleans_up_traffic_state(self) -> None:
        adapter = _make_adapter()
        adapter.set_edge_traffic(_update(0.6))
        adapter.close()
        assert traffic_state_store.get("test-sim", _edge().segment_key) is None


class TestOSRMAdapterSimIsolation:
    """Different sim_id adapters are isolated."""

    def test_two_adapters_isolated(self) -> None:
        a1 = _make_adapter("sim-A")
        a2 = _make_adapter("sim-B")

        a1.set_edge_traffic(_update(0.1))
        a2.set_edge_traffic(_update(0.9))

        assert a1.get_edge_traffic(_edge()) == 0.1
        assert a2.get_edge_traffic(_edge()) == 0.9

    def test_close_only_cleans_own_sim(self) -> None:
        a1 = _make_adapter("sim-A")
        a2 = _make_adapter("sim-B")

        a1.set_edge_traffic(_update(0.1))
        a2.set_edge_traffic(_update(0.9))

        a1.close()
        assert traffic_state_store.get("sim-A", _edge().segment_key) is None
        assert traffic_state_store.get("sim-B", _edge().segment_key) == 0.9

    def test_empty_sim_id(self) -> None:
        adapter = _make_adapter("")
        adapter.set_edge_traffic(_update(0.5))
        assert adapter.get_edge_traffic(_edge()) == 0.5
