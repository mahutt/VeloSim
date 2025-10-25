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

from typing import List, Optional, Any
from pydantic import BaseModel, Field, field_validator, ConfigDict, computed_field

from back.schemas.utils import validate_longitude, validate_latitude


class PositionSchema(BaseModel):
    """Schema for position data [longitude, latitude]."""

    longitude: float = Field(..., description="Longitude coordinate")
    latitude: float = Field(..., description="Latitude coordinate")

    @field_validator("longitude")
    @classmethod
    def check_longitude(cls, v: Any) -> float:
        return validate_longitude(v)

    @field_validator("latitude")
    @classmethod
    def check_latitude(cls, v: Any) -> float:
        return validate_latitude(v)


class StationBase(BaseModel):
    """Base station schema with common fields."""

    name: str = Field(..., min_length=1, max_length=100, description="Station name")
    longitude: float = Field(..., description="Station longitude")
    latitude: float = Field(..., description="Station latitude")

    @field_validator("longitude")
    @classmethod
    def check_longitude(cls, v: Any) -> float:
        return validate_longitude(v)

    @field_validator("latitude")
    @classmethod
    def check_latitude(cls, v: Any) -> float:
        return validate_latitude(v)


class StationCreate(StationBase):
    """Schema for creating a new station."""

    sim_instance_id: int


class StationUpdate(BaseModel):
    """Schema for updating a station."""

    name: Optional[str] = Field(
        None, min_length=1, max_length=100, description="Station name"
    )
    longitude: Optional[float] = Field(None, description="Station longitude")
    latitude: Optional[float] = Field(None, description="Station latitude")

    @field_validator("longitude")
    @classmethod
    def check_optional_longitude(cls, v: Any) -> Optional[float]:
        if v is not None:
            return validate_longitude(v)
        return None

    @field_validator("latitude")
    @classmethod
    def check_optional_latitude(cls, v: Any) -> Optional[float]:
        if v is not None:
            return validate_latitude(v)
        return None


class StationResponse(BaseModel):
    """Schema for station responses."""

    id: int = Field(..., description="Station ID")
    name: str = Field(..., description="Station name")
    sim_instance_id: int
    longitude: float = Field(..., exclude=True)  # Hidden field for position calculation
    latitude: float = Field(..., exclude=True)  # Hidden field for position calculation

    model_config = ConfigDict(from_attributes=True)

    @computed_field
    def position(self) -> list[float]:
        """Get position as [longitude, latitude] to match simulation model."""
        return [self.longitude, self.latitude]


class StationListResponse(BaseModel):
    """Schema for paginated station list responses."""

    stations: List[StationResponse] = Field(..., description="List of stations")
    total: int = Field(..., description="Total number of stations")
    page: int = Field(..., description="Current page number")
    per_page: int = Field(..., description="Items per page")
    total_pages: int = Field(..., description="Total number of pages")
