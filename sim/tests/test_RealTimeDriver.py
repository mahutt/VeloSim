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

import simpy
import pytest
from typing import List, Any
from sim.core.RealTimeDriver import RealTimeDriver
import sim.core.RealTimeDriver as rtd


# Real time driver depends on real time passing by. Too slow for tests.
# Use fake time to run tests instantly
class MockClock:
    def __init__(self, start: float = 100.0) -> None:
        self.now = float(start)
        self.sleeps: List[float] = []

    def perf_counter(self) -> float:
        return self.now

    def sleep(self, dt: float) -> None:
        if dt and dt > 0:
            self.sleeps.append(dt)
            self.now += dt


@pytest.fixture()
def env() -> simpy.Environment:
    return simpy.Environment()


@pytest.fixture()
def fake_time(monkeypatch: Any) -> MockClock:
    clock = MockClock()
    # replaces the time methods in rtd with the above fakeclock methods
    monkeypatch.setattr(rtd.time, "perf_counter", clock.perf_counter)
    monkeypatch.setattr(rtd.time, "sleep", clock.sleep)
    return clock


def run_env_process(env: simpy.Environment, num_steps: int) -> None:
    def fake_process() -> Any:
        for i in range(num_steps):
            yield env.timeout(1)

    env.process(fake_process())


def test_driver_pause(env: simpy.Environment, fake_time: MockClock) -> None:
    driver = RealTimeDriver(env, real_time_factor=1.0, strict=False)

    driver.running = True

    driver.pause()

    assert driver.running is False


def test_driver_resume(env: simpy.Environment, fake_time: MockClock) -> None:
    driver = RealTimeDriver(env, real_time_factor=1.0, strict=False)

    driver.running = False

    driver.resume()

    assert driver.running is True


def test_callback_called_each_step(
    env: simpy.Environment, fake_time: MockClock
) -> None:
    steps = 0

    def callback() -> None:
        nonlocal steps
        steps += 1

    driver = RealTimeDriver(env, real_time_factor=1.0, strict=False)
    run_env_process(env, 5)
    driver.run_until(until=5, step_callback=callback)

    assert steps == 5  # Callback should have been called 5 times


def test_set_real_time_factor(env: simpy.Environment, fake_time: MockClock) -> None:
    driver = RealTimeDriver(env, real_time_factor=1.0, strict=False)
    driver.set_real_time_factor(1 / 60)

    assert driver.real_time_factor == 1 / 60


def test_strict_true(env: simpy.Environment, fake_time: MockClock) -> None:
    driver = RealTimeDriver(env, real_time_factor=1.0, strict=True)
    run_env_process(env, 5)
    driver.run_until(until=5)
    lag = driver.lag
    assert lag is not None
