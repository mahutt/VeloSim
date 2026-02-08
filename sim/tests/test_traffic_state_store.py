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

import threading
from typing import Generator

import pytest

from sim.osm.traffic_state_store import traffic_state_store

KEY_A = ((-73.567, 45.501), (-73.568, 45.502))
KEY_B = ((-73.570, 45.505), (-73.571, 45.506))


@pytest.fixture(autouse=True)
def _reset_store() -> Generator[None, None, None]:
    """Reset the singleton store before each test."""
    traffic_state_store._reset()
    yield
    traffic_state_store._reset()


class TestTrafficStateStoreBasic:
    """Basic set / get / clear operations."""

    def test_get_returns_none_when_empty(self) -> None:
        assert traffic_state_store.get("sim-1", KEY_A) is None

    def test_set_and_get(self) -> None:
        traffic_state_store.set("sim-1", KEY_A, 0.5)
        assert traffic_state_store.get("sim-1", KEY_A) == 0.5

    def test_set_overwrites(self) -> None:
        traffic_state_store.set("sim-1", KEY_A, 0.5)
        traffic_state_store.set("sim-1", KEY_A, 0.8)
        assert traffic_state_store.get("sim-1", KEY_A) == 0.8

    def test_clear_edge_removes_key(self) -> None:
        traffic_state_store.set("sim-1", KEY_A, 0.3)
        assert traffic_state_store.clear_edge("sim-1", KEY_A) is True
        assert traffic_state_store.get("sim-1", KEY_A) is None

    def test_clear_edge_returns_false_when_missing(self) -> None:
        assert traffic_state_store.clear_edge("sim-1", KEY_A) is False

    def test_clear_all(self) -> None:
        traffic_state_store.set("sim-1", KEY_A, 0.1)
        traffic_state_store.set("sim-1", KEY_B, 0.2)
        assert traffic_state_store.clear_all("sim-1") is True
        assert traffic_state_store.get("sim-1", KEY_A) is None
        assert traffic_state_store.get("sim-1", KEY_B) is None

    def test_clear_all_returns_false_when_no_sim(self) -> None:
        assert traffic_state_store.clear_all("no-such-sim") is False

    def test_cleanup_sim(self) -> None:
        traffic_state_store.set("sim-1", KEY_A, 0.5)
        traffic_state_store.cleanup_sim("sim-1")
        assert traffic_state_store.get("sim-1", KEY_A) is None

    def test_get_all_for_sim(self) -> None:
        traffic_state_store.set("sim-1", KEY_A, 0.5)
        traffic_state_store.set("sim-1", KEY_B, 0.3)
        snapshot = traffic_state_store.get_all_for_sim("sim-1")
        assert snapshot == {KEY_A: 0.5, KEY_B: 0.3}

    def test_get_all_for_sim_empty(self) -> None:
        assert traffic_state_store.get_all_for_sim("no-sim") == {}


class TestTrafficStateStoreIsolation:
    """Simulations are isolated from each other."""

    def test_different_sims_isolated(self) -> None:
        traffic_state_store.set("sim-1", KEY_A, 0.1)
        traffic_state_store.set("sim-2", KEY_A, 0.9)
        assert traffic_state_store.get("sim-1", KEY_A) == 0.1
        assert traffic_state_store.get("sim-2", KEY_A) == 0.9

    def test_cleanup_only_affects_target_sim(self) -> None:
        traffic_state_store.set("sim-1", KEY_A, 0.1)
        traffic_state_store.set("sim-2", KEY_A, 0.9)
        traffic_state_store.cleanup_sim("sim-1")
        assert traffic_state_store.get("sim-1", KEY_A) is None
        assert traffic_state_store.get("sim-2", KEY_A) == 0.9

    def test_empty_sim_id_works(self) -> None:
        traffic_state_store.set("", KEY_A, 0.5)
        assert traffic_state_store.get("", KEY_A) == 0.5
        traffic_state_store.cleanup_sim("")
        assert traffic_state_store.get("", KEY_A) is None


class TestTrafficStateStoreThreadSafety:
    """Concurrent access does not corrupt state."""

    def test_concurrent_writes(self) -> None:
        errors: list[Exception] = []

        def writer(sim_id: str, factor: float) -> None:
            try:
                for i in range(100):
                    key = ((float(i), 0.0), (float(i + 1), 0.0))
                    traffic_state_store.set(sim_id, key, factor)
            except Exception as exc:
                errors.append(exc)

        threads = [
            threading.Thread(target=writer, args=(f"sim-{n}", n * 0.1))
            for n in range(5)
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert errors == []
        # Each sim wrote 100 keys
        for n in range(5):
            snapshot = traffic_state_store.get_all_for_sim(f"sim-{n}")
            assert len(snapshot) == 100
