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

from typing import List, Optional
from sqlalchemy.orm import Session
from back.exceptions import VelosimPermissionError
from back.models import SimInstance
from back.schemas import SimInstanceCreate


class SimInstanceCRUD:
    """CRUD operations for SimInstance model."""

    def create(self, db: Session, sim_instance_data: SimInstanceCreate) -> SimInstance:
        """Create a new simulation instance.

        Args:
            db: Database session.
            sim_instance_data: The data for creating a new simulation instance.

        Returns:
            SimInstance: The newly created simulation instance.
        """
        db_sim_instance = SimInstance(
            user_id=sim_instance_data.user_id,
        )
        db.add(db_sim_instance)
        db.flush()
        db.refresh(db_sim_instance)
        return db_sim_instance

    def get(self, db: Session, sim_instance_id: int) -> Optional[SimInstance]:
        """Get a simulation instance by ID.

        Args:
            db: Database session.
            sim_instance_id: The ID of the simulation instance to retrieve.

        Returns:
            Optional[SimInstance]: The simulation instance if found, None otherwise.
        """
        return db.query(SimInstance).filter(SimInstance.id == sim_instance_id).first()

    def get_by_user(
        self,
        db: Session,
        target_user_id: int,
        requesting_user_id: int,
        skip: int = 0,
        limit: int = 100,
    ) -> List[SimInstance]:
        """
        Get all simulation instances for a specific user if permitted.

        Normal users can only see their own simulations. Admins can access any.

        Args:
            db: Database session.
            target_user_id: The ID of the user whose simulations to retrieve.
            requesting_user_id: The ID of the user making the request.
            skip: Number of records to skip (default: 0).
            limit: Maximum number of records to return (default: 100).

        Returns:
            List[SimInstance]: List of simulation instances for the user.
        """
        # Lazy import to avoid circular dependency
        from back.crud import user_crud

        requesting_user = user_crud.get(db, requesting_user_id)
        if not requesting_user or not requesting_user.is_enabled:
            raise VelosimPermissionError("Requesting user cannot access simulations.")
        if requesting_user.id != target_user_id and not requesting_user.is_admin:
            raise VelosimPermissionError(
                "Requesting user cannot access simulations for this user."
            )

        return (
            db.query(SimInstance)
            .filter(SimInstance.user_id == target_user_id)
            .offset(skip)
            .limit(limit)
            .all()
        )

    def get_all(
        self, db: Session, skip: int = 0, limit: int = 100
    ) -> List[SimInstance]:
        """Get all simulation instances (admin function).

        Args:
            db: Database session.
            skip: Number of records to skip (default: 0).
            limit: Maximum number of records to return (default: 100).

        Returns:
            List[SimInstance]: List of all simulation instances.
        """
        return db.query(SimInstance).offset(skip).limit(limit).all()

    def delete(self, db: Session, sim_instance_id: int) -> bool:
        """Delete a simulation instance by ID.

        Args:
            db: Database session.
            sim_instance_id: The ID of the simulation instance to delete.

        Returns:
            bool: True if instance was deleted, False if not found.
        """
        sim_instance = self.get(db, sim_instance_id)
        if not sim_instance:
            return False

        db.delete(sim_instance)
        db.flush()
        return True


# Create a singleton instance
sim_instance_crud = SimInstanceCRUD()
