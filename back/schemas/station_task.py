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

from pydantic import BaseModel, Field
from back.models import StationTaskType, TaskStatus


class StationTaskBase(BaseModel):
    """Base schema for station tasks."""

    type: StationTaskType = Field(..., description="Type of station task")
    station_id: int = Field(..., description="ID of the related station")


class StationTaskCreate(StationTaskBase):
    """Schema for creating a station task."""

    pass


class StationTaskUpdate(BaseModel):
    """Schema for updating a station task."""

    status: TaskStatus = Field(..., description="New task completion status")


class StationTaskResponse(BaseModel):
    """Schema for station task responses."""

    id: int = Field(..., description="Station task ID")
    status: TaskStatus = Field(..., description="Task completion status")
    date_created: str = Field(..., description="Creation timestamp")
    date_updated: str = Field(..., description="Last update timestamp")
