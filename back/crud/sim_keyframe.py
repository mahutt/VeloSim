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
from back.exceptions import BadRequestError, ItemNotFoundError
from back.models.sim_frame import SimFrame
from back.models.sim_keyframe import SimKeyframe
from back.schemas.sim_keyframe import SimKeyframeCreate


class SimKeyframeCRUD:
    """CRUD operations for SimKeyframe model."""

    def create(self, db: Session, keyframe_data: SimKeyframeCreate) -> SimKeyframe:
        """Create a new simulation keyframe.

        Args:
            db: Database session.
            keyframe_data: The data for creating a new keyframe.

        Returns:
            SimKeyframe: The newly created keyframe.
        """
        if not isinstance(keyframe_data.frame_data, dict):
            raise BadRequestError("Keyframe frame_data must be a dictionary")

        if keyframe_data.sim_seconds_elapsed < 0:
            raise BadRequestError("sim_seconds_elapsed must be non-negative")

        db_keyframe = SimKeyframe(
            sim_instance_id=keyframe_data.sim_instance_id,
            sim_seconds_elapsed=keyframe_data.sim_seconds_elapsed,
            frame_data=keyframe_data.frame_data,
        )
        db.add(db_keyframe)
        db.commit()
        db.refresh(db_keyframe)
        return db_keyframe

    def get(self, db: Session, keyframe_id: int) -> SimKeyframe:
        """Get a keyframe by ID.

        Args:
            db: Database session.
            keyframe_id: The ID of the keyframe to retrieve.

        Returns:
            SimKeyframe: The requested keyframe.

        Raises:
            ItemNotFoundError: If keyframe not found.
        """
        keyframe = db.query(SimKeyframe).filter(SimKeyframe.id == keyframe_id).first()
        if not keyframe:
            raise ItemNotFoundError("Keyframe not found")
        return keyframe

    def get_keyframe_at_tick(
        self,
        db: Session,
        sim_id: str,
        tick: float,
    ) -> SimKeyframe:
        """
        Retrieve the most recent keyframe at or before a given simulation tick.

        Args:
            db: Active database session.
            sim_id: UUID of the simulation instance.
            tick: Simulation time (in seconds) to retrieve the keyframe for.

        Returns:
            The keyframe at or immediately preceding the given simulation tick.

        Raises:
            ItemNotFoundError: If no keyframe exists at or before the given tick.
        """
        keyframe = (
            db.query(SimKeyframe)
            .filter(
                SimKeyframe.sim_instance_id == sim_id,
                SimKeyframe.sim_seconds_elapsed <= tick,
            )
            .order_by(SimKeyframe.sim_seconds_elapsed.desc())
            .first()
        )

        if not keyframe:
            raise ItemNotFoundError(
                f"No keyframe found at or before tick {tick} for simulation {sim_id}"
            )

        return keyframe

    def get_by_sim_instance(
        self, db: Session, sim_instance_id: int, skip: int = 0, limit: int = 100
    ) -> Tuple[List[SimKeyframe], int]:
        """Get all keyframes for a simulation instance with pagination.

        Args:
            db: Database session.
            sim_instance_id: The ID of the simulation instance.
            skip: Number of records to skip (default: 0).
            limit: Maximum number of records to return (default: 100).

        Returns:
            Tuple[List[SimKeyframe], int]: Tuple of (keyframes list, total count).
        """
        query = db.query(SimKeyframe).filter(
            SimKeyframe.sim_instance_id == sim_instance_id
        )

        total = query.count()
        keyframes = (
            query.order_by(SimKeyframe.sim_seconds_elapsed.asc())
            .offset(skip)
            .limit(limit)
            .all()
        )

        return keyframes, total

    def get_by_sim_time(
        self, db: Session, sim_instance_id: int, sim_seconds: float
    ) -> Optional[SimKeyframe]:
        """Get the keyframe closest to the specified simulation time.

        Finds the keyframe with the largest sim_seconds_elapsed that is
        less than or equal to the requested time (nearest preceding keyframe).

        Args:
            db: Database session.
            sim_instance_id: The ID of the simulation instance.
            sim_seconds: The target simulation time in seconds.

        Returns:
            Optional[SimKeyframe]: The closest preceding keyframe, or None if
                no keyframes exist before the specified time.
        """
        keyframe = (
            db.query(SimKeyframe)
            .filter(
                SimKeyframe.sim_instance_id == sim_instance_id,
                SimKeyframe.sim_seconds_elapsed <= sim_seconds,
            )
            .order_by(SimKeyframe.sim_seconds_elapsed.desc())
            .first()
        )

        return keyframe

    def delete(self, db: Session, keyframe_id: int) -> None:
        """Delete a keyframe by ID.

        Args:
            db: Database session.
            keyframe_id: The ID of the keyframe to delete.

        Returns:
            None

        Raises:
            ItemNotFoundError: If keyframe not found.
        """
        keyframe = self.get(db, keyframe_id)
        db.delete(keyframe)
        db.commit()

    def get_last_keyframe(
        self, db: Session, sim_instance_id: str
    ) -> Optional[SimFrame]:
        """
        Retrieve the most recently persisted keyframe for a simulation instance.

        Args:
            db: Active database session.
            sim_instance_id: UUID of the simulation instance.

        Returns:
            The most recent keyframe if one exists, otherwise None.

        """

        keyframe = (
            db.query(SimFrame)
            .filter(
                SimFrame.sim_instance_id == sim_instance_id, SimFrame.is_key == True
            )
            .order_by(SimFrame.sim_seconds_elapsed.desc())
            .first()
        )

        if not keyframe:
            raise ItemNotFoundError("No keyframe found.")

        return keyframe


# Singleton instance for use throughout the application
sim_keyframe_crud = SimKeyframeCRUD()
