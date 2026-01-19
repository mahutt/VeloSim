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


class SimFrameBase(BaseModel):
    """Base schema for simulation frame."""

    sim_instance_id: int = Field(..., description="ID of the simulation instance")
    seq_number: int = Field(
        ..., ge=0, description="Frame sequence number (unique per sim instance)"
    )
    sim_seconds_elapsed: float = Field(
        ..., ge=0, description="Simulation time in seconds when frame was captured"
    )
    frame_data: Dict[str, Any] = Field(
        ..., description="Complete frame payload with simulation state"
    )
    is_key: bool = Field(
        ..., description="True if this is a keyframe, false if diff frame"
    )


class SimFrameCreate(SimFrameBase):
    """Schema for creating a new simulation frame (keyframe or diff)."""

    pass


class SimFrameResponse(SimFrameBase):
    """Schema for simulation frame response."""

    id: int = Field(..., description="Unique frame identifier")
    created_at: datetime = Field(..., description="When the frame was persisted")

    model_config = ConfigDict(from_attributes=True)


class SimFrameListResponse(BaseModel):
    """Schema for paginated list of simulation frames."""

    frames: List[SimFrameResponse] = Field(..., description="List of simulation frames")
    total: int = Field(..., description="Total number of frames")
    has_more: bool = Field(
        ..., description="Whether there are more frames beyond this page"
    )


class SeekResponse(BaseModel):
    """Response for seek endpoint.

    Contains the frames needed to reach a target position and frames
    to play forward from that position.
    """

    sim_id: str = Field(..., description="UUID of the simulation")
    initial_frames: List[SimFrameResponse] = Field(
        ...,
        description=(
            "Keyframe + diff frames to apply instantly "
            "to reach the requested position"
        ),
    )
    future_frames: List[SimFrameResponse] = Field(
        ...,
        description="Diff frames to play sequentially after the initial state",
    )
    has_more_frames: bool = Field(
        ...,
        description="True if there are more frames beyond the returned window",
    )
    current_sim_seconds: float = Field(
        ...,
        description="The current live simulation time (if sim is running)",
    )
    is_at_live_edge: bool = Field(
        ...,
        description="True if the returned frames reach the current execution point",
    )
    playback_speed: float = Field(
        ...,
        description="Current playback speed of the simulation",
    )
