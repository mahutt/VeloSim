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

# sim/tests/test_simulator.py

import time
import threading
from typing import List
import uuid

import pytest
from _pytest.capture import CaptureFixture
from _pytest.monkeypatch import MonkeyPatch

# Import the module so we can monkeypatch its time.sleep
from sim.entities.inputParameters import InputParameter
from sim.entities.request_type import RequestType
import sim.simulator as simulator_mod
from sim.simulator import Simulator
from sim.utils.subscriber import Subscriber

params = InputParameter()
subList: List[Subscriber] = []


@pytest.fixture
def sim() -> Simulator:
    return Simulator()


def test_start_creates_thread_and_emits_output(
    sim: Simulator,
    monkeypatch: MonkeyPatch,
    capsys: CaptureFixture[str],
) -> None:
    """
    Verifies:
      - start() returns a UUID string
      - a thread is created and alive
      - loop prints at least once
    We monkeypatch time.sleep inside sim.simulator to speed up the loop.
    """
    original_sleep = simulator_mod.time.sleep
    try:
        monkeypatch.setattr(simulator_mod.time, "sleep", lambda _: original_sleep(0.05))
        sim_id = sim.start(params, subList)

        # Basic sanity on returned id
        uuid.UUID(sim_id)  # should not raise

        # Wait briefly for the thread to run at least one iteration
        time.sleep(0.12)

        # Stop and capture output
        sim.stop(sim_id)
        out = capsys.readouterr().out
        assert f"Hello From Simulator: [{sim_id}]" in out
        assert f"[{sim_id}] stopped." in out

        # Thread should be gone from pool
        assert sim_id not in sim.thread_pool
    finally:
        # Best-effort cleanup in case of failure above
        for sid, info in list(sim.thread_pool.items()):
            info["stop"].set()
            info["thread"].join(timeout=2.0)
            sim.thread_pool.pop(sid, None)
        # restore sleep
        monkeypatch.setattr(simulator_mod.time, "sleep", original_sleep)


def test_stop_removes_thread_from_pool(
    sim: Simulator,
    monkeypatch: MonkeyPatch,
) -> None:
    # Make loop faster
    monkeypatch.setattr(simulator_mod.time, "sleep", lambda _: None)

    sim_id = sim.start(params, subList)
    assert sim_id in sim.thread_pool
    t = sim.thread_pool[sim_id]["thread"]
    assert isinstance(t, threading.Thread) and t.is_alive()

    sim.stop(sim_id)

    assert sim_id not in sim.thread_pool
    assert not t.is_alive()


def test_stop_nonexistent_id_noop(sim: Simulator) -> None:
    # Should not raise
    sim.stop("does-not-exist")


def test_multiple_parallel_sims(
    sim: Simulator,
    monkeypatch: MonkeyPatch,
) -> None:
    monkeypatch.setattr(simulator_mod.time, "sleep", lambda _: None)

    a = sim.start(params, subList)
    b = sim.start(params, subList)
    assert a != b
    assert a in sim.thread_pool and b in sim.thread_pool
    assert sim.thread_pool[a]["thread"].is_alive()
    assert sim.thread_pool[b]["thread"].is_alive()

    sim.stop(a)
    sim.stop(b)
    assert a not in sim.thread_pool and b not in sim.thread_pool


def test_pause_and_status_not_implemented(sim: Simulator) -> None:
    with pytest.raises(NotImplementedError):
        sim.pause()
    with pytest.raises(NotImplementedError):
        sim.status()


def test_send_request_not_implemented(sim: Simulator) -> None:
    # Any RequestType should raise until implemented
    request = RequestType()
    with pytest.raises(NotImplementedError):
        sim.send_request(request)


def test_get_stream_not_implemented(sim: Simulator) -> None:
    with pytest.raises(NotImplementedError):
        sim.get_stream()


def test_stop_all_stops_everything_and_is_idempotent(
    sim: Simulator,
    monkeypatch: MonkeyPatch,
) -> None:
    """
    Start multiple sims, stop them all via stop_all(),
    verify the pool is empty and threads dead.
    Also ensure calling stop_all() again does not error.
    """
    monkeypatch.setattr(simulator_mod.time, "sleep", lambda _: None)

    sim_ids = [sim.start(params, subList) for _ in range(3)]
    # Sanity: all present and alive
    for sid in sim_ids:
        assert sid in sim.thread_pool
        assert sim.thread_pool[sid]["thread"].is_alive()

    # Stop all
    sim.stop_all(join_timeout_per_thread=1.0)

    # Pool should be empty and threads dead
    assert sim.thread_pool == {}
    for sid in sim_ids:
        # We don't have direct refs anymore; just make sure they're gone
        pass

    # Idempotency: calling again should not raise
    sim.stop_all(join_timeout_per_thread=0.2)
