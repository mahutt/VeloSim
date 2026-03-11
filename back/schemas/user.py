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

from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, ConfigDict, Field
from back.exceptions.bad_request_error import BadRequestError


class UserBase(BaseModel):
    """Base schema for users."""

    pass


# Languages explicitly understood by the back-end (e.g. for email notifications).
# null means "use the client OS default".
SupportedLanguage = Optional[Literal["en", "fr"]]

# Prefix that marks a preference as front-end-only. The back-end stores it
# transparently without inspecting the value.
_FRONT_PREFIX = "front_"


class UserPreferencesUpdate(UserBase):
    """Schema for a preferences PATCH.

    Every field is optional; missing keys are left unchanged in the stored blob
    (shallow-merge semantics). Back-end-typed keys (``language``) are validated
    strictly. Any key whose name starts with ``front_`` is accepted without
    inspection and stored as-is. All other unknown top-level keys are rejected to
    catch typos early.
    """

    language: SupportedLanguage = Field(
        None,
        description='Preferred UI/notification language. "en", "fr", or null to '
        "use the OS default.",
    )

    model_config = ConfigDict(extra="allow")

    def validate_extra_keys(self) -> None:
        """Raise BadRequestError if any extra key does not start with 'front_'.

        Returns:
            None
        """
        for key in (self.model_extra or {}).keys():
            if not key.startswith(_FRONT_PREFIX):
                raise BadRequestError(
                    f"Unknown preference key '{key}'. "
                    f"Front-end-only keys must be prefixed with '{_FRONT_PREFIX}'."
                )

    @property
    def as_patch_dict(self) -> Dict[str, Any]:
        """Return only the explicitly-supplied fields as a plain dict.

        Returns:
            Dict containing only fields that were present in the PATCH payload,
            including both typed back-end keys and extra front_* keys.
        """
        result: Dict[str, Any] = {}
        for field_name in self.model_fields_set:
            result[field_name] = getattr(self, field_name)
        for key, val in (self.model_extra or {}).items():
            result[key] = val
        return result


class UserPreferencesResponse(UserBase):
    """Schema for the full preferences blob returned to the caller."""

    language: SupportedLanguage = Field(
        None,
        description="Preferred language, or null if not set.",
    )

    model_config = ConfigDict(extra="allow", from_attributes=False)

    @classmethod
    def from_blob(cls, blob: Optional[Dict[str, Any]]) -> "UserPreferencesResponse":
        """Construct a response from the raw preferences blob stored in the database.

        Args:
            blob: The preferences dict from the user model, or None if not set.

        Returns:
            UserPreferencesResponse populated from the blob, with defaults for
            any missing keys.
        """
        return cls(**(blob or {}))


class UserCreate(UserBase):
    """Schema for creating a new user."""

    username: str = Field(..., description="Username to create")
    password: str = Field(..., description="Password to set for the user")
    is_admin: bool = Field(..., description="Whether the user is an administrator")
    is_enabled: Optional[bool] = Field(
        True, description="Whether the account is enabled"
    )


class UserPasswordUpdate(UserBase):
    """Schema for updating user password."""

    password: str = Field(..., description="Password to set for the user")


class UserRoleUpdate(UserBase):
    """Schema for updating user role and status."""

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
