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
from .station import (
    PositionSchema,
    StationBase,
    StationCreate,
    StationUpdate,
    StationResponse,
    StationListResponse,
)
from .station_task import (
    StationTaskBase,
    StationTaskCreate,
    StationTaskUpdate,
    StationTaskResponse,
    StationTaskType,
    StationTaskListResponse,
)
from .resource import (
    ResourceBase,
    ResourceCreate,
    ResourceTaskIDsRequest,
    ResourceListResponse,
    ResourceResponse,
    ResourceTaskAssign,
    ResourceTaskUnassign,
    ResourceUpdate,
)
from .sim_instance import (
    SimInstanceBase,
    SimInstanceCreate,
    SimInstanceResponse,
)
from .user import (
    UserCreate,
    UserPasswordUpdate,
    UserRoleUpdate,
    UserResponse,
    UsersResponse,
)
from .frontend_log import (
    LogLevel,
    FrontendLogEntry,
    FrontendLogResponse,
)

__all__ = [
    "PositionSchema",
    "StationBase",
    "StationCreate",
    "StationUpdate",
    "StationResponse",
    "StationListResponse",
    "StationTaskBase",
    "StationTaskCreate",
    "StationTaskUpdate",
    "StationTaskResponse",
    "StationTaskType",
    "StationTaskListResponse",
    "ResourceBase",
    "ResourceCreate",
    "ResourceTaskIDsRequest",
    "ResourceListResponse",
    "ResourceResponse",
    "ResourceTaskAssign",
    "ResourceTaskUnassign",
    "ResourceUpdate",
    "SimInstanceBase",
    "SimInstanceCreate",
    "SimInstanceResponse",
    "UserCreate",
    "UserPasswordUpdate",
    "UserRoleUpdate",
    "UserResponse",
    "UsersResponse",
    "LogLevel",
    "FrontendLogEntry",
    "FrontendLogResponse",
]
