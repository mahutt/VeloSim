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
from sqlalchemy.orm import Session
from pydantic import ValidationError
from back.crud.scenario import scenario_crud
from back.crud.user import user_crud
from back.exceptions import ItemNotFoundError
from back.models import User
from back.schemas.scenario import ScenarioCreate, ScenarioUpdate
from back.models.scenario import Scenario


@pytest.fixture
def test_user(db: Session) -> User:
    user = User(
        username="test_user",
        password_hash=user_crud.hash_password("password"),
        is_admin=False,
        is_enabled=True,
    )
    db.add(user)
    db.flush()
    db.refresh(user)
    return user


@pytest.fixture
def another_user(db: Session) -> User:
    user = User(
        username="other_user",
        password_hash=user_crud.hash_password("password"),
        is_admin=False,
        is_enabled=True,
    )
    db.add(user)
    db.flush()
    db.refresh(user)
    return user


@pytest.fixture
def scenario(db: Session, test_user: User) -> Scenario:
    scenario_data = ScenarioCreate(
        name="Test Scenario",
        content={"foo": "bar"},
        description="A test scenario",
        user_id=test_user.id,
    )
    return scenario_crud.create(db, scenario_data)


class TestScenarioCRUD:

    # ------------------ CREATE ------------------ #
    def test_create_valid(self, db: Session, test_user: User) -> None:
        data = ScenarioCreate(
            name="New Scenario",
            content={"data": 123},
            description="Create test",
            user_id=test_user.id,
        )
        s = scenario_crud.create(db, data)
        assert s.id is not None
        assert s.name == "New Scenario"

    def test_create_missing_name_or_content(self, db: Session, test_user: User) -> None:
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

    def test_create_invalid_content_type(self, db: Session, test_user: User) -> None:
        with pytest.raises(ValidationError):
            ScenarioCreate(
                name="Invalid",
                content="string instead of dict",  # type: ignore
                description="desc",
                user_id=test_user.id,
            )

    # ------------------ GET ------------------ #
    def test_get_valid(self, db: Session, scenario: Scenario, test_user: User) -> None:
        fetched = scenario_crud.get(db, scenario.id, user_id=test_user.id)
        assert fetched.id == scenario.id

    def test_get_wrong_user_or_nonexistent(
        self, db: Session, scenario: Scenario, another_user: User
    ) -> None:
        with pytest.raises(ItemNotFoundError):
            scenario_crud.get(db, scenario.id, user_id=another_user.id)
        with pytest.raises(ItemNotFoundError):
            scenario_crud.get(db, 99999, user_id=another_user.id)

    def test_get_by_name_and_user(
        self, db: Session, scenario: Scenario, test_user: User, another_user: User
    ) -> None:
        """Test getting scenario by name and user."""
        # Should find the existing scenario
        found = scenario_crud.get_by_name_and_user(db, scenario.name, test_user.id)
        assert found is not None
        assert found.id == scenario.id
        assert found.name == scenario.name

        # Should not find scenario for different user
        not_found = scenario_crud.get_by_name_and_user(
            db, scenario.name, another_user.id
        )
        assert not_found is None

        # Should not find non-existent scenario name
        not_found2 = scenario_crud.get_by_name_and_user(
            db, "Non-existent Scenario", test_user.id
        )
        assert not_found2 is None

    # ------------------ UPDATE ------------------ #
    def test_update_valid(
        self, db: Session, scenario: Scenario, test_user: User
    ) -> None:
        update_data = ScenarioUpdate(
            name="Updated Scenario",
            content={"a": 1},
            description="Updated description",
        )
        updated = scenario_crud.update(db, scenario.id, test_user.id, update_data)
        assert updated.name == "Updated Scenario"

    def test_update_wrong_user_or_invalid(
        self, db: Session, scenario: Scenario, another_user: User, test_user: User
    ) -> None:
        update_data = ScenarioUpdate(
            name="Hacked", content={"a": 1}, description="desc"
        )
        with pytest.raises(ItemNotFoundError):
            scenario_crud.update(db, scenario.id, another_user.id, update_data)

        # Invalid content type triggers ValidationError
        with pytest.raises(ValidationError):
            ScenarioUpdate(
                name="Invalid",
                content="not dict",  # type: ignore
                description="desc",
            )

    # ------------------ DELETE ------------------ #
    def test_delete_valid(
        self, db: Session, scenario: Scenario, test_user: User
    ) -> None:
        scenario_crud.delete(db, scenario.id, test_user.id)
        with pytest.raises(ItemNotFoundError):
            scenario_crud.get(db, scenario.id, test_user.id)

    def test_delete_wrong_user_or_nonexistent(
        self, db: Session, scenario: Scenario, another_user: User, test_user: User
    ) -> None:
        with pytest.raises(ItemNotFoundError):
            scenario_crud.delete(db, scenario.id, another_user.id)
        with pytest.raises(ItemNotFoundError):
            scenario_crud.delete(db, 99999, test_user.id)

    # ------------------ PAGINATION ------------------ #
    def test_get_by_user_pagination(self, db: Session, test_user: User) -> None:
        for i in range(5):
            scenario_crud.create(
                db,
                ScenarioCreate(
                    name=f"Scenario {i}",
                    content={"num": i},
                    description=f"desc {i}",
                    user_id=test_user.id,
                ),
            )

        scenarios, total = scenario_crud.get_by_user(db, test_user.id, skip=0, limit=2)
        assert total >= 5
        assert len(scenarios) == 2

        scenarios2, _ = scenario_crud.get_by_user(db, test_user.id, skip=2, limit=2)
        assert len(scenarios2) == 2

        scenarios3, _ = scenario_crud.get_by_user(db, test_user.id, skip=10, limit=2)
        assert scenarios3 == []

    # ------------------ SPECIAL CASES ------------------ #
    def test_unicode_and_nested_json(self, db: Session, test_user: User) -> None:
        s = scenario_crud.create(
            db,
            ScenarioCreate(
                name="⚡Special ñame",
                content={"level": {"num": 42}},
                description="desc",
                user_id=test_user.id,
            ),
        )
        assert s.name == "⚡Special ñame"
        assert s.content["level"]["num"] == 42
