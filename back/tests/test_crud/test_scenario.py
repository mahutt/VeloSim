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
from back.crud.scenario import scenario_crud
from back.crud.user import user_crud
from back.exceptions import ItemNotFoundError
from back.models import User
from back.schemas.scenario import ScenarioCreate, ScenarioUpdate
from back.models.scenario import Scenario
from back.tests.mock_utils import setup_mock_db_add_with_id


@pytest.fixture
def test_user() -> User:
    user = User(
        id=1,
        username="test_user",
        password_hash=user_crud.hash_password("password"),
        is_admin=False,
        is_enabled=True,
    )
    return user


@pytest.fixture
def another_user() -> User:
    user = User(
        id=2,
        username="other_user",
        password_hash=user_crud.hash_password("password"),
        is_admin=False,
        is_enabled=True,
    )
    return user


@pytest.fixture
def scenario(test_user: User) -> Scenario:
    return Scenario(
        id=1,
        name="Test Scenario",
        content={"foo": "bar"},
        description="A test scenario",
        user_id=test_user.id,
    )


class TestScenarioCRUD:

    # ------------------ CREATE ------------------ #
    def test_create_valid(self, mock_db: Mock, test_user: User) -> None:
        setup_mock_db_add_with_id(mock_db, id_value=1)

        data = ScenarioCreate(
            name="New Scenario",
            content={"data": 123},
            description="Create test",
            user_id=test_user.id,
        )
        s = scenario_crud.create(mock_db, data)
        assert s.id is not None
        assert s.name == "New Scenario"
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()

    def test_create_missing_name_or_content(self, test_user: User) -> None:
        # Omitting required fields triggers ValidationError
        with pytest.raises(ValidationError):
            ScenarioCreate(  # type: ignore
                content={"data": 1},
                description="desc",
                user_id=test_user.id,
            )

        with pytest.raises(ValidationError):
            ScenarioCreate(  # type: ignore
                name="Missing content",
                description="desc",
                user_id=test_user.id,
            )

    def test_create_invalid_content_type(self, test_user: User) -> None:
        with pytest.raises(ValidationError):
            ScenarioCreate(
                name="Invalid",
                content="string instead of dict",  # type: ignore
                description="desc",
                user_id=test_user.id,
            )

    # ------------------ GET ------------------ #
    def test_get_valid(
        self, mock_db: Mock, scenario: Scenario, test_user: User
    ) -> None:
        mock_query = Mock()
        mock_filter = Mock()
        mock_filter.first.return_value = scenario
        mock_query.filter.return_value = mock_filter
        mock_db.query.return_value = mock_query

        fetched = scenario_crud.get(mock_db, scenario.id, user_id=test_user.id)
        assert fetched.id == scenario.id
        mock_db.query.assert_called_once()

    def test_get_wrong_user_or_nonexistent(
        self, mock_db: Mock, scenario: Scenario, another_user: User
    ) -> None:
        mock_query = Mock()
        mock_filter = Mock()
        mock_filter.first.return_value = None
        mock_query.filter.return_value = mock_filter
        mock_db.query.return_value = mock_query

        with pytest.raises(ItemNotFoundError):
            scenario_crud.get(mock_db, scenario.id, user_id=another_user.id)
        with pytest.raises(ItemNotFoundError):
            scenario_crud.get(mock_db, 99999, user_id=another_user.id)

    def test_get_by_name_and_user(
        self, mock_db: Mock, scenario: Scenario, test_user: User, another_user: User
    ) -> None:
        """Test getting scenario by name and user."""
        mock_query = Mock()
        mock_filter = Mock()
        mock_filter.first.side_effect = [scenario, None, None]
        mock_query.filter.return_value = mock_filter
        mock_db.query.return_value = mock_query

        # Should find the existing scenario
        found = scenario_crud.get_by_name_and_user(mock_db, scenario.name, test_user.id)
        assert found is not None
        assert found.id == scenario.id
        assert found.name == scenario.name

        # Should not find scenario for different user
        not_found = scenario_crud.get_by_name_and_user(
            mock_db, scenario.name, another_user.id
        )
        assert not_found is None

        # Should not find non-existent scenario name
        not_found2 = scenario_crud.get_by_name_and_user(
            mock_db, "Non-existent Scenario", test_user.id
        )
        assert not_found2 is None

    # ------------------ UPDATE ------------------ #
    def test_update_valid(
        self, mock_db: Mock, scenario: Scenario, test_user: User
    ) -> None:
        mock_query = Mock()
        mock_filter = Mock()
        mock_filter.first.return_value = scenario
        mock_query.filter.return_value = mock_filter
        mock_db.query.return_value = mock_query

        update_data = ScenarioUpdate(
            name="Updated Scenario",
            content={"a": 1},
            description="Updated description",
        )
        updated = scenario_crud.update(mock_db, scenario.id, test_user.id, update_data)
        assert updated.name == "Updated Scenario"
        mock_db.commit.assert_called_once()

    def test_update_wrong_user_or_invalid(
        self, mock_db: Mock, scenario: Scenario, another_user: User, test_user: User
    ) -> None:
        mock_query = Mock()
        mock_filter = Mock()
        mock_filter.first.return_value = None
        mock_query.filter.return_value = mock_filter
        mock_db.query.return_value = mock_query

        update_data = ScenarioUpdate(
            name="Hacked", content={"a": 1}, description="desc"
        )
        with pytest.raises(ItemNotFoundError):
            scenario_crud.update(mock_db, scenario.id, another_user.id, update_data)

        # Invalid content type triggers ValidationError
        with pytest.raises(ValidationError):
            ScenarioUpdate(
                name="Invalid",
                content="not dict",  # type: ignore
                description="desc",
            )

    # ------------------ DELETE ------------------ #
    def test_delete_valid(
        self, mock_db: Mock, scenario: Scenario, test_user: User
    ) -> None:
        mock_query = Mock()
        mock_filter = Mock()
        mock_filter.first.side_effect = [scenario, None]
        mock_query.filter.return_value = mock_filter
        mock_db.query.return_value = mock_query

        scenario_crud.delete(mock_db, scenario.id, test_user.id)
        mock_db.delete.assert_called_once_with(scenario)
        mock_db.commit.assert_called_once()

        with pytest.raises(ItemNotFoundError):
            scenario_crud.get(mock_db, scenario.id, test_user.id)

    def test_delete_wrong_user_or_nonexistent(
        self, mock_db: Mock, scenario: Scenario, another_user: User, test_user: User
    ) -> None:
        mock_query = Mock()
        mock_filter = Mock()
        mock_filter.first.return_value = None
        mock_query.filter.return_value = mock_filter
        mock_db.query.return_value = mock_query

        with pytest.raises(ItemNotFoundError):
            scenario_crud.delete(mock_db, scenario.id, another_user.id)
        with pytest.raises(ItemNotFoundError):
            scenario_crud.delete(mock_db, 99999, test_user.id)

    # ------------------ PAGINATION ------------------ #
    def test_get_by_user_pagination(self, mock_db: Mock, test_user: User) -> None:
        # Create mock scenarios
        mock_scenarios = [
            Scenario(
                id=i,
                name=f"Scenario {i}",
                content={"num": i},
                description=f"desc {i}",
                user_id=test_user.id,
            )
            for i in range(5)
        ]

        # Mock count query
        mock_count_query = Mock()
        mock_count_filter = Mock()
        mock_count_filter.scalar.return_value = 5
        mock_count_query.filter.return_value = mock_count_filter

        # Mock data queries
        mock_data_query1 = Mock()
        mock_data_filter1 = Mock()
        mock_order1 = Mock()
        mock_offset1 = Mock()
        mock_limit1 = Mock()
        mock_limit1.all.return_value = mock_scenarios[:2]
        mock_offset1.limit.return_value = mock_limit1
        mock_order1.offset.return_value = mock_offset1
        mock_data_filter1.order_by.return_value = mock_order1
        mock_data_query1.filter.return_value = mock_data_filter1

        mock_data_query2 = Mock()
        mock_data_filter2 = Mock()
        mock_order2 = Mock()
        mock_offset2 = Mock()
        mock_limit2 = Mock()
        mock_limit2.all.return_value = mock_scenarios[2:4]
        mock_offset2.limit.return_value = mock_limit2
        mock_order2.offset.return_value = mock_offset2
        mock_data_filter2.order_by.return_value = mock_order2
        mock_data_query2.filter.return_value = mock_data_filter2

        mock_data_query3 = Mock()
        mock_data_filter3 = Mock()
        mock_order3 = Mock()
        mock_offset3 = Mock()
        mock_limit3 = Mock()
        mock_limit3.all.return_value = []
        mock_offset3.limit.return_value = mock_limit3
        mock_order3.offset.return_value = mock_offset3
        mock_data_filter3.order_by.return_value = mock_order3
        mock_data_query3.filter.return_value = mock_data_filter3

        mock_db.query.side_effect = [
            mock_count_query,
            mock_data_query1,
            mock_count_query,
            mock_data_query2,
            mock_count_query,
            mock_data_query3,
        ]

        scenarios, total = scenario_crud.get_by_user(
            mock_db, test_user.id, skip=0, limit=2
        )
        assert total == 5
        assert len(scenarios) == 2

        scenarios2, _ = scenario_crud.get_by_user(
            mock_db, test_user.id, skip=2, limit=2
        )
        assert len(scenarios2) == 2

        scenarios3, _ = scenario_crud.get_by_user(
            mock_db, test_user.id, skip=10, limit=2
        )
        assert scenarios3 == []

    # ------------------ SPECIAL CASES ------------------ #
    def test_unicode_and_nested_json(self, mock_db: Mock, test_user: User) -> None:
        setup_mock_db_add_with_id(mock_db, id_value=1)

        s = scenario_crud.create(
            mock_db,
            ScenarioCreate(
                name="⚡Special ñame",
                content={"level": {"num": 42}},
                description="desc",
                user_id=test_user.id,
            ),
        )
        assert s.name == "⚡Special ñame"
        assert s.content["level"]["num"] == 42
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()
