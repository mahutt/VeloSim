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

from typing import List, Optional, Type
from pydantic import BaseModel, Field, field_validator, ConfigDict, computed_field
from back.models.resource_type import ResourceType
from back.schemas import StationTaskResponse
from back.schemas.utils import validate_latitude, validate_longitude


class ResourceBase(BaseModel):
    """Base resource schema with common fields."""

    latitude: float = Field(..., description="Current position latitude")
    longitude: float = Field(..., description="Current position longitude")
    route_start_latitude: float = Field(..., description="Current route start latitude")
    route_start_longitude: float = Field(
        ..., description="Current route start longitude"
    )
    route_end_latitude: float = Field(..., description="Current route end latitude")
    route_end_longitude: float = Field(..., description="Current route end longitude")

    @field_validator("latitude", "route_start_latitude", "route_end_latitude")
    @classmethod
    def check_latitude(cls: Type["ResourceBase"], v: float) -> float:
        return validate_latitude(v)

    @field_validator("longitude", "route_start_longitude", "route_end_longitude")
    @classmethod
    def check_longitude(cls: Type["ResourceBase"], v: float) -> float:
        return validate_longitude(v)


class ResourceCreate(ResourceBase):
    """Schema for creating a new resource."""

    type: ResourceType = Field(..., description="Type of resource")

    pass


class ResourceUpdate(BaseModel):
    """Schema for updating a resource, namely the current position and start/end
    of route."""

    latitude: Optional[float] = Field(None, description="Current latitude position")
    longitude: Optional[float] = Field(None, description="Current longitude position")
    route_start_latitude: Optional[float] = Field(
        None, description="Route start latitude"
    )
    route_start_longitude: Optional[float] = Field(
        None, description="Route start longitude"
    )
    route_end_latitude: Optional[float] = Field(None, description="Route end latitude")
    route_end_longitude: Optional[float] = Field(
        None, description="Route end longitude"
    )

    @field_validator("latitude", "route_start_latitude", "route_end_latitude")
    @classmethod
    def check_optional_latitude(
        cls: Type["ResourceUpdate"], v: Optional[float]
    ) -> Optional[float]:
        if v is not None:
            return validate_latitude(v)
        return None

    @field_validator("longitude", "route_start_longitude", "route_end_longitude")
    @classmethod
    def check_optional_longitude(
        cls: Type["ResourceUpdate"], v: Optional[float]
    ) -> Optional[float]:
        if v is not None:
            return validate_longitude(v)
        return None


class ResourceTaskAssign(BaseModel):
    """Schema for assigning a task to a resource."""

    task_id: int = Field(..., description="ID of the task to assign")


class ResourceTaskUnassign(BaseModel):
    """Schema for unassigning a task from a resource."""

    task_id: int = Field(..., description="ID of the task to unassign")


class ResourceTaskIDsRequest(BaseModel):
    """Request model for operations on one or more tasks for a resource."""

    task_ids: List[int]


class ResourceResponse(BaseModel):
    """Schema for resource responses with tasks."""

    id: int
    type: ResourceType
    latitude: float = Field(..., exclude=True)  # Hidden field for position calculation
    longitude: float = Field(..., exclude=True)  # Hidden field for position calculation
    route_start_latitude: float = Field(
        ..., exclude=True
    )  # Hidden field for route start calculation
    route_start_longitude: float = Field(
        ..., exclude=True
    )  # Hidden field for route start calculation
    route_end_latitude: float = Field(
        ..., exclude=True
    )  # Hidden field for route end calculation
    route_end_longitude: float = Field(
        ..., exclude=True
    )  # Hidden field for route end calculation

    model_config = ConfigDict(from_attributes=True)

    @computed_field
    def position(self) -> List[float]:
        """Get current position as [longitude, latitude] to match sim model."""
        return [self.longitude, self.latitude]

    @computed_field
    def route(self) -> List[List[float]]:
        """Get current route as [[start_long, start_lat], [end_long, end_lat]]
        to match provisional sim model."""
        return [
            [self.route_start_longitude, self.route_start_latitude],
            [self.route_end_longitude, self.route_end_latitude],
        ]

    tasks: List[StationTaskResponse] = Field(default_factory=list)
    """The list of full tasks assigned to this resource to match sim model."""

    @computed_field
    def task_count(self) -> int:
        """Return number of tasks assigned to this resource to match sim model."""
        return len(self.tasks)


class ResourceListResponse(BaseModel):
    """Schema for paginated resource list responses."""

    resources: List[ResourceResponse] = Field(..., description="List of resources")
    total: int = Field(..., description="Total number of resources")
    page: int = Field(..., description="Current page number")
    per_page: int = Field(..., description="Items per page")
    total_pages: int = Field(..., description="Total number of pages")
