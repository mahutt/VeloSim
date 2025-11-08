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

from typing import Any, Dict, List, Set
from pydantic import BaseModel, ValidationError, model_validator, field_validator
from datetime import datetime


class PositionValidator(BaseModel):
    lat: float
    lon: float

    @model_validator(mode="before")
    def check_lat_lon(cls, values: Any) -> Dict[str, float]:
        if isinstance(values, (list, tuple)):
            if len(values) != 2:
                raise ValueError(
                    "Position must contain exactly two coordinates [lat, lon]"
                )
            values = {"lat": float(values[0]), "lon": float(values[1])}
        elif not isinstance(values, dict):
            raise ValueError("Position must be a dict or list/tuple")

        lat = float(values["lat"])
        lon = float(values["lon"])

        if not (-90 <= lat <= 90) or not (-180 <= lon <= 180):
            raise ValueError(f"Invalid latitude/longitude range: {lat}, {lon}")
        return {"lat": lat, "lon": lon}


class ResourceValidator(BaseModel):
    resource_id: int
    task_count: int
    resource_position: PositionValidator


class StationValidator(BaseModel):
    station_id: int
    task_count: int
    station_name: str
    station_position: PositionValidator


class TaskValidator(BaseModel):
    id: str
    station_id: str
    time: datetime | None = None

    @field_validator("time", mode="before")
    @classmethod
    def parse_time(cls, v: Any) -> datetime | None:
        """Parse time from various formats to datetime object.

        Supports:
        - RFC 3339 / ISO 8601 datetime strings (e.g., "2025-11-06T08:00:00Z")
        - Simple time strings (e.g., "08:00") - converted to today's date
        - datetime objects (passed through)
        """
        if v is None or isinstance(v, datetime):
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

    @staticmethod
    def check_required_fields(
        item: Dict[str, Any], required_fields: List[str]
    ) -> List[Dict[str, str]]:
        return [
            {"field": f, "message": f"Missing required field '{f}'"}
            for f in required_fields
            if f not in item
        ]

    def validate_syntax(self, content: Dict[str, Any]) -> List[Dict[str, str]]:
        """Validate the syntax of scenario content only."""
        errors: List[Dict[str, str]] = []

        # Validate start_time and end_time exist and are properly formatted
        required_fields = ["start_time", "end_time"]
        errors.extend(self.check_required_fields(content, required_fields))

        # Validate time format and constraints
        try:
            ScenarioTimes(**content)
        except ValidationError as e:
            for err in e.errors():
                field_path = ".".join(map(str, err["loc"]))
                errors.append({"field": field_path, "message": err["msg"]})

        return errors

    def validate_stations(self, stations: List[Dict[str, Any]]) -> List[Dict[str, str]]:
        errors: List[Dict[str, str]] = []
        seen_ids: Set[int] = set()

        for idx, s in enumerate(stations):
            errors.extend(
                self.check_required_fields(
                    s,
                    [
                        "station_id",
                        "station_name",
                        "task_count",
                        "station_position",
                    ],
                )
            )
            station_id_raw: Any = s.get("station_id")
            if isinstance(station_id_raw, int):
                if station_id_raw in seen_ids:
                    errors.append(
                        {
                            "field": f"stations[{idx}].station_id",
                            "message": "Duplicate station ID",
                        }
                    )
                seen_ids.add(station_id_raw)

            try:
                StationValidator(**s)
            except ValidationError as e:
                for err in e.errors():
                    field_name = f"stations[{idx}].{'.'.join(map(str, err['loc']))}"
                    errors.append({"field": field_name, "message": err["msg"]})

        return errors

    def validate_resources(
        self, resources: List[Dict[str, Any]]
    ) -> List[Dict[str, str]]:
        errors: List[Dict[str, str]] = []
        seen_ids: Set[int] = set()

        for idx, r in enumerate(resources):
            errors.extend(
                self.check_required_fields(
                    r, ["resource_id", "task_count", "resource_position"]
                )
            )
            try:
                validated: ResourceValidator = ResourceValidator(**r)
                if validated.resource_id in seen_ids:
                    errors.append(
                        {
                            "field": f"resources[{idx}].resource_id",
                            "message": "Duplicate resource ID",
                        }
                    )
                seen_ids.add(validated.resource_id)
            except ValidationError as e:
                for err in e.errors():
                    field_name = f"resources[{idx}].{'.'.join(map(str, err['loc']))}"
                    errors.append({"field": field_name, "message": err["msg"]})

        return errors

    def validate_tasks(
        self, tasks: List[Dict[str, Any]], valid_station_ids: Set[str]
    ) -> List[Dict[str, str]]:
        errors: List[Dict[str, str]] = []
        seen_task_ids: Set[str] = set()

        for idx, task in enumerate(tasks):
            errors.extend(self.check_required_fields(task, ["id", "station_id"]))
            try:
                validated: TaskValidator = TaskValidator(**task)
                if validated.id in seen_task_ids:
                    errors.append(
                        {"field": f"tasks[{idx}].id", "message": "Duplicate task ID"}
                    )
                seen_task_ids.add(validated.id)

                if validated.station_id not in valid_station_ids:
                    errors.append(
                        {
                            "field": f"tasks[{idx}].station_id",
                            "message": (
                                f"Station ID {validated.station_id} does not exist"
                            ),
                        }
                    )
            except ValidationError as e:
                for err in e.errors():
                    field_name = f"tasks[{idx}].{'.'.join(map(str, err['loc']))}"
                    errors.append({"field": field_name, "message": err["msg"]})

        return errors

    def validate_simulation_params(
        self, params: Dict[str, Any]
    ) -> List[Dict[str, str]]:
        """Validate simulation time parameters.

        Ensures start_time and end_time are valid and that end_time is after start_time.
        Simulations cannot span more than 24 hours.
        """
        errors: List[Dict[str, str]] = []
        start_val: Any = params.get("start_time")
        end_val: Any = params.get("end_time")

        if start_val is not None and end_val is not None:
            try:
                # Parse times using ScenarioTimes validator
                scenario_times = ScenarioTimes(start_time=start_val, end_time=end_val)

                # Validate that end_time is after start_time
                if scenario_times.end_time <= scenario_times.start_time:
                    errors.append(
                        {
                            "field": "end_time",
                            "message": "end_time must be after start_time",
                        }
                    )

                # Validate that simulation doesn't span more than 24 hours
                duration = scenario_times.end_time - scenario_times.start_time
                if duration.total_seconds() > 86400:  # 24 hours in seconds
                    errors.append(
                        {
                            "field": "end_time",
                            "message": "Simulation duration cannot exceed 24 hours",
                        }
                    )
            except ValidationError as e:
                for err in e.errors():
                    field_path = ".".join(map(str, err["loc"]))
                    errors.append(
                        {
                            "field": field_path,
                            "message": err["msg"],
                        }
                    )

        return errors

    def validate_all(self, scenario_content: Dict[str, Any]) -> List[Dict[str, str]]:
        """Validate all aspects of scenario content."""
        errors: List[Dict[str, str]] = self.validate_syntax(scenario_content)

        stations: List[Dict[str, Any]] = scenario_content.get("stations", [])
        resources: List[Dict[str, Any]] = scenario_content.get("resources", [])
        initial_tasks: List[Dict[str, Any]] = scenario_content.get("initial_tasks", [])
        scheduled_tasks: List[Dict[str, Any]] = scenario_content.get(
            "scheduled_tasks", []
        )

        errors.extend(self.validate_stations(stations))
        errors.extend(self.validate_resources(resources))

        valid_station_ids: Set[str] = {str(s["station_id"]) for s in stations}
        for task_list in [initial_tasks, scheduled_tasks]:
            errors.extend(self.validate_tasks(task_list, valid_station_ids))

        errors.extend(self.validate_simulation_params(scenario_content))
        return errors
