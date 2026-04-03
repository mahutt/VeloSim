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
from typing import Optional, List

from pydantic import BaseModel, ConfigDict, Field, model_validator


MAX_TEMPLATE_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB


class TrafficTemplateBase(BaseModel):
    """Base schema shared by traffic template create and update models."""

    content: Optional[str] = Field(
        None,
        description="Traffic CSV content with required headers",
        min_length=1,
        max_length=MAX_TEMPLATE_SIZE_BYTES,
    )
    description: Optional[str] = Field(
        None,
        description="Optional template description",
    )


class TrafficTemplateCreateRequest(BaseModel):
    """API request schema for creating a traffic template."""

    key: str = Field(
        ...,
        description="Stable template key (1-32 chars, lowercase letters/digits/_/-)",
        pattern=r"^[a-z0-9_-]{1,32}$",
    )
    content: str = Field(
        ...,
        description="Traffic CSV content (max 10 MB)",
        min_length=1,
        max_length=MAX_TEMPLATE_SIZE_BYTES,
    )
    description: Optional[str] = Field(
        None,
        description="Optional template description",
    )


class TrafficTemplateCreate(BaseModel):
    """Internal schema for creating a traffic template."""

    key: str = Field(..., pattern=r"^[a-z0-9_-]{1,32}$")
    content: str = Field(..., min_length=1, max_length=MAX_TEMPLATE_SIZE_BYTES)
    description: Optional[str] = None


class TrafficTemplateUpdateRequest(BaseModel):
    """API request schema for updating a traffic template."""

    content: Optional[str] = Field(
        None,
        description="Traffic CSV content with required headers",
        min_length=1,
        max_length=MAX_TEMPLATE_SIZE_BYTES,
    )
    description: Optional[str] = Field(
        None,
        description="Optional template description",
    )

    @model_validator(mode="after")
    def _require_at_least_one_field(self) -> "TrafficTemplateUpdateRequest":
        if self.content is None and self.description is None:
            raise ValueError("At least one of content or description must be provided")
        return self


class TrafficTemplateUpdate(BaseModel):
    """Internal schema for updating a traffic template."""

    content: Optional[str] = Field(
        None, min_length=1, max_length=MAX_TEMPLATE_SIZE_BYTES
    )
    description: Optional[str] = None

    @model_validator(mode="after")
    def _require_at_least_one_field(self) -> "TrafficTemplateUpdate":
        if self.content is None and self.description is None:
            raise ValueError("At least one of content or description must be provided")
        return self


class TrafficTemplateResponse(BaseModel):
    """Traffic template response schema."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    key: str
    content: str
    description: Optional[str] = None
    date_created: datetime
    date_updated: datetime


class TrafficTemplateSummaryResponse(BaseModel):
    """Traffic template metadata response schema used for list endpoints."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    key: str
    description: Optional[str] = None
    date_created: datetime
    date_updated: datetime


class TrafficTemplateListResponse(BaseModel):
    """Paginated traffic template summary response schema."""

    templates: List[TrafficTemplateSummaryResponse]
    total: int
    page: int
    per_page: int
    total_pages: int


class TrafficTemplateValidationRequest(BaseModel):
    """Validation request schema for CSV traffic template content."""

    content: str = Field(..., min_length=1, max_length=MAX_TEMPLATE_SIZE_BYTES)


class TrafficTemplateValidationResponse(BaseModel):
    """Validation response schema for CSV traffic template content."""

    valid: bool
    errors: List[str] = Field(default_factory=list)
