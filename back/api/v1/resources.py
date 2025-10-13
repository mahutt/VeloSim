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
from typing import Dict, Optional

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


@router.get("/{resource_id}", response_model=ResourceResponse)
def get_resource(resource_id: int, db: Session = Depends(get_db)) -> ResourceResponse:
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
    db_resource = resource_crud.update(db, resource_id, resource_data)
    if not db_resource:
        raise HTTPException(
            status_code=404, detail=f"Resource with ID {resource_id} not found"
        )
    return ResourceResponse.model_validate(db_resource)


@router.delete("/{resource_id}", status_code=204)
def delete_resource(resource_id: int, db: Session = Depends(get_db)) -> None:
    success = resource_crud.delete(db, resource_id)
    if not success:
        raise HTTPException(
            status_code=404, detail=f"Resource with ID {resource_id} not found"
        )


@router.post("/{resource_id}/assign/{task_id}", status_code=200)
def assign_task_to_resource(
    resource_id: int, task_id: int, db: Session = Depends(get_db)
) -> Dict[str, str]:
    success = resource_crud.assign_task(db, resource_id, task_id)
    if not success:
        raise HTTPException(
            status_code=400,
            detail=f"Failed to assign task {task_id} to resource {resource_id}",
        )
    return {"message": f"Task {task_id} assigned to resource {resource_id}"}


@router.post("/{resource_id}/unassign/{task_id}", status_code=200)
def unassign_task_from_resource(
    resource_id: int, task_id: int, db: Session = Depends(get_db)
) -> Dict[str, str]:
    success = resource_crud.unassign_task(db, resource_id, task_id)
    if not success:
        raise HTTPException(
            status_code=400,
            detail=f"Failed to unassign task {task_id} from resource {resource_id}",
        )
    return {"message": f"Task {task_id} unassigned from resource {resource_id}"}


@router.post("/{resource_id}/service/{task_id}", status_code=200)
def service_task_for_resource(
    resource_id: int, task_id: int, db: Session = Depends(get_db)
) -> Dict[str, str]:
    success = resource_crud.service_task(db, resource_id, task_id)
    if not success:
        raise HTTPException(
            status_code=400,
            detail=f"Failed to service task {task_id} for resource {resource_id}",
        )
    return {"message": f"Task {task_id} serviced by resource {resource_id}"}
