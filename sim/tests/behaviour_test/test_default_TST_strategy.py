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

from sim.behaviour.default.default_TST_strategy import DefaultTSTStrategy
from sim.entities.battery_swap_task import BatterySwapTask
from sim.entities.driver import Driver
from sim.entities.position import Position
from sim.entities.shift import Shift
from sim.entities.station import Station


def test_default_tst_strategy_returns_default_time() -> None:
    strat = DefaultTSTStrategy()
    assert strat.get_task_servicing_time() == 240


def test_default_tst_strategy_halves_time_for_same_station_followup() -> None:
    station = Station(1, "A", Position([0.0, 0.0]))
    driver = Driver(
        driver_id=1,
        position=station.get_position(),
        shift=Shift(0.0, 24.0 * 60 * 60, None, 0.0),
    )
    driver.service_chain_station_id = station.id
    task = BatterySwapTask(1, station)

    strat = DefaultTSTStrategy()

    assert strat.get_task_servicing_time(driver, task) == 120
