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

from enum import Enum
from pydantic import BaseModel, Field, field_validator

ALLOWED_SPEEDS = {0.0, 0.5, 1.0, 2.0, 4.0, 8.0}


class PlaybackSpeedBase(BaseModel):
    """Base schema for playback speed."""

    playback_speed: float = Field(...)

    @field_validator("playback_speed")
    def validate_speed(cls, v: float) -> float:
        if v not in ALLOWED_SPEEDS:
            raise ValueError(f"Playback speed must be one of {sorted(ALLOWED_SPEEDS)}")
        return v


class SimulationPlaybackStatus(str, Enum):
    INITIALIZED = "initialized"
    RUNNING = "running"
    PAUSED = "paused"


class PlaybackSpeedResponse(PlaybackSpeedBase):
    simulation_id: str
    status: SimulationPlaybackStatus
