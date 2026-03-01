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
from typing import Dict, Any, List
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session
from pydantic import BaseModel

from back.database.session import get_db
from back.auth.dependency import get_user_id
from back.crud.scenario import scenario_crud
from back.exceptions import (
    BadRequestError,
    ItemNotFoundError,
    UnexpectedError,
    VelosimPermissionError,
)
from back.schemas.scenario import (
    ScenarioCreate,
    ScenarioCreateRequest,
    ScenarioListResponse,
    ScenarioResponse,
    ScenarioUpdate,
    ScenarioUpdateRequest,
)
from sim.utils.json_parser_strategy import JsonParseStrategy
from grafana_logging.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/scenarios", tags=["scenarios"])


async def get_raw_body(request: Request) -> bytes:
    """Async dependency that reads and returns the raw request body.

    Allows route handlers to be plain ``def`` while still accessing the raw
    body for line-number extraction, avoiding a blocking session inside an
    ``async def`` handler.

    Args:
        request: The incoming FastAPI request object.

    Returns:
        The raw request body as bytes.
    """
    return await request.body()


class ValidationRequest(BaseModel):
    """Request schema for validating scenario content only."""

    content: Dict[str, Any]


class ValidationResponse(BaseModel):
    """Response schema for validation endpoint."""

    valid: bool
    errors: List[Dict[str, Any]] = []


@router.post("/validate", response_model=ValidationResponse)
async def validate_scenario_content(
    request: Request, validation_request: ValidationRequest
) -> ValidationResponse:
    """Validate scenario content without creating a scenario.

    Extracts line numbers from the original JSON for better error reporting.

    Args:
        request: FastAPI request object for accessing raw body
        validation_request: Scenario content to validate

    Returns:
        ValidationResponse with validation status and any errors found
    """
    # Get the raw body for line number extraction
    raw_body = await request.body()
    try:
        json_string = raw_body.decode("utf-8")
    except UnicodeDecodeError:
        # If decoding fails, return validation error
        return ValidationResponse(
            valid=False,
            errors=[
                {
                    "field": "content",
                    "message": "Invalid UTF-8 encoding in request body",
                }
            ],
        )

    # Initialize parser with JSON string for line tracking
    parser = JsonParseStrategy(
        scenario_json=validation_request.content, json_string=json_string
    )
    validation_errors = parser.validate()

    return ValidationResponse(
        valid=len(validation_errors) == 0, errors=validation_errors
    )


@router.get("/template")
def get_scenario_template(
    requesting_user: int = Depends(get_user_id),
) -> dict:
    """
    Get a template for creating a new scenario.

    This endpoint provides an example scenario structure with comments
    explaining each field to help users understand the expected format.

    Args:
        requesting_user: ID of the authenticated user making the request

    Returns:
        dict: A template scenario with example data and documentation.
    """
    return {
        "name": "Example Scenario",
        "content": {
            "start_time": "day1:08:00",
            "end_time": "day1:17:00",
            "vehicle_battery_capacity": 50,
            "stations": [
                {
                    "name": "Station 1",
                    "position": [-73.57314, 45.50137],
                    "initial_task_count": 1,
                    "scheduled_tasks": ["day1:09:00"],
                }
            ],
            "vehicles": [
                {
                    "name": "Vehicle 1",
                    "position": [-73.561, 45.507],
                    "battery_count": 2,
                }
            ],
            "drivers": [
                {
                    "name": "Driver 1",
                    "shift": {
                        "start_time": "day1:08:00",
                        "end_time": "day1:17:00",
                        "lunch_break": "day1:12:00",
                    },
                }
            ],
        },
        "description": (
            "Template for scenario creation. Updated format:\n\n"
            "- start_time: Simple time format with relative day (e.g., 'day1:08:00')\n"
            "- end_time: Simple time format with relative day (can span days)\n"
            "- vehicle_battery_capacity: Positive integer capacity per vehicle\n"
            "- stations: List of { name, position [lon, lat], initial_task_count,\n"
            "  scheduled_tasks[] }\n"
            "- vehicles: List of { name, position [lon, lat],\n"
            "  battery_count }\n"
            "- drivers: List of { name, shift { start_time, end_time,\n"
            "  lunch_break } }\n\n"
            "Notes: Tasks are now per-station via initial_task_count and\n"
            "scheduled_tasks times."
        ),
    }


@router.get("/", response_model=ScenarioListResponse)
def get_scenarios(
    skip: int = Query(0, ge=0, description="Number of scenarios to skip"),
    limit: int = Query(10, ge=1, le=100, description="Number of scenarios to retrieve"),
    requesting_user: int = Depends(get_user_id),
    db: Session = Depends(get_db),
) -> ScenarioListResponse:
    """Get all scenarios with pagination.

    Args:
        skip: Number of scenarios to skip for pagination
        limit: Number of scenarios to retrieve (1-100)
        requesting_user: ID of the authenticated user
        db: Database session dependency

    Returns:
        ScenarioListResponse containing paginated list of scenarios and metadata
    """
    scenarios, total = scenario_crud.get_by_user(db, requesting_user, skip, limit)

    total_pages = math.ceil(total / limit) if total > 0 else 0
    page = (skip // limit) + 1

    return ScenarioListResponse(
        scenarios=[ScenarioResponse.model_validate(scenario) for scenario in scenarios],
        total=total,
        page=page,
        per_page=limit,
        total_pages=total_pages,
    )


@router.get("/{scenario_id}", response_model=ScenarioResponse)
def get_scenario(
    scenario_id: int,
    requesting_user: int = Depends(get_user_id),
    db: Session = Depends(get_db),
) -> ScenarioResponse:
    """Get a specific scenario by ID.

    Args:
        scenario_id: ID of the scenario to retrieve
        requesting_user: ID of the authenticated user
        db: Database session dependency

    Returns:
        ScenarioResponse containing the requested scenario data
    """
    db_scenario = scenario_crud.get(db, scenario_id, requesting_user)
    return ScenarioResponse.model_validate(db_scenario)


@router.post("/", response_model=ScenarioResponse, status_code=status.HTTP_201_CREATED)
def create_scenario(
    request: ScenarioCreateRequest,
    requesting_user: int = Depends(get_user_id),
    db: Session = Depends(get_db),
    raw_body: bytes = Depends(get_raw_body),
) -> ScenarioResponse:
    """
    Create a new scenario.

    Args:
        request_obj: FastAPI request object for accessing raw body
        request: Scenario creation request with name, content, and options
        requesting_user: ID of the authenticated user
        db: Database session dependency

    Returns:
        ScenarioResponse containing the created scenario data
    """
    try:
        # Check for duplicate name if not allowed
        if not request.allow_duplicate_name:
            existing = scenario_crud.get_by_name_and_user(
                db, request.name, requesting_user
            )
            if existing:
                raise BadRequestError(
                    f"A scenario with name '{request.name}' already exists. "
                    f"Set allow_duplicate_name=true to create anyway."
                )

        # Get raw body for line number extraction (injected via get_raw_body dependency)
        content_json_string = None
        try:
            import json

            full_json = json.loads(raw_body.decode("utf-8"))
            # Extract just the content field for line mapping
            if "content" in full_json:
                content_json_string = json.dumps(full_json["content"], indent=2)
        except (UnicodeDecodeError, json.JSONDecodeError):
            pass  # Continue without line numbers if decoding/parsing fails

        # Validate scenario content against ScenarioContent schema
        parser = JsonParseStrategy(
            scenario_json=request.content, json_string=content_json_string
        )
        validation_errors = parser.validate()
        if validation_errors:
            # Return structured error with line numbers in HTTPException detail
            raise HTTPException(
                status_code=400,
                detail={
                    "message": "Invalid scenario content",
                    "errors": validation_errors,
                },
            )

        # Create the scenario
        scenario_data = ScenarioCreate(
            name=request.name,
            content=request.content,
            description=request.description,
            user_id=requesting_user,
        )
        db_scenario = scenario_crud.create(db, scenario_data)
        return ScenarioResponse.model_validate(db_scenario)

    except (HTTPException, BadRequestError, VelosimPermissionError):
        raise
    except Exception as err:
        # Handle unexpected database errors
        logger.exception("Unexpected error: %s", err)
        raise UnexpectedError() from err


@router.put("/{scenario_id}", response_model=ScenarioResponse)
def update_scenario(
    scenario_id: int,
    request: ScenarioUpdateRequest,
    requesting_user: int = Depends(get_user_id),
    db: Session = Depends(get_db),
    raw_body: bytes = Depends(get_raw_body),
) -> ScenarioResponse:
    """
    Update an existing scenario.

    Args:
        request_obj: FastAPI request object for accessing raw body
        scenario_id: ID of the scenario to update
        request: Scenario update request with optional name, content, and description
        requesting_user: ID of the authenticated user
        db: Database session dependency

    Returns:
        ScenarioResponse containing the updated scenario data
    """
    try:
        # Validate scenario content if it's being updated
        if request.content is not None:
            # Get raw body for line number extraction
            # (injected via get_raw_body dependency)
            content_json_string = None
            try:
                import json

                full_json = json.loads(raw_body.decode("utf-8"))
                # Extract just the content field for line mapping
                if "content" in full_json:
                    content_json_string = json.dumps(full_json["content"], indent=2)
            except (UnicodeDecodeError, json.JSONDecodeError):
                pass  # Continue without line numbers if decoding/parsing fails

            parser = JsonParseStrategy(
                scenario_json=request.content, json_string=content_json_string
            )
            validation_errors = parser.validate()
            if validation_errors:
                raise HTTPException(
                    status_code=400,
                    detail={
                        "message": "Invalid scenario content",
                        "errors": validation_errors,
                    },
                )

        scenario_data = ScenarioUpdate(
            name=request.name,
            content=request.content,
            description=request.description,
        )
        db_scenario = scenario_crud.update(
            db, scenario_id, requesting_user, scenario_data
        )
        return ScenarioResponse.model_validate(db_scenario)

    except (HTTPException, ItemNotFoundError, BadRequestError, VelosimPermissionError):
        raise
    except Exception as err:
        logger.exception("Unexpected error: %s", err)
        raise UnexpectedError() from err


@router.delete("/{scenario_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_scenario(
    scenario_id: int,
    requesting_user: int = Depends(get_user_id),
    db: Session = Depends(get_db),
) -> None:
    """
    Delete a scenario.

    Args:
        scenario_id: ID of the scenario to delete
        requesting_user: ID of the authenticated user
        db: Database session dependency

    Returns:
        None (204 No Content status on success)
    """
    try:
        scenario_crud.delete(db, scenario_id, requesting_user)
    except (ItemNotFoundError, BadRequestError, VelosimPermissionError):
        raise
    except Exception as err:
        logger.exception("Unexpected error: %s", err)
        raise UnexpectedError() from err
