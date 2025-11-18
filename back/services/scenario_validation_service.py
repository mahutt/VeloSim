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

from typing import Any, Dict, List, Set, Optional
from pydantic import BaseModel, ValidationError, model_validator, field_validator
from datetime import datetime
import re


class PositionValidator(BaseModel):
    lat: float
    lon: float

    @model_validator(mode="before")
    def check_lat_lon(cls, values: Any) -> Dict[str, float]:
        if isinstance(values, (list, tuple)):
            if len(values) != 2:
                raise ValueError(
                    "Position must contain exactly two coordinates [lon, lat]"
                )
            values = {"lon": float(values[0]), "lat": float(values[1])}
        elif not isinstance(values, dict):
            raise ValueError("Position must be a dict or list/tuple")

        lat = float(values["lat"])
        lon = float(values["lon"])

        if not (-90 <= lat <= 90) or not (-180 <= lon <= 180):
            raise ValueError(f"Invalid latitude/longitude range: {lat}, {lon}")
        return {"lat": lat, "lon": lon}


class ResourceValidator(BaseModel):
    resource_id: int
    resource_position: PositionValidator


class StationValidator(BaseModel):
    station_id: int
    station_name: str
    station_position: PositionValidator


class TaskValidator(BaseModel):
    id: str | None = None
    station_id: int
    time: int | float | None = None

    @field_validator("time", mode="before")
    @classmethod
    def parse_time(cls, v: Any) -> int | float | None:
        """Parse time in simulator format.

        Simulator expects:
        - None or omitted for initial_tasks (spawns immediately)
        - Integer/float seconds for scheduled_tasks (e.g., 600, 1800.5)

        This validator enforces the simulator's expected format as the source of truth.
        """
        if v is None:
            return v

        # Accept only numeric seconds (simulator format)
        if isinstance(v, (int, float)):
            if v < 0:
                raise ValueError("Time in seconds cannot be negative")
            return v

        # Reject string formats - simulator doesn't accept them
        if isinstance(v, str):
            raise ValueError(
                f"Time must be numeric seconds (e.g., 600, 1800), not string '{v}'. "
                "The simulator expects numeric seconds only."
            )

        raise ValueError(
            f"Time must be numeric seconds or None, got {type(v).__name__}"
        )


class ScenarioTimes(BaseModel):
    start_time: datetime
    end_time: datetime

    @field_validator("start_time", "end_time", mode="before")
    @classmethod
    def parse_time(cls, v: Any) -> datetime:
        """Parse time from various formats to datetime object.

        Supports:
        - RFC 3339 / ISO 8601 datetime strings
          (e.g., "2025-11-06T08:00:00Z")
        - Simple time strings (e.g., "08:00") - converted to today's date
        - datetime objects (passed through)
        """
        if isinstance(v, datetime):
            return v

        if isinstance(v, str):
            # Try RFC 3339 / ISO 8601 format first
            try:
                return datetime.fromisoformat(v.replace("Z", "+00:00"))
            except ValueError:
                pass

            # Try simple time format (HH:MM or HH:MM:SS)
            for fmt in ["%H:%M:%S", "%H:%M"]:
                try:
                    parsed_time = datetime.strptime(v, fmt).time()
                    # Combine with today's date
                    return datetime.combine(datetime.today().date(), parsed_time)
                except ValueError:
                    continue

            raise ValueError(
                f"Invalid time format: {v}. Use RFC 3339 format "
                "(e.g., '2025-11-06T08:00:00Z') or simple time "
                "(e.g., '08:00')"
            )

        raise ValueError(f"Time must be a string or datetime, got {type(v)}")


class ScenarioValidator:
    """Validator for scenario content."""

    def __init__(self, json_string: Optional[str] = None) -> None:
        """Initialize validator with optional JSON string for line number tracking."""
        self.line_map: Dict[str, int] = {}
        if json_string:
            self._build_line_map(json_string)

    def _build_line_map(self, json_string: str) -> None:
        """Build a map of JSON paths to line numbers."""
        lines = json_string.split("\n")
        path_stack: List[str] = []

        for line_num, line in enumerate(lines, start=1):
            # Track keys in objects
            key_match = re.search(r'"([^"]+)"\s*:', line)
            if key_match:
                key = key_match.group(1)
                # Build the current path
                current_path = ".".join(path_stack + [key]) if path_stack else key
                self.line_map[current_path] = line_num
                self.line_map[key] = line_num

                # Track if we're entering an array or object
                if "[" in line:
                    path_stack.append(key)
                elif "{" in line and "}" not in line:
                    path_stack.append(key)

            # Track array indices
            if re.match(r"^\s*\{\s*$", line) and path_stack:
                # Entering an array element
                pass

            # Pop from stack when closing
            if "}" in line or "]" in line:
                if path_stack:
                    path_stack.pop()

    def _get_line_number(self, field_path: str) -> Optional[int]:
        """Get line number for a field path, trying multiple variations."""
        # Try exact match first
        if field_path in self.line_map:
            return self.line_map[field_path]

        # Try extracting just the field name from paths like "stations[0].station_id"
        parts = field_path.split(".")
        if parts:
            last_part = parts[-1]
            if last_part in self.line_map:
                return self.line_map[last_part]

            # Try the parent field for array elements
            if "[" in field_path:
                parent = re.sub(r"\[\d+\].*", "", field_path)
                if parent in self.line_map:
                    return self.line_map[parent]

        return None

    @staticmethod
    def check_required_fields(
        item: Dict[str, Any], required_fields: List[str]
    ) -> List[Dict[str, Any]]:
        return [
            {"field": f, "message": f"Missing required field '{f}'"}
            for f in required_fields
            if f not in item
        ]

    def validate_syntax(self, content: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Validate the syntax of scenario content only."""
        errors: List[Dict[str, Any]] = []

        # Validate start_time and end_time exist and are properly formatted
        required_fields = ["start_time", "end_time"]
        for error in self.check_required_fields(content, required_fields):
            line_num = self._get_line_number(error["field"])
            if line_num:
                error["line"] = line_num
            errors.append(error)

        # Validate time format and constraints
        try:
            ScenarioTimes(**content)
        except ValidationError as e:
            for err in e.errors():
                field_path = ".".join(map(str, err["loc"]))
                error_dict: Dict[str, Any] = {
                    "field": field_path,
                    "message": err["msg"],
                }
                line_num = self._get_line_number(field_path)
                if line_num:
                    error_dict["line"] = line_num
                errors.append(error_dict)

        return errors

    def validate_stations(self, stations: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        errors: List[Dict[str, Any]] = []
        seen_ids: Set[int] = set()

        for idx, s in enumerate(stations):
            for error in self.check_required_fields(
                s,
                [
                    "station_id",
                    "station_name",
                    "station_position",
                ],
            ):
                field_path = f"stations[{idx}].{error['field']}"
                line_num = self._get_line_number(field_path)
                if line_num:
                    error["line"] = line_num
                error["field"] = field_path
                errors.append(error)

            station_id_raw: Any = s.get("station_id")
            if isinstance(station_id_raw, int):
                if station_id_raw in seen_ids:
                    field_path = f"stations[{idx}].station_id"
                    dup_error: Dict[str, Any] = {
                        "field": field_path,
                        "message": "Duplicate station ID",
                    }
                    line_num = self._get_line_number(field_path)
                    if line_num:
                        dup_error["line"] = line_num
                    errors.append(dup_error)
                seen_ids.add(station_id_raw)

            try:
                StationValidator(**s)
            except ValidationError as e:
                for err in e.errors():
                    field_name = f"stations[{idx}].{'.'.join(map(str, err['loc']))}"
                    val_error: Dict[str, Any] = {
                        "field": field_name,
                        "message": err["msg"],
                    }
                    line_num = self._get_line_number(field_name)
                    if line_num:
                        val_error["line"] = line_num
                    errors.append(val_error)

        return errors

    def validate_resources(
        self, resources: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        errors: List[Dict[str, Any]] = []
        seen_ids: Set[int] = set()

        for idx, r in enumerate(resources):
            for error in self.check_required_fields(
                r, ["resource_id", "resource_position"]
            ):
                field_path = f"resources[{idx}].{error['field']}"
                line_num = self._get_line_number(field_path)
                if line_num:
                    error["line"] = line_num
                error["field"] = field_path
                errors.append(error)

            try:
                validated: ResourceValidator = ResourceValidator(**r)
                if validated.resource_id in seen_ids:
                    field_path = f"resources[{idx}].resource_id"
                    dup_error: Dict[str, Any] = {
                        "field": field_path,
                        "message": "Duplicate resource ID",
                    }
                    line_num = self._get_line_number(field_path)
                    if line_num:
                        dup_error["line"] = line_num
                    errors.append(dup_error)
                seen_ids.add(validated.resource_id)
            except ValidationError as e:
                for err in e.errors():
                    field_name = f"resources[{idx}].{'.'.join(map(str, err['loc']))}"
                    val_error: Dict[str, Any] = {
                        "field": field_name,
                        "message": err["msg"],
                    }
                    line_num = self._get_line_number(field_name)
                    if line_num:
                        val_error["line"] = line_num
                    errors.append(val_error)

        return errors

    def validate_tasks(
        self, tasks: List[Dict[str, Any]], valid_station_ids: Set[int]
    ) -> List[Dict[str, Any]]:
        errors: List[Dict[str, Any]] = []

        for idx, task in enumerate(tasks):
            for error in self.check_required_fields(task, ["station_id"]):
                field_path = f"tasks[{idx}].{error['field']}"
                line_num = self._get_line_number(field_path)
                if line_num:
                    error["line"] = line_num
                error["field"] = field_path
                errors.append(error)

            if "id" in task:
                field_path = f"tasks[{idx}].id"
                warning: Dict[str, Any] = {
                    "field": field_path,
                    "message": (
                        "Task IDs are auto-generated and cannot be "
                        "specified. This field will be ignored."
                    ),
                }
                line_num = self._get_line_number(field_path)
                if line_num:
                    warning["line"] = line_num
                errors.append(warning)

            try:
                validated: TaskValidator = TaskValidator(**task)

                if validated.station_id not in valid_station_ids:
                    field_path = f"tasks[{idx}].station_id"
                    station_error: Dict[str, Any] = {
                        "field": field_path,
                        "message": f"Station ID {validated.station_id} does not exist",
                    }
                    line_num = self._get_line_number(field_path)
                    if line_num:
                        station_error["line"] = line_num
                    errors.append(station_error)
            except ValidationError as e:
                for err in e.errors():
                    field_name = f"tasks[{idx}].{'.'.join(map(str, err['loc']))}"
                    val_error: Dict[str, Any] = {
                        "field": field_name,
                        "message": err["msg"],
                    }
                    line_num = self._get_line_number(field_name)
                    if line_num:
                        val_error["line"] = line_num
                    errors.append(val_error)

        return errors

    def validate_simulation_params(
        self, params: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Validate simulation time parameters.

        Ensures start_time and end_time are valid and that end_time is after start_time.
        Simulations cannot span more than 24 hours.
        """
        errors: List[Dict[str, Any]] = []
        start_val: Any = params.get("start_time")
        end_val: Any = params.get("end_time")

        if start_val is not None and end_val is not None:
            try:
                # Parse times using ScenarioTimes validator
                scenario_times = ScenarioTimes(start_time=start_val, end_time=end_val)

                # Validate that end_time is after start_time
                if scenario_times.end_time <= scenario_times.start_time:
                    time_error: Dict[str, Any] = {
                        "field": "end_time",
                        "message": "end_time must be after start_time",
                    }
                    line_num = self._get_line_number("end_time")
                    if line_num:
                        time_error["line"] = line_num
                    errors.append(time_error)

                # Validate that simulation doesn't span more than 24 hours
                duration = scenario_times.end_time - scenario_times.start_time
                if duration.total_seconds() > 86400:  # 24 hours in seconds
                    duration_error: Dict[str, Any] = {
                        "field": "end_time",
                        "message": "Simulation duration cannot exceed 24 hours",
                    }
                    line_num = self._get_line_number("end_time")
                    if line_num:
                        duration_error["line"] = line_num
                    errors.append(duration_error)
            except ValidationError as e:
                for err in e.errors():
                    field_path = ".".join(map(str, err["loc"]))
                    val_error: Dict[str, Any] = {
                        "field": field_path,
                        "message": err["msg"],
                    }
                    line_num = self._get_line_number(field_path)
                    if line_num:
                        val_error["line"] = line_num
                    errors.append(val_error)

        return errors

    def validate_all(self, scenario_content: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Validate all aspects of scenario content."""
        errors: List[Dict[str, Any]] = self.validate_syntax(scenario_content)

        stations: List[Dict[str, Any]] = scenario_content.get("stations", [])
        resources: List[Dict[str, Any]] = scenario_content.get("resources", [])
        initial_tasks: List[Dict[str, Any]] = scenario_content.get("initial_tasks", [])
        scheduled_tasks: List[Dict[str, Any]] = scenario_content.get(
            "scheduled_tasks", []
        )

        errors.extend(self.validate_stations(stations))
        errors.extend(self.validate_resources(resources))

        valid_station_ids: Set[int] = {
            int(s["station_id"]) for s in stations if "station_id" in s
        }
        for task_list in [initial_tasks, scheduled_tasks]:
            errors.extend(self.validate_tasks(task_list, valid_station_ids))

        errors.extend(self.validate_simulation_params(scenario_content))
        return errors
