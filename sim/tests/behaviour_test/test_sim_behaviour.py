import simpy

from sim.behaviour.sim_behaviour import SimBehaviour
from sim.entities.station import Station
from sim.entities.position import Position


class _StubTPU:
    def __init__(self):
        self.calls = 0
        self.return_value = False

    def check_for_new_task(self):
        self.calls += 1
        return self.return_value


class _StubRCNT:
    pass


def test_sim_behaviour_setters_assign_strategies():
    beh = SimBehaviour()
    tpu = _StubTPU()
    rcnt = _StubRCNT()

    beh.set_TPU_strategy(tpu)
    beh.set_RCNT_strategy(rcnt)  # type: ignore[arg-type]

    assert beh.TPU_strategy is tpu
    assert beh.RCNT_strategy is rcnt


def test_station_uses_tpu_strategy_in_run_loop():
    env = simpy.Environment()
    station = Station(env, station_id=1, name="S1", position=Position([0.0, 0.0]))

    # Set up behaviour with a TPU strategy that returns True once
    beh = SimBehaviour()
    tpu = _StubTPU()
    tpu.return_value = True
    beh.set_TPU_strategy(tpu)
    station.set_behaviour(beh)

    # Run long enough for the station to call check_for_new_task once
    env.run(until=2)

    # The TPU strategy should have been invoked
    assert tpu.calls >= 1
    # If it returned True, station should have created a pop-up task
    assert len(station.pop_up_tasks) == 1
    assert station.get_task_count() >= 1
