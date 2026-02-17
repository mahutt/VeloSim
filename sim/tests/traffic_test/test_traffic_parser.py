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

import os
import tempfile

import pytest

from sim.entities.map_payload import TrafficConfig
from sim.entities.traffic_event import TrafficEvent
from sim.entities.traffic_event_state import TrafficEventState
from sim.traffic.traffic_parser import TrafficParser, TrafficParseError


# =============================================================================
# TrafficEventState Tests
# =============================================================================


class TestTrafficEventState:
    """Tests for TrafficEventState enum."""

    def test_all_states_exist(self) -> None:
        assert TrafficEventState.PENDING.value == 0
        assert TrafficEventState.TRIGGERED.value == 1
        assert TrafficEventState.APPLIED.value == 2
        assert TrafficEventState.EXPIRED.value == 3
        assert TrafficEventState.DONE.value == 4

    def test_str_pending(self) -> None:
        assert str(TrafficEventState.PENDING) == "pending"

    def test_str_triggered(self) -> None:
        assert str(TrafficEventState.TRIGGERED) == "triggered"

    def test_str_applied(self) -> None:
        assert str(TrafficEventState.APPLIED) == "applied"

    def test_str_expired(self) -> None:
        assert str(TrafficEventState.EXPIRED) == "expired"

    def test_str_done(self) -> None:
        assert str(TrafficEventState.DONE) == "done"

    def test_state_count(self) -> None:
        assert len(TrafficEventState) == 5


# =============================================================================
# TrafficEvent Tests
# =============================================================================


class TestTrafficEvent:
    """Tests for TrafficEvent dataclass."""

    def test_default_state_is_pending(self) -> None:
        event = TrafficEvent(
            event_type="local_traffic",
            tick_start=100,
            segment_key=((-73.5673, 45.5017), (-73.5680, 45.5020)),
            duration=50,
            weight=0.5,
        )
        assert event.state == TrafficEventState.PENDING

    def test_name_defaults_to_none(self) -> None:
        event = TrafficEvent(
            event_type="local_traffic",
            tick_start=100,
            segment_key=((-73.5673, 45.5017), (-73.5680, 45.5020)),
            duration=50,
            weight=0.5,
        )
        assert event.name is None

    def test_all_fields_set(self) -> None:
        key = ((-73.5673, 45.5017), (-73.5680, 45.5020))
        event = TrafficEvent(
            event_type="local_traffic",
            tick_start=100,
            segment_key=key,
            duration=50,
            weight=0.3,
            name="rush_hour",
        )
        assert event.event_type == "local_traffic"
        assert event.tick_start == 100
        assert event.segment_key == key
        assert event.duration == 50
        assert event.weight == 0.3
        assert event.name == "rush_hour"
        assert event.state == TrafficEventState.PENDING

    def test_state_can_be_overridden(self) -> None:
        event = TrafficEvent(
            event_type="local_traffic",
            tick_start=100,
            segment_key=((-73.5673, 45.5017), (-73.5680, 45.5020)),
            duration=50,
            weight=0.5,
            state=TrafficEventState.TRIGGERED,
        )
        assert event.state == TrafficEventState.TRIGGERED


# =============================================================================
# TrafficParser Tests
# =============================================================================


class TestTrafficParser:
    """Tests for TrafficParser CSV parsing."""

    @staticmethod
    def _write_csv(content: str) -> str:
        """Helper to write CSV content to a temp file, returns path."""
        fd, path = tempfile.mkstemp(suffix=".csv")
        with os.fdopen(fd, "w") as f:
            f.write(content)
        return path

    def test_parse_valid_csv(self) -> None:
        csv_content = (
            "TYPE,start_time,segment_key,name,duration,weight\n"
            'local_traffic,"08:05","((-73.5673,45.5017),(-73.5680,45.5020))",'
            "rush_hour,50,0.3\n"
            'local_traffic,"09:00","((-73.5700,45.5100),(-73.5710,45.5110))",'
            ",30,0.8\n"
        )
        path = self._write_csv(csv_content)
        traffic_config = TrafficConfig(
            traffic_path=path, sim_start_time="day1:08:00", sim_end_time="day1:12:00"
        )
        try:
            parser = TrafficParser(traffic_config)
            events = parser.parse()
            assert len(events) == 2

            assert events[0].event_type == "local_traffic"
            assert events[0].tick_start == 300
            assert events[0].name == "rush_hour"
            assert events[0].duration == 50
            assert events[0].weight == 0.3
            assert events[0].state == TrafficEventState.PENDING

            assert events[1].tick_start == 3600
            assert events[1].name is None
            assert events[1].duration == 30
            assert events[1].weight == 0.8
            assert events[1].state == TrafficEventState.PENDING
        finally:
            os.unlink(path)

    def test_parse_single_row(self) -> None:
        csv_content = (
            "TYPE,start_time,segment_key,name,duration,weight\n"
            'local_traffic,"08:00","((-73.5,45.5),(-73.6,45.6))",start_event,10,0.5\n'
        )
        path = self._write_csv(csv_content)
        traffic_config = TrafficConfig(
            traffic_path=path, sim_start_time="day1:08:00", sim_end_time="day1:12:00"
        )
        try:
            parser = TrafficParser(traffic_config)
            events = parser.parse()
            assert len(events) == 1
            assert events[0].tick_start == 0
            assert events[0].name == "start_event"
            assert events[0].weight == 0.5
        finally:
            os.unlink(path)

    def test_parse_header_only_returns_empty(self) -> None:
        csv_content = "TYPE,start_time,segment_key,name,duration,weight\n"
        path = self._write_csv(csv_content)
        traffic_config = TrafficConfig(
            traffic_path=path, sim_start_time="day1:08:00", sim_end_time="day1:12:00"
        )
        try:
            parser = TrafficParser(traffic_config)
            events = parser.parse()
            assert len(events) == 0
        finally:
            os.unlink(path)

    def test_file_not_found(self) -> None:
        traffic_config = TrafficConfig(
            traffic_path="/nonexistent/path/traffic.csv",
            sim_start_time="day1:08:00",
            sim_end_time="day1:12:00",
        )
        with pytest.raises(FileNotFoundError):
            TrafficParser(traffic_config)

    def test_empty_csv_file(self) -> None:
        csv_content = ""
        path = self._write_csv(csv_content)
        traffic_config = TrafficConfig(
            traffic_path=path, sim_start_time="day1:08:00", sim_end_time="day1:12:00"
        )
        try:
            parser = TrafficParser(traffic_config)
            with pytest.raises(TrafficParseError, match="empty"):
                parser.parse()
        finally:
            os.unlink(path)

    def test_missing_required_columns(self) -> None:
        csv_content = "TYPE,start_time\n" 'local_traffic,"08:00"\n'
        path = self._write_csv(csv_content)
        traffic_config = TrafficConfig(
            traffic_path=path, sim_start_time="day1:08:00", sim_end_time="day1:12:00"
        )
        try:
            parser = TrafficParser(traffic_config)
            with pytest.raises(TrafficParseError, match="Missing required columns"):
                parser.parse()
        finally:
            os.unlink(path)

    def test_unsupported_type(self) -> None:
        csv_content = (
            "TYPE,start_time,segment_key,name,duration,weight\n"
            'global_traffic,"08:00","((-73.5,45.5),(-73.6,45.6))",test,50,0.5\n'
        )
        path = self._write_csv(csv_content)
        traffic_config = TrafficConfig(
            traffic_path=path, sim_start_time="day1:08:00", sim_end_time="day1:12:00"
        )
        try:
            parser = TrafficParser(traffic_config)
            with pytest.raises(TrafficParseError, match="Unsupported TYPE"):
                parser.parse()
        finally:
            os.unlink(path)

    def test_empty_type(self) -> None:
        csv_content = (
            "TYPE,start_time,segment_key,name,duration,weight\n"
            ',"08:00","((-73.5,45.5),(-73.6,45.6))",test,50,0.5\n'
        )
        path = self._write_csv(csv_content)
        traffic_config = TrafficConfig(
            traffic_path=path, sim_start_time="day1:08:00", sim_end_time="day1:12:00"
        )
        try:
            parser = TrafficParser(traffic_config)
            with pytest.raises(TrafficParseError, match="TYPE column is empty"):
                parser.parse()
        finally:
            os.unlink(path)

    def test_invalid_start_time_empty(self) -> None:
        csv_content = (
            "TYPE,start_time,segment_key,name,duration,weight\n"
            'local_traffic,,"((-73.5,45.5),(-73.6,45.6))",test,50,0.5\n'
        )
        path = self._write_csv(csv_content)
        traffic_config = TrafficConfig(
            traffic_path=path, sim_start_time="day1:08:00", sim_end_time="day1:12:00"
        )
        try:
            parser = TrafficParser(traffic_config)
            with pytest.raises(TrafficParseError, match="start_time is empty"):
                parser.parse()
        finally:
            os.unlink(path)

    def test_invalid_start_time_format(self) -> None:
        csv_content = (
            "TYPE,start_time,segment_key,name,duration,weight\n"
            'local_traffic,"day1:08:00","((-73.5,45.5),(-73.6,45.6))",test,50,0.5\n'
        )
        path = self._write_csv(csv_content)
        traffic_config = TrafficConfig(
            traffic_path=path, sim_start_time="day1:08:00", sim_end_time="day1:12:00"
        )
        try:
            parser = TrafficParser(traffic_config)
            with pytest.raises(TrafficParseError):
                parser.parse()
        finally:
            os.unlink(path)

    def test_invalid_segment_key_format(self) -> None:
        csv_content = (
            "TYPE,start_time,segment_key,name,duration,weight\n"
            'local_traffic,"08:00",not_a_tuple,test,50,0.5\n'
        )
        path = self._write_csv(csv_content)
        traffic_config = TrafficConfig(
            traffic_path=path, sim_start_time="day1:08:00", sim_end_time="day1:12:00"
        )
        try:
            parser = TrafficParser(traffic_config)
            with pytest.raises(TrafficParseError, match="Invalid segment_key"):
                parser.parse()
        finally:
            os.unlink(path)

    def test_segment_key_wrong_structure(self) -> None:
        csv_content = (
            "TYPE,start_time,segment_key,name,duration,weight\n"
            'local_traffic,"08:00","(1,2,3)",test,50,0.5\n'
        )
        path = self._write_csv(csv_content)
        traffic_config = TrafficConfig(
            traffic_path=path, sim_start_time="day1:08:00", sim_end_time="day1:12:00"
        )
        try:
            parser = TrafficParser(traffic_config)
            with pytest.raises(TrafficParseError, match="segment_key must be"):
                parser.parse()
        finally:
            os.unlink(path)

    def test_empty_segment_key(self) -> None:
        csv_content = (
            "TYPE,start_time,segment_key,name,duration,weight\n"
            'local_traffic,"08:00",,test,50,0.5\n'
        )
        path = self._write_csv(csv_content)
        traffic_config = TrafficConfig(
            traffic_path=path, sim_start_time="day1:08:00", sim_end_time="day1:12:00"
        )
        try:
            parser = TrafficParser(traffic_config)
            with pytest.raises(TrafficParseError, match="segment_key is empty"):
                parser.parse()
        finally:
            os.unlink(path)

    def test_zero_duration(self) -> None:
        csv_content = (
            "TYPE,start_time,segment_key,name,duration,weight\n"
            'local_traffic,"08:00","((-73.5,45.5),(-73.6,45.6))",test,0,0.5\n'
        )
        path = self._write_csv(csv_content)
        traffic_config = TrafficConfig(
            traffic_path=path, sim_start_time="day1:08:00", sim_end_time="day1:12:00"
        )
        try:
            parser = TrafficParser(traffic_config)
            with pytest.raises(TrafficParseError, match="duration must be positive"):
                parser.parse()
        finally:
            os.unlink(path)

    def test_negative_duration(self) -> None:
        csv_content = (
            "TYPE,start_time,segment_key,name,duration,weight\n"
            'local_traffic,"08:00","((-73.5,45.5),(-73.6,45.6))",test,-10,0.5\n'
        )
        path = self._write_csv(csv_content)
        traffic_config = TrafficConfig(
            traffic_path=path, sim_start_time="day1:08:00", sim_end_time="day1:12:00"
        )
        try:
            parser = TrafficParser(traffic_config)
            with pytest.raises(TrafficParseError, match="duration must be positive"):
                parser.parse()
        finally:
            os.unlink(path)

    def test_invalid_duration_not_integer(self) -> None:
        csv_content = (
            "TYPE,start_time,segment_key,name,duration,weight\n"
            'local_traffic,"08:00","((-73.5,45.5),(-73.6,45.6))",test,abc,0.5\n'
        )
        path = self._write_csv(csv_content)
        traffic_config = TrafficConfig(
            traffic_path=path, sim_start_time="day1:08:00", sim_end_time="day1:12:00"
        )
        try:
            parser = TrafficParser(traffic_config)
            with pytest.raises(TrafficParseError, match="duration must be an integer"):
                parser.parse()
        finally:
            os.unlink(path)

    def test_segment_key_parsed_as_correct_type(self) -> None:
        csv_content = (
            "TYPE,start_time,segment_key,name,duration,weight\n"
            'local_traffic,"08:00","((-73.5673,45.5017),(-73.5680,45.5020))"'
            ",test,50,0.5\n"
        )
        path = self._write_csv(csv_content)
        traffic_config = TrafficConfig(
            traffic_path=path, sim_start_time="day1:08:00", sim_end_time="day1:12:00"
        )
        try:
            parser = TrafficParser(traffic_config)
            events = parser.parse()
            key = events[0].segment_key
            assert key == ((-73.5673, 45.5017), (-73.5680, 45.5020))
            assert isinstance(key, tuple)
            assert isinstance(key[0], tuple)
            assert isinstance(key[1], tuple)
            assert len(key) == 2
            assert len(key[0]) == 2
            assert len(key[1]) == 2
        finally:
            os.unlink(path)

    def test_multiple_errors_aggregated(self) -> None:
        csv_content = (
            "TYPE,start_time,segment_key,name,duration,weight\n"
            'local_traffic,,"((-73.5,45.5),(-73.6,45.6))",test,50,0.5\n'
            'local_traffic,"08:00","((-73.5,45.5),(-73.6,45.6))",test,-5,0.5\n'
        )
        path = self._write_csv(csv_content)
        traffic_config = TrafficConfig(
            traffic_path=path, sim_start_time="day1:08:00", sim_end_time="day1:12:00"
        )
        try:
            parser = TrafficParser(traffic_config)
            with pytest.raises(TrafficParseError) as exc_info:
                parser.parse()
            assert len(exc_info.value.errors) == 2
            assert "Row 2" in exc_info.value.errors[0]
            assert "Row 3" in exc_info.value.errors[1]
        finally:
            os.unlink(path)

    def test_weight_out_of_range_high(self) -> None:
        csv_content = (
            "TYPE,start_time,segment_key,name,duration,weight\n"
            'local_traffic,"08:00","((-73.5,45.5),(-73.6,45.6))",test,50,1.5\n'
        )
        path = self._write_csv(csv_content)
        traffic_config = TrafficConfig(
            traffic_path=path, sim_start_time="day1:08:00", sim_end_time="day1:12:00"
        )
        try:
            parser = TrafficParser(traffic_config)
            with pytest.raises(
                TrafficParseError, match="weight must be >= 0.0 and < 1.0"
            ):
                parser.parse()
        finally:
            os.unlink(path)

    def test_weight_out_of_range_negative(self) -> None:
        csv_content = (
            "TYPE,start_time,segment_key,name,duration,weight\n"
            'local_traffic,"08:00","((-73.5,45.5),(-73.6,45.6))",test,50,-0.1\n'
        )
        path = self._write_csv(csv_content)
        traffic_config = TrafficConfig(
            traffic_path=path, sim_start_time="day1:08:00", sim_end_time="day1:12:00"
        )
        try:
            parser = TrafficParser(traffic_config)
            with pytest.raises(
                TrafficParseError, match="weight must be >= 0.0 and < 1.0"
            ):
                parser.parse()
        finally:
            os.unlink(path)

    def test_weight_invalid_format(self) -> None:
        csv_content = (
            "TYPE,start_time,segment_key,name,duration,weight\n"
            'local_traffic,"08:00","((-73.5,45.5),(-73.6,45.6))",test,50,abc\n'
        )
        path = self._write_csv(csv_content)
        traffic_config = TrafficConfig(
            traffic_path=path, sim_start_time="day1:08:00", sim_end_time="day1:12:00"
        )
        try:
            parser = TrafficParser(traffic_config)
            with pytest.raises(TrafficParseError, match="weight must be a number"):
                parser.parse()
        finally:
            os.unlink(path)

    def test_traffic_parse_error_stores_errors(self) -> None:
        error = TrafficParseError(["error1", "error2"])
        assert error.errors == ["error1", "error2"]
        assert "error1" in str(error)
        assert "error2" in str(error)
