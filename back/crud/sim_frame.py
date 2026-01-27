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

from sqlalchemy.orm import Session
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy import desc, select, literal, func
from typing import List, Optional
from back.models.sim_frame import SimFrame
from back.schemas.sim_frame import SimFrameCreate


class SimFrameCRUD:
    """CRUD operations for SimFrame model."""

    def upsert(self, db: Session, frame_data: SimFrameCreate) -> SimFrame:
        """Create or update a simulation frame (idempotent operation).

        Uses PostgreSQL INSERT ... ON CONFLICT to ensure idempotent writes.
        If a frame with the same (sim_instance_id, seq_number) exists,
        it updates the frame_data, sim_seconds_elapsed, and is_key fields.

        Args:
            db: Database session.
            frame_data: The data for creating/updating the frame.
                Validation is handled by Pydantic schema.

        Returns:
            SimFrame: The created or updated frame.
        """
        # Build insert statement with ON CONFLICT DO UPDATE
        stmt = insert(SimFrame).values(
            sim_instance_id=frame_data.sim_instance_id,
            seq_number=frame_data.seq_number,
            sim_seconds_elapsed=frame_data.sim_seconds_elapsed,
            frame_data=frame_data.frame_data,
            is_key=frame_data.is_key,
        )

        # On conflict, update the frame
        stmt = stmt.on_conflict_do_update(
            index_elements=["sim_instance_id", "seq_number"],
            set_={
                "sim_seconds_elapsed": stmt.excluded.sim_seconds_elapsed,
                "frame_data": stmt.excluded.frame_data,
                "is_key": stmt.excluded.is_key,
            },
        )

        # Execute and return the frame ID
        result = db.execute(stmt.returning(SimFrame.id))
        db.commit()

        frame_id = result.scalar_one()

        # Fetch the full frame object
        frame = db.query(SimFrame).filter(SimFrame.id == frame_id).first()
        if frame is None:
            raise RuntimeError(f"Frame with id {frame_id} not found after upsert")
        return frame

    def get_keyframe_at_or_before(
        self, db: Session, sim_instance_id: int, position: float
    ) -> Optional[SimFrame]:
        """Get the most recent keyframe at or before the specified position.

        Args:
            db: Database session.
            sim_instance_id: The simulation instance ID.
            position: The simulation time (in seconds) to find a keyframe at or before.

        Returns:
            SimFrame: The keyframe, or None if no keyframe exists before position.
        """
        return (
            db.query(SimFrame)
            .filter(
                SimFrame.sim_instance_id == sim_instance_id,
                SimFrame.is_key == True,  # noqa: E712
                SimFrame.sim_seconds_elapsed <= position,
            )
            .order_by(desc(SimFrame.sim_seconds_elapsed))
            .first()
        )

    def get_frames_in_range(
        self,
        db: Session,
        sim_instance_id: int,
        start_time: float,
        end_time: float,
        include_start: bool = True,
    ) -> List[SimFrame]:
        """Get all frames within a time range, ordered by sim_seconds_elapsed.

        Args:
            db: Database session.
            sim_instance_id: The simulation instance ID.
            start_time: Start of the time range (inclusive or exclusive based on
                include_start).
            end_time: End of the time range (exclusive).
            include_start: If True, include frames at exactly start_time. Default True.

        Returns:
            List[SimFrame]: List of frames in the range, ordered by time.
                Returns empty list if no frames match the criteria or if
                start_time >= end_time.
        """
        query = db.query(SimFrame).filter(
            SimFrame.sim_instance_id == sim_instance_id,
            SimFrame.sim_seconds_elapsed < end_time,
        )

        if include_start:
            query = query.filter(SimFrame.sim_seconds_elapsed >= start_time)
        else:
            query = query.filter(SimFrame.sim_seconds_elapsed > start_time)

        return query.order_by(SimFrame.sim_seconds_elapsed).all()

    def upsert_many(self, db: Session, frames: List[SimFrameCreate]) -> int:
        """
        Bulk upsert multiple frames in a single DB statement.

        Uses PostgreSQL INSERT ... ON CONFLICT to upsert multiple rows.

        Important: If the input contains duplicate (sim_instance_id, seq_number)
        pairs, only the last occurrence is retained. This prevents PostgreSQL
        unique constraint violations (IntegrityError) while ensuring the most
        recent data is persisted.

        Args:
            db: Database session.
            frames: List of SimFrameCreate objects (may contain duplicates).

        Returns:
            int: Number of unique frames submitted for upsert (after deduplication).

        Raises:
            SQLAlchemyError: If the database operation fails.
        """
        if not frames:
            return 0

        # Deduplicate and build values in a single pass
        unique = {}
        for f in frames:
            key = (f.sim_instance_id, f.seq_number)
            unique[key] = {
                "sim_instance_id": f.sim_instance_id,
                "seq_number": f.seq_number,
                "sim_seconds_elapsed": f.sim_seconds_elapsed,
                "frame_data": f.frame_data,
                "is_key": f.is_key,
            }

        values = list(unique.values())

        stmt = insert(SimFrame).values(values)
        stmt = stmt.on_conflict_do_update(
            index_elements=["sim_instance_id", "seq_number"],
            set_={
                "sim_seconds_elapsed": stmt.excluded.sim_seconds_elapsed,
                "frame_data": stmt.excluded.frame_data,
                "is_key": stmt.excluded.is_key,
            },
        )

        db.execute(stmt)
        db.commit()

        return len(values)

    def has_frames_after(
        self, db: Session, sim_instance_id: int, after_time: float
    ) -> bool:
        """Check if any frames exist after the specified time.

        Uses an efficient LIMIT 1 query to check existence without fetching
        all matching frames.

        Args:
            db: Database session.
            sim_instance_id: The simulation instance ID.
            after_time: The simulation time (in seconds) to check after.

        Returns:
            bool: True if at least one frame exists after the specified time.
        """
        return (
            db.query(SimFrame)
            .filter(
                SimFrame.sim_instance_id == sim_instance_id,
                SimFrame.sim_seconds_elapsed > after_time,
            )
            .limit(1)
            .first()
            is not None
        )

    def get_frames_up_to_seq(
        self, db: Session, sim_instance_id: int, max_seq: int
    ) -> List[SimFrame]:
        """Get all frames from seq 0 up to and including max_seq.

        Used for branching to retrieve all frames that should be copied.

        Args:
            db: Database session.
            sim_instance_id: The simulation instance ID.
            max_seq: The maximum sequence number to retrieve (inclusive).

        Returns:
            List[SimFrame]: List of frames ordered by seq_number.
        """
        return (
            db.query(SimFrame)
            .filter(
                SimFrame.sim_instance_id == sim_instance_id,
                SimFrame.seq_number <= max_seq,
            )
            .order_by(SimFrame.seq_number)
            .all()
        )

    def copy_frames_to_new_instance(
        self,
        db: Session,
        source_sim_instance_id: int,
        target_sim_instance_id: int,
        max_seq: int,
    ) -> int:
        """Copy all frames from source to target simulation up to max_seq.

        Uses efficient SQLAlchemy INSERT ... SELECT for bulk copying.
        Frames are copied with the same seq_number, sim_seconds_elapsed,
        frame_data, and is_key values, but with the new sim_instance_id.

        Args:
            db: Database session.
            source_sim_instance_id: The source simulation instance ID.
            target_sim_instance_id: The target simulation instance ID.
            max_seq: Maximum sequence number to copy (inclusive).

        Returns:
            int: Number of frames copied.
        """
        # Build SELECT query for source frames
        source_select = (
            select(
                literal(target_sim_instance_id).label("sim_instance_id"),
                SimFrame.seq_number,
                SimFrame.sim_seconds_elapsed,
                SimFrame.frame_data,
                SimFrame.is_key,
                func.now().label("created_at"),
            )
            .where(SimFrame.sim_instance_id == source_sim_instance_id)
            .where(SimFrame.seq_number <= max_seq)
            .order_by(SimFrame.seq_number)
        )

        # Use INSERT ... FROM SELECT for efficient bulk copy
        insert_stmt = insert(SimFrame).from_select(
            [
                "sim_instance_id",
                "seq_number",
                "sim_seconds_elapsed",
                "frame_data",
                "is_key",
                "created_at",
            ],
            source_select,
        )

        result = db.execute(insert_stmt)
        db.commit()

        # rowcount is available but not in typing stubs
        return result.rowcount  # type: ignore[attr-defined,no-any-return]


sim_frame_crud = SimFrameCRUD()
