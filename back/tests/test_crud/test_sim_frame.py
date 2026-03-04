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

    def test_upsert_many_deduplication_and_on_conflict(
        self, mock_db: MagicMock
    ) -> None:
        """
        Test upsert_many deduplicates by (sim_instance_id, seq_number)
        and uses ON CONFLICT.
        """
        frames = [
            SimFrameCreate(
                sim_instance_id=1,
                seq_number=1,
                sim_seconds_elapsed=1.0,
                frame_data={"a": 1},
                is_key=True,
            ),
            SimFrameCreate(
                sim_instance_id=1,
                seq_number=1,
                sim_seconds_elapsed=2.0,
                frame_data={"a": 2},
                is_key=False,
            ),  # duplicate, should overwrite previous
            SimFrameCreate(
                sim_instance_id=1,
                seq_number=2,
                sim_seconds_elapsed=3.0,
                frame_data={"b": 3},
                is_key=True,
            ),
            SimFrameCreate(
                sim_instance_id=2,
                seq_number=1,
                sim_seconds_elapsed=4.0,
                frame_data={"c": 4},
                is_key=False,
            ),
        ]
        mock_db.execute.return_value = None
        mock_db.commit.return_value = None
        count = sim_frame_crud.upsert_many(mock_db, frames)
        assert count == 3
        assert mock_db.execute.call_count == 1
        assert mock_db.commit.call_count == 1

    def test_upsert_many_empty_list(self, mock_db: MagicMock) -> None:
        """Test upsert_many returns 0 and does not call db for empty input."""
        count = sim_frame_crud.upsert_many(mock_db, [])
        assert count == 0
        mock_db.execute.assert_not_called()
        mock_db.commit.assert_not_called()

    def test_upsert_many_sqlalchemy_error(self, mock_db: MagicMock) -> None:
        """Test upsert_many propagates SQLAlchemyError on DB failure."""
        from sqlalchemy.exc import SQLAlchemyError

        frames = [
            SimFrameCreate(
                sim_instance_id=1,
                seq_number=1,
                sim_seconds_elapsed=1.0,
                frame_data={"a": 1},
                is_key=True,
            )
        ]
        mock_db.execute.side_effect = SQLAlchemyError("DB error")
        with pytest.raises(SQLAlchemyError):
            sim_frame_crud.upsert_many(mock_db, frames)
        mock_db.commit.assert_not_called()

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

    def test_get_keyframe_at_or_before_returns_latest_keyframe(
        self, mock_db: MagicMock
    ) -> None:
        """Test that get_keyframe_at_or_before returns the most recent keyframe."""
        # Mock keyframes at 0, 5, 10 seconds
        keyframe = SimFrame(
            id=2,
            sim_instance_id=100,
            seq_number=10,
            sim_seconds_elapsed=5.0,
            frame_data={"time": 5.0},
            is_key=True,
        )

        mock_query = MagicMock()
        mock_query.first.return_value = keyframe
        mock_db.query.return_value.filter.return_value.order_by.return_value = (
            mock_query
        )

        result = sim_frame_crud.get_keyframe_at_or_before(
            mock_db, sim_instance_id=100, position=7.5
        )

        assert result is not None
        assert result.sim_seconds_elapsed == 5.0
        assert result.is_key is True

    def test_get_keyframe_at_or_before_returns_none_when_no_keyframe(
        self, mock_db: MagicMock
    ) -> None:
        """Test that get_keyframe_at_or_before returns None when no keyframe exists."""
        mock_query = MagicMock()
        mock_query.first.return_value = None
        mock_db.query.return_value.filter.return_value.order_by.return_value = (
            mock_query
        )

        result = sim_frame_crud.get_keyframe_at_or_before(
            mock_db, sim_instance_id=100, position=0.5
        )

        assert result is None

    def test_get_keyframe_at_or_before_exact_match(self, mock_db: MagicMock) -> None:
        """Test get_keyframe_at_or_before when position exactly matches a keyframe."""
        keyframe = SimFrame(
            id=1,
            sim_instance_id=100,
            seq_number=0,
            sim_seconds_elapsed=10.0,
            frame_data={"time": 10.0},
            is_key=True,
        )

        mock_query = MagicMock()
        mock_query.first.return_value = keyframe
        mock_db.query.return_value.filter.return_value.order_by.return_value = (
            mock_query
        )

        result = sim_frame_crud.get_keyframe_at_or_before(
            mock_db, sim_instance_id=100, position=10.0
        )

        assert result is not None
        assert result.sim_seconds_elapsed == 10.0

    def test_get_frames_in_range_returns_frames_in_order(
        self, mock_db: MagicMock
    ) -> None:
        """Test that get_frames_in_range returns frames in chronological order."""
        frames = [
            SimFrame(
                id=1,
                sim_instance_id=100,
                seq_number=1,
                sim_seconds_elapsed=1.0,
                frame_data={},
                is_key=False,
            ),
            SimFrame(
                id=2,
                sim_instance_id=100,
                seq_number=2,
                sim_seconds_elapsed=2.0,
                frame_data={},
                is_key=False,
            ),
            SimFrame(
                id=3,
                sim_instance_id=100,
                seq_number=3,
                sim_seconds_elapsed=3.0,
                frame_data={},
                is_key=False,
            ),
        ]

        mock_query_chain = (
            mock_db.query.return_value.filter.return_value.filter.return_value
        )
        mock_query_chain.order_by.return_value.all.return_value = frames

        result = sim_frame_crud.get_frames_in_range(
            mock_db, sim_instance_id=100, start_time=0.5, end_time=3.5
        )

        assert len(result) == 3
        assert result[0].sim_seconds_elapsed == 1.0
        assert result[2].sim_seconds_elapsed == 3.0

    def test_get_frames_in_range_exclude_start(self, mock_db: MagicMock) -> None:
        """Test that get_frames_in_range excludes start when include_start=False."""
        frames = [
            SimFrame(
                id=2,
                sim_instance_id=100,
                seq_number=2,
                sim_seconds_elapsed=2.0,
                frame_data={},
                is_key=False,
            ),
        ]

        mock_query_chain = (
            mock_db.query.return_value.filter.return_value.filter.return_value
        )
        mock_query_chain.order_by.return_value.all.return_value = frames

        result = sim_frame_crud.get_frames_in_range(
            mock_db,
            sim_instance_id=100,
            start_time=1.0,
            end_time=3.0,
            include_start=False,
        )

        # Should not include frame at exactly 1.0 seconds
        assert len(result) == 1
        assert result[0].sim_seconds_elapsed == 2.0

    def test_get_frames_in_range_empty_range(self, mock_db: MagicMock) -> None:
        """Test that get_frames_in_range returns empty list when no frames in range."""
        mock_query_chain = (
            mock_db.query.return_value.filter.return_value.filter.return_value
        )
        mock_query_chain.order_by.return_value.all.return_value = []

        result = sim_frame_crud.get_frames_in_range(
            mock_db, sim_instance_id=100, start_time=100.0, end_time=200.0
        )

        assert result == []

    def test_get_frames_in_range_include_end_includes_frame_at_end_time(
        self, mock_db: MagicMock
    ) -> None:
        """Test that include_end=True includes the frame at exactly end_time.

        Regression: without include_end=True, a frame at exactly end_time
        is excluded by the strict `< end_time` filter, creating a silent dead
        zone where the frame appears in neither future_frames nor has_more_frames.
        """
        frame_at_end = SimFrame(
            id=1,
            sim_instance_id=100,
            seq_number=7,
            sim_seconds_elapsed=7.0,
            frame_data={},
            is_key=False,
        )

        mock_query_chain = (
            mock_db.query.return_value.filter.return_value.filter.return_value
        )
        mock_query_chain.order_by.return_value.all.return_value = [frame_at_end]

        result = sim_frame_crud.get_frames_in_range(
            mock_db,
            sim_instance_id=100,
            start_time=2.0,
            end_time=7.0,
            include_start=True,
            include_end=True,
        )

        assert len(result) == 1
        assert result[0].sim_seconds_elapsed == 7.0

    def test_get_frames_in_range_zero_width_with_include_end_returns_frame_at_boundary(
        self, mock_db: MagicMock
    ) -> None:
        """Test zero-width range [t, t] with include_end=True returns frame at t.

        Regression: seeking with frame_window_seconds=0 produced an empty range
        [position, position) that excluded the frame at exactly position even
        though it is the first frame the player needs.
        """
        frame_at_position = SimFrame(
            id=1,
            sim_instance_id=100,
            seq_number=2,
            sim_seconds_elapsed=2.0,
            frame_data={},
            is_key=False,
        )

        mock_query_chain = (
            mock_db.query.return_value.filter.return_value.filter.return_value
        )
        mock_query_chain.order_by.return_value.all.return_value = [frame_at_position]

        result = sim_frame_crud.get_frames_in_range(
            mock_db,
            sim_instance_id=100,
            start_time=2.0,
            end_time=2.0,  # zero-width range
            include_start=True,
            include_end=True,
        )

        assert len(result) == 1
        assert result[0].sim_seconds_elapsed == 2.0

    def test_has_frames_after_returns_true_when_frames_exist(
        self, mock_db: MagicMock
    ) -> None:
        """Test has_frames_after returns True when frames exist after the time."""
        frame = SimFrame(
            id=1,
            sim_instance_id=100,
            seq_number=10,
            sim_seconds_elapsed=15.0,
            frame_data={},
            is_key=False,
        )

        mock_query = MagicMock()
        mock_query.first.return_value = frame
        mock_db.query.return_value.filter.return_value.limit.return_value = mock_query

        result = sim_frame_crud.has_frames_after(
            mock_db, sim_instance_id=100, after_time=10.0
        )

        assert result is True

    def test_has_frames_after_returns_false_when_no_frames(
        self, mock_db: MagicMock
    ) -> None:
        """Test has_frames_after returns False when no frames exist after the time."""
        mock_query = MagicMock()
        mock_query.first.return_value = None
        mock_db.query.return_value.filter.return_value.limit.return_value = mock_query

        result = sim_frame_crud.has_frames_after(
            mock_db, sim_instance_id=100, after_time=100.0
        )

        assert result is False

    def test_get_frames_up_to_seq(self, mock_db: MagicMock) -> None:
        """Test get_frames_up_to_seq retrieves all frames up to max_seq."""
        mock_frames = [
            SimFrame(
                id=1,
                sim_instance_id=100,
                seq_number=0,
                sim_seconds_elapsed=0.0,
                frame_data={"test": "data0"},
                is_key=True,
            ),
            SimFrame(
                id=2,
                sim_instance_id=100,
                seq_number=1,
                sim_seconds_elapsed=0.5,
                frame_data={"test": "data1"},
                is_key=False,
            ),
            SimFrame(
                id=3,
                sim_instance_id=100,
                seq_number=2,
                sim_seconds_elapsed=1.0,
                frame_data={"test": "data2"},
                is_key=False,
            ),
        ]

        mock_query = MagicMock()
        mock_query.all.return_value = mock_frames
        (mock_db.query.return_value.filter.return_value.order_by.return_value) = (
            mock_query
        )

        result = sim_frame_crud.get_frames_up_to_seq(
            mock_db, sim_instance_id=100, max_seq=2
        )

        assert len(result) == 3
        assert all(f.sim_instance_id == 100 for f in result)
        assert all(f.seq_number <= 2 for f in result)

    def test_get_frames_up_to_seq_empty_result(self, mock_db: MagicMock) -> None:
        """Test get_frames_up_to_seq returns empty list when no frames match."""
        mock_query = MagicMock()
        mock_query.all.return_value = []
        (mock_db.query.return_value.filter.return_value.order_by.return_value) = (
            mock_query
        )

        result = sim_frame_crud.get_frames_up_to_seq(
            mock_db, sim_instance_id=999, max_seq=10
        )

        assert result == []

    def test_copy_frames_to_new_instance(self, mock_db: MagicMock) -> None:
        """Test copy_frames_to_new_instance executes SQL and returns rowcount."""
        mock_result = MagicMock()
        mock_result.rowcount = 5
        mock_db.execute.return_value = mock_result

        frames_copied = sim_frame_crud.copy_frames_to_new_instance(
            mock_db,
            source_sim_instance_id=100,
            target_sim_instance_id=200,
            max_seq=4,
        )

        # Verify SQL was executed (now using SQLAlchemy constructs)
        assert mock_db.execute.call_count == 1

        # Verify commit was called
        assert mock_db.commit.call_count == 1

        # Verify rowcount was returned
        assert frames_copied == 5

    def test_copy_frames_to_new_instance_no_frames(self, mock_db: MagicMock) -> None:
        """Test copy_frames_to_new_instance returns 0 when no frames to copy."""
        mock_result = MagicMock()
        mock_result.rowcount = 0
        mock_db.execute.return_value = mock_result

        frames_copied = sim_frame_crud.copy_frames_to_new_instance(
            mock_db,
            source_sim_instance_id=100,
            target_sim_instance_id=200,
            max_seq=10,
        )

        assert frames_copied == 0
        assert mock_db.commit.call_count == 1

    def test_get_max_seq_number_returns_max(self, mock_db: MagicMock) -> None:
        """Test get_max_seq_number returns the highest seq_number when frames exist."""
        mock_db.query.return_value.filter.return_value.scalar.return_value = 49

        result = sim_frame_crud.get_max_seq_number(mock_db, sim_instance_id=1)

        assert result == 49

    def test_get_max_seq_number_no_frames_returns_minus_one(
        self, mock_db: MagicMock
    ) -> None:
        """Test get_max_seq_number returns -1 when no frames exist for the sim."""
        mock_db.query.return_value.filter.return_value.scalar.return_value = None

        result = sim_frame_crud.get_max_seq_number(mock_db, sim_instance_id=999)

        assert result == -1
