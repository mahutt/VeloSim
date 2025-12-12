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
        """Validate latitude is within valid range.

        Args:
            v: The latitude value to validate.

        Returns:
            float: Validated latitude value.
        """
        return validate_latitude(v)

    @field_validator("longitude", "route_start_longitude", "route_end_longitude")
    @classmethod
    def check_longitude(cls: Type["ResourceBase"], v: float) -> float:
        """Validate longitude is within valid range.

        Args:
            v: The longitude value to validate.

        Returns:
            float: Validated longitude value.
        """
        return validate_longitude(v)


class ResourceCreate(ResourceBase):
    """Schema for creating a new resource."""

    type: ResourceType = Field(..., description="Type of resource")
    sim_instance_id: int


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
        """Validate optional latitude is within valid range.

        Args:
            v: The optional latitude value to validate.

        Returns:
            Optional[float]: Validated latitude value or None.
        """
        if v is not None:
            return validate_latitude(v)
        return None

    @field_validator("longitude", "route_start_longitude", "route_end_longitude")
    @classmethod
    def check_optional_longitude(
        cls: Type["ResourceUpdate"], v: Optional[float]
    ) -> Optional[float]:
        """Validate optional longitude is within valid range.

        Args:
            v: The optional longitude value to validate.

        Returns:
            Optional[float]: Validated longitude value or None.
        """
        if v is not None:
            return validate_longitude(v)
        return None


class ResourceTaskIDsRequest(BaseModel):
    """Request model for operations on one or more tasks for a resource."""

    task_ids: List[int]


class ResourceResponse(BaseModel):
    """Schema for resource responses with tasks."""

    id: int
    type: ResourceType
    sim_instance_id: int
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

    tasks: List[StationTaskResponse] = Field(default_factory=list)
    """The list of full tasks assigned to this resource to match sim model."""

    model_config = ConfigDict(from_attributes=True)

    @computed_field
    def position(self) -> List[float]:
        """Get current position as [longitude, latitude] to match sim model.

        Returns:
            List[float]: Position as [longitude, latitude].
        """
        return [self.longitude, self.latitude]

    @computed_field
    def route(self) -> List[List[float]]:
        """Get current route as [[start_long, start_lat], [end_long, end_lat]]
        to match provisional sim model.

        Returns:
            List[List[float]]: Route as [[start_long, start_lat], [end_long, end_lat]].
        """
        return [
            [self.route_start_longitude, self.route_start_latitude],
            [self.route_end_longitude, self.route_end_latitude],
        ]

    @computed_field
    def task_count(self) -> int:
        """Return number of tasks assigned to this resource to match sim model.

        Returns:
            int: Number of assigned tasks.
        """
        return len(self.tasks)


class ResourceListResponse(BaseModel):
    """Schema for paginated resource list responses."""

    resources: List[ResourceResponse] = Field(..., description="List of resources")
    total: int = Field(..., description="Total number of resources")
    page: int = Field(..., description="Current page number")
    per_page: int = Field(..., description="Items per page")
    total_pages: int = Field(..., description="Total number of pages")


class ResourceTaskAssignRequest(BaseModel):
    """Request schema for assigning a task to a resource."""

    task_id: int = Field(..., description="ID of the task to assign")
    resource_id: int = Field(
        ..., description="ID of the resource to assign the task to"
    )


class ResourceTaskAssignResponse(BaseModel):
    """Response schema for successfully assigning a task to a resource."""

    resource_id: int
    task_id: int


class ResourceTaskUnassignRequest(BaseModel):
    """Request schema for unassigning a task from a resource."""

    task_id: int = Field(..., description="ID of the task to unassign")
    resource_id: int = Field(
        ..., description="ID of the resource from which to unassign the task"
    )


class ResourceTaskUnassignResponse(BaseModel):
    """Response schema for successfully unassigning a task from a resource."""

    resource_id: int
    task_id: int


class ResourceTaskReassignRequest(BaseModel):
    """Request schema for reassigning a task from one resource to another."""

    task_id: int
    old_resource_id: int
    new_resource_id: int


class ResourceTaskReassignResponse(BaseModel):
    """Response schema for successfully reassigning a task to a new resource."""

    task_id: int
    old_resource_id: int
    new_resource_id: int


class ResourceTaskReorderRequest(BaseModel):
    """Request schema for reordering tasks in a resource's task list."""

    resource_id: int = Field(
        ..., description="ID of the resource whose tasks to reorder"
    )
    task_ids: list[int] = Field(
        ...,
        min_length=1,
        description="Partial list of task IDs to reorder (must be non-empty)",
    )
    apply_from_top: bool = Field(
        ...,
        description=(
            "If true, insert tasks after in-progress tasks; " "if false, append to end"
        ),
    )


class ResourceTaskReorderResponse(BaseModel):
    """Response schema for successfully reordering tasks in a resource's task list."""

    resource_id: int = Field(
        ..., description="ID of the resource whose tasks were reordered"
    )
    task_order: list[int] = Field(
        ..., description="Complete list of task IDs in new order"
    )
