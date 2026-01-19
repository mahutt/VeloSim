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

# Import all schemas here for easy access
from .driver import (
    DriverTaskAssignRequest,
    DriverTaskUnassignRequest,
    DriverTaskReassignRequest,
    DriverTaskReorderRequest,
    DriverTaskAssignResponse,
    DriverTaskUnassignResponse,
    DriverTaskReassignResponse,
    DriverTaskReorderResponse,
)
from .sim_instance import (
    SimInstanceBase,
    SimInstanceCreate,
    SimInstanceResponse,
    SimulationResponse,
    SimulationListResponse,
)
from .user import (
    UserCreate,
    UserPasswordUpdate,
    UserRoleUpdate,
    UserResponse,
    UsersResponse,
)
from .playback_speed import (
    PlaybackSpeedBase,
    SimulationPlaybackStatus,
    PlaybackSpeedResponse,
)
from .frontend_log import (
    LogLevel,
    FrontendLogEntry,
    FrontendLogResponse,
)

from .scenario import (
    ScenarioBase,
    ScenarioCreate,
    ScenarioUpdate,
    ScenarioResponse,
    ScenarioListResponse,
)
from .sim_frame import (
    SimFrameBase,
    SimFrameCreate,
    SimFrameResponse,
    SimFrameListResponse,
    SeekResponse,
)

__all__ = [
    "DriverTaskAssignRequest",
    "DriverTaskUnassignRequest",
    "DriverTaskReassignRequest",
    "DriverTaskReorderRequest",
    "DriverTaskAssignResponse",
    "DriverTaskUnassignResponse",
    "DriverTaskReassignResponse",
    "DriverTaskReorderResponse",
    "SimInstanceBase",
    "SimInstanceCreate",
    "SimInstanceResponse",
    "SimulationResponse",
    "SimulationListResponse",
    "UserCreate",
    "UserPasswordUpdate",
    "UserRoleUpdate",
    "UserResponse",
    "UsersResponse",
    "PlaybackSpeedBase",
    "SimulationPlaybackStatus",
    "PlaybackSpeedResponse",
    "LogLevel",
    "FrontendLogEntry",
    "FrontendLogResponse",
    "ScenarioBase",
    "ScenarioCreate",
    "ScenarioUpdate",
    "ScenarioResponse",
    "ScenarioListResponse",
    "SimFrameBase",
    "SimFrameCreate",
    "SimFrameResponse",
    "SimFrameListResponse",
    "SeekResponse",
]
