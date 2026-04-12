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
from sim.entities.position import Position


class TestPosition:
    @pytest.fixture
    def default_position(self) -> Position:
        return Position([-73.5673, 45.5017])  # [longitude, latitude]

    def test_position_creation(self, default_position: Position) -> None:
        assert default_position.get_position() == [-73.5673, 45.5017]

    def test_position_defaults_to_unoccupied(self) -> None:
        position = Position([-73.5673, 45.5017])
        assert position.occupied is False

    def test_position_can_be_initialized_as_occupied(self) -> None:
        position = Position([-73.5673, 45.5017], occupied=True)
        assert position.occupied is True

    def test_position_equality_and_hash(self) -> None:
        p1 = Position([-73.5673, 45.5017])
        p2 = Position([-73.5673, 45.5017])
        p3 = Position([-73.5674, 45.5017])

        assert p1 == p2
        assert p1 != p3
        assert isinstance(hash(p1), int)

    def test_position_comparison_with_non_position(self) -> None:
        p = Position([-73.5673, 45.5017])
        assert (p == object()) is False
        assert p.close_enough(object()) is False

    def test_close_enough_threshold_behavior(self) -> None:
        base = Position([-73.5673, 45.5017])
        close = Position([-73.5679, 45.5022])
        far = Position([-73.5690, 45.5030])

        assert base.close_enough(close) is True
        assert base.close_enough(far) is False
