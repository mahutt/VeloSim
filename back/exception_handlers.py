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

import logging

from fastapi import Request, status
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)


async def unexpected_error_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle UnexpectedError exceptions with a consistent HTTP 500 response.

    Args:
        request: The incoming HTTP request that triggered the exception.
        exc: The UnexpectedError exception instance.

    Returns:
        JSONResponse with HTTP 500 status code and a generic error detail.
    """
    logger.error("UnexpectedError at %s: %s", request.url.path, str(exc))
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "An unexpected error occurred."},
    )


async def bad_request_error_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle BadRequestError exceptions with a consistent HTTP 400 response.

    Args:
        request: The incoming HTTP request that triggered the exception.
        exc: The BadRequestError exception instance.

    Returns:
        JSONResponse with HTTP 400 status code and error detail.
    """
    logger.warning("BadRequestError at %s: %s", request.url.path, str(exc))
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={"detail": str(exc)},
    )


async def item_not_found_error_handler(
    request: Request, exc: Exception
) -> JSONResponse:
    """Handle ItemNotFoundError exceptions with a consistent HTTP 404 response.

    Args:
        request: The incoming HTTP request that triggered the exception.
        exc: The ItemNotFoundError exception instance.

    Returns:
        JSONResponse with HTTP 404 status code and error detail.
    """
    logger.warning("ItemNotFoundError at %s: %s", request.url.path, str(exc))
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content={"detail": str(exc)},
    )


async def velosim_permission_error_handler(
    request: Request, exc: Exception
) -> JSONResponse:
    """Handle VelosimPermissionError exceptions with a consistent HTTP 403 response.

    Args:
        request: The incoming HTTP request that triggered the exception.
        exc: The VelosimPermissionError exception instance.

    Returns:
        JSONResponse with HTTP 403 status code and error detail.
    """
    logger.warning("VelosimPermissionError at %s: %s", request.url.path, str(exc))
    return JSONResponse(
        status_code=status.HTTP_403_FORBIDDEN,
        content={"detail": str(exc)},
    )
