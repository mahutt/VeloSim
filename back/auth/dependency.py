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

from typing import Annotated, Optional
from fastapi import Depends, WebSocket, Cookie, HTTPException
from fastapi.security import OAuth2PasswordBearer

from back.auth.auth import validate_access_token
from back.exceptions import WebSocketAuthError


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


async def get_user_id(token: Annotated[str, Depends(oauth2_scheme)]) -> int:
    """Extract and validate user ID from OAuth2 bearer token.

    Args:
        token: The OAuth2 bearer token from the request.

    Returns:
        int: The authenticated user's ID.
    """
    user_id = validate_access_token(token)
    if user_id is None:
        raise HTTPException(
            status_code=401,
            detail="Access token invalid",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user_id


async def get_user_id_over_websocket(
    websocket: WebSocket,
    access_token: Optional[str] = Cookie(None),
) -> int:
    """
    WebSocket-compatible authentication.
    Raises a WebSocketAuthError with the appropriate WebSocket error code if
    authentication fails.

    Args:
        websocket: The WebSocket connection containing authentication headers.
        access_token: Optional access token from cookie.

    Returns:
        int: The authenticated user's ID.
    """
    token_to_use: Optional[str] = None

    auth_header: Optional[str] = websocket.headers.get("authorization")
    if auth_header and auth_header.lower().startswith("bearer "):
        token_to_use = auth_header[7:]  # strip "Bearer "

    elif access_token:
        token_to_use = access_token

    if not token_to_use:
        raise WebSocketAuthError(websocket, code=1008)

    user_id = validate_access_token(token_to_use)
    if user_id is None:
        raise WebSocketAuthError(websocket, code=1008)

    return user_id
