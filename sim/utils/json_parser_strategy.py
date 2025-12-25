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

from datetime import datetime
from typing import Dict, List, Any, Set, Optional, cast
import re
from pydantic import BaseModel, ValidationError, model_validator, field_validator

from sim.entities.inputParameters import InputParameter
from sim.entities.station import Station
from sim.entities.driver import Driver
from sim.entities.vehicle import Vehicle
from sim.entities.BatterySwapTask import BatterySwapTask
from sim.entities.position import Position
from sim.utils.base_parse_strategy import BaseParseStrategy


# ==============================================================================
# Pydantic Validation Models
# ==============================================================================

DEFAULT_VEHICLE_POSITION: List[float] = [-73.57314, 45.50137]


def _validate_day_time_format(time_value: Any) -> str:
    """Validate and parse day-time format string (e.g., 'day1:08:00').

    Supports: Simple time strings with relative day value (e.g., "day1:08:00")

    Args:
        time_value: Time value to validate as a string.

    Returns:
        Validated time string.

    Raises:
        ValueError: If time format is invalid.
    """
    if not isinstance(time_value, str):
        raise ValueError(f"Time must be a string, got {type(time_value)}")

    try:
        daytime_str = time_value.split(":", 1)
        if daytime_str[0] == time_value:
            raise Exception(f"Invalid time format: {time_value}.")
        day_str = daytime_str[0]
        time_str = daytime_str[1]

        # validate day_str
        pattern = r"^day\d+$"
        if re.match(pattern, day_str, re.IGNORECASE) is None:
            raise Exception(
                f"Invalid time format due provided day {day_str} in {time_value}."
            )

        # validate time_str
        try:
            datetime.strptime(time_str, "%H:%M").time()
        except Exception:
            raise Exception(
                f"Invalid time format due provided time {time_str} in {time_value}."
            )
        return time_value
    except Exception as e:
        raise ValueError(
            f"""{e} Retry by using a relative day number
            and simple time format (e.g. 'day1:08:00')"""
        )


class PositionValidator(BaseModel):
    """Validator for geographical position coordinates."""

    lat: float
    lon: float

    @model_validator(mode="before")
    def check_lat_lon(cls, values: Any) -> Dict[str, float]:
        """Validate and normalize position coordinates.

        Accepts position data as either a dict with lat/lon keys or a list/tuple
        of [lon, lat] and validates that coordinates are within valid ranges.

        Args:
            values: Position data as dict, list, or tuple.

        Returns:
            Dictionary with validated 'lat' and 'lon' keys.

        Raises:
            ValueError: If position format is invalid or coordinates are out of range.
        """
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


class VehicleValidator(BaseModel):
    """Validator for vehicle entity data."""

    name: str
    position: Optional[PositionValidator] = None
    battery_count: Optional[int] = 0


class ShiftValidator(BaseModel):
    """Validator for driver shift times."""

    start_time: str
    end_time: str
    lunch_break: Optional[str] = None

    @field_validator("start_time", "end_time", "lunch_break", mode="before")
    @classmethod
    def validate_shift(cls, v: Any) -> str:
        """Validate a single shift time value.

        Args:
            v: Time value to validate as a string.

        Returns:
            Validated time string in format "dayX:HH:MM".

        Raises:
            ValueError: If value is not a string or has invalid format.
        """
        if isinstance(v, str):
            return _validate_day_time_format(v)
        else:
            raise ValueError(f"Time must be a string or None, got {type(v)}")


class DriverValidator(BaseModel):
    """Validator for driver entity data."""

    name: str
    shift: ShiftValidator


class StationValidator(BaseModel):
    """Validator for station entity data."""

    name: str
    position: PositionValidator
    initial_task_count: Optional[int] = 0
    scheduled_tasks: List[str]

    @field_validator("scheduled_tasks", mode="before")
    @classmethod
    def parse_time(cls, v: Any) -> List[str]:
        """Parse time to validate valid format.

        Supports: Simple time strings with relative day value (e.g., "day1:08:00")

        Simulator expects:
        - Simple time strings with relative day value for `scheduled_tasks`.

        Args:
            v: Iterable of string times.

        Returns:
            List of validated time strings.

        Raises:
            ValueError: If type is not iterable of strings or format is invalid.
        """
        times = []
        if isinstance(v, (list, tuple)):
            for time_str in v:
                if isinstance(time_str, str):
                    times.append(_validate_day_time_format(time_str))
                else:
                    raise ValueError(
                        f"Time must be a string or None, got {type(time_str)}"
                    )
            return times
        else:
            raise ValueError(f"scheduled_tasks must be iterable type, got {type(v)}")


class TaskValidator(BaseModel):
    """Validator for task entity data."""

    id: str | None = None
    station_id: int
    time: str | None = None

    @model_validator(mode="before")
    @classmethod
    def reject_task_id(cls, values: Any) -> Dict[str, Any]:
        """Reject task IDs if provided, as they are auto-generated.

        Args:
            values: Task data as dict.

        Returns:
            Task data dict if 'id' is not present.

        Raises:
            ValueError: If 'id' field is present in task data.
        """
        if isinstance(values, dict) and "id" in values:
            raise ValueError(
                "Task 'id' field is not allowed. "
                "Task IDs are auto-generated by the simulator."
            )
        return values  # type: ignore[no-any-return]

    @field_validator("time", mode="before")
    @classmethod
    def parse_time(cls, v: Any) -> str | None:
        """Parse time to validate valid format.

        Supports: Simple time strings with relative day value (e.g., "day1:08:00")

        Simulator expects:
        - None or omitted for initial_tasks (spawns immediately)
        - Simple time strings with relative day value for scheduled_tasks
        (e.g., "day1:08:00")

        Args:
            v: Time value to validate as a string.

        Returns:
            Validated time string.

        Raises:
            ValueError: If time is not a string or format is invalid.
        """
        if isinstance(v, str):
            return _validate_day_time_format(v)
        else:
            raise ValueError(f"Time must be a string or None, got {type(v)}")


class ScenarioGlobals(BaseModel):
    """Validator for scenario start and end times."""

    start_time: str
    end_time: str
    vehicle_battery_capacity: int

    @field_validator("start_time", "end_time", mode="before")
    @classmethod
    def parse_time(cls, v: Any) -> str:
        """Parse time to validate valid format.

        Supports: Simple time strings with relative day value (e.g., "day1:08:00")

        Args:
            v: Time value to validate as a string.

        Returns:
            Validated time string.

        Raises:
            ValueError: If time format is invalid.
        """
        if isinstance(v, str):

            return _validate_day_time_format(v)

        else:
            raise ValueError(f"Time must be a string, got {type(v)}")

    @field_validator("vehicle_battery_capacity", mode="before")
    @classmethod
    def parse_battery_capacity(cls, v: Any) -> int:
        """Validate vehicle battery capacity.

        Args:
            v: Capacity value to validate.

        Returns:
            The validated positive integer capacity.

        Raises:
            ValueError: If capacity is not an integer greater than 0.
        """
        if isinstance(v, int) and v > 0:
            return v
        else:
            raise ValueError(
                f"vehicle_battery_capacity should be an integer greater than 0. Got {v}"
            )


# ==============================================================================
# Internal Validator Class
# ==============================================================================


class _ScenarioValidator:
    """Internal validator for scenario content.

    This class is an implementation detail. Use JsonParseStrategy instead.
    """

    def __init__(self, json_string: Optional[str] = None) -> None:
        """Initialize validator with optional JSON string for line number tracking.

        Args:
            json_string: Optional JSON string to build line number mapping
                for error reporting.
        """
        self.line_map: Dict[str, int] = {}
        if json_string:
            self._build_line_map(json_string)

    def _build_line_map(self, json_string: str) -> None:
        """Build a map of JSON paths to line numbers.

        Args:
            json_string: JSON string to parse for line number mapping.
        """
        lines = json_string.split("\n")
        path_stack: List[str] = []
        array_counters: Dict[str, int] = {}
        in_array: Dict[str, bool] = {}

        for line_num, line in enumerate(lines, start=1):
            # Track arrays starting
            key_array_match = re.search(r'"([^"]+)"\s*:\s*\[', line)
            if key_array_match:
                key = key_array_match.group(1)
                current_path = ".".join(path_stack + [key]) if path_stack else key
                self.line_map[current_path] = line_num
                array_counters[current_path] = 0
                in_array[current_path] = True
                if "[" in line and "]" not in line:
                    path_stack.append(key)
                continue

            # Track keys in objects
            key_match = re.search(r'"([^"]+)"\s*:', line)
            if key_match:
                key = key_match.group(1)
                # Build the current path
                current_path = ".".join(path_stack + [key]) if path_stack else key
                self.line_map[current_path] = line_num

                # For fields inside arrays, also map with array index
                if path_stack:
                    parent_path = ".".join(path_stack)
                    if parent_path in in_array and in_array[parent_path]:
                        array_idx = array_counters.get(parent_path, 0)
                        indexed_path = f"{parent_path}[{array_idx}].{key}"
                        self.line_map[indexed_path] = line_num

                # Track if we're entering an object
                if "{" in line and "[" not in line and "}" not in line:
                    path_stack.append(key)

            # Detect array element start
            if re.match(r"^\s*\{\s*$", line) and path_stack:
                parent_path = ".".join(path_stack)
                if parent_path in in_array and in_array[parent_path]:
                    array_idx = array_counters[parent_path]
                    element_path = f"{parent_path}[{array_idx}]"
                    self.line_map[element_path] = line_num

            # Pop from stack when closing
            if "}" in line and path_stack:
                parent_path = ".".join(path_stack)
                if parent_path in in_array and in_array[parent_path]:
                    # Increment array counter when closing array element
                    array_counters[parent_path] = array_counters.get(parent_path, 0) + 1
                else:
                    path_stack.pop()
            elif "]" in line and path_stack:
                parent_path = ".".join(path_stack)
                if parent_path in in_array:
                    in_array[parent_path] = False
                path_stack.pop()

    def _get_line_number(self, field_path: str) -> Optional[int]:
        """Get line number for a field path, trying multiple variations.

        Args:
            field_path: JSON field path (e.g., 'stations[0].station_id').

        Returns:
            Line number if found, None otherwise.
        """
        # Try exact match first
        if field_path in self.line_map:
            return self.line_map[field_path]

        # Try with "content." prefix (JSON may have content wrapper)
        prefixed_path = f"content.{field_path}"
        if prefixed_path in self.line_map:
            return self.line_map[prefixed_path]

        # Try the array element itself (e.g., 'drivers[1]')
        if "[" in field_path:
            array_element = re.match(r"^([^\[]+\[\d+\])", field_path)
            if array_element:
                element_path = array_element.group(1)
                if element_path in self.line_map:
                    return self.line_map[element_path]
                # Try with content prefix
                prefixed_element = f"content.{element_path}"
                if prefixed_element in self.line_map:
                    return self.line_map[prefixed_element]

                # Fallback: use the first known subfield mapping under the array element
                # This handles inline array objects like `{ "name": "D1" }` where
                # we may have `drivers[0].name` but not `drivers[0]` mapped.
                candidate_prefixes = [f"{element_path}.", f"content.{element_path}."]
                for prefix in candidate_prefixes:
                    # Collect all matching subfield paths and choose the earliest line
                    matching = [
                        self.line_map[k]
                        for k in self.line_map.keys()
                        if k.startswith(prefix)
                    ]
                    if matching:
                        return min(matching)

        # Try extracting just the field name from paths
        parts = field_path.split(".")
        if parts:
            last_part = parts[-1]
            # Only use this fallback if there's no array index
            if "[" not in field_path and last_part in self.line_map:
                return self.line_map[last_part]

        return None

    @staticmethod
    def check_required_fields(
        item: Dict[str, Any], required_fields: List[str]
    ) -> List[Dict[str, Any]]:
        """Check if all required fields are present in an item.

        Args:
            item: Dictionary to check for required fields.
            required_fields: List of field names that must be present.

        Returns:
            List of error dictionaries for missing fields.
        """
        return [
            {"field": f, "message": f"Missing required field '{f}'"}
            for f in required_fields
            if f not in item
        ]

    def validate_syntax(self, content: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Validate the syntax of scenario content only.

        Args:
            content: Scenario content dictionary to validate.

        Returns:
            List of error dictionaries with field, message, and optional line number.
        """
        errors: List[Dict[str, Any]] = []

        # Validate start_time and end_time exist and are properly formatted
        required_fields = ["start_time", "end_time", "vehicle_battery_capacity"]
        for error in self.check_required_fields(content, required_fields):
            line_num = self._get_line_number(error["field"])
            if line_num:
                error["line"] = line_num
            errors.append(error)

        # Validate time format and constraints
        try:
            ScenarioGlobals(**content)
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
        """Validate station definitions including names, positions, and tasks.

        Args:
            stations: List of station dictionaries to validate.

        Returns:
            List of error dictionaries for invalid or duplicate stations.
        """
        errors: List[Dict[str, Any]] = []

        for idx, s in enumerate(stations):
            for error in self.check_required_fields(
                s,
                ["name", "position", "scheduled_tasks"],
            ):
                field_path = f"stations[{idx}].{error['field']}"
                line_num = self._get_line_number(field_path)
                if line_num:
                    error["line"] = line_num
                error["field"] = field_path
                errors.append(error)

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

    def validate_tasks(
        self,
        tasks: List[Dict[str, Any]],
        valid_station_ids: Set[int],
        task_type: str = "tasks",
    ) -> List[Dict[str, Any]]:
        """Validate task definitions and station ID references.

        Args:
            tasks: List of task dictionaries to validate.
            valid_station_ids: Set of valid station IDs for reference checking.
            task_type: Type of task list for error messages
                (e.g., 'initial_tasks', 'scheduled_tasks').

        Returns:
            List of error dictionaries for invalid tasks or station references.
        """
        errors: List[Dict[str, Any]] = []

        for idx, task in enumerate(tasks):
            for error in self.check_required_fields(task, ["station_id"]):
                field_path = f"{task_type}[{idx}].{error['field']}"
                line_num = self._get_line_number(field_path)
                if line_num:
                    error["line"] = line_num
                error["field"] = field_path
                errors.append(error)

            try:
                validated: TaskValidator = TaskValidator(**task)

                if validated.station_id not in valid_station_ids:
                    field_path = f"{task_type}[{idx}].station_id"
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
                    field_name = f"{task_type}[{idx}].{'.'.join(map(str, err['loc']))}"
                    val_error: Dict[str, Any] = {
                        "field": field_name,
                        "message": err["msg"],
                    }
                    line_num = self._get_line_number(field_name)
                    if line_num:
                        val_error["line"] = line_num
                    errors.append(val_error)

        return errors

    def validate_vehicles(self, vehicles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Validate vehicle definitions including required fields and schema.

        Args:
            vehicles: List of vehicle dictionaries to validate.

        Returns:
            List of error dictionaries for invalid or duplicate vehicles.
        """
        errors: List[Dict[str, Any]] = []

        for idx, v in enumerate(vehicles):
            # Required fields for vehicles and ID tracking
            for error in self.check_required_fields(v, ["name"]):
                field_path = f"vehicles[{idx}].{error['field']}"
                line_num = self._get_line_number(field_path)
                if line_num:
                    error["line"] = line_num
                error["field"] = field_path
                errors.append(error)

            # Schema validation via Pydantic
            try:
                VehicleValidator(**v)
            except ValidationError as e:
                for err in e.errors():
                    field_name = f"vehicles[{idx}].{'.'.join(map(str, err['loc']))}"
                    val_error: Dict[str, Any] = {
                        "field": field_name,
                        "message": err["msg"],
                    }
                    line_num = self._get_line_number(field_name)
                    if line_num:
                        val_error["line"] = line_num
                    errors.append(val_error)

        return errors

    def validate_drivers(
        self,
        drivers: List[Dict[str, Any]],
        valid_vehicle_ids: Optional[Set[int]] = None,
    ) -> List[Dict[str, Any]]:
        """Validate driver definitions, shift schema, and vehicle references.

        Args:
            drivers: List of driver dictionaries to validate.
            valid_vehicle_ids: Optional set of known vehicle IDs to validate references.

        Returns:
            List of error dictionaries for invalid or duplicate drivers.
        """
        errors: List[Dict[str, Any]] = []
        valid_vehicle_ids = valid_vehicle_ids or set()

        for idx, d in enumerate(drivers):
            # Required fields for drivers and ID tracking
            for error in self.check_required_fields(d, ["name", "shift"]):
                field_path = f"drivers[{idx}].{error['field']}"
                line_num = self._get_line_number(field_path)
                if line_num:
                    error["line"] = line_num
                error["field"] = field_path
                errors.append(error)
            # Schema validation via Pydantic (name + shift)
            try:
                DriverValidator(**d)
            except ValidationError as e:
                for err in e.errors():
                    field_name = f"drivers[{idx}].{'.'.join(map(str, err['loc']))}"
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

        Args:
            params: Dictionary containing simulation parameters with
                start_time and end_time.

        Returns:
            List of validation error dictionaries, empty if no errors.
        """
        errors: List[Dict[str, Any]] = []
        start_val: Any = params.get("start_time")
        end_val: Any = params.get("end_time")

        if start_val is not None and end_val is not None:
            try:
                # Parse times using ScenarioGlobals validator
                capacity: int = cast(int, params.get("vehicle_battery_capacity"))
                scenario_times = ScenarioGlobals(
                    start_time=start_val,
                    end_time=end_val,
                    vehicle_battery_capacity=capacity,
                )

                # Validate that end_time is after start_time
                start_daytime = scenario_times.start_time.split(":", 1)
                start_day = start_daytime[0]
                start_time = start_daytime[1]
                end_daytime = scenario_times.end_time.split(":", 1)
                end_day = end_daytime[0]
                end_time = end_daytime[1]
                error = False

                if start_day == end_day:  # if start and end are on the same day
                    st = datetime.strptime(start_time, "%H:%M").time()
                    et = datetime.strptime(end_time, "%H:%M").time()
                    if et <= st:
                        error = True
                else:  # if start and end not on the same day
                    sd = start_day[-1]
                    ed = end_day[-1]
                    if ed < sd:
                        error = True
                if error:
                    time_error: Dict[str, Any] = {
                        "field": "end_time",
                        "message": "end_time must be after start_time",
                    }
                    line_num = self._get_line_number("end_time")
                    if line_num:
                        time_error["line"] = line_num
                    errors.append(time_error)
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
        """Validate all aspects of scenario content.

        Args:
            scenario_content: Complete scenario dictionary to validate.

        Returns:
            List of all validation errors found across all validation checks.
        """
        errors: List[Dict[str, Any]] = self.validate_syntax(scenario_content)

        stations: List[Dict[str, Any]] = scenario_content.get("stations", [])
        vehicles: List[Dict[str, Any]] = scenario_content.get("vehicles", [])
        drivers: List[Dict[str, Any]] = scenario_content.get("drivers", [])

        errors.extend(self.validate_stations(stations))
        errors.extend(self.validate_drivers(drivers))
        errors.extend(self.validate_vehicles(vehicles))

        errors.extend(self.validate_simulation_params(scenario_content))
        return errors


# ==============================================================================
# Public API - Exceptions
# ==============================================================================


class ScenarioParseError(Exception):
    """Exception raised when scenario parsing/validation fails."""

    def __init__(self, errors: List[Dict[str, Any]]) -> None:
        """Initialize with validation errors.

        Args:
            errors: List of validation error dictionaries.
        """
        self.errors = errors
        error_messages = [
            f"{e.get('field', 'unknown')}: {e.get('message', 'unknown error')}"
            for e in errors
        ]
        super().__init__(f"Scenario validation failed: {'; '.join(error_messages)}")


# ==============================================================================
# Public API - Parser with Integrated Validation
# ==============================================================================


class JsonParseStrategy(BaseParseStrategy):
    """JSON-based scenario parsing strategy with integrated validation.

    This is the main entry point for scenario validation and parsing.
    It combines validation and parsing into a single operation, ensuring
    a single source of truth for what constitutes a valid scenario.
    """

    def __init__(
        self,
        scenario_json: Optional[dict] = None,
        json_string: Optional[str] = None,
    ) -> None:
        """Initialize parser with scenario content and optional JSON string.

        Args:
            scenario_json: Optional dictionary containing scenario configuration.
                If provided, validate() and parse() can be called without parameters.
            json_string: Optional JSON string for line number tracking in errors.
        """
        self.scenario_json = scenario_json
        self._validator = _ScenarioValidator(json_string=json_string)

    def validate(self, scenario_json: Optional[dict] = None) -> List[Dict[str, Any]]:
        """Validate scenario content without parsing.

        Args:
            scenario_json: Optional dictionary containing scenario configuration.
                If not provided, uses the scenario_json from constructor.

        Returns:
            List of validation errors (empty list if valid).

        Raises:
            ValueError: If no scenario_json provided in constructor or parameter.
        """
        json_to_validate = (
            scenario_json if scenario_json is not None else self.scenario_json
        )
        if json_to_validate is None:
            raise ValueError(
                "scenario_json must be provided either in constructor or as parameter"
            )
        content = json_to_validate.get("content", json_to_validate)
        return self._validator.validate_all(content)

    def _time_to_seconds(self, time_str: str) -> int:
        """Convert day-time string to total seconds.

        Converts time format 'dayX:HH:MM' to total seconds from start.

        Args:
            time_str: Time string in format 'dayX:HH:MM' (e.g., 'day1:08:30').

        Returns:
            Total seconds from simulation start.
        """
        daytime_split = time_str.split(":", 1)
        day = daytime_split[0]
        time = daytime_split[1]

        # Extract day number
        day_match = re.match(r"^day(\d+)$", day, re.IGNORECASE)
        day_int = int(day_match.group(1)) - 1  # type: ignore

        # Parse time
        t = datetime.strptime(time, "%H:%M")
        return (day_int * 24) * 3600 + t.hour * 3600 + t.minute * 60

    def parse(self, scenario_json: Optional[dict] = None) -> InputParameter:
        """Parse and validate scenario JSON, returning InputParameter.

        Validates the scenario using Pydantic models before parsing.
        If validation fails, raises ScenarioParseError with details.

        Converts scenario JSON format into an InputParameter object containing
        all simulation configuration including stations, drivers, vehicles, and tasks.

        Args:
            scenario_json: Optional dictionary containing scenario configuration.
                If not provided, uses the scenario_json from constructor.

        Returns:
            InputParameter object with parsed simulation configuration.

        Raises:
            ValueError: If no scenario_json provided in constructor or parameter.
            ScenarioParseError: If scenario validation fails.
        """
        json_to_parse = (
            scenario_json if scenario_json is not None else self.scenario_json
        )
        if json_to_parse is None:
            raise ValueError(
                "scenario_json must be provided either in constructor or as parameter"
            )

        # Extract content (handle both direct content and wrapped format)
        content = json_to_parse.get("content", json_to_parse)

        # Validate before parsing
        validation_errors = self.validate(json_to_parse)
        if validation_errors:
            raise ScenarioParseError(validation_errors)

        # Parse times (validation ensures these are valid)
        start_time = self._time_to_seconds(str(content.get("start_time", "day1:00:00")))
        end_time = self._time_to_seconds(str(content.get("end_time", "day1:00:00")))

        sim_time = end_time - start_time

        # Entity Counters
        task_id_counter = 1
        station_id_counter = 1
        vehicle_id_counter = 1
        driver_id_counter = 1

        # Build stations and tasks
        stations: Dict[int, Station] = {}
        tasks: Dict[int, BatterySwapTask] = {}
        for s in content.get("stations", []):
            station_id = station_id_counter
            station_id_counter += 1
            pos = Position(s.get("position", [0, 0]))
            stations[station_id] = Station(
                station_id=station_id,
                name=s.get("name", f"Station {station_id}"),
                position=pos,
            )

            # initial tasks
            initial_task_count = s.get("initial_task_count", 0)
            for _ in range(initial_task_count):
                tid = task_id_counter
                task_id_counter += 1
                tasks[tid] = BatterySwapTask(
                    task_id=tid, station=stations[station_id], spawn_delay=0
                )
                stations[station_id].add_task(tasks[tid])

            for t in s.get("scheduled_tasks", []):
                tid = task_id_counter
                task_id_counter += 1
                delay = self._time_to_seconds(t) - start_time
                tasks[tid] = BatterySwapTask(
                    task_id=tid, station=stations[station_id], spawn_delay=delay
                )
                stations[station_id].add_task(tasks[tid])

        # Build Vehicles and Drivers
        # For now, a driver must have a vehicle to drive and
        # vice versa, to be added to the sim. Excess of either are discarded
        vehicles: Dict[int, Vehicle] = {}
        drivers: Dict[int, Driver] = {}
        drivers_from_scenario = content.get("drivers", [])
        for v in content.get("vehicles", []):
            vid = vehicle_id_counter
            vehicle_id_counter += 1
            battery_count = int(v.get("battery_count", 0))
            vehicles[vid] = Vehicle(vehicle_id=vid, battery_count=battery_count)
            # Match as many drivers and vehicles as possible.
            try:
                # Pop next driver from scenario (details unused here)
                drivers_from_scenario.pop(0)
                did = driver_id_counter
                driver_id_counter += 1
                pos = v.get("position")
                if pos:
                    pos = Position(pos)
                else:
                    pos = Position(DEFAULT_VEHICLE_POSITION)
                drivers[did] = Driver(
                    driver_id=did, position=pos, task_list=[], vehicle=vehicles[vid]
                )
                vehicles[vid].set_vehicle_driver(drivers[did])
            except IndexError:
                # We currently only consider driver and vehicle pairs.
                # Excess drivers/vehicles are currently ignored
                break

        params = InputParameter(
            station_entities=stations,
            driver_entities=drivers,
            vehicles_entities=vehicles,
            task_entities=tasks,
            real_time_factor=content.get("real_time_factor", 1.0),
            key_frame_freq=content.get("key_frame_freq", 20),
            sim_time=sim_time,
            start_time=start_time,
        )

        return params
