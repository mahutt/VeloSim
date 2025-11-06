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
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from back.database.session import get_db
from back.auth.dependency import get_user_id
from back.crud.scenario import scenario_crud
from back.exceptions import BadRequestError, ItemNotFoundError, VelosimPermissionError
from back.schemas.scenario import ScenarioListResponse, ScenarioResponse

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
