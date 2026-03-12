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

import math
from fastapi import APIRouter, Depends, Query
from back.auth.dependency import get_user_id
from back.database.session import get_db
from back.exceptions import ItemNotFoundError
from back.schemas import (
    UserCreate,
    UserPasswordUpdate,
    UserRoleUpdate,
    UserResponse,
    UsersResponse,
    UserPreferencesUpdate,
    UserPreferencesResponse,
)
from back.crud.user import user_crud
from sqlalchemy.orm import Session


router = APIRouter(prefix="/users", tags=["users"])


@router.get("/", response_model=UsersResponse)
def get_users(
    is_enabled: bool | None = Query(
        None, description="Filter to enabled or disabled users", alias="isEnabled"
    ),
    is_admin: bool | None = Query(None, description="Filter by role", alias="isAdmin"),
    skip: int = Query(0, ge=0, description="Number of stations to skip"),
    limit: int = Query(10, ge=1, le=100, description="Number of stations to retrieve"),
    db: Session = Depends(get_db),
    requesting_user: int = Depends(get_user_id),
) -> UsersResponse:
    """Get all users with pagination.

    Args:
        is_enabled: Optional filter for enabled or disabled users.
        is_admin: Optional filter by admin role.
        skip: Number of records to skip for pagination (default: 0).
        limit: Maximum number of records to return (default: 10, max: 100).
        db: Database session dependency.
        requesting_user: ID of the user making the request.

    Returns:
        UsersResponse: Paginated list of users matching the filters.
    """
    users, total = user_crud.get_all(
        db,
        is_enabled,
        is_admin,
        requesting_user,
        skip,
        limit,
    )

    total_pages = math.ceil(total / limit) if total > 0 else 0
    page = (skip // limit) + 1

    return UsersResponse(
        users=[UserResponse.model_validate(user) for user in users],
        total=total,
        page=page,
        per_page=limit,
        total_pages=total_pages,
    )


@router.get("/me", response_model=UserResponse)
def get_me(
    db: Session = Depends(get_db),
    requesting_user: int = Depends(get_user_id),
) -> UserResponse:
    """Get the requesting user.

    Args:
        db: Database session dependency.
        requesting_user: ID of the user making the request.

    Returns:
        UserResponse: The requesting user's profile.
    """
    user = user_crud.get_if_permission(db, requesting_user, requesting_user)

    return UserResponse.model_validate(user)


@router.get("/{user_id}", response_model=UserResponse)
def get_by_id(
    user_id: int,
    db: Session = Depends(get_db),
    requesting_user: int = Depends(get_user_id),
) -> UserResponse:
    """Get the requested user if it is the user themselves, or the user is an admin.

    Args:
        user_id: The ID of the user to retrieve.
        db: Database session dependency.
        requesting_user: ID of the user making the request.

    Returns:
        UserResponse: The requested user's profile.
    """
    user = user_crud.get_if_permission(db, user_id, requesting_user)

    if not user:
        raise ItemNotFoundError("User not found")

    return UserResponse.model_validate(user)


@router.post("/create", response_model=UserResponse, status_code=201)
def create(
    user_create_data: UserCreate,
    db: Session = Depends(get_db),
    requesting_user: int = Depends(get_user_id),
) -> UserResponse:
    """Create a new user.

    The requesting user must be an admin.

    Args:
        user_create_data: The data for creating a new user.
        db: Database session dependency.
        requesting_user: ID of the user making the request.

    Returns:
        UserResponse: The created user profile.
    """
    new_user = user_crud.create(db, user_create_data, requesting_user)
    return UserResponse.model_validate(new_user)


@router.put("/{user_id}/password", response_model=UserResponse)
def password_update(
    user_id: int,
    password_data: UserPasswordUpdate,
    db: Session = Depends(get_db),
    requesting_user: int = Depends(get_user_id),
) -> UserResponse:
    """Update a user's password.

    The requesting user must be an admin or the user themselves.

    Args:
        user_id: The ID of the user whose password to update.
        password_data: The new password data.
        db: Database session dependency.
        requesting_user: ID of the user making the request.

    Returns:
        UserResponse: The updated user profile.
    """
    updated_user = user_crud.update_password(
        db, user_id, password_data, requesting_user
    )
    return UserResponse.model_validate(updated_user)


@router.put("/{user_id}/role", response_model=UserResponse)
def role_update(
    user_id: int,
    role_data: UserRoleUpdate,
    db: Session = Depends(get_db),
    requesting_user: int = Depends(get_user_id),
) -> UserResponse:
    """Update a user's role.

    The requesting user must be an admin. The requesting user cannot change their own
    role. This prevents an admin from demoting themselves without another admin to
    restore access to the app.

    Args:
        user_id: The ID of the user whose role to update.
        role_data: The new role data.
        db: Database session dependency.
        requesting_user: ID of the user making the request.

    Returns:
        UserResponse: The updated user profile.
    """
    updated_user = user_crud.update_role(db, user_id, role_data, requesting_user)
    return UserResponse.model_validate(updated_user)


@router.get("/me/preferences", response_model=UserPreferencesResponse)
def get_my_preferences(
    db: Session = Depends(get_db),
    requesting_user: int = Depends(get_user_id),
) -> UserPreferencesResponse:
    """Get the requesting user's own preferences.

    Args:
        db: Database session dependency.
        requesting_user: ID of the user making the request.

    Returns:
        UserPreferencesResponse: The preferences blob.
    """
    return get_user_preferences(
        user_id=requesting_user, db=db, requesting_user=requesting_user
    )


@router.get("/{user_id}/preferences", response_model=UserPreferencesResponse)
def get_user_preferences(
    user_id: int,
    db: Session = Depends(get_db),
    requesting_user: int = Depends(get_user_id),
) -> UserPreferencesResponse:
    """Get a user's preferences.

    The requesting user must be the user themselves or an admin.

    Args:
        user_id: The ID of the user whose preferences to retrieve.
        db: Database session dependency.
        requesting_user: ID of the user making the request.

    Returns:
        UserPreferencesResponse: The preferences blob.
    """
    user = user_crud.get_if_permission(db, user_id, requesting_user)
    if not user:
        raise ItemNotFoundError("User not found")
    return UserPreferencesResponse.from_blob(user.preferences)


@router.patch("/me/preferences", response_model=UserPreferencesResponse)
def update_my_preferences(
    preferences_data: UserPreferencesUpdate,
    db: Session = Depends(get_db),
    requesting_user: int = Depends(get_user_id),
) -> UserPreferencesResponse:
    """Merge the supplied keys into the requesting user's own preferences.

    Args:
        preferences_data: Partial preferences to merge.
        db: Database session dependency.
        requesting_user: ID of the user making the request.

    Returns:
        UserPreferencesResponse: The full updated preferences blob.
    """
    return update_preferences(
        user_id=requesting_user,
        preferences_data=preferences_data,
        db=db,
        requesting_user=requesting_user,
    )


@router.patch("/{user_id}/preferences", response_model=UserPreferencesResponse)
def update_preferences(
    user_id: int,
    preferences_data: UserPreferencesUpdate,
    db: Session = Depends(get_db),
    requesting_user: int = Depends(get_user_id),
) -> UserPreferencesResponse:
    """Merge the supplied keys into a user's preferences.

    The requesting user must be the user themselves or an admin.
    Only the keys present in the request body are modified; other stored keys are
    left untouched. Front-end-only keys must be prefixed with ``front_``.

    Args:
        user_id: The ID of the user whose preferences to update.
        preferences_data: Partial preferences to merge.
        db: Database session dependency.
        requesting_user: ID of the user making the request.

    Returns:
        UserPreferencesResponse: The full updated preferences blob.
    """
    updated_user = user_crud.update_preferences(
        db, user_id, preferences_data, requesting_user
    )
    return UserPreferencesResponse.from_blob(updated_user.preferences)
