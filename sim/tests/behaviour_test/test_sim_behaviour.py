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

from sim.behaviour.sim_behaviour import SimBehaviour
from sim.entities.station import Station


class _StubTPU:
    def __init__(self) -> None:
        self.calls = 0
        self.return_value = False

    def check_for_new_task(self, station: Station) -> bool:
        self.calls += 1
        return self.return_value


class _StubRCNT:
    pass


def test_sim_behaviour_setters_assign_strategies() -> None:
    beh = SimBehaviour()
    tpu = _StubTPU()
    rcnt = _StubRCNT()

    beh.set_TPU_strategy(tpu)  # type: ignore[arg-type]
    beh.set_RCNT_strategy(rcnt)  # type: ignore[arg-type]

    assert beh.TPU_strategy is tpu  # type: ignore[comparison-overlap]
    assert beh.RCNT_strategy is rcnt  # type: ignore[comparison-overlap]
