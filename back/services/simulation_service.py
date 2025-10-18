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

from typing import Dict, List
from sqlalchemy.orm import Session
from sim.simulator import Simulator
from sim.entities.inputParameters import InputParameter
from back.crud.sim_instance import sim_instance_crud
from back.schemas.sim_instance import SimInstanceCreate


class SimulationService:
    """Service layer for managing simulations"""

    def __init__(self) -> None:
        self.simulator = Simulator()
        # Maps sim_id (UUID from simulator) -> (db_id, status)
        self.active_simulations: Dict[str, Dict[str, int | str]] = {}

    def start_simulation(
        self, db: Session, user_id: int, params: InputParameter | None = None
    ) -> tuple[str, int]:
        """
        Start a new simulation and return its ID.

        Args:
            db: Database session
            user_id: ID of the user starting the simulation
            params: Optional input parameters for the simulation

        Returns:
            Tuple of (sim_id, db_id) where sim_id is the UUID from the simulator
            and db_id is the database record ID
        """
        if params is None:
            params = InputParameter()

        # Create database record first
        sim_instance_data = SimInstanceCreate(user_id=user_id)
        db_sim_instance = sim_instance_crud.create(db, sim_instance_data)
        db.commit()

        # Initialize simulation with empty subscriber list
        # Subscribers will attach via WebSocket connections
        sim_id = self.simulator.initialize(params, subscribers=[])

        # Start the simulation with a default runtime of 1 hour (3600 seconds)
        self.simulator.start(sim_id, simTime=3600)

        # Track both the simulator UUID and database ID
        self.active_simulations[sim_id] = {
            "db_id": db_sim_instance.id,
            "status": "running",
        }

        return sim_id, db_sim_instance.id

    def stop_simulation(self, db: Session, sim_id: str, user_id: int) -> bool:
        """
        Stop a simulation by ID.

        Args:
            db: Database session
            sim_id: The simulator UUID
            user_id: ID of the user requesting to stop the simulation

        Returns:
            True if stopped successfully, False if not found or unauthorized
        """
        if sim_id not in self.active_simulations:
            return False

        # Check authorization - verify the user owns this simulation
        sim_data = self.active_simulations[sim_id]
        db_id: int = sim_data["db_id"]  # type: ignore[assignment]
        db_sim_instance = sim_instance_crud.get(db, db_id)

        if not db_sim_instance or db_sim_instance.user_id != user_id:
            return False

        # Stop the simulator
        self.simulator.stop(sim_id)

        # Delete the database record
        sim_instance_crud.delete(db, db_id)
        db.commit()

        # Remove from active simulations
        del self.active_simulations[sim_id]
        return True

    def get_active_simulations(self) -> List[str]:
        """Get list of active simulation IDs"""
        return list(self.active_simulations.keys())

    def get_simulation_status(self, sim_id: str) -> str:
        """Get status of a specific simulation"""
        if sim_id in self.active_simulations:
            return str(self.active_simulations[sim_id]["status"])
        return "not_found"

    def stop_all_simulations(self, db: Session) -> None:
        """
        Stop all running simulations and clean up database records.

        Args:
            db: Database session
        """
        # Stop all simulators
        self.simulator.stop_all()

        # Delete all database records
        for sim_data in self.active_simulations.values():
            db_id: int = sim_data["db_id"]  # type: ignore[assignment]
            sim_instance_crud.delete(db, db_id)

        db.commit()
        self.active_simulations.clear()

    def get_simulator(self) -> Simulator:
        """Get the underlying simulator instance for advanced operations"""
        return self.simulator


# Global simulation service instance
simulation_service = SimulationService()
