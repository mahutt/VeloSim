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
from fastapi import APIRouter, Depends, HTTPException, Query
from back.auth.dependency import get_user_id
from back.database.session import get_db
from back.exceptions.bad_request_error import BadRequestError
from back.exceptions.velosim_permission_error import VelosimPermissionError
from back.schemas import (
    UserCreate,
    UserPasswordUpdate,
    UserRoleUpdate,
    UserResponse,
    UsersResponse,
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
    """Get all station tasks with pagination."""
    try:
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
    except VelosimPermissionError as err:
        raise HTTPException(status_code=401, detail=err.args)


@router.post("/create", response_model=UserResponse, status_code=201)
async def create(
    user_create_data: UserCreate,
    db: Session = Depends(get_db),
    requesting_user: int = Depends(get_user_id),
) -> UserResponse:
    """Create a new user.

    The requesting user must be an admin."""
    try:
        new_user = user_crud.create(db, user_create_data, requesting_user)
        return UserResponse.model_validate(new_user)
    except BadRequestError as err:
        raise HTTPException(status_code=400, detail=err.args)
    except VelosimPermissionError as err:
        raise HTTPException(status_code=401, detail=err.args)


@router.put("/{user_id}/password", response_model=UserResponse)
async def password_update(
    user_id: int,
    password_data: UserPasswordUpdate,
    db: Session = Depends(get_db),
    requesting_user: int = Depends(get_user_id),
) -> UserResponse:
    """Update a user's password.

    The requesting user must be an admin or the user themselves."""
    try:
        updated_user = user_crud.update_password(
            db, user_id, password_data, requesting_user
        )
        return UserResponse.model_validate(updated_user)
    except BadRequestError as err:
        raise HTTPException(status_code=400, detail=err.args)
    except VelosimPermissionError as err:
        raise HTTPException(status_code=401, detail=err.args)


@router.put("/{user_id}/role", response_model=UserResponse)
async def role_update(
    user_id: int,
    role_data: UserRoleUpdate,
    db: Session = Depends(get_db),
    requesting_user: int = Depends(get_user_id),
) -> UserResponse:
    """Update a user's role.

    The requesting user must be an admin. The requesting user cannot change their own
    role. This prevents an admin from demoting themselves without another admin to
    restore access to the app."""
    try:
        updated_user = user_crud.update_role(db, user_id, role_data, requesting_user)
        return UserResponse.model_validate(updated_user)
    except BadRequestError as err:
        raise HTTPException(status_code=400, detail=err.args)
    except VelosimPermissionError as err:
        raise HTTPException(status_code=401, detail=err.args)
