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

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, ConfigDict


class SimStateResponse(BaseModel):
    """Schema for current simulation state convenience endpoint.

    Simplified wrapper around keyframe data for easy access to current simulation state.
    """

    sim_id: str = Field(..., description="UUID of the simulation instance")
    sim_seconds: float = Field(
        ..., ge=0, description="Simulation time in seconds when state was captured"
    )
    clock: Dict[str, Any] = Field(..., description="Simulation clock information")
    tasks: Optional[List[Dict[str, Any]]] = Field(
        default=None, description="List of tasks if included"
    )
    drivers: Optional[List[Dict[str, Any]]] = Field(
        default=None, description="List of drivers if included"
    )
    stations: Optional[List[Dict[str, Any]]] = Field(
        default=None, description="List of stations if included"
    )
    vehicles: Optional[List[Dict[str, Any]]] = Field(
        default=None, description="List of vehicles if included"
    )
    headquarters: Optional[Dict[str, Any]] = Field(
        default=None, description="Headquarters information if included"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "sim_id": "abc123-sim-uuid",
                "sim_seconds": 3600.5,
                "clock": {
                    "simSecondsPassed": 3600.5,
                    "simMinutesPassed": 60.0,
                    "realSecondsPassed": 36.05,
                    "realMinutesPassed": 0.6,
                    "startTime": "2026-02-05T10:00:00Z",
                    "running": True,
                    "realTimeFactor": 100,
                    "pausedByUser": False,
                },
                "tasks": [
                    {
                        "id": 1,
                        "state": "OPEN",
                        "stationId": 5,
                        "priority": 1,
                    }
                ],
                "drivers": [
                    {
                        "id": 1,
                        "state": "IDLE",
                        "position": [45.5017, -73.5673],
                    }
                ],
                "stations": [
                    {
                        "id": 1,
                        "name": "Station Alpha",
                        "position": [45.5017, -73.5673],
                    }
                ],
                "vehicles": [
                    {
                        "id": 1,
                        "batteryCount": 85,
                        "batteryCapacity": 100,
                        "driverId": 1,
                    }
                ],
            }
        },
        json_encoders={},  # Add any custom JSON encoders if needed
    )
