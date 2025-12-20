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
from unittest.mock import Mock
from pydantic import ValidationError
from back.crud.sim_keyframe import sim_keyframe_crud
from back.exceptions import ItemNotFoundError
from back.models.sim_keyframe import SimKeyframe
from back.schemas.sim_keyframe import SimKeyframeCreate
from back.tests.mock_utils import setup_mock_db_add_with_id


@pytest.fixture
def keyframe() -> SimKeyframe:
    return SimKeyframe(
        id=1,
        sim_instance_id=100,
        sim_seconds_elapsed=120.5,
        frame_data={"simId": "test-123", "tasks": [], "stations": [], "resources": []},
    )


@pytest.fixture
def keyframe_data() -> SimKeyframeCreate:
    return SimKeyframeCreate(
        sim_instance_id=100,
        sim_seconds_elapsed=60.0,
        frame_data={"simId": "test-456", "tasks": [], "stations": []},
    )


class TestSimKeyframeCRUD:

    # ------------------ CREATE ------------------ #
    def test_create_valid(
        self, mock_db: Mock, keyframe_data: SimKeyframeCreate
    ) -> None:
        setup_mock_db_add_with_id(mock_db, id_value=1)

        kf = sim_keyframe_crud.create(mock_db, keyframe_data)
        assert kf.id is not None
        assert kf.sim_instance_id == 100
        assert kf.sim_seconds_elapsed == 60.0
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()

    def test_create_invalid_frame_data_type(self, mock_db: Mock) -> None:
        """Test that non-dict frame_data raises ValidationError."""
        with pytest.raises(ValidationError):
            SimKeyframeCreate(
                sim_instance_id=100,
                sim_seconds_elapsed=60.0,
                frame_data="not a dict",  # type: ignore
            )

    def test_create_negative_sim_seconds(self, mock_db: Mock) -> None:
        """Test that negative sim_seconds_elapsed raises ValidationError."""
        with pytest.raises(ValidationError):
            SimKeyframeCreate(
                sim_instance_id=100,
                sim_seconds_elapsed=-10.0,
                frame_data={"test": "data"},
            )

    def test_create_missing_required_fields(self) -> None:
        """Test that missing required fields triggers ValidationError."""
        with pytest.raises(ValidationError):
            SimKeyframeCreate(  # type: ignore
                sim_instance_id=100,
                frame_data={"test": "data"},
            )

    # ------------------ GET ------------------ #
    def test_get_valid(self, mock_db: Mock, keyframe: SimKeyframe) -> None:
        mock_query = Mock()
        mock_filter = Mock()
        mock_filter.first.return_value = keyframe
        mock_query.filter.return_value = mock_filter
        mock_db.query.return_value = mock_query

        fetched = sim_keyframe_crud.get(mock_db, keyframe.id)
        assert fetched.id == keyframe.id
        mock_db.query.assert_called_once()

    def test_get_nonexistent(self, mock_db: Mock) -> None:
        mock_query = Mock()
        mock_filter = Mock()
        mock_filter.first.return_value = None
        mock_query.filter.return_value = mock_filter
        mock_db.query.return_value = mock_query

        with pytest.raises(ItemNotFoundError, match="Keyframe not found"):
            sim_keyframe_crud.get(mock_db, 99999)

    # ------------------ GET BY SIM INSTANCE ------------------ #
    def test_get_by_sim_instance(self, mock_db: Mock, keyframe: SimKeyframe) -> None:
        mock_query = Mock()
        mock_filter = Mock()
        mock_order = Mock()
        mock_offset = Mock()
        mock_limit = Mock()

        mock_filter.count.return_value = 1
        mock_limit.all.return_value = [keyframe]
        mock_offset.limit.return_value = mock_limit
        mock_order.offset.return_value = mock_offset
        mock_filter.order_by.return_value = mock_order
        mock_query.filter.return_value = mock_filter
        mock_db.query.return_value = mock_query

        keyframes, total = sim_keyframe_crud.get_by_sim_instance(
            mock_db, 100, skip=0, limit=10
        )
        assert len(keyframes) == 1
        assert total == 1
        assert keyframes[0].id == keyframe.id

    def test_get_by_sim_instance_pagination(self, mock_db: Mock) -> None:
        """Test pagination works correctly."""
        kf1 = SimKeyframe(
            id=1, sim_instance_id=100, sim_seconds_elapsed=10.0, frame_data={}
        )
        kf2 = SimKeyframe(
            id=2, sim_instance_id=100, sim_seconds_elapsed=20.0, frame_data={}
        )
        SimKeyframe(id=3, sim_instance_id=100, sim_seconds_elapsed=30.0, frame_data={})

        mock_query = Mock()
        mock_filter = Mock()
        mock_order = Mock()
        mock_offset = Mock()
        mock_limit = Mock()

        mock_filter.count.return_value = 3
        # First page
        mock_limit.all.return_value = [kf1, kf2]
        mock_offset.limit.return_value = mock_limit
        mock_order.offset.return_value = mock_offset
        mock_filter.order_by.return_value = mock_order
        mock_query.filter.return_value = mock_filter
        mock_db.query.return_value = mock_query

        keyframes, total = sim_keyframe_crud.get_by_sim_instance(
            mock_db, 100, skip=0, limit=2
        )
        assert len(keyframes) == 2
        assert total == 3

    # ------------------ GET BY SIM TIME ------------------ #
    def test_get_by_sim_time_exact_match(
        self, mock_db: Mock, keyframe: SimKeyframe
    ) -> None:
        mock_query = Mock()
        mock_filter = Mock()
        mock_order = Mock()
        mock_order.first.return_value = keyframe
        mock_filter.order_by.return_value = mock_order
        mock_query.filter.return_value = mock_filter
        mock_db.query.return_value = mock_query

        result = sim_keyframe_crud.get_by_sim_time(mock_db, 100, 120.5)
        assert result is not None
        assert result.id == keyframe.id
        assert result.sim_seconds_elapsed == 120.5

    def test_get_by_sim_time_nearest_preceding(self, mock_db: Mock) -> None:
        """Test that it returns the nearest preceding keyframe."""
        kf = SimKeyframe(
            id=1, sim_instance_id=100, sim_seconds_elapsed=100.0, frame_data={}
        )

        mock_query = Mock()
        mock_filter = Mock()
        mock_order = Mock()
        mock_order.first.return_value = kf
        mock_filter.order_by.return_value = mock_order
        mock_query.filter.return_value = mock_filter
        mock_db.query.return_value = mock_query

        # Request time 150.0, should get keyframe at 100.0
        result = sim_keyframe_crud.get_by_sim_time(mock_db, 100, 150.0)
        assert result is not None
        assert result.sim_seconds_elapsed == 100.0

    def test_get_by_sim_time_none_before(self, mock_db: Mock) -> None:
        """Test that None is returned when no keyframe exists before requested time."""
        mock_query = Mock()
        mock_filter = Mock()
        mock_order = Mock()
        mock_order.first.return_value = None
        mock_filter.order_by.return_value = mock_order
        mock_query.filter.return_value = mock_filter
        mock_db.query.return_value = mock_query

        result = sim_keyframe_crud.get_by_sim_time(mock_db, 100, 5.0)
        assert result is None

    # ------------------ DELETE ------------------ #
    def test_delete_valid(self, mock_db: Mock, keyframe: SimKeyframe) -> None:
        mock_query = Mock()
        mock_filter = Mock()
        mock_filter.first.return_value = keyframe
        mock_query.filter.return_value = mock_filter
        mock_db.query.return_value = mock_query

        sim_keyframe_crud.delete(mock_db, keyframe.id)
        mock_db.delete.assert_called_once_with(keyframe)
        mock_db.commit.assert_called_once()

    def test_delete_nonexistent(self, mock_db: Mock) -> None:
        mock_query = Mock()
        mock_filter = Mock()
        mock_filter.first.return_value = None
        mock_query.filter.return_value = mock_filter
        mock_db.query.return_value = mock_query

        with pytest.raises(ItemNotFoundError, match="Keyframe not found"):
            sim_keyframe_crud.delete(mock_db, 99999)
