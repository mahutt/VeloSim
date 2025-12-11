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

from typing import List
from fastapi import APIRouter, Depends, HTTPException, Request
from back.schemas.frontend_log import FrontendLogEntry, FrontendLogResponse
from back.services.frontend_log_service import frontend_log_service
from back.auth.dependency import get_user_id
from datetime import datetime, timedelta
from collections import defaultdict

router = APIRouter(prefix="/logs", tags=["logs"])

# Simple in-memory rate limiting (per user)
_rate_limit_store: dict[int, list[datetime]] = defaultdict(list)
MAX_LOGS_PER_MINUTE = 60  # Allow 60 log entries per minute per user
RATE_LIMIT_WINDOW = timedelta(minutes=1)


def check_rate_limit(user_id: int) -> bool:
    """
    Check if user has exceeded rate limit for logging.

    Args:
        user_id: The user ID to check

    Returns:
        True if within rate limit, False if exceeded
    """
    now = datetime.now()
    user_logs = _rate_limit_store[user_id]

    # Remove old entries outside the window
    _rate_limit_store[user_id] = [
        ts for ts in user_logs if now - ts < RATE_LIMIT_WINDOW
    ]

    # Check if limit exceeded
    if len(_rate_limit_store[user_id]) >= MAX_LOGS_PER_MINUTE:
        return False

    # Add current timestamp
    _rate_limit_store[user_id].append(now)
    return True


@router.post("/frontend", response_model=FrontendLogResponse, status_code=201)
async def log_frontend_entry(
    request: Request,
    log_entry: FrontendLogEntry,
    user_id: int = Depends(get_user_id),
) -> FrontendLogResponse:
    """Receive and persist a log entry from the frontend.

    Args:
        request: FastAPI request object containing headers and metadata
        log_entry: Frontend log entry data to be recorded
        user_id: ID of the authenticated user making the request

    Returns:
        FrontendLogResponse indicating success or failure of the operation
    """
    # Check rate limit
    if not check_rate_limit(user_id):
        raise HTTPException(
            status_code=429,
            detail=(
                "Rate limit exceeded. "
                "Maximum " + str(MAX_LOGS_PER_MINUTE) + " logs per minute."
            ),
        )

    try:
        # Add user agent from request headers if not provided
        if not log_entry.userAgent and "user-agent" in request.headers:
            log_entry.userAgent = request.headers["user-agent"]

        # Process and log the entry
        frontend_log_service.log_entry(log_entry, user_id)

        return FrontendLogResponse(success=True, message="Log recorded successfully")

    except Exception as e:
        # Log the error but don't fail - logging should be resilient
        frontend_log_service.logger.error(
            f"Failed to process frontend log: {str(e)}", exc_info=True
        )
        raise HTTPException(status_code=500, detail="Failed to process log entry")


@router.post("/frontend/batch", response_model=FrontendLogResponse, status_code=201)
async def log_frontend_batch(
    request: Request,
    log_entries: List[FrontendLogEntry],
    user_id: int = Depends(get_user_id),
) -> FrontendLogResponse:
    """Receive and persist multiple log entries from the frontend in a batch.

    Args:
        request: FastAPI request object containing headers and metadata
        log_entries: List of frontend log entries to be recorded (max 50)
        user_id: ID of the authenticated user making the request

    Returns:
        FrontendLogResponse indicating success and number of entries processed
    """
    # Validate batch size
    if len(log_entries) > 50:
        raise HTTPException(
            status_code=400,
            detail="Batch size too large. Maximum 50 log entries per batch.",
        )

    # Check rate limit (count each log in batch)
    for _ in range(len(log_entries)):
        if not check_rate_limit(user_id):
            raise HTTPException(
                status_code=429,
                detail=(
                    "Rate limit exceeded. "
                    "Maximum " + str(MAX_LOGS_PER_MINUTE) + " logs per minute."
                ),
            )

    try:
        # Add user agent to entries if not provided
        user_agent = request.headers.get("user-agent")
        for entry in log_entries:
            if not entry.userAgent and user_agent:
                entry.userAgent = user_agent

        # Process all log entries
        frontend_log_service.log_batch(log_entries, user_id)

        return FrontendLogResponse(
            success=True,
            message=(
                "Batch recorded successfully: " + str(len(log_entries)) + " entries"
            ),
        )

    except Exception as e:
        frontend_log_service.logger.error(
            f"Failed to process frontend log batch: {str(e)}", exc_info=True
        )
        raise HTTPException(status_code=500, detail="Failed to process log batch")
