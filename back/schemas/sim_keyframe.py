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
from typing import Any, Dict, List
from pydantic import BaseModel, Field, ConfigDict


class SimKeyframeBase(BaseModel):
    """Base schema for simulation keyframe."""

    sim_instance_id: int = Field(..., description="ID of the simulation instance")
    sim_seconds_elapsed: float = Field(
        ..., ge=0, description="Simulation time in seconds when keyframe was captured"
    )
    frame_data: Dict[str, Any] = Field(
        ..., description="Complete frame payload with simulation state"
    )


class SimKeyframeCreate(SimKeyframeBase):
    """Schema for creating a new simulation keyframe."""

    pass


class SimKeyframeResponse(SimKeyframeBase):
    """Schema for simulation keyframe response."""

    id: int = Field(..., description="Unique keyframe identifier")
    created_at: datetime = Field(..., description="When the keyframe was persisted")

    model_config = ConfigDict(from_attributes=True)


class SimKeyframeListResponse(BaseModel):
    """Schema for paginated list of simulation keyframes."""

    keyframes: List[SimKeyframeResponse] = Field(
        default_factory=list, description="List of keyframes"
    )
    total: int = Field(..., description="Total number of keyframes")
    page: int = Field(..., description="Current page number (1-indexed)")
    per_page: int = Field(..., description="Number of items per page")
    total_pages: int = Field(..., description="Total number of pages")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "keyframes": [
                    {
                        "id": 1,
                        "sim_instance_id": 123,
                        "sim_seconds_elapsed": 120.5,
                        "frame_data": {
                            "simId": "abc-123",
                            "tasks": [],
                            "stations": [],
                            "resources": [],
                            "clock": {"simSecondsPassed": 120.5},
                        },
                        "created_at": "2025-12-18T10:30:00Z",
                    }
                ],
                "total": 50,
                "page": 1,
                "per_page": 20,
                "total_pages": 3,
            }
        }
    )
