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

from dataclasses import dataclass
from sim.map.MapController import MapController
from sim.entities.inputParameters import InputParameter


@dataclass
class SimulationRuntimeState:
    """
    Active in-memory state of a simulation instance.
    """

    input_parameters: InputParameter
    map_controller: MapController
    current_time_seconds: int
    was_running: bool = True
    real_time_factor: float = 1.0
    paused_by_user: bool = False

    @property
    def should_auto_resume(self) -> bool:
        """
        Determine if simulation should auto-resume on restore.

        Auto-resumes unless the user explicitly paused the simulation.
        This respects user intent while providing good UX for disconnects.

        Returns:
            True if simulation should auto-resume, False to stay paused.
        """
        return not self.paused_by_user
