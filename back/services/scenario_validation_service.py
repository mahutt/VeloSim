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
from pydantic import BaseModel, ValidationError, model_validator
from datetime import time, datetime
import re

from back.schemas.scenario import ScenarioResponse


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
    time: str | None = None

    @model_validator(mode="before")
    def validate_time_format(cls, values: Dict[str, Any]) -> Dict[str, Any]:
        t: str | None = values.get("time")
        if t is not None and not re.match(r"^\d{2}:\d{2}$", t):
            raise ValueError(f"time must be in HH:MM format, got '{t}'")
        return values


class ScenarioTimes(BaseModel):
    start_time: time
    end_time: time


class ScenarioValidator:
    """Validator for scenario content."""

    @staticmethod
    def check_required_fields(
        item: Dict[str, Any], required_fields: List[str]
    ) -> List[Dict[str, str]]:
        return [
            {"field": f, "error": f"Missing required field '{f}'"}
            for f in required_fields
            if f not in item
        ]

    def validate_syntax(self, content: Dict[str, Any]) -> List[Dict[str, str]]:
        errors: List[Dict[str, str]] = []

        required_fields = [
            name
            for name, field in ScenarioResponse.model_fields.items()
            if getattr(field, "is_required", False)
        ]
        errors.extend(self.check_required_fields(content, required_fields))

        if "content" in content:
            scenario_content = content["content"]
            try:
                ScenarioTimes(**scenario_content)
            except ValidationError as e:
                for err in e.errors():
                    field_path = "content." + ".".join(map(str, err["loc"]))
                    errors.append({"field": field_path, "error": err["msg"]})
        else:
            errors.append(
                {"field": "content", "error": "Missing required field 'content'"}
            )

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
                            "error": "Duplicate station ID",
                        }
                    )
                seen_ids.add(station_id_raw)

            try:
                StationValidator(**s)
            except ValidationError as e:
                for err in e.errors():
                    field_name = f"stations[{idx}].{'.'.join(map(str, err['loc']))}"
                    errors.append({"field": field_name, "error": err["msg"]})

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
                            "error": "Duplicate resource ID",
                        }
                    )
                seen_ids.add(validated.resource_id)
            except ValidationError as e:
                for err in e.errors():
                    field_name = f"resources[{idx}].{'.'.join(map(str, err['loc']))}"
                    errors.append({"field": field_name, "error": err["msg"]})

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
                        {"field": f"tasks[{idx}].id", "error": "Duplicate task ID"}
                    )
                seen_task_ids.add(validated.id)

                if validated.station_id not in valid_station_ids:
                    errors.append(
                        {
                            "field": f"tasks[{idx}].station_id",
                            "error": (
                                f"Station ID {validated.station_id} does not exist"
                            ),
                        }
                    )
            except ValidationError as e:
                for err in e.errors():
                    field_name = f"tasks[{idx}].{'.'.join(map(str, err['loc']))}"
                    errors.append({"field": field_name, "error": err["msg"]})

        return errors

    def validate_simulation_params(
        self, params: Dict[str, Any]
    ) -> List[Dict[str, str]]:
        errors: List[Dict[str, str]] = []
        start_str: Any = params.get("start_time")
        end_str: Any = params.get("end_time")

        if isinstance(start_str, str) and isinstance(end_str, str):
            try:
                start_dt: datetime = datetime.strptime(start_str, "%H:%M")
                end_dt: datetime = datetime.strptime(end_str, "%H:%M")
                if end_dt <= start_dt:
                    errors.append(
                        {
                            "field": "end_time",
                            "error": "end_time must be after start_time",
                        }
                    )
            except ValueError as e:
                errors.append(
                    {
                        "field": "start_time/end_time",
                        "error": f"Invalid time format: {e}",
                    }
                )

        return errors

    def validate_all(self, scenario: Dict[str, Any]) -> List[Dict[str, str]]:
        errors: List[Dict[str, str]] = self.validate_syntax(scenario)

        content: Dict[str, Any] = scenario.get("content", {})
        stations: List[Dict[str, Any]] = content.get("stations", [])
        resources: List[Dict[str, Any]] = content.get("resources", [])
        initial_tasks: List[Dict[str, Any]] = content.get("initial_tasks", [])
        scheduled_tasks: List[Dict[str, Any]] = content.get("scheduled_tasks", [])

        errors.extend(self.validate_stations(stations))
        errors.extend(self.validate_resources(resources))

        valid_station_ids: Set[str] = {str(s["station_id"]) for s in stations}
        for task_list in [initial_tasks, scheduled_tasks]:
            errors.extend(self.validate_tasks(task_list, valid_station_ids))

        errors.extend(self.validate_simulation_params(content))
        return errors
