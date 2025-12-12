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
from back.exceptions import BadRequestError, ItemNotFoundError, VelosimPermissionError
from back.schemas.scenario import (
    ScenarioCreate,
    ScenarioCreateRequest,
    ScenarioListResponse,
    ScenarioResponse,
    ScenarioUpdate,
    ScenarioUpdateRequest,
)
from sim.validation import ScenarioValidator

router = APIRouter(prefix="/scenarios", tags=["scenarios"])


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

    # Initialize validator with JSON string for line tracking
    validator = ScenarioValidator(json_string=json_string)
    validation_errors = validator.validate_all(validation_request.content)

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
        "content": {
            "scenario_title": "Example Scenario",
            "start_time": "day1:08:00",
            "end_time": "day1:17:00",
            "stations": [
                {
                    "station_id": 1,
                    "station_name": "Station 1",
                    "station_position": [-74.0060, 40.7128],
                }
            ],
            "resources": [
                {
                    "resource_id": 1,
                    "resource_position": [-74.0060, 40.7128],
                }
            ],
            "initial_tasks": [
                {
                    "station_id": 1,
                }
            ],
            "scheduled_tasks": [
                {
                    "station_id": 1,
                    "time": "day1:08:30",
                },
                {
                    "station_id": 1,
                    "time": "day1:09:00",
                },
            ],
        },
        "description": (
            "Template for scenario creation. Format requirements:\n\n"
            "- scenario_title: Name of the scenario\n"
            "- start_time: Simple time format and day1 "
            "(e.g., 'day1:08:00', 'day1:17:00')\n"
            "- end_time: Simple time format with relative day "
            "(can span multiple days e.g. 'day2:11:00')\n"
            "- stations: List of station objects with id, name, "
            "and position [lon, lat]\n"
            "- resources: List of resource objects with id "
            "and position [lon, lat]\n"
            "- initial_tasks: Tasks to spawn immediately at simulation start.\n"
            "  * station_id: Target station ID (integer, required)\n"
            "  * time: NOT REQUIRED (tasks spawn immediately)\n"
            "- scheduled_tasks: Tasks to spawn after a delay.\n"
            "  * station_id: Target station ID (integer, required)\n"
            "  * time: REQUIRED - Simple time format with relative day "
            "(e.g., 'day1:09:00', 'day2:10:00' if sim spans multiple days)\n\n"
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
    try:
        scenarios, total = scenario_crud.get_by_user(db, requesting_user, skip, limit)
    except BadRequestError as err:
        raise HTTPException(status_code=400, detail=str(err))
    except VelosimPermissionError as err:
        raise HTTPException(status_code=403, detail=str(err))
    except ItemNotFoundError as err:
        raise HTTPException(status_code=404, detail=str(err))

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
    try:
        db_scenario = scenario_crud.get(db, scenario_id, requesting_user)
        return ScenarioResponse.model_validate(db_scenario)
    except ItemNotFoundError as err:
        raise HTTPException(status_code=404, detail=str(err))
    except BadRequestError as err:
        raise HTTPException(status_code=400, detail=str(err))
    except VelosimPermissionError as err:
        raise HTTPException(status_code=403, detail=str(err))


@router.post("/", response_model=ScenarioResponse, status_code=status.HTTP_201_CREATED)
def create_scenario(
    request: ScenarioCreateRequest,
    requesting_user: int = Depends(get_user_id),
    db: Session = Depends(get_db),
) -> ScenarioResponse:
    """
    Create a new scenario.

    Args:
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

        # Validate scenario content against ScenarioContent schema
        # Supports RFC 3339 datetime format for multi-day scenarios
        validator = ScenarioValidator()
        validation_errors = validator.validate_all(request.content)
        if validation_errors:
            error_details = "; ".join(
                [f"{err['field']}: {err['message']}" for err in validation_errors]
            )
            raise BadRequestError(f"Invalid scenario content: {error_details}")

        # Create the scenario
        scenario_data = ScenarioCreate(
            name=request.name,
            content=request.content,
            description=request.description,
            user_id=requesting_user,
        )
        db_scenario = scenario_crud.create(db, scenario_data)
        return ScenarioResponse.model_validate(db_scenario)

    except BadRequestError as err:
        raise HTTPException(status_code=400, detail=str(err))
    except VelosimPermissionError as err:
        raise HTTPException(status_code=403, detail=str(err))
    except Exception as err:
        # Handle unexpected database errors
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create scenario: {str(err)}",
        )


@router.put("/{scenario_id}", response_model=ScenarioResponse)
def update_scenario(
    scenario_id: int,
    request: ScenarioUpdateRequest,
    requesting_user: int = Depends(get_user_id),
    db: Session = Depends(get_db),
) -> ScenarioResponse:
    """
    Update an existing scenario.

    Args:
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
            validator = ScenarioValidator()
            validation_errors = validator.validate_all(request.content)
            if validation_errors:
                error_details = "; ".join(
                    [f"{err['field']}: {err['message']}" for err in validation_errors]
                )
                raise BadRequestError(f"Invalid scenario content: {error_details}")

        scenario_data = ScenarioUpdate(
            name=request.name,
            content=request.content,
            description=request.description,
        )
        db_scenario = scenario_crud.update(
            db, scenario_id, requesting_user, scenario_data
        )
        return ScenarioResponse.model_validate(db_scenario)

    except ItemNotFoundError as err:
        raise HTTPException(status_code=404, detail=str(err))
    except BadRequestError as err:
        raise HTTPException(status_code=400, detail=str(err))
    except VelosimPermissionError as err:
        raise HTTPException(status_code=403, detail=str(err))
    except Exception as err:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to update scenario: {str(err)}",
        )


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
    except ItemNotFoundError as err:
        raise HTTPException(status_code=404, detail=str(err))
    except BadRequestError as err:
        raise HTTPException(status_code=400, detail=str(err))
    except VelosimPermissionError as err:
        raise HTTPException(status_code=403, detail=str(err))
    except Exception as err:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to delete scenario: {str(err)}",
        )
