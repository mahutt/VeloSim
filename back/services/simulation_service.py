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

from typing import Any, Dict, List
from sqlalchemy.orm import Session
from back.models import User
from back.models.sim_instance import SimInstance
from back.schemas import (
    PlaybackSpeedBase,
    PlaybackSpeedResponse,
    SimulationPlaybackStatus,
)
from sim.simulator import Simulator
from sim.entities.inputParameters import InputParameter
from back.crud import sim_instance_crud, user_crud
from back.schemas.sim_instance import (
    SimInstanceCreate,
    SimulationResponse,
)
from back.exceptions import VelosimPermissionError, ItemNotFoundError


class SimulationService:
    """Service layer for managing the lifecycle and access control of simulations."""

    def __init__(self) -> None:
        # Maps sim_id (UUID from simulator) -> (db_id, status, sim_time, simulator)
        # sim_time comes from InputParameter.sim_time
        self.active_simulations: Dict[str, Dict[str, Any]] = {}
        self.simulator = Simulator()
        # Example of an entry to represent an in-memory simulation instance:
        # sim_id: {
        #     "db_id": 123,
        #     "status": "running",
        #     "sim_time": 3600,
        #     "simulator": <Simulator instance from sim package>,
        # }

    # Internal helper
    def _get_requesting_user(self, db: Session, requesting_user: int) -> User:
        """
        Attempt to fetch and validate the requesting user.

        This method retrieves the user from the database by their ID, verifying
        that the account exists and is currently enabled. It raises an
        ItemNotFoundError if the user does not exist or a VelosimPermissionError
        if the user is disabled.
        """
        user = user_crud.get(db, requesting_user)
        if not user:
            raise ItemNotFoundError("Requesting user not found.")
        if not user.is_enabled:
            raise VelosimPermissionError("Requesting user is disabled.")
        return user

    def verify_access(self, db: Session, sim_id: str, requesting_user: int) -> bool:
        """
        Return True if the requesting user has permission to access the simulation
        identified by its in-memory UUID.

        Admins always have permission, otherwise the requesting user must be the
        owner of that simulation instance.

        Args:
            db: Database session.
            sim_id: The UUID of the simulation to verify access for.
            requesting_user: The ID of the user requesting access.

        Returns:
            bool: True if user has access, False otherwise.

        Raises:
            ItemNotFoundError: if the simulation is not found, either in-memory
                or from its database record.
        """
        user = self._get_requesting_user(db, requesting_user)

        sim_data = self.active_simulations.get(sim_id)
        if not sim_data:
            raise ItemNotFoundError(f"Simulation {sim_id} is not currently active")

        db_id: int = sim_data["db_id"]
        db_sim_instance = sim_instance_crud.get(db, db_id)
        if not db_sim_instance:
            raise ItemNotFoundError(f"Simulation instance record {db_id} not found")

        return user.is_admin or db_sim_instance.user_id == user.id

    def initialize_simulation(
        self, db: Session, requesting_user: int, params: InputParameter
    ) -> SimulationResponse:
        """Initialize a new simulation with the given parameters.

        Args:
            db: Database session.
            requesting_user: The ID of the user initializing the simulation.
            params: Input parameters for the simulation.

        Returns:
            SimulationResponse: Response containing sim_id, db_id, and status.
        """
        user = self._get_requesting_user(db, requesting_user)

        # Create DB record
        sim_instance_data = SimInstanceCreate(user_id=user.id)
        db_sim_instance = sim_instance_crud.create(db, sim_instance_data)
        db.commit()

        # Create a fresh Simulator for this simulation
        sim = self.simulator

        # Initialize simulation with InputParameter
        sim_id = sim.initialize(params, subscribers=[])

        # Store the Simulator instance per sim_id
        self.active_simulations[sim_id] = {
            "db_id": db_sim_instance.id,
            "status": "initialized",
            "sim_time": params.sim_time,
            "user_id": user.id,
        }

        return SimulationResponse(
            sim_id=sim_id,
            db_id=db_sim_instance.id,
            status="initialized",
        )

    def start_simulation(
        self,
        db: Session,
        sim_id: str,
        requesting_user: int,
    ) -> SimulationResponse:
        """
        Start an initialized simulation and return a confirmation response.

        Args:
            db: Database session.
            sim_id: The UUID of the simulation to start.
            requesting_user: The ID of the user starting the simulation.

        Returns:
            SimulationResponse: Response containing sim_id, db_id, and running status.
        """
        if not self.verify_access(db, sim_id, requesting_user):
            raise VelosimPermissionError("Unauthorized to start this simulation.")

        if sim_id not in self.active_simulations:
            raise ItemNotFoundError(sim_id, "Simulation not found")

        sim_data = self.active_simulations[sim_id]
        db_id: int = sim_data["db_id"]

        db_sim_instance = sim_instance_crud.get(db, db_id)
        if db_sim_instance is None:
            raise ItemNotFoundError(db_id, "Simulation instance record not found")

        # Use the Simulator instance tied to this sim
        sim = self.simulator
        if sim is None:
            raise RuntimeError(f"Simulator for simulation {sim_id} not found")

        # Ensure the sim actually contains this sim_id
        sim_info = sim.get_sim_by_id(sim_id)
        if sim_info is None:
            raise RuntimeError(f"Simulation {sim_id} not found in its Simulator")

        sim_time_value = sim_data.get("sim_time")
        if sim_time_value is None:
            raise ValueError(
                f"Simulation {sim_id} does not have a valid sim_time defined."
            )

        sim.start(sim_id, sim_time_value)

        # Update state
        sim_data["status"] = "running"

        return SimulationResponse(
            sim_id=sim_id,
            db_id=db_sim_instance.id,
            status="running",
        )

    def stop_simulation(
        self,
        db: Session,
        sim_id: str,
        requesting_user: int,
    ) -> bool:
        """
        Stop a simulation by ID (owner or admin only).

        Args:
            db: Database session
            sim_id: The simulator UUID
            requesting_user: Requesting user's ID
        Returns:
            True if stopped successfully
        Raises:
            ItemNotFoundError if not found
            VelosimPermissionError if unauthorized
        """
        user = self._get_requesting_user(db, requesting_user)

        if sim_id not in self.active_simulations:
            raise ItemNotFoundError(sim_id, "Simulation not found")

        sim_data = self.active_simulations[sim_id]
        db_id: int = sim_data["db_id"]
        db_sim_instance = sim_instance_crud.get(db, db_id)
        if db_sim_instance is None:
            raise ItemNotFoundError(db_id, "Simulation instance record not found")

        assert db_sim_instance is not None

        # Authorization check
        if db_sim_instance.user_id != user.id and not user.is_admin:
            raise VelosimPermissionError("Unauthorized to stop this simulation.")

        # Stop simulator and delete DB record
        sim = self.simulator
        if sim is None:
            raise RuntimeError(f"Simulator for simulation {sim_id} not found")
        sim.stop(sim_id)
        sim_instance_crud.delete(db, db_id)
        db.commit()

        del self.active_simulations[sim_id]
        return True

    def get_active_user_simulations(
        self, db: Session, requesting_user: int, skip: int = 0, limit: int = 10
    ) -> tuple[List[SimInstance], int]:
        """
        Retrieve simulations owned by the requesting user with pagination.

        Args:
            db: Database session
            requesting_user: Requesting user's ID
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            Tuple of (list of SimInstance objects, total count)
        """
        user = self._get_requesting_user(db, requesting_user)

        if not self.active_simulations:
            return [], 0

        db_ids = [int(data["db_id"]) for data in self.active_simulations.values()]
        all_instances = (
            db.query(SimInstance)
            .filter(SimInstance.id.in_(db_ids), SimInstance.user_id == user.id)
            .all()
        )

        total = len(all_instances)
        paginated = all_instances[skip : skip + limit]

        return paginated, total

    def get_all_active_simulations(
        self, db: Session, requesting_user: int, skip: int = 0, limit: int = 10
    ) -> tuple[List[SimInstance], int]:
        """
        Retrieve all active simulations with pagination.
        This is an admin-only operation.

        Args:
            db: Database session
            requesting_user: Requesting user's ID
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            Tuple of (list of SimInstance objects, total count)
        """
        user = self._get_requesting_user(db, requesting_user)
        if not user.is_admin:
            raise VelosimPermissionError(
                "Admin privileges required to list all active simulations."
            )

        # Batch fetch all sim_instances in a single query
        if not self.active_simulations:
            return [], 0

        db_ids = [int(data["db_id"]) for data in self.active_simulations.values()]
        all_instances = db.query(SimInstance).filter(SimInstance.id.in_(db_ids)).all()

        total = len(all_instances)
        paginated = all_instances[skip : skip + limit]

        return paginated, total

    def get_simulation_status(
        self, db: Session, sim_id: str, requesting_user: int
    ) -> str:
        """
        Get status of a specific simulation.

        Admins can query the status of any simulation, whereas non-admin users
        can only query their own.

        Args:
            db: Database session
            sim_id: Simulator UUID
            requesting_user: Requesting user's ID

        Returns:
            string representing the simulation status
        """
        user = self._get_requesting_user(db, requesting_user)

        if sim_id not in self.active_simulations:
            raise ItemNotFoundError(sim_id, "Simulation not found")

        sim_data = self.active_simulations[sim_id]
        db_id: int = sim_data["db_id"]
        db_sim_instance = sim_instance_crud.get(db, db_id)
        if db_sim_instance is None:
            raise ItemNotFoundError(db_id, "Simulation instance record not found")

        assert db_sim_instance is not None

        if db_sim_instance.user_id != user.id and not user.is_admin:
            raise VelosimPermissionError("Unauthorized to access this simulation.")

        return str(sim_data["status"])

    def _stop_all_simulations_core(self, db: Session) -> None:
        """
        Core logic to stop all running simulations and clean up DB records. Does
        not perform any permission checks so it can be called by system code.
        """
        try:
            # Stop all simulators
            sim = self.simulator

            for sim_id in list(self.active_simulations.keys()):
                try:
                    sim.stop(sim_id)
                except Exception as exc:
                    print(f"Failed to stop simulation {sim_id}: {exc}")

            # Clean up database records in a single batch operation
            if self.active_simulations:
                db_ids = [
                    int(data["db_id"]) for data in self.active_simulations.values()
                ]
                db.query(SimInstance).filter(SimInstance.id.in_(db_ids)).delete(
                    synchronize_session=False
                )

            db.commit()
            self.active_simulations.clear()

        except Exception as exc:
            db.rollback()
            raise RuntimeError(f"Failed to stop all simulations: {exc}") from exc

    def stop_all_simulations(self, db: Session, requesting_user: int) -> None:
        """
        Stop all running simulations and clean up database records.

        This is an admin-only operation.

        Args:
            db: Database session
            requesting_user: Requesting user's ID

        Returns:
            None
        """
        user = self._get_requesting_user(db, requesting_user)
        if not user.is_admin:
            raise VelosimPermissionError("Only admins can stop all simulations.")

        self._stop_all_simulations_core(db)

    def stop_all_simulations_system(self, db: Session) -> None:
        """
        Stop all running simulations from system context (ex. during shutdown).

        No user check. Use carefully.

        Args:
            db: Database session.

        Returns:
            None
        """
        self._stop_all_simulations_core(db)

    def set_playback_speed(
        self,
        db: Session,
        sim_id: str,
        playback_speed: PlaybackSpeedBase,
        requesting_user: int,
    ) -> PlaybackSpeedResponse:
        """Set the playback speed for a simulation.

        Args:
            db: Database session.
            sim_id: The UUID of the simulation.
            playback_speed: The new playback speed settings.
            requesting_user: The ID of the user making the request.

        Returns:
            PlaybackSpeedResponse: Response containing the updated playback speed.
        """
        user = self._get_requesting_user(db, requesting_user)

        if sim_id not in self.active_simulations:
            raise ItemNotFoundError(sim_id, "Simulation not found")

        sim_data = self.active_simulations[sim_id]
        db_id: int = sim_data["db_id"]
        db_sim_instance = sim_instance_crud.get(db, db_id)
        if db_sim_instance is None:
            raise ItemNotFoundError(db_id, "Simulation instance record not found")

        if db_sim_instance.user_id != user.id and not user.is_admin:
            raise VelosimPermissionError("Unauthorized to modify this simulation.")

        sim = self.simulator
        if sim is None:
            raise RuntimeError(f"Simulator for simulation {sim_id} not found")
        sim_info = sim.get_sim_by_id(sim_id)
        if sim_info is None:
            raise RuntimeError(f"Simulation {sim_id} not found in simulator")
        driver = sim_info["simController"].realTimeDriver

        # Adjust playback based on requested speed
        speed_value = playback_speed.playback_speed

        if speed_value == 0:  # the requested value is equivalent to pausing
            driver.pause()
        else:  # handle any other valid playback speed properly
            driver.resume()
            inverted_factor = 1.0 / speed_value
            driver.set_real_time_factor(inverted_factor)

        status = (
            SimulationPlaybackStatus.RUNNING
            if driver.running
            else SimulationPlaybackStatus.PAUSED
        )

        return PlaybackSpeedResponse(
            simulation_id=sim_id, playback_speed=speed_value, status=status
        )

    def get_playback_speed(
        self,
        db: Session,
        sim_id: str,
        requesting_user: int,
    ) -> PlaybackSpeedResponse:
        """
        Return the current playback speed and runtime status for a simulation.

        Args:
            db: Database session.
            sim_id: The UUID of the simulation.
            requesting_user: The ID of the user making the request.

        Returns:
            PlaybackSpeedResponse: Response containing the current playback
                speed and status.
        """
        user = self._get_requesting_user(db, requesting_user)

        if sim_id not in self.active_simulations:
            raise ItemNotFoundError(sim_id, "Simulation not found")

        sim_data = self.active_simulations[sim_id]
        db_id: int = sim_data["db_id"]
        db_sim_instance = sim_instance_crud.get(db, db_id)
        if db_sim_instance is None:
            raise ItemNotFoundError(db_id, "Simulation instance record not found")

        if db_sim_instance.user_id != user.id and not user.is_admin:
            raise VelosimPermissionError("Unauthorized to access this simulation.")

        # Get simulator runtime information from the sim package
        sim = self.simulator
        if sim is None:
            raise RuntimeError(f"Simulator for simulation {sim_id} not found")
        sim_info = sim.get_sim_by_id(sim_id)
        # Retrieve the corresponding realTimeDriver
        driver = sim_info["simController"].realTimeDriver  # type: ignore

        # Determine status based on the boolean value of 'running' attribute
        # from realTimeDriver
        status = (
            SimulationPlaybackStatus.RUNNING
            if driver.running
            else SimulationPlaybackStatus.PAUSED
        )

        return PlaybackSpeedResponse(
            simulation_id=sim_id,
            playback_speed=float(driver.real_time_factor),
            status=status,
        )


# Global simulation service instance
simulation_service = SimulationService()
