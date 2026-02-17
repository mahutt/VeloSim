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

import ast
import csv
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from sim.entities.traffic_event import TrafficEvent
from sim.entities.traffic_event_state import TrafficEventState
from sim.map.routing_provider import SegmentKey
from sim.entities.map_payload import TrafficConfig


class TrafficParseError(Exception):
    """Exception raised when traffic CSV parsing fails."""

    def __init__(self, errors: List[str]) -> None:
        self.errors = errors
        super().__init__(f"Traffic CSV parsing failed: {'; '.join(errors)}")


class TrafficParser:
    """Parses a traffic CSV file into a list of TrafficEvent objects.

    Expected CSV columns:
        TYPE,tick_start,segment_key,name,duration,weight

    Where:
        - TYPE: Must be "local_traffic" (only supported type for now)
        - tick_start: Integer simulation tick (>= 0)
        - segment_key: Coordinate tuple string in format
            "((lon1,lat1),(lon2,lat2))"
        - name: Optional string label (can be empty)
        - duration: Integer number of ticks (> 0)
        - weight: Float >= 0.0 and < 1.0 (traffic multiplier; 1.0 means no
            slowdown so no event is needed)
    """

    SUPPORTED_TYPES = {"local_traffic"}
    REQUIRED_COLUMNS = {"TYPE", "start_time", "segment_key", "duration", "weight"}

    def __init__(self, traffic_config: TrafficConfig) -> None:
        """Initialize the parser with a CSV file path and sim start time.

        Args:
            traffic_config: TrafficConfig with traffic settings.

        Raises:
            FileNotFoundError: If the CSV file does not exist.
        """
        csv_path = traffic_config.traffic_path
        self._start_time = traffic_config.sim_start_time
        self._end_time = traffic_config.sim_end_time
        self._window_start: Optional[int] = None
        self._window_end: Optional[int] = None
        self._path = Path(csv_path)
        if not self._path.exists():
            raise FileNotFoundError(f"Traffic CSV file not found: {csv_path}")

    def parse(self) -> List[TrafficEvent]:
        """Parse the CSV file and return a list of TrafficEvent objects.

        All returned events have state = TrafficEventState.PENDING.

        Returns:
            List of TrafficEvent objects parsed from the CSV rows.

        Raises:
            TrafficParseError: If CSV has missing columns or invalid data.
        """
        events: List[TrafficEvent] = []
        errors: List[str] = []

        with open(self._path, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)

            if reader.fieldnames is None:
                raise TrafficParseError(["CSV file is empty or has no header row"])

            missing = self.REQUIRED_COLUMNS - set(reader.fieldnames)
            if missing:
                raise TrafficParseError(
                    [f"Missing required columns: {', '.join(sorted(missing))}"]
                )

            for row_num, row in enumerate(reader, start=2):
                try:
                    new_events = self._parse_row(row, row_num)
                    if new_events:
                        events.extend(new_events)
                except ValueError as e:
                    errors.append(f"Row {row_num}: {e}")

        if errors:
            raise TrafficParseError(errors)

        return events

    def _parse_row(self, row: dict, row_num: int) -> list[TrafficEvent]:
        """Parse a single CSV row into a TrafficEvent.

        Args:
            row: Dictionary from csv.DictReader.
            row_num: Row number for error reporting.

        Returns:
            TrafficEvent if row is valid.

        Raises:
            ValueError: If row data is invalid.
        """
        event_type = row.get("TYPE", "").strip()

        if not event_type:
            raise ValueError("TYPE column is empty")

        if event_type not in self.SUPPORTED_TYPES:
            raise ValueError(
                f"Unsupported TYPE '{event_type}'. "
                f"Supported: {', '.join(sorted(self.SUPPORTED_TYPES))}"
            )

        # Parse start_time
        start_time_str = row.get("start_time", "").strip()
        if not start_time_str:
            raise ValueError("start_time is empty")
        try:
            start_ticks = self._get_all_ticks(start_time_str)
        except Exception:
            raise ValueError(
                f"Unsupported start_time format {start_time_str}. Should use simple "
                f"time format (e.g. '08:00')"
            )

        # Parse segment_key
        segment_key_str = row.get("segment_key", "").strip()
        segment_key = self._parse_segment_key(segment_key_str)

        # Parse name (optional)
        name = row.get("name", "").strip() or None

        # Parse duration
        duration_str = row.get("duration", "").strip()
        if not duration_str:
            raise ValueError("duration is empty")
        try:
            duration = int(duration_str)
        except ValueError:
            raise ValueError(f"duration must be an integer, got '{duration_str}'")
        if duration <= 0:
            raise ValueError(f"duration must be positive, got {duration}")

        # Parse weight
        weight_str = row.get("weight", "").strip()
        if not weight_str:
            raise ValueError("weight is empty")
        try:
            weight = float(weight_str)
        except ValueError:
            raise ValueError(f"weight must be a number, got '{weight_str}'")
        if not (0.0 <= weight < 1.0):
            raise ValueError(f"weight must be >= 0.0 and < 1.0, got {weight}")

        events = []
        for tick in start_ticks:
            events.append(
                TrafficEvent(
                    event_type=event_type,
                    tick_start=tick,
                    segment_key=segment_key,
                    duration=duration,
                    weight=weight,
                    name=name,
                    state=TrafficEventState.PENDING,
                )
            )
        return events

    @staticmethod
    def _parse_segment_key(raw: str) -> SegmentKey:
        """Parse a segment key string into a SegmentKey tuple.

        Expected format: "((lon1,lat1),(lon2,lat2))"

        Args:
            raw: Raw string representation of the segment key.

        Returns:
            SegmentKey tuple: ((lon1, lat1), (lon2, lat2))

        Raises:
            ValueError: If the format is invalid.
        """
        if not raw:
            raise ValueError("segment_key is empty")

        try:
            parsed = ast.literal_eval(raw)
        except (ValueError, SyntaxError):
            raise ValueError(
                f"Invalid segment_key format: '{raw}'. "
                f"Expected format: ((lon1,lat1),(lon2,lat2))"
            )

        if (
            not isinstance(parsed, tuple)
            or len(parsed) != 2
            or not isinstance(parsed[0], tuple)
            or not isinstance(parsed[1], tuple)
            or len(parsed[0]) != 2
            or len(parsed[1]) != 2
        ):
            raise ValueError(
                f"segment_key must be ((lon1,lat1),(lon2,lat2)), got: {raw}"
            )

        try:
            lon1, lat1 = float(parsed[0][0]), float(parsed[0][1])
            lon2, lat2 = float(parsed[1][0]), float(parsed[1][1])
        except (TypeError, ValueError):
            raise ValueError(f"segment_key coordinates must be numeric, got: {raw}")

        if not (-180 <= lon1 <= 180 and -180 <= lon2 <= 180):
            raise ValueError(
                f"Longitude must be between -180 and 180, got: ({lon1}, {lon2})"
            )
        if not (-90 <= lat1 <= 90 and -90 <= lat2 <= 90):
            raise ValueError(
                f"Latitude must be between -90 and 90, got: ({lat1}, {lat2})"
            )

        return (lon1, lat1), (lon2, lat2)

    def _convert_relative_time_to_seconds(self, time_str: str) -> int:
        """
        Converts time in format "dayX:HH:MM" to integer seconds.

        Args:
            time_str: Time string in format "dayX:HH:MM".

        Returns:
            Relative time in seconds.
        """
        try:
            parts = time_str.replace("day", "").split(":")
            days = int(parts[0]) - 1  # normalizes day1 to 0 offset
            hours = int(parts[1])
            minutes = int(parts[2])
            return (days * 24 * 3600) + (hours * 3600) + (minutes * 60)
        except (ValueError, IndexError):
            raise ValueError(f"Invalid format: {time_str}. Use 'dayX:HH:MM'")

    def _get_daily_seconds(self, time_str: str) -> int:
        """
        Converts a time in the day to integer seconds.

        Args:
            time_str: Time string in format "HH:MM" or "HH:MM:SS".

        Returns:
            Time in seconds.
        """
        t = datetime.strptime(time_str, "%H:%M").time()
        return (t.hour * 3600) + (t.minute * 60)

    def _get_all_ticks(self, event_time_str: str) -> list[int]:
        """
        Calculates all occurrences of a daily recurring event within the
        [start_time, end_time] window. It takes a static daily time and
        projects it across multiple days to find every instance that falls
        within the simulation bounds.

        Args:
            event_time_str: Static daily time string.

        Returns:
            List of ticks in seconds relative to the simulation's start time.
            Returns an empty list if no occurences happen during the sim window.
        """
        if self._window_start is None or self._window_end is None:
            self._window_start = self._convert_relative_time_to_seconds(
                self._start_time
            )
            self._window_end = self._convert_relative_time_to_seconds(self._end_time)

        daily_event_seconds = self._get_daily_seconds(event_time_str)

        ticks = []
        # determine how many full days have passed since the beginning of day1
        total_days_in_window = (self._window_end // (24 * 3600)) + 1

        for day_offset in range(total_days_in_window + 1):
            event_tick = (day_offset * 24 * 3600) + daily_event_seconds

            # add tick if within the sim window
            if self._window_start <= event_tick <= self._window_end:
                ticks.append(event_tick - self._window_start)

        return ticks
