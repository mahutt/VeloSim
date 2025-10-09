import simpy
import pytest
from typing import List, Any
from sim.RealTimeDriver import RealTimeDriver
import sim.RealTimeDriver as rtd

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

@pytest.fixture()
def realTimeDriver(env: simpy.Environment) -> RealTimeDriver:
    return RealTimeDriver(simEnv=env)
    


