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
from sqlalchemy.orm import Session
from back.models import StationTask, TaskStatus
from back.schemas.station_task import StationTaskCreate, StationTaskUpdate


class StationTaskCRUD:
    """CRUD operations for StationTask model."""

    def create(self, db: Session, station_task_data: StationTaskCreate) -> StationTask:
        """Create a new station task.

        Args:
            db: Database session.
            station_task_data: The data for creating a new station task.

        Returns:
            StationTask: The newly created station task.
        """
        with db.begin(nested=True):
            db_task = StationTask(
                sim_instance_id=station_task_data.sim_instance_id,
                type=station_task_data.type,
                station_id=station_task_data.station_id,
            )
            db.add(db_task)
            db.flush()
            db.refresh(db_task)
            return db_task

    def get(self, db: Session, task_id: int) -> Optional[StationTask]:
        """Get a station task by ID.

        Args:
            db: Database session.
            task_id: The ID of the station task to retrieve.

        Returns:
            Optional[StationTask]: The station task if found, None otherwise.
        """
        return db.query(StationTask).filter(StationTask.id == task_id).first()

    def get_all(
        self,
        db: Session,
        station_id: Optional[int] = None,
        task_status: Optional[TaskStatus] = None,
        skip: int = 0,
        limit: int = 10,
    ) -> Tuple[List[StationTask], int]:
        """Get all station tasks with optional filters and pagination.

        Args:
            db: Database session.
            station_id: Optional filter by station ID.
            task_status: Optional filter by task status.
            skip: Number of records to skip (default: 0).
            limit: Maximum number of records to return (default: 10).

        Returns:
            Tuple[List[StationTask], int]: Tuple of (station tasks list, total count).
        """

        # Build the base query
        query = db.query(StationTask)

        # Apply filters conditionally
        if station_id is not None:
            query = query.filter(StationTask.station_id == station_id)
        if task_status is not None:
            query = query.filter(StationTask.status == task_status)

        # Get total count for pagination
        total = query.count()

        # Apply pagination
        station_tasks = query.offset(skip).limit(limit).all()

        return station_tasks, total

    def update(
        self, db: Session, task_id: int, station_task_data: StationTaskUpdate
    ) -> Optional[StationTask]:
        """Update a station task (status only).

        Args:
            db: Database session.
            task_id: The ID of the station task to update.
            station_task_data: The updated data for the station task.

        Returns:
            Optional[StationTask]: The updated station task if found, None otherwise.
        """
        with db.begin(nested=True):
            db_task = self.get(db, task_id)
            if not db_task:
                return None

            update_data = station_task_data.model_dump(exclude_unset=True)
            for field, value in update_data.items():
                setattr(db_task, field, value)

            db.flush()
            db.refresh(db_task)
            return db_task

    def delete(self, db: Session, task_id: int) -> bool:
        """Delete a station task.

        Args:
            db: Database session.
            task_id: The ID of the station task to delete.

        Returns:
            bool: True if task was deleted, False if not found.
        """
        with db.begin(nested=True):
            db_task = self.get(db, task_id)
            if not db_task:
                return False

            db.delete(db_task)
            db.flush()
            return True


# Create a singleton instance
station_task_crud = StationTaskCRUD()
