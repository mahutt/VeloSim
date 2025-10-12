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
from sim.simulator import Simulator
from sim.entities.inputParameters import InputParameter


class SimulationService:
    """Service layer for managing simulations"""

    def __init__(self) -> None:
        self.simulator = Simulator()
        self.active_simulations: Dict[str, str] = {}

    def start_simulation(self, params: InputParameter | None = None) -> str:
        """Start a new simulation and return its ID"""
        if params is None:
            params = InputParameter()

        # Start simulation with empty subscriber list
        # Subscribers will attach via WebSocket connections
        sim_id = self.simulator.start(params, subscribers=[])
        self.active_simulations[sim_id] = "running"
        return sim_id

    def stop_simulation(self, sim_id: str) -> bool:
        """Stop a simulation by ID"""
        if sim_id in self.active_simulations:
            self.simulator.stop(sim_id)
            del self.active_simulations[sim_id]
            return True
        return False

    def get_active_simulations(self) -> List[str]:
        """Get list of active simulation IDs"""
        return list(self.active_simulations.keys())

    def get_simulation_status(self, sim_id: str) -> str:
        """Get status of a specific simulation"""
        return self.active_simulations.get(sim_id, "not_found")

    def stop_all_simulations(self) -> None:
        """Stop all running simulations"""
        self.simulator.stop_all()
        self.active_simulations.clear()

    def get_simulator(self) -> Simulator:
        """Get the underlying simulator instance for advanced operations"""
        return self.simulator


# Global simulation service instance
simulation_service = SimulationService()
