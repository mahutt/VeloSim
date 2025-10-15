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

from fastapi import APIRouter, Depends, HTTPException
from back.auth.dependency import get_user_id
from back.database.session import get_db
from back.exceptions.bad_request_error import BadRequestError
from back.exceptions.velosim_permission_error import VelosimPermissionError
from back.schemas.user import UserCreate, UserResponse
from back.crud.user import user_crud
from sqlalchemy.orm import Session


router = APIRouter(prefix="/users", tags=["users"])


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
