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
from typing import Any, Dict, List, Optional
from pydantic import UUID4, BaseModel, ConfigDict, Field, computed_field


class SimInstanceBase(BaseModel):
    """Base schema for SimInstance."""

    user_id: int


class SimInstanceCreate(SimInstanceBase):
    """Schema for creating a new SimInstance."""

    scenario_payload: Optional[Dict[str, Any]] = None
    name: Optional[str] = None
    parent_sim_instance_id: Optional[int] = None
    branch_keyframe_seq: Optional[int] = None


class SimInstanceResponse(SimInstanceBase):
    """Schema for SimInstance response."""

    id: int
    name: Optional[str] = None
    playback_capable: bool = False
    parent_sim_instance_id: Optional[int] = None
    branch_keyframe_seq: Optional[int] = None
    date_created: datetime
    date_updated: datetime
    uuid: UUID4
    completed: bool = Field(default=False)

    model_config = ConfigDict(from_attributes=True)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def resource_count(self) -> int:
        """Compute the number of drivers.

        Returns:
            int: Number of drivers in the simulation instance.
        """
        return len(self.drivers) if hasattr(self, "drivers") else 0

    @computed_field  # type: ignore[prop-decorator]
    @property
    def station_count(self) -> int:
        """Compute the number of stations.

        Returns:
            int: Number of stations in the simulation instance.
        """
        return len(self.stations) if hasattr(self, "stations") else 0

    @computed_field  # type: ignore[prop-decorator]
    @property
    def task_count(self) -> int:
        """Compute the number of tasks.

        Returns:
            int: Number of tasks in the simulation instance.
        """
        return len(self.tasks) if hasattr(self, "tasks") else 0


class SimulationResponse(BaseModel):
    """Response schema for simulation operations."""

    sim_id: str
    db_id: int
    status: str


class SimulationListResponse(BaseModel):
    """Response schema for paginated simulation list."""

    simulations: List[SimInstanceResponse]
    total: int
    page: int
    per_page: int
    total_pages: int


class BranchRequest(BaseModel):
    """Request schema for branching a simulation from a keyframe.

    If keyframe_seq does not point to an actual keyframe (is_key=True),
    the branch will occur from the most recent prior keyframe.
    """

    keyframe_seq: int
    name: Optional[str] = None


class BranchResponse(BaseModel):
    """Response schema for branch operation."""

    sim_id: str  # UUID of the new simulation
    db_id: int  # Database ID of the new simulation
    name: Optional[str]  # Name of the new simulation
    branched_from_sim_id: str  # Original simulation UUID
    branched_from_keyframe_seq: int  # The actual keyframe seq used for branching
    status: str  # "created" - sim not yet running
