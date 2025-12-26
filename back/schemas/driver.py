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

from typing import List
from pydantic import BaseModel, Field


class DriverTaskAssignRequest(BaseModel):
    """Request schema for assigning a task to a driver."""

    driver_id: int = Field(..., description="ID of the driver to assign the task to")
    task_id: int = Field(..., description="ID of the task to assign")


class DriverTaskAssignResponse(BaseModel):
    """Response schema for successfully assigning a task to a driver."""

    driver_id: int = Field(..., description="ID of the driver the task was assigned to")
    task_id: int = Field(..., description="ID of the task that was assigned")


class DriverTaskUnassignRequest(BaseModel):
    """Request schema for unassigning a task from a driver."""

    driver_id: int = Field(
        ..., description="ID of the driver from which to unassign the task"
    )
    task_id: int = Field(..., description="ID of the task to unassign")


class DriverTaskUnassignResponse(BaseModel):
    """Response schema for successfully unassigning a task from a driver."""

    driver_id: int = Field(
        ..., description="ID of the driver the task was unassigned from"
    )
    task_id: int = Field(..., description="ID of the task that was unassigned")


class DriverTaskReassignRequest(BaseModel):
    """Request schema for reassigning a task from one driver to another."""

    old_driver_id: int = Field(
        ..., description="ID of the driver currently assigned to the task"
    )
    new_driver_id: int = Field(
        ..., description="ID of the driver to reassign the task to"
    )
    task_id: int = Field(..., description="ID of the task to reassign")


class DriverTaskReassignResponse(BaseModel):
    """Response schema for successfully reassigning a task to a new driver."""

    old_driver_id: int = Field(
        ..., description="ID of the driver the task was reassigned from"
    )
    new_driver_id: int = Field(
        ..., description="ID of the driver the task was reassigned to"
    )
    task_id: int = Field(..., description="ID of the task that was reassigned")


class DriverTaskReorderRequest(BaseModel):
    """Request schema for reordering tasks in a driver's task list."""

    driver_id: int = Field(..., description="ID of the driver whose tasks to reorder")
    task_ids: List[int] = Field(
        ...,
        description="Partial list of task IDs to reorder (must be non-empty)",
        min_length=1,
    )
    apply_from_top: bool = Field(
        ...,
        description=(
            "If true, insert tasks after in-progress tasks; " "if false, append to end"
        ),
    )


class DriverTaskReorderResponse(BaseModel):
    """Response schema for successfully reordering tasks."""

    driver_id: int = Field(
        ..., description="ID of the driver whose tasks were reordered"
    )
    task_order: List[int] = Field(
        ..., description="Complete list of task IDs in new order"
    )
