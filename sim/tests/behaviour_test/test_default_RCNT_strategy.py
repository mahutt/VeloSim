import pytest

from sim.behaviour.default.defualt_RCNT_strategy import DefaultRCNTStrategy


class _FakeResource:
    def __init__(self, tasks):
        self._tasks = tasks

    def get_task_list(self):
        return self._tasks


def test_default_rcnt_strategy_picks_first_task():
    t1, t2 = object(), object()
    resource = _FakeResource([t1, t2])
    strat = DefaultRCNTStrategy()

    chosen = strat.select_next_task(resource)
    assert chosen is t1


def test_default_rcnt_strategy_raises_on_empty_list():
    resource = _FakeResource([])
    strat = DefaultRCNTStrategy()

    with pytest.raises(IndexError):
        _ = strat.select_next_task(resource)
