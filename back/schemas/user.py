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

from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field


class UserBase(BaseModel):
    """Base schema for users."""

    pass


class UserCreate(UserBase):
    """Schema for creating a new user"""

    username: str = Field(..., description="Username to create")
    password: str = Field(..., description="Password to set for the user")
    is_admin: bool = Field(..., description="Whether the user is an administrator")
    is_enabled: Optional[bool] = Field(
        True, description="Whether the account is enabled"
    )


class UserPasswordUpdate(UserBase):
    password: str = Field(..., description="Password to set for the user")


class UserRoleUpdate(UserBase):
    is_admin: Optional[bool] = Field(
        None, description="Whether the user is an administrator"
    )
    is_enabled: Optional[bool] = Field(
        None, description="Whether the account is enabled"
    )


class UserResponse(UserBase):
    """Schema for user responses."""

    id: int = Field(..., description="The internal identifier for the user")
    username: str = Field(..., description="Username")
    is_admin: bool = Field(..., description="Whether the user is an administrator")
    is_enabled: bool = Field(..., description="Whether the account is enabled")

    model_config = ConfigDict(from_attributes=True)


class UsersResponse(BaseModel):
    """Schema for paginated user responses."""

    users: List[UserResponse] = Field(..., description="List of users")
    total: int = Field(..., description="Total number of users")
    page: int = Field(..., description="Current page number")
    per_page: int = Field(..., description="Items per page")
    total_pages: int = Field(..., description="Total number of pages")
