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

from typing import Optional
from enum import Enum
from pydantic import BaseModel, Field, field_validator, ConfigDict


class LogLevel(str, Enum):
    """Log level enumeration."""

    DEBUG = "debug"
    INFO = "info"
    WARN = "warn"
    ERROR = "error"


class FrontendLogEntry(BaseModel):
    """
    Schema for frontend log entries sent to backend.

    Matches the structure from front/app/utils/simulation-error-utils.ts:
    - message: error message string
    - stack: optional stack trace
    - context: optional context string (e.g., "Missing station data")
    - timestamp: ISO timestamp
    - userAgent: browser user agent
    - url: current page URL
    - Additional fields: entityType, entityId, errorType, etc.
    """

    message: str = Field(
        ..., min_length=1, max_length=2000, description="Log/error message"
    )
    timestamp: str = Field(
        ..., description="ISO timestamp when log was created on frontend"
    )
    level: Optional[LogLevel] = Field(
        default=LogLevel.ERROR,
        description=(
            "Log level (debug, info, warn, error). "
            "Defaults to error for backward compatibility."
        ),
    )
    stack: Optional[str] = Field(
        None, max_length=5000, description="Stack trace if available"
    )
    context: Optional[str] = Field(
        None,
        max_length=500,
        description="Context string (e.g., 'Missing station data')",
    )
    userAgent: Optional[str] = Field(
        None, max_length=500, description="Browser user agent string"
    )
    url: Optional[str] = Field(
        None, max_length=500, description="URL where log occurred"
    )

    entityType: Optional[str] = Field(
        None, max_length=100, description="Entity type (e.g., 'station', 'resource')"
    )
    entityId: Optional[int] = Field(None, description="Entity ID if applicable")
    errorType: Optional[str] = Field(
        None, max_length=100, description="Error type (e.g., 'MISSING_ENTITY_DATA')"
    )

    # Accept any additional fields frontend might send
    model_config = ConfigDict(extra="allow")

    @field_validator("message")
    @classmethod
    def validate_message_not_empty(cls, v: str) -> str:
        """Ensure message is not just whitespace."""
        if not v or not v.strip():
            raise ValueError("Message cannot be empty")
        return v


class FrontendLogResponse(BaseModel):
    """Response after logging frontend entry."""

    success: bool = Field(..., description="Whether log was recorded successfully")
    message: str = Field(default="Log recorded", description="Response message")
