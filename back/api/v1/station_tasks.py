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
from typing import List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from back.models import TaskStatus
from back.database.session import get_db
from back.crud import station_crud, station_task_crud
from back.models.station_task_type import StationTaskType
from back.schemas import (
    StationTaskCreate,
    StationTaskUpdate,
    StationTaskResponse,
    StationTaskListResponse,
)

router = APIRouter(prefix="/stationTasks", tags=["stationTasks"])


@router.post("/", response_model=StationTaskResponse, status_code=201)
def create_station_task(
    station_task_create_data: StationTaskCreate, db: Session = Depends(get_db)
) -> StationTaskResponse:
    """Create a new station task."""
    # Check if the station exists. This had to be done explicitly rather than relying on
    # SqlAlchemy's IntegrityError (used below as well to avoid race condition) to work
    # under unit testing.
    station = station_crud.get(db, station_task_create_data.station_id)
    if not station:
        raise HTTPException(
            status_code=400,
            detail=f"Station with ID {station_task_create_data.station_id} not found",
        )

    try:
        db_station_task = station_task_crud.create(db, station_task_create_data)
        return StationTaskResponse.model_validate(db_station_task)
    except IntegrityError:
        raise HTTPException(
            status_code=400,
            detail=f"Station with ID {station_task_create_data.station_id} not found",
        )


@router.get("/", response_model=StationTaskListResponse)
def get_station_tasks(
    station_id: int | None = Query(
        None, description="Filter tasks by a specific station ID", alias="stationId"
    ),
    task_status: TaskStatus | None = Query(
        None, description="Filter tasks by status", alias="taskStatus"
    ),
    skip: int = Query(0, ge=0, description="Number of stations to skip"),
    limit: int = Query(10, ge=1, le=100, description="Number of stations to retrieve"),
    db: Session = Depends(get_db),
) -> StationTaskListResponse:
    """Get all station tasks with pagination."""
    station_tasks, total = station_task_crud.get_all(
        db, station_id, task_status, skip, limit
    )

    total_pages = math.ceil(total / limit) if total > 0 else 0
    page = (skip // limit) + 1

    return StationTaskListResponse(
        station_tasks=[
            StationTaskResponse.model_validate(station_task)
            for station_task in station_tasks
        ],
        total=total,
        page=page,
        per_page=limit,
        total_pages=total_pages,
    )


# This must come ahead of the parameterized routes to prioritize the exact match on
# 'types'
@router.get("/types", response_model=List[str])
def get_task_types() -> List[str]:
    return [task_type.value for task_type in StationTaskType]


@router.get("/{station_task_id}", response_model=StationTaskResponse)
def get_station_task(
    station_task_id: int, db: Session = Depends(get_db)
) -> StationTaskResponse:
    """Get a specific station task by ID."""
    db_station_task = station_task_crud.get(db, station_task_id)
    if not db_station_task:
        raise HTTPException(
            status_code=404, detail=f"Station task with ID {station_task_id} not found"
        )
    return StationTaskResponse.model_validate(db_station_task)


@router.put("/{station_task_id}", response_model=StationTaskResponse)
def update_station_task(
    station_task_id: int,
    station_task_data: StationTaskUpdate,
    db: Session = Depends(get_db),
) -> StationTaskResponse:
    """Update a station task."""
    existing_station_task = station_task_crud.get(db, station_task_id)
    if not existing_station_task:
        raise HTTPException(
            status_code=404, detail=f"Station task with ID {station_task_id} not found"
        )

    new_station_task = station_task_crud.update(db, station_task_id, station_task_data)
    return StationTaskResponse.model_validate(new_station_task)


@router.delete("/{station_task_id}", status_code=204)
def delete_station_task(station_task_id: int, db: Session = Depends(get_db)) -> None:
    """Delete a station task."""
    success = station_task_crud.delete(db, station_task_id)
    if not success:
        raise HTTPException(
            status_code=404, detail=f"Station task with ID {station_task_id} not found"
        )
