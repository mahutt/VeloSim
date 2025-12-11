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

from typing import List, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import func
from back.exceptions import BadRequestError, ItemNotFoundError
from back.models import Scenario
from back.schemas.scenario import ScenarioCreate, ScenarioUpdate


class ScenarioCRUD:
    """CRUD operations for Scenario model with user ownership and validation."""

    def create(self, db: Session, scenario_data: ScenarioCreate) -> Scenario:
        """Create a new scenario. Raises 400 if invalid data.

        Args:
            db: Database session.
            scenario_data: The data for creating a new scenario.

        Returns:
            Scenario: The newly created scenario.
        """
        if not scenario_data.name:
            raise BadRequestError("Scenario must have a name")

        if not isinstance(scenario_data.content, dict):
            raise BadRequestError("Scenario content must be a dictionary")

        db_scenario = Scenario(
            name=scenario_data.name,
            content=scenario_data.content,
            description=scenario_data.description,
            user_id=scenario_data.user_id,
        )
        db.add(db_scenario)
        db.commit()
        db.refresh(db_scenario)
        return db_scenario

    def get(self, db: Session, scenario_id: int, user_id: int) -> Scenario:
        """Get a scenario by ID only if it belongs to the user.

        Args:
            db: Database session.
            scenario_id: The ID of the scenario to retrieve.
            user_id: The ID of the user who owns the scenario.

        Returns:
            Scenario: The requested scenario.
        """
        scenario = (
            db.query(Scenario)
            .filter(Scenario.id == scenario_id, Scenario.user_id == user_id)
            .first()
        )
        if not scenario:
            raise ItemNotFoundError("Scenario not found or not owned by user")

        return scenario

    def get_by_name_and_user(
        self, db: Session, name: str, user_id: int
    ) -> Scenario | None:
        """
        Get a scenario by name for a specific user.

        Returns None if no scenario with that name exists for the user.
        Used for duplicate name checking.

        Args:
            db: Database session.
            name: The name of the scenario to find.
            user_id: The ID of the user who owns the scenario.

        Returns:
            Scenario | None: The scenario if found, None otherwise.
        """
        return (
            db.query(Scenario)
            .filter(Scenario.name == name, Scenario.user_id == user_id)
            .first()
        )

    def get_by_user(
        self, db: Session, user_id: int, skip: int = 0, limit: int = 100
    ) -> Tuple[List[Scenario], int]:
        """Get all scenarios for a user with pagination.

        Args:
            db: Database session.
            user_id: The ID of the user who owns the scenarios.
            skip: Number of records to skip (default: 0).
            limit: Maximum number of records to return (default: 100).

        Returns:
            Tuple[List[Scenario], int]: Tuple of (scenarios list, total count).
        """
        total = (
            db.query(func.count(Scenario.id))
            .filter(Scenario.user_id == user_id)
            .scalar()
            or 0
        )

        scenarios = (
            db.query(Scenario)
            .filter(Scenario.user_id == user_id)
            .order_by(Scenario.id.asc())  # deterministic pagination
            .offset(skip)
            .limit(limit)
            .all()
        )
        return scenarios, total

    def update(
        self, db: Session, scenario_id: int, user_id: int, scenario_data: ScenarioUpdate
    ) -> Scenario:
        """Update a scenario only if it belongs to the user.

        Args:
            db: Database session.
            scenario_id: The ID of the scenario to update.
            user_id: The ID of the user who owns the scenario.
            scenario_data: The updated data for the scenario.

        Returns:
            Scenario: The updated scenario.
        """
        scenario = self.get(db, scenario_id, user_id)

        update_data = scenario_data.model_dump(exclude_unset=True)
        if not update_data:
            raise BadRequestError("No valid fields to update")

        if "content" in update_data and not isinstance(update_data["content"], dict):
            raise BadRequestError("Scenario content must be a dictionary")

        for key, value in update_data.items():
            setattr(scenario, key, value)

        db.commit()
        db.refresh(scenario)
        return scenario

    def delete(self, db: Session, scenario_id: int, user_id: int) -> None:
        """Delete a scenario only if it belongs to the user.

        Args:
            db: Database session.
            scenario_id: The ID of the scenario to delete.
            user_id: The ID of the user who owns the scenario.

        Returns:
            None
        """
        scenario = self.get(db, scenario_id, user_id)
        db.delete(scenario)
        db.commit()


# Singleton instance
scenario_crud = ScenarioCRUD()
