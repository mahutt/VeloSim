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
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

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
from back.services.scenario_validation_service import ScenarioValidator

router = APIRouter(prefix="/scenarios", tags=["scenarios"])


@router.get("/", response_model=ScenarioListResponse)
def get_scenarios(
    skip: int = Query(0, ge=0, description="Number of scenarios to skip"),
    limit: int = Query(10, ge=1, le=100, description="Number of scenarios to retrieve"),
    requesting_user: int = Depends(get_user_id),
    db: Session = Depends(get_db),
) -> ScenarioListResponse:
    """Get all scenarios with pagination."""
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
    """Get a specific scenario by ID."""
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
