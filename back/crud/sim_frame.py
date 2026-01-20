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


sim_frame_crud = SimFrameCRUD()
