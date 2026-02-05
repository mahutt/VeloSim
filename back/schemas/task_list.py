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

from typing import List, Optional
from pydantic import BaseModel, Field


class TaskStation(BaseModel):
    """Nested station information in task response."""

    id: int = Field(..., description="Station ID")
    name: str = Field(..., description="Station name")
    position: List[float] = Field(..., description="Station position [lon, lat]")


class TaskItem(BaseModel):
    """Individual task item in list response."""

    id: int = Field(..., description="Task ID")
    state: str = Field(
        ..., description="Task state (OPEN, ASSIGNED, IN_PROGRESS, COMPLETED)"
    )
    station_id: int = Field(..., description="Station ID where task is located")
    driver_id: Optional[int] = Field(
        None, description="Assigned driver ID, null if unassigned"
    )
    task_type: str = Field(..., description="Task type (PICKUP, DROPOFF, etc.)")
    priority: int = Field(..., description="Task priority")
    created_at: Optional[str] = Field(None, description="Task creation timestamp")
    station: Optional[TaskStation] = Field(None, description="Station details")


class TaskListResponse(BaseModel):
    """Response schema for task listing endpoint."""

    tasks: List[TaskItem] = Field(..., description="List of tasks")
    total: int = Field(..., description="Total number of tasks matching filters")
    page: int = Field(..., description="Current page number")
    per_page: int = Field(..., description="Items per page")
    total_pages: int = Field(..., description="Total number of pages")
