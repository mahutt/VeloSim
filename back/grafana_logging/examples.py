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

from typing import Dict, List

from back.grafana_logging.logger import (
    get_logger,
    log_request,
    log_simulation_event,
)


def example_basic_logging() -> None:
    """Example: Basic logging in any Python module."""
    logger = get_logger(__name__)

    logger.debug("This is a debug message")
    logger.info("This is an info message")
    logger.warning("This is a warning message")
    logger.error("This is an error message")
    logger.critical("This is a critical message")


def example_backend_api_logging() -> List[str]:
    """Example: Logging in a FastAPI endpoint."""
    logger = get_logger("api.stations")

    # Log when endpoint is called
    logger.info("Fetching all stations from database")

    try:
        # Simulating database call
        stations = ["Station A", "Station B"]
        logger.info(f"Successfully retrieved {len(stations)} stations")
        return stations
    except Exception as e:
        logger.error(f"Failed to fetch stations: {e}", exc_info=True)
        raise


def example_http_request_logging() -> None:
    """Example: Logging HTTP requests."""
    import time

    start_time = time.time()

    # ... process request ...

    duration_ms = (time.time() - start_time) * 1000

    # Log the request
    log_request(
        method="GET", path="/api/v1/stations", status_code=200, duration_ms=duration_ms
    )


def example_simulator_logging() -> None:
    """Example: Logging in the simulator."""
    logger = get_logger("simulator")

    # Log simulation start
    logger.info("Starting new simulation run")

    # Log simulation steps with data
    log_simulation_event(
        event_type="STEP",
        message="Vehicle moved to new position",
        data={
            "vehicle_id": 123,
            "position": (10.5, 20.3),
            "speed": 15.2,
            "timestamp": "2025-10-12T14:30:00",
        },
    )

    # Log simulation completion
    log_simulation_event(
        event_type="COMPLETE",
        message="Simulation finished successfully",
        data={"total_steps": 1000, "duration_seconds": 45.2},
    )


def example_error_logging_with_context() -> None:
    """Example: Logging errors with full context."""
    logger = get_logger("database")

    try:
        # Simulating an error
        _ = 1 / 0
    except Exception as e:
        # Log with full traceback
        logger.error(
            f"Database operation failed: {e}",
            exc_info=True,  # Includes full stack trace
            extra={"operation": "insert", "table": "stations", "user_id": 12345},
        )


def example_conditional_logging() -> None:
    """Example: Conditional logging based on environment."""
    import os

    logger = get_logger(__name__)

    is_development = os.getenv("ENVIRONMENT", "development") == "development"

    if is_development:
        logger.debug("Detailed debug information for development")

    logger.info("This logs in all environments")


def example_structured_logging() -> None:
    """Example: Structured logging with consistent format."""
    logger = get_logger("user_service")

    user_id = 12345
    action = "login"

    # Structured log message for easy parsing
    logger.info(
        f"User action completed | user_id={user_id} | action={action} | status=success"
    )


def example_frontend_api_logging() -> None:
    """
    Example: FastAPI endpoint for receiving frontend logs.

    Add this to your FastAPI router:
    """
    from fastapi import APIRouter, Body

    router = APIRouter()
    frontend_logger = get_logger("frontend")

    @router.post("/api/v1/logs")
    async def log_from_frontend(
        level: str = Body(...), message: str = Body(...), context: dict = Body(None)
    ) -> Dict[str, str]:
        """Receive and log messages from the frontend."""
        # Map string level to logger method
        log_func = getattr(frontend_logger, level.lower(), frontend_logger.info)

        # Format message with context
        if context:
            context_str = ", ".join([f"{k}={v}" for k, v in context.items()])
            log_func(f"[Frontend] {message} | {context_str}")
        else:
            log_func(f"[Frontend] {message}")

        return {"status": "logged"}


if __name__ == "__main__":
    print("Running logging examples...")
    print("-" * 60)

    example_basic_logging()
    print()

    example_backend_api_logging()
    print()

    example_http_request_logging()
    print()

    example_simulator_logging()
    print()

    example_structured_logging()
    print()

    print("-" * 60)
    print("✅ Examples completed! Check logs.txt for output.")
    print("   View logs in Grafana: http://localhost:3000")
