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

from datetime import datetime, timedelta, timezone
from math import floor
import os
import secrets

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from argon2.profiles import RFC_9106_LOW_MEMORY
import jwt

from back.crud.user import user_crud
from back.database.session import get_db

ph = PasswordHasher.from_parameters(RFC_9106_LOW_MEMORY)

jwt_secret: str = os.getenv("VELOSIM_JWT_SECRET")  # type: ignore
if not jwt_secret:
    jwt_secret = secrets.token_hex(32)
    print("WARNING: JWT secret environment variable not set. Generated a random key.")
    print("WARNING: This means JWT tokens will be invalid after server restart.")
    print("WARNING: Set VELOSIM_JWT_SECRET environment variable for production use.")

ACCESS_TOKEN_LIFE = timedelta(minutes=30)
JWT_ALGORITHM = "HS256"


def authenticate_user(username: str | None, password: str | None) -> str | None:
    """Attempts to authenticate the user and issue an access token. Returns None if the
    user cannot be authenticated with these credentials.
    """
    if username is None or password is None:
        return None

    db = next(get_db())
    user = user_crud.get_by_username(db, username)
    if user is None or not user.is_enabled:
        return None

    try:
        ph.verify(user.password_hash, password)
        return generate_access_token(user.id)
    except VerifyMismatchError:
        return None


def generate_access_token(user_id: int) -> str:
    """Returns a JSON Web Token (JWT) for a given user ID which can be validated in the
    future.
    """
    now = datetime.now(timezone.utc)
    token_data: dict[str, str | int] = {
        "iat": floor(now.timestamp()),
        "exp": floor((now + ACCESS_TOKEN_LIFE).timestamp()),
        "sub": "user:" + str(user_id),
    }
    token: str = jwt.encode(token_data, jwt_secret, algorithm=JWT_ALGORITHM)
    return token


def validate_access_token(access_token: str) -> int | None:
    """Attempts to validate the access token and returns the user ID contained within
    the signed token if still valid, or None if it cannot be validated.
    """
    try:
        now = floor(datetime.now(timezone.utc).timestamp())
        payload = jwt.decode(access_token, jwt_secret, algorithms=[JWT_ALGORITHM])
        if "iat" not in payload or payload["iat"] > now:
            return None
        if "exp" not in payload or payload["exp"] < now:
            return None
        if "sub" not in payload or payload["sub"][0:5] != "user:":
            return None
        # Remove user: prefix
        return int(payload["sub"][5:])
    except jwt.exceptions.InvalidTokenError:
        return None
