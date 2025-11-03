import pytest

from sim.behaviour.default.default_TPU_strategy import DefaultTPUStrategy


def test_default_tpu_strategy_returns_true_when_random_hits(monkeypatch):
    # Force random to hit the 0 case
    monkeypatch.setattr("random.randrange", lambda n: 0)
    strat = DefaultTPUStrategy()
    assert strat.check_for_new_task() is True


def test_default_tpu_strategy_returns_false_when_random_misses(monkeypatch):
    # Force random to return a non-zero number
    monkeypatch.setattr("random.randrange", lambda n: 42)
    strat = DefaultTPUStrategy()
    assert strat.check_for_new_task() is False
