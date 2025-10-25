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

from typing import List, Optional, Tuple
from sqlalchemy import func
from sqlalchemy.orm import Session, aliased
from back.models import Resource, StationTask, TaskStatus
from back.models import ResourceType
from back.schemas import ResourceCreate, ResourceUpdate


class ResourceCRUD:
    """CRUD operations for Resource model."""

    def create(self, db: Session, resource_data: ResourceCreate) -> Resource:
        """Create a new resource."""
        with db.begin(nested=True):
            db_resource = Resource(
                sim_instance_id=resource_data.sim_instance_id,
                type=resource_data.type,
                latitude=resource_data.latitude,
                longitude=resource_data.longitude,
                route_start_latitude=resource_data.route_start_latitude,
                route_start_longitude=resource_data.route_start_longitude,
                route_end_latitude=resource_data.route_end_latitude,
                route_end_longitude=resource_data.route_end_longitude,
            )
        db.add(db_resource)
        db.flush()
        db.refresh(db_resource)
        return db_resource

    def get(self, db: Session, resource_id: int) -> Optional[Resource]:
        """Get a resource by ID."""
        return db.query(Resource).filter(Resource.id == resource_id).first()

    def get_all(
        self, db: Session, skip: int = 0, limit: int = 100
    ) -> Tuple[List[Resource], int]:
        """Get all resources with pagination."""
        total = db.query(func.count(Resource.id)).scalar() or 0
        resources = db.query(Resource).offset(skip).limit(limit).all()
        return resources, total

    def get_type(self, db: Session, resource_id: int) -> Optional[ResourceType]:
        """Get a resource's type by id."""
        resource = self.get(db, resource_id)
        return resource.type if resource else None

    def get_all_filtered(
        self,
        db: Session,
        skip: int = 0,
        limit: int = 100,
        type: Optional[ResourceType] = None,
        status: Optional[TaskStatus] = None,
    ) -> Tuple[List[Resource], int]:
        """
        Get all resources with optional filters by type or task status.
        Returns: (resources_list, total_count)
        """
        query = db.query(Resource)

        if type:
            query = query.filter(Resource.type == type)

        if status:
            # Use an aliased join to prevent multiple rows for same resource
            TaskAlias = aliased(Resource.tasks.property.mapper.class_)
            query = query.join(TaskAlias, Resource.tasks).filter(
                TaskAlias.status == status
            )

        # Use distinct to avoid duplicates from join
        total = query.distinct().count()

        # Pagination
        resources = query.distinct().offset(skip).limit(limit).all()
        return resources, total

    def update(
        self, db: Session, resource_id: int, resource_data: ResourceUpdate
    ) -> Optional[Resource]:
        """Update a resource (only current position and start/end of route)."""
        resource = self.get(db, resource_id)
        if not resource:
            return None
        update_data = resource_data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(resource, key, value)
        db.commit()
        db.refresh(resource)
        return resource

    def delete(self, db: Session, resource_id: int) -> bool:
        """Delete a resource."""
        resource = self.get(db, resource_id)
        if not resource:
            return False
        # To handle the case where a resource may be deleted abruptly, all of
        # its assigned tasks are marked as 'open' (before no longer being
        # associated with a resource).
        for task in resource.tasks:
            task.resource = None
            task.status = TaskStatus.OPEN
        db.delete(resource)
        db.commit()
        return True

    def assign_task(self, db: Session, resource_id: int, task_id: int) -> bool:
        """Assign a task to a resource using task_id."""
        resource = self.get(db, resource_id)
        task = db.get(StationTask, task_id)
        if not resource or not task:
            return False
        resource.assign_task(task)
        db.commit()
        db.refresh(resource)
        db.refresh(task)
        return True

    def unassign_task(self, db: Session, resource_id: int, task_id: int) -> bool:
        """Unassign a task from a resource using task_id."""
        resource = self.get(db, resource_id)
        task = db.get(StationTask, task_id)
        if not resource or not task:
            return False
        resource.unassign_task(task)
        db.commit()
        db.refresh(resource)
        db.refresh(task)
        return True

    def service_task(self, db: Session, resource_id: int, task_id: int) -> bool:
        """Mark a task as closed and remove it from the resource's assignments."""
        resource = self.get(db, resource_id)
        task = db.get(StationTask, task_id)
        if not resource or not task:
            return False
        resource.service_task(task)
        db.commit()
        db.refresh(resource)
        db.refresh(task)
        return True


# Create a singleton instance
resource_crud = ResourceCRUD()
