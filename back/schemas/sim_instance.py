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
from typing import List
from pydantic import BaseModel, ConfigDict, computed_field


class SimInstanceBase(BaseModel):
    """Base schema for SimInstance."""

    user_id: int


class SimInstanceCreate(SimInstanceBase):
    """Schema for creating a new SimInstance."""

    pass


class SimInstanceResponse(SimInstanceBase):
    """Schema for SimInstance response."""

    id: int
    date_created: datetime
    date_updated: datetime

    model_config = ConfigDict(from_attributes=True)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def resource_count(self) -> int:
        """Compute the number of resources.

        Returns:
            int: Number of resources in the simulation instance.
        """
        return len(self.resources) if hasattr(self, "resources") else 0

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
