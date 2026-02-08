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
from typing import Dict, Optional

from sim.map.routing_provider import SegmentKey


class TrafficStateStore:
    """Thread-safe in-memory traffic state store, keyed by simulation ID.

    Each simulation gets its own isolated dict of SegmentKey -> speed_factor.
    All methods acquire a lock so concurrent simulations (separate threads)
    can read/write safely.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._store: Dict[str, Dict[SegmentKey, float]] = {}

    def set(self, sim_id: str, key: SegmentKey, factor: float) -> None:
        """Set the speed factor for an edge in a simulation.

        Args:
            sim_id: Simulation identifier (None for default partition).
            key: Geometry-based segment key.
            factor: Speed multiplier (0.0-1.0).

        Returns:
            None
        """
        with self._lock:
            if sim_id not in self._store:
                self._store[sim_id] = {}
            self._store[sim_id][key] = factor

    def get(self, sim_id: str, key: SegmentKey) -> Optional[float]:
        """Get the speed factor for an edge, or None if not set.

        Args:
            sim_id: Simulation identifier.
            key: Geometry-based segment key.

        Returns:
            The speed factor, or None if not set.
        """
        with self._lock:
            sim_data = self._store.get(sim_id)
            if sim_data is None:
                return None
            return sim_data.get(key)

    def clear_edge(self, sim_id: str, key: SegmentKey) -> bool:
        """Remove a single edge's traffic state.

        Args:
            sim_id: Simulation identifier.
            key: Geometry-based segment key.

        Returns:
            True if the edge existed and was removed, False otherwise.
        """
        with self._lock:
            sim_data = self._store.get(sim_id)
            if sim_data is None:
                return False
            removed = key in sim_data
            sim_data.pop(key, None)
            return removed

    def clear_all(self, sim_id: str) -> bool:
        """Remove all traffic state for a simulation.

        Args:
            sim_id: Simulation identifier.

        Returns:
            True if the simulation had state to clear, False otherwise.
        """
        with self._lock:
            if sim_id in self._store:
                self._store[sim_id].clear()
                return True
            return False

    def cleanup_sim(self, sim_id: str) -> None:
        """Remove a simulation's entry entirely (called on adapter close).

        Args:
            sim_id: Simulation identifier.

        Returns:
            None
        """
        with self._lock:
            self._store.pop(sim_id, None)

    def get_all_for_sim(self, sim_id: str) -> Dict[SegmentKey, float]:
        """Return a snapshot of all traffic state for a simulation.

        Args:
            sim_id: Simulation identifier.

        Returns:
            Dict mapping SegmentKey to speed factor.
        """
        with self._lock:
            sim_data = self._store.get(sim_id)
            if sim_data is None:
                return {}
            return dict(sim_data)

    def _reset(self) -> None:
        """Clear all state. For test teardown only.

        Returns:
            None
        """
        with self._lock:
            self._store.clear()


traffic_state_store = TrafficStateStore()
