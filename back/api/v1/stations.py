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
from back.crud.station import station_crud
from back.schemas.station import (
    StationCreate,
    StationUpdate,
    StationResponse,
    StationListResponse,
)

router = APIRouter(prefix="/stations", tags=["stations"])


@router.post("/", response_model=StationResponse, status_code=201)
def create_station(
    station_data: StationCreate, db: Session = Depends(get_db)
) -> StationResponse:
    """Create a new bike station.

    Args:
        station_data: Station creation data including name and position
        db: Database session dependency

    Returns:
        StationResponse containing the created station data
    """
    # Check if station with same name already exists
    existing_station = station_crud.get_by_name(db, station_data.name)
    if existing_station:
        raise HTTPException(
            status_code=400,
            detail=f"Station with name '{station_data.name}' already exists",
        )

    db_station = station_crud.create(db, station_data)
    return StationResponse.model_validate(db_station)


@router.get("/", response_model=StationListResponse)
def get_stations(
    skip: int = Query(0, ge=0, description="Number of stations to skip"),
    limit: int = Query(10, ge=1, le=100, description="Number of stations to retrieve"),
    db: Session = Depends(get_db),
) -> StationListResponse:
    """Get all stations with pagination.

    Args:
        skip: Number of stations to skip for pagination
        limit: Number of stations to retrieve (1-100)
        db: Database session dependency

    Returns:
        StationListResponse containing paginated list of stations and metadata
    """
    stations, total = station_crud.get_all(db, skip, limit)

    total_pages = math.ceil(total / limit) if total > 0 else 0
    page = (skip // limit) + 1

    return StationListResponse(
        stations=[StationResponse.model_validate(station) for station in stations],
        total=total,
        page=page,
        per_page=limit,
        total_pages=total_pages,
    )


@router.get("/{station_id}", response_model=StationResponse)
def get_station(station_id: int, db: Session = Depends(get_db)) -> StationResponse:
    """Get a specific station by ID.

    Args:
        station_id: ID of the station to retrieve
        db: Database session dependency

    Returns:
        StationResponse containing the requested station data
    """
    db_station = station_crud.get(db, station_id)
    if not db_station:
        raise HTTPException(
            status_code=404, detail=f"Station with ID {station_id} not found"
        )
    return StationResponse.model_validate(db_station)


@router.put("/{station_id}", response_model=StationResponse)
def update_station(
    station_id: int, station_data: StationUpdate, db: Session = Depends(get_db)
) -> StationResponse:
    """Update a station.

    Args:
        station_id: ID of the station to update
        station_data: Updated station data
        db: Database session dependency

    Returns:
        StationResponse containing the updated station data
    """
    # Check if station exists
    existing_station = station_crud.get(db, station_id)
    if not existing_station:
        raise HTTPException(
            status_code=404, detail=f"Station with ID {station_id} not found"
        )

    # Check if name conflicts with another station
    if station_data.name:
        name_conflict = station_crud.get_by_name(db, station_data.name)
        if name_conflict and name_conflict.id != station_id:
            raise HTTPException(
                status_code=400,
                detail=f"Station with name '{station_data.name}' already exists",
            )

    db_station = station_crud.update(db, station_id, station_data)
    return StationResponse.model_validate(db_station)


@router.delete("/{station_id}", status_code=204)
def delete_station(station_id: int, db: Session = Depends(get_db)) -> None:
    """Delete a station.

    Args:
        station_id: ID of the station to delete
        db: Database session dependency

    Returns:
        None (204 No Content status on success)
    """
    success = station_crud.delete(db, station_id)
    if not success:
        raise HTTPException(
            status_code=404, detail=f"Station with ID {station_id} not found"
        )
