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
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, ConfigDict, computed_field


class Position(BaseModel):
    """Schema for geographic position (latitude, longitude)."""

    lat: float = Field(..., ge=-90, le=90, description="Latitude")
    lon: float = Field(..., ge=-180, le=180, description="Longitude")


class Station(BaseModel):
    """Schema for a station in the scenario."""

    station_id: int = Field(..., description="Unique station identifier")
    station_name: str = Field(..., description="Name of the station")
    task_count: int = Field(..., ge=0, description="Number of tasks at this station")
    station_position: List[float] | Position = Field(
        ..., description="Position as [lat, lon] or Position object"
    )


class Resource(BaseModel):
    """Schema for a resource in the scenario."""

    resource_id: int = Field(..., description="Unique resource identifier")
    task_count: int = Field(..., ge=0, description="Number of tasks for this resource")
    resource_position: List[float] | Position = Field(
        ..., description="Position as [lat, lon] or Position object"
    )


class Task(BaseModel):
    """Schema for a task in the scenario."""

    id: str = Field(..., description="Unique task identifier")
    station_id: str = Field(..., description="ID of the station this task belongs to")
    time: Optional[datetime | str] = Field(
        None,
        description="Task scheduled time (RFC 3339 format or HH:MM)",
    )


class ScenarioContent(BaseModel):
    """Type-safe schema for scenario content.

    This defines the expected structure for scenario JSON content,
    supporting both type checking and validation.
    """

    scenario_title: Optional[str] = Field(None, description="Title of the scenario")
    start_time: datetime | str = Field(
        ...,
        description=(
            "Simulation start time (RFC 3339 format like "
            "'2025-11-06T08:00:00Z' or simple 'HH:MM')"
        ),
    )
    end_time: datetime | str = Field(
        ...,
        description=(
            "Simulation end time (RFC 3339 format like "
            "'2025-11-06T17:00:00Z' or simple 'HH:MM'). "
            "Cannot exceed 24 hours from start_time."
        ),
    )
    stations: List[Station] = Field(
        default_factory=list, description="List of stations in the scenario"
    )
    resources: List[Resource] = Field(
        default_factory=list, description="List of resources in the scenario"
    )
    initial_tasks: List[Task] = Field(
        default_factory=list, description="Initial tasks to be assigned"
    )
    scheduled_tasks: List[Task] = Field(
        default_factory=list, description="Tasks scheduled for specific times"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "scenario_title": "Multi-day Delivery Scenario",
                "start_time": "2025-11-06T08:00:00Z",
                "end_time": "2025-11-07T17:00:00Z",  # Spans 2 days
                "resources": [
                    {
                        "resource_id": 1,
                        "resource_position": [45.5070, -73.5610],
                        "task_count": 5,
                    }
                ],
                "stations": [
                    {
                        "station_id": 1,
                        "station_name": "Main Hub",
                        "station_position": [45.50137, -73.57314],
                        "task_count": 5,
                    }
                ],
                "initial_tasks": [{"id": "t1", "station_id": "1"}],
                "scheduled_tasks": [
                    {
                        "id": "t2",
                        "station_id": "1",
                        "time": "2025-11-06T14:30:00Z",
                    }
                ],
            }
        }
    )


class ScenarioBase(BaseModel):
    """Base schema with optional fields shared between create and update."""

    name: Optional[str] = Field(None, description="Name of the scenario")
    content: Optional[Dict[str, Any]] = Field(
        None,
        description=(
            "Scenario content (see ScenarioContent schema for "
            "type-safe structure). Stored as JSONB in database for "
            "flexibility while maintaining type safety through validation."
        ),
    )
    description: Optional[str] = Field(
        None, description="Optional scenario description"
    )


class ScenarioCreate(ScenarioBase):
    """Schema for creating a new scenario. Required fields enforced."""

    name: str = Field(..., description="Name of the scenario")
    content: Dict[str, Any] = Field(
        ...,
        description="Scenario content (validated against ScenarioContent schema). "
        "Use RFC 3339 datetime format for multi-day scenarios.",
    )
    user_id: int = Field(..., description="ID of the user who owns the scenario")


class ScenarioCreateRequest(BaseModel):
    """Schema for API request to create a scenario (user_id comes from auth)."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "My Test Scenario",
                "content": {
                    "scenario_title": "My Test Scenario",
                    "start_time": "08:00",
                    "end_time": "12:00",
                    "resources": [
                        {
                            "resource_id": 1,
                            "resource_position": [45.5070, -73.5610],
                            "task_count": 2,
                        }
                    ],
                    "stations": [
                        {
                            "station_id": 1,
                            "station_name": "Test Station",
                            "station_position": [45.50137, -73.57314],
                            "task_count": 2,
                        }
                    ],
                    "initial_tasks": [{"id": "t1", "station_id": "1"}],
                    "scheduled_tasks": [
                        {"id": "t2", "station_id": "1", "time": "09:30"}
                    ],
                },
                "description": "A sample scenario for testing",
                "allow_duplicate_name": False,
            }
        }
    )

    name: str = Field(..., description="Name of the scenario")
    content: Dict[str, Any] = Field(..., description="JSON content for the scenario")
    description: Optional[str] = Field(
        None, description="Optional scenario description"
    )
    allow_duplicate_name: bool = Field(
        False, description="Allow duplicate scenario names for the same user"
    )


class ScenarioUpdateRequest(BaseModel):
    """Schema for API request to update a scenario."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "Updated Scenario Name",
                "content": {
                    "scenario_title": "Updated Scenario Name",
                    "start_time": "08:00",
                    "end_time": "12:00",
                    "resources": [
                        {
                            "resource_id": 1,
                            "resource_position": [45.5070, -73.5610],
                            "task_count": 2,
                        }
                    ],
                    "stations": [
                        {
                            "station_id": 1,
                            "station_name": "Updated Station",
                            "station_position": [45.50137, -73.57314],
                            "task_count": 2,
                        }
                    ],
                    "initial_tasks": [{"id": "t1", "station_id": "1"}],
                    "scheduled_tasks": [
                        {"id": "t2", "station_id": "1", "time": "09:30"}
                    ],
                },
                "description": "Updated scenario description",
            }
        }
    )

    name: Optional[str] = Field(None, description="New name for the scenario")
    content: Optional[Dict[str, Any]] = Field(None, description="New JSON content")
    description: Optional[str] = Field(None, description="New description")


class ScenarioUpdate(ScenarioBase):
    """Schema for updating a scenario. All fields optional for partial update."""

    pass


class ScenarioResponse(BaseModel):
    """Schema for returning a scenario from the API."""

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": 1,
                "name": "Test Scenario",
                "content": {
                    "scenario_title": "Test Scenario",
                    "start_time": "08:00",
                    "end_time": "12:00",
                    "resources": [
                        {
                            "resource_id": 1,
                            "resource_position": [45.5070, -73.5610],
                            "task_count": 2,
                        }
                    ],
                    "stations": [
                        {
                            "station_id": 1,
                            "station_name": "Test Station",
                            "station_position": [45.50137, -73.57314],
                            "task_count": 2,
                        }
                    ],
                    "initial_tasks": [{"id": "t1", "station_id": "1"}],
                    "scheduled_tasks": [
                        {"id": "t2", "station_id": "1", "time": "09:30"}
                    ],
                },
                "description": "Test description for Scenario",
                "user_id": 1,
                "date_created": "2025-11-05T14:30:00",
                "date_updated": "2025-11-05T14:30:00",
                "content_size": 6,
            }
        },
    )

    id: int
    name: str
    content: Dict[str, Any]
    description: Optional[str] = None
    user_id: int
    date_created: datetime
    date_updated: datetime

    @computed_field
    def content_size(self) -> int:
        """Return the approximate size of the content (number of keys for dict)."""
        return len(self.content) if isinstance(self.content, dict) else 0


class ScenarioListResponse(BaseModel):
    """Schema for paginated scenario list responses."""

    scenarios: List[ScenarioResponse] = Field(..., description="List of scenarios")
    total: int = Field(..., description="Total number of scenarios")
    page: int = Field(..., description="Current page number")
    per_page: int = Field(..., description="Items per page")
    total_pages: int = Field(..., description="Total number of pages")


class ScenarioValidationRequest(BaseModel):
    """Schema for scenario validation requests."""

    content: Dict[str, Any] = Field(..., description="Scenario content to validate")


class ScenarioValidationResponse(BaseModel):
    """Schema for scenario validation responses."""

    valid: bool = Field(..., description="Whether the scenario is valid")
    errors: List[str] = Field(
        default_factory=list, description="List of validation errors"
    )
    warnings: List[str] = Field(
        default_factory=list, description="List of validation warnings"
    )
