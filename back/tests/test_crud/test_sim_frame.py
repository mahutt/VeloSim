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

import pytest
from unittest.mock import MagicMock
from back.crud.sim_frame import sim_frame_crud
from back.models.sim_frame import SimFrame
from back.schemas.sim_frame import SimFrameCreate


@pytest.fixture
def frame() -> SimFrame:
    return SimFrame(
        id=1,
        sim_instance_id=100,
        seq_number=5,
        sim_seconds_elapsed=5.0,
        frame_data={"test": "data"},
        is_key=True,
    )


@pytest.fixture
def frame_data() -> SimFrameCreate:
    return SimFrameCreate(
        sim_instance_id=100,
        seq_number=10,
        sim_seconds_elapsed=10.5,
        frame_data={"clock": {"simSecondsPassed": 10.5}},
        is_key=False,
    )


class TestSimFrameCRUD:
    """Tests for SimFrame CRUD operations."""

    def test_upsert_creates_new_frame(
        self, mock_db: MagicMock, frame_data: SimFrameCreate
    ) -> None:
        """Test that upsert creates a new frame when it doesn't exist."""
        # Mock the execute and query chain
        mock_result = MagicMock()
        mock_result.scalar_one.return_value = 123
        mock_db.execute.return_value = mock_result

        mock_query = MagicMock()
        mock_frame = SimFrame(
            id=123,
            sim_instance_id=frame_data.sim_instance_id,
            seq_number=frame_data.seq_number,
            sim_seconds_elapsed=frame_data.sim_seconds_elapsed,
            frame_data=frame_data.frame_data,
            is_key=frame_data.is_key,
        )
        mock_query.first.return_value = mock_frame
        mock_db.query.return_value.filter.return_value = mock_query

        result = sim_frame_crud.upsert(mock_db, frame_data)

        # Verify insert statement was executed
        assert mock_db.execute.call_count == 1
        assert mock_db.commit.call_count == 1

        # Verify frame was fetched and returned
        assert result is not None
        assert result.id == 123

    def test_upsert_updates_existing_frame(
        self, mock_db: MagicMock, frame_data: SimFrameCreate
    ) -> None:
        """Test upsert updates existing frame with same sim_instance_id, seq."""
        # Mock the execute and query chain for update scenario
        mock_result = MagicMock()
        mock_result.scalar_one.return_value = 456
        mock_db.execute.return_value = mock_result

        # Mock existing frame with different data
        mock_frame = SimFrame(
            id=456,
            sim_instance_id=frame_data.sim_instance_id,
            seq_number=frame_data.seq_number,
            sim_seconds_elapsed=8.0,  # Old value
            frame_data={"old": "data"},  # Old value
            is_key=True,  # Old value
        )
        mock_query = MagicMock()
        mock_query.first.return_value = mock_frame
        mock_db.query.return_value.filter.return_value = mock_query

        result = sim_frame_crud.upsert(mock_db, frame_data)

        # Verify upsert was called (ON CONFLICT DO UPDATE)
        assert mock_db.execute.call_count == 1
        assert mock_db.commit.call_count == 1

        # Verify frame was returned
        assert result is not None
        assert result.id == 456

    def test_upsert_idempotency(
        self, mock_db: MagicMock, frame_data: SimFrameCreate
    ) -> None:
        """Test that upserting the same frame twice is idempotent."""
        # Mock the execute and query chain
        mock_result = MagicMock()
        mock_result.scalar_one.return_value = 789
        mock_db.execute.return_value = mock_result

        mock_frame = SimFrame(
            id=789,
            sim_instance_id=frame_data.sim_instance_id,
            seq_number=frame_data.seq_number,
            sim_seconds_elapsed=frame_data.sim_seconds_elapsed,
            frame_data=frame_data.frame_data,
            is_key=frame_data.is_key,
        )
        mock_query = MagicMock()
        mock_query.first.return_value = mock_frame
        mock_db.query.return_value.filter.return_value = mock_query

        # Insert first time
        result1 = sim_frame_crud.upsert(mock_db, frame_data)

        # Reset mocks
        mock_db.reset_mock()
        mock_result.scalar_one.return_value = 789  # Same ID
        mock_db.execute.return_value = mock_result
        mock_db.query.return_value.filter.return_value = mock_query

        # Insert second time with same data
        result2 = sim_frame_crud.upsert(mock_db, frame_data)

        # Should succeed both times and return same frame ID
        assert result1.id == result2.id
        assert mock_db.commit.call_count == 1  # Second upsert also commits

    def test_upsert_validates_frame_data_dict(self, mock_db: MagicMock) -> None:
        """Test that Pydantic schema rejects non-dict frame_data."""
        from pydantic import ValidationError

        with pytest.raises(ValidationError, match="Input should be a valid dictionary"):
            SimFrameCreate(
                sim_instance_id=100,
                seq_number=1,
                sim_seconds_elapsed=1.0,
                frame_data="invalid",  # type: ignore
                is_key=False,
            )

        # Should never reach CRUD layer
        mock_db.execute.assert_not_called()
        mock_db.commit.assert_not_called()

    def test_upsert_validates_negative_sim_seconds(self, mock_db: MagicMock) -> None:
        """Test that Pydantic schema rejects negative sim_seconds_elapsed."""
        from pydantic import ValidationError

        with pytest.raises(
            ValidationError, match="Input should be greater than or equal to 0"
        ):
            SimFrameCreate(
                sim_instance_id=100,
                seq_number=1,
                sim_seconds_elapsed=-5.0,
                frame_data={"test": "data"},
                is_key=False,
            )

        mock_db.execute.assert_not_called()
        mock_db.commit.assert_not_called()

    def test_upsert_validates_negative_seq_number(self, mock_db: MagicMock) -> None:
        """Test that Pydantic schema rejects negative seq_number."""
        from pydantic import ValidationError

        with pytest.raises(
            ValidationError, match="Input should be greater than or equal to 0"
        ):
            SimFrameCreate(
                sim_instance_id=100,
                seq_number=-1,
                sim_seconds_elapsed=1.0,
                frame_data={"test": "data"},
                is_key=False,
            )

        mock_db.execute.assert_not_called()
        mock_db.commit.assert_not_called()

    def test_upsert_handles_keyframes_and_diffs(self, mock_db: MagicMock) -> None:
        """Test that upsert correctly handles both keyframes and diff frames."""
        # Create keyframe
        keyframe_data = SimFrameCreate(
            sim_instance_id=100,
            seq_number=0,
            sim_seconds_elapsed=0.0,
            frame_data={"full": "state"},
            is_key=True,
        )

        # Create diff frame
        diff_data = SimFrameCreate(
            sim_instance_id=100,
            seq_number=1,
            sim_seconds_elapsed=0.016,
            frame_data={"diff": "changes"},
            is_key=False,
        )

        # Mock responses
        mock_result = MagicMock()
        mock_result.scalar_one.side_effect = [111, 222]
        mock_db.execute.return_value = mock_result

        mock_keyframe = SimFrame(
            id=111,
            sim_instance_id=100,
            seq_number=0,
            sim_seconds_elapsed=0.0,
            frame_data={"full": "state"},
            is_key=True,
        )
        mock_diff = SimFrame(
            id=222,
            sim_instance_id=100,
            seq_number=1,
            sim_seconds_elapsed=0.016,
            frame_data={"diff": "changes"},
            is_key=False,
        )

        mock_query = MagicMock()
        mock_query.first.side_effect = [mock_keyframe, mock_diff]
        mock_db.query.return_value.filter.return_value = mock_query

        # Upsert both
        keyframe_result = sim_frame_crud.upsert(mock_db, keyframe_data)
        diff_result = sim_frame_crud.upsert(mock_db, diff_data)

        # Verify both were created
        assert keyframe_result.is_key is True
        assert diff_result.is_key is False
        assert mock_db.commit.call_count == 2

    def test_upsert_unique_constraint_respected(self, mock_db: MagicMock) -> None:
        """Test that unique constraint on (sim_instance_id, seq_number) works."""
        frame1 = SimFrameCreate(
            sim_instance_id=100,
            seq_number=5,
            sim_seconds_elapsed=5.0,
            frame_data={"version": "1"},
            is_key=True,
        )

        frame2 = SimFrameCreate(
            sim_instance_id=100,
            seq_number=5,  # Same seq_number
            sim_seconds_elapsed=5.5,  # Different data
            frame_data={"version": "2"},
            is_key=False,
        )

        # Mock first insert
        mock_result1 = MagicMock()
        mock_result1.scalar_one.return_value = 333
        mock_db.execute.return_value = mock_result1

        mock_frame1 = SimFrame(
            id=333,
            sim_instance_id=100,
            seq_number=5,
            sim_seconds_elapsed=5.0,
            frame_data={"version": "1"},
            is_key=True,
        )
        mock_query = MagicMock()
        mock_query.first.return_value = mock_frame1
        mock_db.query.return_value.filter.return_value = mock_query

        result1 = sim_frame_crud.upsert(mock_db, frame1)
        assert result1.id == 333

        # Mock second insert (should update, not create new)
        mock_db.reset_mock()
        mock_result2 = MagicMock()
        mock_result2.scalar_one.return_value = 333  # Same ID!
        mock_db.execute.return_value = mock_result2

        # Updated frame with new data
        updated_frame = SimFrame(
            id=333,
            sim_instance_id=100,
            seq_number=5,
            sim_seconds_elapsed=5.5,
            frame_data={"version": "2"},
            is_key=False,
        )
        mock_query.first.return_value = updated_frame
        mock_db.query.return_value.filter.return_value = mock_query

        result2 = sim_frame_crud.upsert(mock_db, frame2)

        # Should return same ID (update, not insert)
        assert result2.id == 333
