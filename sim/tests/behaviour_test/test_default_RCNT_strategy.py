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

import pytest

from sim.behaviour.default.default_RCNT_strategy import DefaultRCNTStrategy
from typing import Any


class _FakeResource:
    def __init__(self, tasks: list[Any]) -> None:
        self._tasks = tasks

    def get_task_list(self) -> list[Any]:
        return self._tasks


def test_default_rcnt_strategy_picks_first_task() -> None:
    t1, t2 = object(), object()
    resource = _FakeResource([t1, t2])
    strat = DefaultRCNTStrategy()

    chosen = strat.select_next_task(resource)  # type: ignore[arg-type]
    assert chosen is t1


def test_default_rcnt_strategy_raises_on_empty_list() -> None:
    resource = _FakeResource([])
    strat = DefaultRCNTStrategy()

    with pytest.raises(IndexError):
        _ = strat.select_next_task(resource)  # type: ignore[arg-type]
