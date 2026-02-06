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

from typing import List, Optional, Sequence
from pydantic import BaseModel, Field


class DriverTask(BaseModel):
    """Task information in driver response when expanded."""

    id: int = Field(..., description="Task ID")
    state: str = Field(..., description="Task state")
    station_id: int = Field(..., description="Station ID")


class DriverVehicle(BaseModel):
    """Vehicle information in driver response when expanded."""

    id: int = Field(..., description="Vehicle ID")
    battery_count: int = Field(..., description="Current battery count")
    battery_capacity: int = Field(..., description="Battery capacity")


class DriverItem(BaseModel):
    """Individual driver item in list response."""

    id: int = Field(..., description="Driver ID")
    state: str = Field(
        ..., description="Driver state (IDLE, ON_ROUTE, EXECUTING_TASK, CHARGING)"
    )
    position: List[float] = Field(..., description="Driver position [lon, lat]")
    vehicle_id: Optional[int] = Field(None, description="Assigned vehicle ID")
    tasks: Sequence[int | DriverTask] = Field(
        default_factory=list, description="Task IDs or full task objects if expanded"
    )
    current_task: Optional[int] = Field(
        None, description="Current task ID, null if no active task"
    )
    battery_level: Optional[float] = Field(None, description="Battery level percentage")
    vehicle: Optional[DriverVehicle] = Field(
        None, description="Vehicle details if expanded"
    )


class DriverListResponse(BaseModel):
    """Response schema for driver listing endpoint."""

    drivers: List[DriverItem] = Field(..., description="List of drivers")
    total: int = Field(..., description="Total number of drivers matching filters")
    page: int = Field(..., description="Current page number")
    per_page: int = Field(..., description="Items per page")
    total_pages: int = Field(..., description="Total number of pages")
