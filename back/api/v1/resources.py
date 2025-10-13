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
from typing import Dict, List, Optional

from back.database.session import get_db
from back.crud import resource_crud
from back.models import ResourceType, TaskStatus
from back.schemas import (
    ResourceCreate,
    ResourceUpdate,
    ResourceTaskIDsRequest,
    ResourceResponse,
    ResourceListResponse,
)

router = APIRouter(prefix="/resources", tags=["resources"])


@router.post("/", response_model=ResourceResponse, status_code=201)
def create_resource(
    resource_data: ResourceCreate, db: Session = Depends(get_db)
) -> ResourceResponse:
    """Create a new resource."""
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
    """Get all resources with pagination."""
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
    """Get all resource types."""
    return [r_type.value for r_type in ResourceType]


@router.get("/{resource_id}", response_model=ResourceResponse)
def get_resource(resource_id: int, db: Session = Depends(get_db)) -> ResourceResponse:
    """Get a specific resource by ID."""
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
    """Update a resource (only current position and start/end of route)."""
    db_resource = resource_crud.update(db, resource_id, resource_data)
    if not db_resource:
        raise HTTPException(
            status_code=404, detail=f"Resource with ID {resource_id} not found"
        )
    return ResourceResponse.model_validate(db_resource)


@router.delete("/{resource_id}", status_code=204)
def delete_resource(resource_id: int, db: Session = Depends(get_db)) -> None:
    success = resource_crud.delete(db, resource_id)
    """Delete a resource."""
    if not success:
        raise HTTPException(
            status_code=404, detail=f"Resource with ID {resource_id} not found"
        )


@router.post("/{resource_id}/assign", status_code=200)
def assign_tasks_to_resource(
    resource_id: int, request: ResourceTaskIDsRequest, db: Session = Depends(get_db)
) -> Dict[str, str]:
    """Assign one or more tasks to a resource."""
    failed = []
    for task_id in request.task_ids:
        if not resource_crud.assign_task(db, resource_id, task_id):
            failed.append(task_id)
    if failed:
        raise HTTPException(
            status_code=400,
            detail=f"Failed to assign task(s) {failed} to resource {resource_id}",
        )
    return {"message": f"Task(s) {request.task_ids} assigned to resource {resource_id}"}


@router.post("/{resource_id}/unassign", status_code=200)
def unassign_tasks_from_resource(
    resource_id: int, request: ResourceTaskIDsRequest, db: Session = Depends(get_db)
) -> Dict[str, str]:
    """Unassign one or more tasks from a resource."""
    failed = []
    for task_id in request.task_ids:
        if not resource_crud.unassign_task(db, resource_id, task_id):
            failed.append(task_id)
    if failed:
        raise HTTPException(
            status_code=400,
            detail=f"Failed to unassign task(s) {failed} from resource {resource_id}",
        )
    return {
        "message": f"Task(s) {request.task_ids} unassigned from resource {resource_id}"
    }


@router.post("/{resource_id}/service", status_code=200)
def service_tasks_for_resource(
    resource_id: int, request: ResourceTaskIDsRequest, db: Session = Depends(get_db)
) -> Dict[str, str]:
    """Mark one or more tasks as closed and then remove them from the resource."""
    failed = []
    for task_id in request.task_ids:
        if not resource_crud.service_task(db, resource_id, task_id):
            failed.append(task_id)
    if failed:
        raise HTTPException(
            status_code=400,
            detail=f"Failed to service task(s) {failed} for resource {resource_id}",
        )
    return {"message": f"Task(s) {request.task_ids} serviced by resource {resource_id}"}
