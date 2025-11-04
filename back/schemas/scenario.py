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

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, ConfigDict, computed_field


class ScenarioBase(BaseModel):
    """Base schema with optional fields shared between create and update."""

    name: Optional[str] = Field(None, description="Name of the scenario")
    content: Optional[Dict[str, Any]] = Field(
        None, description="JSON or dictionary content"
    )
    description: Optional[str] = Field(
        None, description="Optional scenario description"
    )


class ScenarioCreate(ScenarioBase):
    """Schema for creating a new scenario. Required fields enforced."""

    name: str = Field(..., description="Name of the scenario")
    content: Dict[str, Any] = Field(..., description="JSON content for the scenario")
    user_id: int = Field(..., description="ID of the user who owns the scenario")


class ScenarioUpdate(ScenarioBase):
    """Schema for updating a scenario. All fields optional for partial update."""

    pass


class ScenarioResponse(BaseModel):
    """Schema for returning a scenario from the API."""

    id: int
    name: str
    content: Dict[str, Any]
    description: Optional[str] = None
    user_id: int
    date_created: Optional[str] = None
    date_updated: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

    @computed_field
    def content_size(self) -> int:
        """Return the approximate size of the content (number of keys for dict)."""
        return len(self.content) if isinstance(self.content, dict) else 0


class ScenarioListResponse(BaseModel):
    """Schema for paginated scenario list responses."""

    scenarios: List[ScenarioResponse] = Field(..., description="List of scenarios")
    total: int = Field(..., description="Total number of scenarios")
    page: int = Field(..., description="Current page number")
    per_page: int = Field(..., description="Items per page")
    total_pages: int = Field(..., description="Total number of pages")
