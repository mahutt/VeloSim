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

from unittest.mock import patch

import pytest

from sim.entities.map_payload import MapPayload


class TestMapPayloadRouteRecalculationInterval:
    """Tests for route interval defaults, normalization, and payload resolution."""

    def test_default_route_recalculation_interval_seconds(self) -> None:
        """Default interval should be 30 minutes expressed in seconds."""
        assert MapPayload.default_route_recalculation_interval_seconds() == 1800

    def test_normalize_minutes_rejects_bool_and_uses_default(self) -> None:
        """Boolean input should be rejected and default to 30 minutes."""
        with patch("sim.entities.map_payload.logger.warning") as warning_mock:
            result = MapPayload.normalize_route_recalculation_interval_minutes(True)

        assert result == 30
        warning_mock.assert_called_once()

    def test_normalize_minutes_rejects_non_integer_float(self) -> None:
        """Non-integer float should fallback to default."""
        with patch("sim.entities.map_payload.logger.warning") as warning_mock:
            result = MapPayload.normalize_route_recalculation_interval_minutes(1.5)

        assert result == 30
        warning_mock.assert_called_once()

    def test_normalize_minutes_accepts_integer_float(self) -> None:
        """Whole-number float should be converted to int minutes."""
        assert MapPayload.normalize_route_recalculation_interval_minutes(15.0) == 15

    def test_normalize_minutes_rejects_invalid_type(self) -> None:
        """Non-castable values should fallback to default minutes."""
        with patch("sim.entities.map_payload.logger.warning") as warning_mock:
            result = MapPayload.normalize_route_recalculation_interval_minutes(object())

        assert result == 30
        warning_mock.assert_called_once()

    @pytest.mark.parametrize("raw_value", [0, -1])
    def test_normalize_minutes_rejects_non_positive(self, raw_value: int) -> None:
        """Non-positive minute values should fallback to default."""
        with patch("sim.entities.map_payload.logger.warning") as warning_mock:
            result = MapPayload.normalize_route_recalculation_interval_minutes(
                raw_value
            )

        assert result == 30
        warning_mock.assert_called_once()

    def test_normalize_seconds_rejects_invalid_value(self) -> None:
        """Invalid seconds input should fallback to default seconds."""
        with patch("sim.entities.map_payload.logger.warning") as warning_mock:
            result = MapPayload.normalize_route_recalculation_interval_seconds("bad")

        assert result == 1800
        warning_mock.assert_called_once()

    @pytest.mark.parametrize("raw_value", [0, -30])
    def test_normalize_seconds_rejects_non_positive(self, raw_value: int) -> None:
        """Non-positive second values should fallback to default seconds."""
        with patch("sim.entities.map_payload.logger.warning") as warning_mock:
            result = MapPayload.normalize_route_recalculation_interval_seconds(
                raw_value
            )

        assert result == 1800
        warning_mock.assert_called_once()

    def test_normalize_seconds_accepts_positive_value(self) -> None:
        """Positive second values should be preserved."""
        assert MapPayload.normalize_route_recalculation_interval_seconds(45) == 45

    def test_get_route_recalculation_interval_seconds(self) -> None:
        """Payload should normalize minutes and return interval in seconds."""
        payload = MapPayload(route_recalculation_interval_minutes=2)

        assert payload.get_route_recalculation_interval_seconds() == 120
