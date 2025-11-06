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

from sim.behaviour.default.default_TPU_strategy import DefaultTPUStrategy
from pytest import MonkeyPatch


def test_default_tpu_strategy_returns_true_when_random_hits(
    monkeypatch: MonkeyPatch,
) -> None:
    # Force random to hit the 0 case
    monkeypatch.setattr("random.randrange", lambda n: 0)
    strat = DefaultTPUStrategy()
    assert strat.check_for_new_task(None) is True  # type: ignore[arg-type]


def test_default_tpu_strategy_returns_false_when_random_misses(
    monkeypatch: MonkeyPatch,
) -> None:
    # Force random to return a non-zero number
    monkeypatch.setattr("random.randrange", lambda n: 42)
    strat = DefaultTPUStrategy()
    assert strat.check_for_new_task(None) is False  # type: ignore[arg-type]
