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

from typing import Any, cast
from sqlalchemy.orm import Session

from back.crud.sim_keyframe import sim_keyframe_crud
from back.models.sim_instance import SimInstance
from back.exceptions import ItemNotFoundError


class SimulationDataService:
    """
    Service responsible for retrieving persisted simulation data
    such as scenarios and keyframes from the database.

    This service is read-only and contains no simulation logic.
    """

    def get_scenario(
        self,
        db: Session,
        sim_id: str,
    ) -> dict[str, Any]:
        """
        Retrieve the scenario payload for a simulation instance.

        Args:
            db: Active database session.
            sim_id: UUID of the simulation instance.

        Returns:
            The scenario payload as a dictionary.

        Raises:
            ItemNotFoundError: If the simulation or scenario payload does not exist.
        """
        sim_instance: SimInstance | None = (
            db.query(SimInstance).filter(SimInstance.uuid == sim_id).first()
        )

        if not sim_instance:
            raise ItemNotFoundError(f"Simulation instance {sim_id} not found")

        if not sim_instance.scenario_payload:
            raise ItemNotFoundError(
                f"No scenario payload found for simulation {sim_id}"
            )

        return cast(dict[str, Any], sim_instance.scenario_payload)

    def get_keyframes_from_tick(
        self,
        db: Session,
        sim_id: str,
        tick: float,
    ) -> dict[str, Any]:
        """
        Retrieve the keyframe data at or before a given simulation tick.

        Args:
            db: Active database session.
            sim_id: UUID of the simulation instance.
            tick: Simulation time (in seconds).

        Returns:
            The keyframe frame data as a dictionary.

        Raises:
            ItemNotFoundError: If no keyframe exists at or before the given tick.
        """
        keyframe = sim_keyframe_crud.get_keyframe_at_tick(db, sim_id, tick)

        if not keyframe:
            raise ItemNotFoundError(
                f"No keyframe found at or before tick {tick} "
                f"for simulation {sim_id}"
            )

        return cast(dict[str, Any], keyframe.frame_data)

    def get_last_persisted_keyframe(
        self,
        db: Session,
        sim_id: str,
    ) -> dict[str, Any]:
        """
        Retrieve the last persisted keyframe for a simulation.

        Args:
            db: Active database session.
            sim_id: UUID of the simulation instance.

        Returns:
            The last persisted keyframe frame data as a dictionary.

        Raises:
            ItemNotFoundError: If the simulation or keyframe does not exist.
        """
        sim_instance = db.query(SimInstance).filter(SimInstance.uuid == sim_id).first()

        if not sim_instance:
            raise ItemNotFoundError(f"Simulation instance with UUID {sim_id} not found")

        keyframe = sim_keyframe_crud.get_last_keyframe(
            db,
            sim_instance_id=sim_instance.id,
        )

        if not keyframe:
            raise ItemNotFoundError(f"No keyframe found for simulation {sim_id}")

        return cast(dict[str, Any], keyframe.frame_data)

    def get_traffic_csv_data(
        self,
        db: Session,
        sim_id: str,
    ) -> str | None:
        """
        Retrieve the persisted traffic CSV data for a simulation instance.

        Args:
            db: Active database session.
            sim_id: UUID of the simulation instance.

        Returns:
            The traffic CSV data as a string, or None if no traffic data exists.

        Raises:
            ItemNotFoundError: If the simulation instance does not exist.
        """
        sim_instance = db.query(SimInstance).filter(SimInstance.uuid == sim_id).first()

        if not sim_instance:
            raise ItemNotFoundError(f"Simulation instance {sim_id} not found")

        return sim_instance.traffic_csv_data

    def get_last_persisted_keyframe_by_id(
        self,
        db: Session,
        sim_instance_id: int,
    ) -> dict[str, Any]:
        """
        Retrieve the last persisted keyframe for a simulation instance ID.

        Args:
            db: Active database session.
            sim_instance_id: Integer ID of the simulation instance.

        Returns:
            The last persisted keyframe frame data as a dictionary.

        Raises:
            ItemNotFoundError: If no keyframe exists for the simulation instance.
        """
        keyframe = sim_keyframe_crud.get_last_keyframe(
            db,
            sim_instance_id=sim_instance_id,
        )

        if not keyframe:
            raise ItemNotFoundError(
                f"No keyframe found for simulation instance {sim_instance_id}"
            )

        return cast(dict[str, Any], keyframe.frame_data)
