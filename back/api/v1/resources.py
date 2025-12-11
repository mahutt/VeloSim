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
from typing import List, Optional

from back.database.session import get_db
from back.crud import resource_crud
from back.models import ResourceType, TaskStatus
from back.schemas import (
    ResourceCreate,
    ResourceUpdate,
    ResourceResponse,
    ResourceListResponse,
)

router = APIRouter(prefix="/resources", tags=["resources"])


@router.post("/", response_model=ResourceResponse, status_code=201)
def create_resource(
    resource_data: ResourceCreate, db: Session = Depends(get_db)
) -> ResourceResponse:
    """Create a new resource.

    Args:
        resource_data: Data for creating the new resource
        db: Database session dependency

    Returns:
        ResourceResponse containing the created resource data
    """
    db_resource = resource_crud.create(db, resource_data)
    return ResourceResponse.model_validate(db_resource)


@router.get("/", response_model=ResourceListResponse)
def get_resources(
    type: Optional[ResourceType] = Query(None, description="Filter by resource type"),
    status: Optional[TaskStatus] = Query(
        None, description="Filter by current task status"
    ),
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db),
) -> ResourceListResponse:
    """Get all resources with pagination.

    Args:
        type: Optional filter by resource type
        status: Optional filter by current task status
        skip: Number of records to skip for pagination
        limit: Maximum number of records to return (1-100)
        db: Database session dependency

    Returns:
        ResourceListResponse containing paginated list of resources and metadata
    """
    resources, total = resource_crud.get_all_filtered(
        db, skip=skip, limit=limit, type=type, status=status
    )
    total_pages = math.ceil(total / limit) if total else 0
    page = (skip // limit) + 1
    return ResourceListResponse(
        resources=[ResourceResponse.model_validate(r) for r in resources],
        total=total,
        page=page,
        per_page=limit,
        total_pages=total_pages,
    )


@router.get("/types", response_model=List[str])
def get_resource_types() -> List[str]:
    """Get all resource types.

    Returns:
        List of all available resource type values
    """
    return [r_type.value for r_type in ResourceType]


@router.get("/{resource_id}", response_model=ResourceResponse)
def get_resource(resource_id: int, db: Session = Depends(get_db)) -> ResourceResponse:
    """Get a specific resource by ID.

    Args:
        resource_id: ID of the resource to retrieve
        db: Database session dependency

    Returns:
        ResourceResponse containing the requested resource data
    """
    db_resource = resource_crud.get(db, resource_id)
    if not db_resource:
        raise HTTPException(
            status_code=404, detail=f"Resource with ID {resource_id} not found"
        )
    return ResourceResponse.model_validate(db_resource)


@router.put("/{resource_id}", response_model=ResourceResponse)
def update_resource(
    resource_id: int, resource_data: ResourceUpdate, db: Session = Depends(get_db)
) -> ResourceResponse:
    """Update a resource (only current position and start/end of route).

    Args:
        resource_id: ID of the resource to update
        resource_data: Updated resource data
        db: Database session dependency

    Returns:
        ResourceResponse containing the updated resource data
    """
    db_resource = resource_crud.update(db, resource_id, resource_data)
    if not db_resource:
        raise HTTPException(
            status_code=404, detail=f"Resource with ID {resource_id} not found"
        )
    return ResourceResponse.model_validate(db_resource)


@router.delete("/{resource_id}", status_code=204)
def delete_resource(resource_id: int, db: Session = Depends(get_db)) -> None:
    """Delete a resource.

    Args:
        resource_id: ID of the resource to delete
        db: Database session dependency

    Returns:
        None (204 No Content status on success)
    """
    success = resource_crud.delete(db, resource_id)
    if not success:
        raise HTTPException(
            status_code=404, detail=f"Resource with ID {resource_id} not found"
        )
