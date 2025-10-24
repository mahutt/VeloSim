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

from sqlite3 import IntegrityError
from typing import List, Optional, Tuple
from argon2 import PasswordHasher
from argon2.profiles import RFC_9106_LOW_MEMORY
from sqlalchemy.orm import Session

from back.exceptions.bad_request_error import BadRequestError
from back.exceptions.velosim_permission_error import VelosimPermissionError
from back.models.user import User
from back.schemas import UserCreate, UserPasswordUpdate, UserRoleUpdate

ph = PasswordHasher.from_parameters(RFC_9106_LOW_MEMORY)


class UserCRUD:
    """CRUD operations for User model."""

    def get(self, db: Session, user_id: int) -> Optional[User]:
        """Get a user by ID."""
        return db.query(User).filter(User.id == user_id).first()

    def get_by_username(self, db: Session, username: str) -> Optional[User]:
        """Get a user by username."""
        return db.query(User).filter(User.username == username).first()

    def get_if_permission(
        self, db: Session, user_id: int, requesting_user_id: int
    ) -> Optional[User]:
        """Get a user by ID if the requester is the user themselves or an admin."""
        requesting_user = self.get(db, requesting_user_id)
        if not requesting_user or not requesting_user.is_enabled:
            raise VelosimPermissionError("Requesting user cannot access this user.")
        if requesting_user.id != user_id and not requesting_user.is_admin:
            raise VelosimPermissionError("Requesting user cannot access this user.")

        return self.get(db, user_id)

    def get_all(
        self,
        db: Session,
        is_enabled: Optional[bool],
        is_admin: Optional[bool],
        requesting_user_id: int,
        skip: int = 0,
        limit: int = 10,
    ) -> Tuple[List[User], int]:
        """Get all users with optional filters and pagination, if the requester is an
        admin."""
        requesting_user = self.get(db, requesting_user_id)
        if (
            not requesting_user
            or not requesting_user.is_admin
            or not requesting_user.is_enabled
        ):
            raise VelosimPermissionError("Requesting user cannot list users.")

        # Build the base query
        query = db.query(User)

        # Apply filters conditionally
        if is_enabled is not None:
            query = query.filter(User.is_enabled == is_enabled)
        if is_admin is not None:
            query = query.filter(User.is_admin == is_admin)

        # Get total count for pagination
        total = query.count()

        # Apply pagination
        users = query.offset(skip).limit(limit).all()

        return users, total

    def create(
        self, db: Session, user_data: UserCreate, requesting_user_id: int
    ) -> User:
        """Checks whether the requester is an admin, and if so, creates a new user."""
        requesting_user = self.get(db, requesting_user_id)
        if (
            not requesting_user
            or not requesting_user.is_admin
            or not requesting_user.is_enabled
        ):
            raise VelosimPermissionError("Requesting user cannot create users.")

        # Need to make this explicit for the test environment
        existing_user = self.get_by_username(db, user_data.username)
        if existing_user:
            raise BadRequestError("Username already exists")

        try:
            new_user = User(
                username=user_data.username,
                password_hash=self.hash_password(user_data.password),
                is_admin=user_data.is_admin,
                is_enabled=user_data.is_enabled,
            )
            db.add(new_user)
            db.flush()
            db.refresh(new_user)
            return new_user
        except IntegrityError:
            raise BadRequestError("Username already exists")

    def update_password(
        self,
        db: Session,
        user_id: int,
        password_data: UserPasswordUpdate,
        requesting_user_id: int,
    ) -> User:
        """Updates a password if the requester is the user themselves or an admin."""
        requesting_user = self.get(db, requesting_user_id)
        if not requesting_user or not requesting_user.is_enabled:
            raise VelosimPermissionError("Requesting user cannot update this password.")
        if requesting_user.id != user_id and not requesting_user.is_admin:
            raise VelosimPermissionError("Requesting user cannot update this password.")

        user = self.get(db, user_id)
        if not user:
            raise BadRequestError("User not found")

        user.password_hash = self.hash_password(password_data.password)
        db.add(user)
        db.flush()
        db.refresh(user)
        return user

    def update_role(
        self,
        db: Session,
        user_id: int,
        role_data: UserRoleUpdate,
        requesting_user_id: int,
    ) -> User:
        """Updates a user's role if the requester is an admin and not the user
        themselves."""
        requesting_user = self.get(db, requesting_user_id)
        if not requesting_user or not requesting_user.is_enabled:
            raise VelosimPermissionError("Requesting user cannot update this role.")
        if requesting_user.id == user_id or not requesting_user.is_admin:
            raise VelosimPermissionError("Requesting user cannot update this role.")

        user = self.get(db, user_id)
        if not user:
            raise BadRequestError("User not found")

        if role_data.is_admin is not None:
            user.is_admin = role_data.is_admin
        if role_data.is_enabled is not None:
            user.is_enabled = role_data.is_enabled

        db.add(user)
        db.flush()
        db.refresh(user)
        return user

    def hash_password(self, password: str) -> str:
        """Hashes the password in a manner that will be understood by
        auth.authenticate_user later. This had to be taken out of the auth module to
        avoid a circular import."""
        return str(ph.hash(password))


# Create a singleton instance
user_crud = UserCRUD()
