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

import time
import math
from typing import Dict
from fastapi import (
    APIRouter,
    Body,
    HTTPException,
    WebSocket,
    Depends,
    Query,
    Request,
    status,
)
from back.api.v1.utils import (
    cleanup_simulation,
    get_simulation_or_error,
    start_or_resume_simulation,
)
from back.api.v1.utils.sim_websocket_helpers import (
    accept_websocket_connection,
    attach_ws_subscriber,
    run_message_loop,
    verify_simulation_access,
)
from back.models.scenario import Scenario
from back.schemas import (
    DriverTaskAssignRequest,
    DriverTaskUnassignRequest,
    DriverTaskReassignRequest,
    DriverTaskReorderRequest,
    DriverTaskAssignResponse,
    DriverTaskUnassignResponse,
    DriverTaskReassignResponse,
    DriverTaskReorderResponse,
    DriverTaskBatchAssignRequest,
    DriverTaskBatchAssignResponse,
)
from back.schemas.sim_keyframe import (
    SimKeyframeListResponse,
    SimKeyframeResponse,
)
from back.schemas.sim_state import (
    SimStateResponse,
)
from back.schemas.task_list import (
    TaskListResponse,
    TaskItem,
    TaskStation,
)
from back.schemas.driver_list import (
    DriverListResponse,
    DriverItem,
)
from back.schemas.sim_frame import (
    SeekResponse,
)
from sqlalchemy.orm import Session

from back.auth.dependency import get_user_id, get_user_id_over_websocket
from back.exceptions import VelosimPermissionError, ItemNotFoundError
from back.services.driver_service import driver_service
from back.crud.sim_keyframe import sim_keyframe_crud
from back.crud.sim_instance import sim_instance_crud
from back.crud.user import user_crud
from back.schemas import PlaybackSpeedBase, PlaybackSpeedResponse
from back.schemas.sim_instance import (
    SimInstanceResponse,
    SimulationListResponse,
    SimulationResponse,
    BranchRequest,
    BranchResponse,
)
from back.services import simulation_service
from back.database.session import get_db
from back.core.config import settings
from sim.utils.json_parser_strategy import JsonParseStrategy, ScenarioParseError
from sim.entities.task_state import State
from sim.entities.driver import DriverState
from back.schemas.driver_list import DriverTask, DriverVehicle
from pydantic import BaseModel
from typing import Any

# Constants
MAX_PAGE_SIZE = 500

# Allowed sortable fields for task and driver endpoints
ALLOWED_TASK_SORT_FIELDS = {
    "id",
    "state",
    "priority",
    "station_id",
    "driver_id",
    "task_type",
    "created_at",
}
ALLOWED_DRIVER_SORT_FIELDS = {
    "id",
    "state",
    "vehicle_id",
    "current_task",
    "battery_level",
}

# Valid state constants based on simulation entity enums
# Task states for API filtering (excludes SCHEDULED/CLOSED)
VALID_TASK_STATES = {
    str(s).upper() for s in State if s not in [State.SCHEDULED, State.CLOSED]
}

# Driver states for API filtering (excludes shift transitions)
VALID_DRIVER_STATES = {
    state.name
    for state in DriverState
    if state
    not in [DriverState.OFF_SHIFT, DriverState.PENDING_SHIFT, DriverState.ENDING_SHIFT]
}

router = APIRouter(prefix="/simulation", tags=["simulation"])


class InitializeRequest(BaseModel):
    """Request schema for initializing simulation with scenario content."""

    content: Dict[str, Any]
    name: str | None = None


@router.post("/initialize", response_model=SimulationResponse)
def initialize_simulation(
    request: Request,
    initialize_request: InitializeRequest | None = Body(None),
    scenario_id: int | None = Query(None),
    db: Session = Depends(get_db),
    requesting_user: int = Depends(get_user_id),
) -> SimulationResponse:
    """Initialize a new simulation and return a confirmation response.

    Args:
        initialize_request: Request containing scenario content
            (mutually exclusive with scenario_id)
        scenario_id: ID of scenario to load from database
            (mutually exclusive with initialize_request)
        db: Database session dependency
        requesting_user: ID of the authenticated user

    Returns:
        SimulationResponse containing the initialized simulation details
    """
    start_time = time.perf_counter()  # Start timer for total startup metric
    if (initialize_request is None and scenario_id is None) or (
        initialize_request is not None and scenario_id is not None
    ):
        raise HTTPException(
            status_code=400,
            detail="Must provide 'scenario content' or 'scenario_id', but not both.",
        )

    try:
        # if a scenario_id was provided then load the scenario the from the DB
        scenario = None
        json_string = None

        sim_name: str | None = None

        if initialize_request is not None:
            scenario = initialize_request.content
            sim_name = initialize_request.name
            # Extract raw JSON string for line number tracking
            # Re-format the content with indentation to match user's editor view
            try:
                import json

                json_string = json.dumps(scenario, indent=2)
            except Exception:
                json_string = None
        else:
            db_scenario = db.query(Scenario).filter(Scenario.id == scenario_id).first()
            scenario = db_scenario.content  # type: ignore[union-attr]
            # Use the scenario's name as the default sim name when not provided
            sim_name = db_scenario.name  # type: ignore[union-attr]

        # Parse scenario into InputParameter with line tracking
        json_parser = JsonParseStrategy(scenario_json=scenario, json_string=json_string)
        scenario_params = json_parser.parse()

        # Initialize simulation
        result = simulation_service.initialize_simulation(
            db,
            requesting_user,
            scenario_params,
            scenario_payload=scenario,
            name=sim_name,
        )

        # Store the start time for the total startup metric
        sim_id = result.sim_id
        if sim_id in simulation_service.active_simulations:
            simulation_service.active_simulations[sim_id][
                "initialization_start_time"
            ] = start_time
        return result

    except ScenarioParseError as err:
        # Return structured validation errors instead of concatenated string
        raise HTTPException(
            status_code=400,
            detail={
                "valid": False,
                "errors": err.errors,
                "message": "Scenario validation failed",
            },
        )
    except VelosimPermissionError:
        raise
    except ItemNotFoundError as ve:
        raise HTTPException(
            status_code=404 if "not found" in str(ve) else 400, detail=str(ve)
        )
    except Exception as err:
        raise HTTPException(status_code=500, detail=str(err))


@router.post("/stop/{sim_id}", response_model=SimulationResponse)
def stop_simulation(
    sim_id: str,
    db: Session = Depends(get_db),
    requesting_user: int = Depends(get_user_id),
) -> SimulationResponse:
    """Stop a specific simulation.

    Args:
        sim_id: ID of the simulation to stop
        db: Database session dependency
        requesting_user: ID of the authenticated user

    Returns:
        SimulationResponse with stopped status
    """
    try:
        simulation_service.stop_simulation(db, sim_id, requesting_user)
        return SimulationResponse(sim_id=sim_id, db_id=-1, status="stopped")
    except (VelosimPermissionError, ItemNotFoundError):
        raise
    except Exception as err:
        raise HTTPException(status_code=500, detail=str(err))


@router.get("/my", response_model=SimulationListResponse)
def list_my_simulations(
    skip: int = Query(0, ge=0, description="Number of simulations to skip"),
    limit: int = Query(
        10, ge=1, le=100, description="Number of simulations to retrieve"
    ),
    db: Session = Depends(get_db),
    requesting_user: int = Depends(get_user_id),
) -> SimulationListResponse:
    """List active simulations owned by the requesting user with pagination.

    Args:
        skip: Number of simulations to skip for pagination
        limit: Number of simulations to retrieve (1-100)
        db: Database session dependency
        requesting_user: ID of the authenticated user

    Returns:
        SimulationListResponse containing paginated list of user's simulations
    """
    sims, total = simulation_service.get_all_user_simulations(
        db, requesting_user, skip, limit
    )

    total_pages = math.ceil(total / limit) if total > 0 else 0
    page = (skip // limit) + 1

    return SimulationListResponse(
        simulations=[SimInstanceResponse.model_validate(sim) for sim in sims],
        total=total,
        page=page,
        per_page=limit,
        total_pages=total_pages,
    )


@router.get("/list", response_model=SimulationListResponse)
def list_all_simulations(
    skip: int = Query(0, ge=0, description="Number of simulations to skip"),
    limit: int = Query(
        10, ge=1, le=100, description="Number of simulations to retrieve"
    ),
    db: Session = Depends(get_db),
    requesting_user: int = Depends(get_user_id),
) -> SimulationListResponse:
    """List all active simulations globally (admin-only) with pagination.

    Args:
        skip: Number of simulations to skip for pagination
        limit: Number of simulations to retrieve (1-100)
        db: Database session dependency
        requesting_user: ID of the authenticated user (must be admin)

    Returns:
        SimulationListResponse containing paginated list of all active simulations
    """
    sims, total = simulation_service.get_all_active_simulations(
        db, requesting_user, skip, limit
    )

    total_pages = math.ceil(total / limit) if total > 0 else 0
    page = (skip // limit) + 1

    return SimulationListResponse(
        simulations=[SimInstanceResponse.model_validate(sim) for sim in sims],
        total=total,
        page=page,
        per_page=limit,
        total_pages=total_pages,
    )


@router.get("/status/{sim_id}")
def get_simulation_status(
    sim_id: str,
    db: Session = Depends(get_db),
    requesting_user: int = Depends(get_user_id),
) -> Dict[str, str]:
    """Get the status of a specific simulation.

    Args:
        sim_id: ID of the simulation to check
        db: Database session dependency
        requesting_user: ID of the authenticated user

    Returns:
        Dictionary containing sim_id and status
    """
    try:
        status = simulation_service.get_simulation_status(db, sim_id, requesting_user)
        return {"sim_id": sim_id, "status": status}
    except (ItemNotFoundError, VelosimPermissionError):
        raise
    except Exception as err:
        raise HTTPException(status_code=500, detail=str(err))


@router.post("/stopAll")
def stop_all_simulations(
    db: Session = Depends(get_db),
    requesting_user: int = Depends(get_user_id),
) -> Dict[str, str]:
    """
    Stop all running simulations.

    This is an admin-only operation that stops all simulations and cleans up
    database records.

    Args:
        db: Database session dependency
        requesting_user: ID of the authenticated user (must be admin)

    Returns:
        Dictionary with success message
    """
    try:
        simulation_service.stop_all_simulations(db, requesting_user)
        return {"message": "All simulations stopped"}
    except VelosimPermissionError:
        raise
    except Exception as err:
        raise HTTPException(
            status_code=500, detail=f"Failed to stop all simulations: {str(err)}"
        )


@router.get("/{sim_id}/playbackSpeed", response_model=PlaybackSpeedResponse)
def get_playback_speed(
    sim_id: str,
    db: Session = Depends(get_db),
    requesting_user: int = Depends(get_user_id),
) -> PlaybackSpeedResponse:
    """Get the playback status and playback speed of an in-memory simulation.

    Args:
        sim_id: ID of the simulation to query
        db: Database session dependency
        requesting_user: ID of the authenticated user

    Returns:
        PlaybackSpeedResponse containing current playback speed and status
    """
    try:
        result = simulation_service.get_playback_speed(
            db=db, sim_id=sim_id, requesting_user=requesting_user
        )
        return result
    except (ItemNotFoundError, VelosimPermissionError):
        raise
    except Exception as err:
        raise HTTPException(status_code=500, detail=str(err))


@router.post("/{sim_id}/playbackSpeed", response_model=PlaybackSpeedResponse)
def set_playback_speed(
    sim_id: str,
    playback_speed: PlaybackSpeedBase,
    db: Session = Depends(get_db),
    requesting_user: int = Depends(get_user_id),
) -> PlaybackSpeedResponse:
    """Set the playback speed for a specified in-memory simulation.

    Args:
        sim_id: ID of the simulation to modify
        playback_speed: New playback speed configuration
        db: Database session dependency
        requesting_user: ID of the authenticated user

    Returns:
        PlaybackSpeedResponse with updated playback speed and status
    """
    try:
        result = simulation_service.set_playback_speed(
            db=db,
            sim_id=sim_id,
            playback_speed=playback_speed,
            requesting_user=requesting_user,
        )
        return result
    except (ItemNotFoundError, VelosimPermissionError):
        raise
    except Exception as err:
        raise HTTPException(status_code=500, detail=str(err))


@router.get("/{sim_id}/seek", response_model=SeekResponse)
def seek_to_position(
    sim_id: str,
    position: float = Query(
        ..., ge=0, description="Target simulation time in seconds to seek to"
    ),
    frame_window_seconds: float | None = Query(
        None,
        ge=0,
        description=(
            "Number of simulation seconds worth of future frames to return. "
            f"Default: {settings.SEEK_DEFAULT_FRAME_WINDOW_SECONDS}s, "
            f"Max: {settings.SEEK_MAX_FRAME_WINDOW_SECONDS}s"
        ),
    ),
    playback_speed: float | None = Query(
        None,
        ge=0,
        description=(
            "Desired playback speed to set on the simulation "
            "(e.g., 1.0 for normal, 0.5 for half speed, 0 to pause). "
            "If provided, the simulation's playback speed will be updated."
        ),
    ),
    db: Session = Depends(get_db),
    requesting_user: int = Depends(get_user_id),
) -> SeekResponse:
    """Seek to a specific position in a simulation's timeline.

    This endpoint enables both seeking to historical frames and playback of
    persisted simulations. It returns a keyframe at or before the requested
    position, along with diff frames to reach the exact position and future
    frames for smooth playback.

    Args:
        sim_id: ID of the simulation to seek in
        position: Target simulation time in seconds (>= 0)
        frame_window_seconds: Number of simulation seconds of future frames to
            return. Defaults to SEEK_DEFAULT_FRAME_WINDOW_SECONDS.
        playback_speed: Optional playback speed to set (>= 0). If provided,
            updates the simulation's playback speed.
        db: Database session dependency
        requesting_user: ID of the authenticated user

    Returns:
        SeekResponse containing:
        - position: Information about where the seek landed
        - frames: Initial frames (keyframe + diffs to reach position) and
            future frames for playback
        - state: Current simulation state including playback speed and live edge status

    Raises:
        HTTPException: 400 for invalid parameters, 403 for unauthorized access,
            404 if simulation not found, 500 for server errors
    """
    try:
        # Validate and apply frame window limit
        if frame_window_seconds is None:
            frame_window_seconds = settings.SEEK_DEFAULT_FRAME_WINDOW_SECONDS
        elif frame_window_seconds > settings.SEEK_MAX_FRAME_WINDOW_SECONDS:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"frame_window_seconds exceeds maximum allowed value of "
                    f"{settings.SEEK_MAX_FRAME_WINDOW_SECONDS} seconds"
                ),
            )

        return simulation_service.seek_to_position(
            db=db,
            sim_id=sim_id,
            position=position,
            frame_window_seconds=frame_window_seconds,
            playback_speed=playback_speed,
            requesting_user=requesting_user,
        )

    except (ItemNotFoundError, VelosimPermissionError, HTTPException):
        raise
    except Exception as err:
        raise HTTPException(status_code=500, detail=str(err))


@router.post("/{sim_id}/branch", response_model=BranchResponse)
def branch_simulation(
    sim_id: str,
    request: BranchRequest,
    db: Session = Depends(get_db),
    requesting_user: int = Depends(get_user_id),
) -> BranchResponse:
    """Branch a simulation from a specific keyframe.

    Creates a new simulation instance that starts from a keyframe of an existing
    simulation. All frames from the beginning up to and including the specified
    keyframe are copied to the new simulation. The new simulation can then be
    started independently via the WebSocket stream endpoint.

    If the provided keyframe_seq does not point to an actual keyframe (is_key=True),
    the branch will occur from the most recent prior keyframe, and the actual
    keyframe sequence number used will be returned in the response.

    Args:
        sim_id: UUID of the source simulation to branch from
        request: BranchRequest containing:
            - keyframe_seq: Sequence number to branch from (will use prior keyframe
                if not a keyframe)
            - name: Optional name for the new simulation
        db: Database session dependency
        requesting_user: ID of the authenticated user

    Returns:
        BranchResponse containing:
        - sim_id: UUID or temporary ID of the new simulation
        - db_id: Database ID of the new simulation
        - name: Name of the new simulation (if provided)
        - branched_from_sim_id: UUID of the source simulation
        - branched_from_keyframe_seq: Actual keyframe seq used for branching
        - status: "initialized" (simulation initialized but paused)

    Raises:
        HTTPException:
            - 400: If no keyframes exist in the source simulation
            - 403: If user lacks permission to access source simulation
            - 404: If source simulation not found
            - 500: For unexpected server errors

    Example:
        ```
        POST /simulation/abc-123/branch
        {
            "keyframe_seq": 240,
            "name": "Experimental branch"
        }
        ```
    """
    try:
        return simulation_service.branch_simulation(
            db=db,
            sim_id=sim_id,
            keyframe_seq=request.keyframe_seq,
            name=request.name,
            requesting_user=requesting_user,
        )
    except (VelosimPermissionError, ItemNotFoundError):
        raise
    except ValueError as err:
        # No keyframes found - return 400 client error
        raise HTTPException(status_code=400, detail=str(err))
    except Exception as err:
        raise HTTPException(status_code=500, detail=str(err))


@router.post(
    "/{sim_id}/drivers/assign",
    status_code=200,
    response_model=DriverTaskAssignResponse,
)
def assign_task_to_driver(
    sim_id: str,
    task_assign_data: DriverTaskAssignRequest,
    requesting_user: int = Depends(get_user_id),
    db: Session = Depends(get_db),
) -> DriverTaskAssignResponse:
    """Assign a task to a driver in a running simulation.

    Args:
        sim_id: ID of the simulation
        task_assign_data: Task assignment request containing driver and task IDs
        requesting_user: ID of the authenticated user
        db: Database session dependency

    Returns:
        DriverTaskAssignResponse confirming the task assignment
    """
    try:
        return driver_service.assign_task(
            db=db,
            sim_id=sim_id,
            requesting_user=requesting_user,
            task_assign_data=task_assign_data,
        )
    except RuntimeError as err:
        raise HTTPException(status_code=500, detail=str(err))


@router.post(
    "/{sim_id}/drivers/assign/batch",
    status_code=200,
    response_model=DriverTaskBatchAssignResponse,
)
def batch_assign_tasks_to_driver(
    sim_id: str,
    bulk_request: DriverTaskBatchAssignRequest,
    requesting_user: int = Depends(get_user_id),
    db: Session = Depends(get_db),
) -> DriverTaskBatchAssignResponse:
    """
    Assign or reassign many tasks to a driver in a running simulation.

    For each task in the request:
    - If unassigned: assigns to the target driver
    - If already assigned to target driver: treats as success (no-op)
    - If assigned to a different driver: reassigns to the target driver

    Each operation is attempted independently and the response indicates
    per-item success or failure. No rollback is performed.

    Args:
        sim_id: ID of the simulation
        bulk_request: Batch request containing `driver_id` and `task_ids`
        requesting_user: ID of the authenticated user
        db: Database session dependency

    Returns:
        DriverTaskBatchAssignResponse: Per-item assignment results.

    Raises:
        HTTPException: 400 for duplicate task_ids, 403/404/500 for other errors
    """
    try:
        result = driver_service.batch_assign(
            db=db,
            sim_id=sim_id,
            requesting_user=requesting_user,
            batch_request=bulk_request,
        )
        return result
    except RuntimeError as err:
        raise HTTPException(status_code=500, detail=str(err))


@router.post(
    "/{sim_id}/drivers/unassign",
    status_code=200,
    response_model=DriverTaskUnassignResponse,
)
def unassign_task_from_driver(
    sim_id: str,
    task_unassign_data: DriverTaskUnassignRequest,
    requesting_user: int = Depends(get_user_id),
    db: Session = Depends(get_db),
) -> DriverTaskUnassignResponse:
    """Unassign a task from a driver in a running simulation.

    Args:
        sim_id: ID of the simulation
        task_unassign_data: Task unassignment request containing driver and task IDs
        requesting_user: ID of the authenticated user
        db: Database session dependency

    Returns:
        DriverTaskUnassignResponse confirming the task unassignment
    """
    try:
        return driver_service.unassign_task(
            db=db,
            sim_id=sim_id,
            requesting_user=requesting_user,
            task_unassign_data=task_unassign_data,
        )
    except RuntimeError as err:
        raise HTTPException(status_code=500, detail=str(err))


@router.post(
    "/{sim_id}/drivers/reassign",
    status_code=200,
    response_model=DriverTaskReassignResponse,
)
def reassign_task_between_drivers(
    sim_id: str,
    task_reassign_data: DriverTaskReassignRequest,
    requesting_user: int = Depends(get_user_id),
    db: Session = Depends(get_db),
) -> DriverTaskReassignResponse:
    """Reassign a task from one driver to another in a running simulation.

    Args:
        sim_id: ID of the simulation
        task_reassign_data: Task reassignment request with source, target
            drivers and task ID
        requesting_user: ID of the authenticated user
        db: Database session dependency

    Returns:
        DriverTaskReassignResponse confirming the task reassignment
    """
    try:
        return driver_service.reassign_task(
            db=db,
            sim_id=sim_id,
            requesting_user=requesting_user,
            task_reassign_data=task_reassign_data,
        )
    except RuntimeError as err:
        raise HTTPException(status_code=500, detail=str(err))


@router.post(
    "/{sim_id}/drivers/reorder-tasks",
    status_code=200,
    response_model=DriverTaskReorderResponse,
)
def reorder_driver_tasks(
    sim_id: str,
    reorder_data: DriverTaskReorderRequest,
    requesting_user: int = Depends(get_user_id),
    db: Session = Depends(get_db),
) -> DriverTaskReorderResponse:
    """Reorder tasks in a driver's task list within a running simulation.

    Args:
        sim_id: ID of the simulation
        reorder_data: Task reorder request containing driver ID and new task order
        requesting_user: ID of the authenticated user
        db: Database session dependency

    Returns:
        DriverTaskReorderResponse confirming the task reordering
    """
    try:
        return driver_service.reorder_tasks(
            db=db,
            sim_id=sim_id,
            requesting_user=requesting_user,
            reorder_data=reorder_data,
        )
    except RuntimeError as err:
        raise HTTPException(status_code=500, detail=str(err))


@router.websocket("/stream/{sim_id}")
async def websocket_simulation_stream(
    websocket: WebSocket,
    sim_id: str,
    requesting_user: int = Depends(get_user_id_over_websocket),
    db: Session = Depends(get_db),
) -> None:
    """
    WebSocket endpoint for starting an initialized sim instance and
    receiving real-time simulation frames.

    The frontend connects to this endpoint to receive frame updates
    from the running simulation via the FrameEmitter.

    Args:
        websocket: WebSocket connection
        sim_id: ID of the simulation to stream
        requesting_user: ID of the authenticated user
        db: Database session dependency

    Returns:
        None (streams data through websocket until connection closes)
    """
    # Accept WebSocket connection
    if not await accept_websocket_connection(websocket):
        return

    # Verify the client/user has access to this simulation
    if not await verify_simulation_access(websocket, db, sim_id, requesting_user):
        return

    # Retrieve simulation data and info
    result = await get_simulation_or_error(sim_id, websocket)
    if result is None:
        return
    sim_data, sim_info = result

    # Attach subscriber and start/resume simulation
    subscriber = await attach_ws_subscriber(sim_id, sim_data, sim_info, websocket)
    await start_or_resume_simulation(sim_info, sim_id, websocket, requesting_user)

    # Run message loop until disconnect
    try:
        await run_message_loop(websocket)
    finally:
        # Clean up the in-memory simulation's resources
        await cleanup_simulation(sim_id, sim_data, sim_info, subscriber, websocket)


@router.get("/{sim_id}/keyframes", response_model=SimKeyframeListResponse)
def get_simulation_keyframes(
    sim_id: str,
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    per_page: int = Query(20, ge=1, le=100, description="Items per page"),
    db: Session = Depends(get_db),
    requesting_user: int = Depends(get_user_id),
) -> SimKeyframeListResponse:
    """Get all keyframes for a simulation with pagination.

    Only the simulation owner or admins can retrieve keyframes.

    Args:
        sim_id: ID of the simulation instance (UUID string).
        page: Page number (1-indexed).
        per_page: Number of items per page.
        db: Database session.
        requesting_user: ID of the authenticated user.

    Returns:
        SimKeyframeListResponse with paginated keyframes.

    Raises:
        HTTPException: 404 if simulation not found, 403 if unauthorized.
    """
    try:
        # Get simulation data to retrieve db_id
        # First try active simulations (fast path)
        if sim_id in simulation_service.active_simulations:
            sim_data = simulation_service.active_simulations[sim_id]
            db_id: int = sim_data["db_id"]
        else:
            # Fallback to database for historical simulations
            sim_instance = sim_instance_crud.get_by_uuid(db, sim_id)
            if not sim_instance:
                raise ItemNotFoundError("Simulation not found")
            db_id = sim_instance.id

        # Verify simulation exists and get ownership (for active sims or re-fetch)
        sim_instance = sim_instance_crud.get(db, db_id)
        if not sim_instance:
            raise ItemNotFoundError("Simulation instance not found")

        # Check authorization
        user = user_crud.get(db, requesting_user)
        if not user:
            raise ItemNotFoundError("User not found")

        if sim_instance.user_id != user.id and not user.is_admin:
            raise VelosimPermissionError(
                "Unauthorized to access this simulation's keyframes"
            )

        # Get keyframes with pagination using the db_id
        skip = (page - 1) * per_page
        keyframes, total = sim_keyframe_crud.get_by_sim_instance(
            db, db_id, skip=skip, limit=per_page
        )

        # Calculate total pages
        total_pages = math.ceil(total / per_page) if total > 0 else 0

        return SimKeyframeListResponse(
            keyframes=[SimKeyframeResponse.model_validate(kf) for kf in keyframes],
            total=total,
            page=page,
            per_page=per_page,
            total_pages=total_pages,
        )

    except (ItemNotFoundError, VelosimPermissionError):
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving keyframes: {str(e)}",
        )


@router.get("/{sim_id}/keyframes/{sim_seconds}", response_model=SimKeyframeResponse)
def get_simulation_keyframe_at_time(
    sim_id: str,
    sim_seconds: float,
    db: Session = Depends(get_db),
    requesting_user: int = Depends(get_user_id),
) -> SimKeyframeResponse:
    """Get the keyframe at or before the specified simulation time.

    Returns the most recent keyframe at or before the given time. Only returns
    frames that occurred earlier (not later) than the requested time.

    Args:
        sim_id: ID of the simulation instance (UUID string).
        sim_seconds: Target simulation time in seconds.
        db: Database session.
        requesting_user: ID of the authenticated user.

    Returns:
        SimKeyframeResponse with id, sim_seconds_elapsed, and frame_data.

    Raises:
        HTTPException: 404 if simulation or keyframe not found, 403 if unauthorized,
                      422 if sim_seconds is negative.
    """
    # Validate sim_seconds is non-negative
    if sim_seconds < 0:
        raise HTTPException(
            status_code=422,
            detail="sim_seconds must be non-negative",
        )

    try:
        # Get simulation data to retrieve db_id
        # First try active simulations (fast path)
        if sim_id in simulation_service.active_simulations:
            sim_data = simulation_service.active_simulations[sim_id]
            db_id: int = sim_data["db_id"]
        else:
            # Fallback to database for historical simulations
            sim_instance = sim_instance_crud.get_by_uuid(db, sim_id)
            if not sim_instance:
                raise ItemNotFoundError("Simulation not found")
            db_id = sim_instance.id

        # Verify simulation exists and get ownership (for active sims or re-fetch)
        sim_instance = sim_instance_crud.get(db, db_id)
        if not sim_instance:
            raise ItemNotFoundError("Simulation instance not found")

        # Check authorization
        user = user_crud.get(db, requesting_user)
        if not user:
            raise ItemNotFoundError("User not found")

        if sim_instance.user_id != user.id and not user.is_admin:
            raise VelosimPermissionError(
                "Unauthorized to access this simulation's keyframes"
            )

        # Get keyframe at or before specified time (not after) using the db_id
        keyframe = sim_keyframe_crud.get_by_sim_time(db, db_id, sim_seconds)

        if keyframe is None:
            raise ItemNotFoundError(
                f"No keyframe found at or before {sim_seconds} seconds"
            )

        return SimKeyframeResponse.model_validate(keyframe)

    except (ItemNotFoundError, VelosimPermissionError):
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving keyframe: {str(e)}",
        )


@router.get(
    "/{sim_id}/state", response_model=SimStateResponse, response_model_exclude_none=True
)
def get_simulation_state(
    sim_id: str,
    db: Session = Depends(get_db),
    requesting_user: int = Depends(get_user_id),
) -> SimStateResponse:
    """Get the current simulation state.

    Convenience endpoint that returns the latest simulation state.

    Args:
        sim_id: ID of the simulation instance (UUID string).
        db: Database session.
        requesting_user: ID of the authenticated user.

    Returns:
        SimStateResponse with sim_id, sim_seconds, clock, and all entities.

    Raises:
        HTTPException: 404 if simulation or keyframe not found,
                      403 if unauthorized.
    """
    try:
        # Get simulation data to retrieve db_id
        # First try active simulations (fast path)
        if sim_id in simulation_service.active_simulations:
            sim_data = simulation_service.active_simulations[sim_id]
            db_id: int = sim_data["db_id"]
            # Verify simulation exists and get ownership
            sim_instance = sim_instance_crud.get(db, db_id)
        else:
            # Fallback to database for historical simulations
            sim_instance = sim_instance_crud.get_by_uuid(db, sim_id)
            if not sim_instance:
                raise ItemNotFoundError("Simulation not found")
            db_id = sim_instance.id
        if not sim_instance:
            raise ItemNotFoundError("Simulation instance not found")

        # Check authorization
        user = user_crud.get(db, requesting_user)
        if not user:
            raise ItemNotFoundError("User not found")

        if sim_instance.user_id != user.id and not user.is_admin:
            raise VelosimPermissionError(
                "Unauthorized to access this simulation's state"
            )

        # Get the latest keyframe (most recent by sim_seconds_elapsed)
        # Raises ItemNotFoundError if no keyframe exists
        latest_keyframe = sim_keyframe_crud.get_last_keyframe(db, db_id)

        # Build response
        frame_data = latest_keyframe.frame_data
        response_data = {
            "sim_id": frame_data.get("simId", sim_id),
            "sim_seconds": latest_keyframe.sim_seconds_elapsed,
            "clock": frame_data.get("clock", {}),
            "tasks": frame_data.get("tasks"),
            "drivers": frame_data.get("drivers"),
            "stations": frame_data.get("stations"),
            "vehicles": frame_data.get("vehicles"),
            "headquarters": frame_data.get("headquarters"),
        }

        return SimStateResponse(**response_data)

    except (ItemNotFoundError, VelosimPermissionError):
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving simulation state: {str(e)}",
        )


@router.get("/{sim_id}/tasks", response_model=TaskListResponse)
def get_simulation_tasks(
    sim_id: str,
    max_results: int = Query(
        default=MAX_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE, alias="maxResults"
    ),
    start_result: int = Query(default=0, ge=0, alias="startResult"),
    state: str = Query(default=None),
    station: int = Query(default=None),
    driver: int = Query(default=None),
    order: str = Query(default="id ASC"),
    db: Session = Depends(get_db),
    requesting_user: int = Depends(get_user_id),
) -> TaskListResponse:
    """Get paginated list of tasks for a simulation.

    ProgressionLIVE-compatible endpoint for listing tasks with filtering,
    sorting, and pagination.

    Args:
        sim_id: ID of the simulation instance (UUID string).
        max_results: Maximum results per page (1-500, default 500).
        start_result: Pagination offset (default 0).
        state: Filter by task state(s), comma-separated
               (OPEN, ASSIGNED, IN_PROGRESS, COMPLETED).
        station: Filter by station ID.
        driver: Filter by assigned driver ID.
        order: Sort order (e.g., "id ASC", "priority DESC").
        db: Database session.
        requesting_user: ID of the authenticated user.

    Returns:
        TaskListResponse with filtered tasks and pagination info.

    Raises:
        HTTPException: 404 if simulation not found, 403 if unauthorized.
    """
    try:
        # Get simulation and check authorization
        if sim_id in simulation_service.active_simulations:
            sim_data = simulation_service.active_simulations[sim_id]
            db_id: int = sim_data["db_id"]
        else:
            sim_instance = sim_instance_crud.get_by_uuid(db, sim_id)
            if not sim_instance:
                raise ItemNotFoundError("Simulation not found")
            db_id = sim_instance.id

        sim_instance = sim_instance_crud.get(db, db_id)
        if not sim_instance:
            raise ItemNotFoundError("Simulation instance not found")

        user = user_crud.get(db, requesting_user)
        if not user:
            raise ItemNotFoundError("User not found")

        if sim_instance.user_id != user.id and not user.is_admin:
            raise VelosimPermissionError(
                "Unauthorized to access this simulation's tasks"
            )

        # Get latest keyframe
        latest_keyframe = sim_keyframe_crud.get_last_keyframe(db, db_id)
        frame_data = latest_keyframe.frame_data

        # Extract tasks from frame data
        tasks_data = frame_data.get("tasks", [])
        stations_data = {s.get("id"): s for s in frame_data.get("stations", [])}

        # Apply filtering BEFORE building full objects to reduce overhead
        if state:
            states = [s.strip().upper() for s in state.split(",")]
            # Validate states against allowed values
            invalid_states = set(states) - VALID_TASK_STATES
            if invalid_states:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid task states: {', '.join(invalid_states)}. "
                    f"Valid states: {', '.join(sorted(VALID_TASK_STATES))}",
                )
            tasks_data = [
                t for t in tasks_data if t.get("state", "OPEN").upper() in states
            ]

        if station is not None:
            tasks_data = [t for t in tasks_data if t.get("stationId") == station]

        if driver is not None:
            tasks_data = [t for t in tasks_data if t.get("driverId") == driver]

        # Build task items from filtered data
        task_items = []
        for task in tasks_data:
            station_id = task.get("stationId")
            station_info = stations_data.get(station_id)

            task_item = TaskItem(
                id=task.get("id"),
                state=task.get("state", "OPEN"),
                station_id=station_id,
                driver_id=task.get("driverId"),
                task_type=task.get("taskType", "PICKUP"),
                priority=task.get("priority", 0),
                created_at=task.get("createdAt"),
                station=(
                    TaskStation(
                        id=station_info.get("id"),
                        name=station_info.get("name", f"Station {station_id}"),
                        position=station_info.get("position", [0.0, 0.0]),
                    )
                    if station_info
                    else None
                ),
            )
            task_items.append(task_item)

        # Apply sorting
        if order:
            sort_parts = order.split()
            if len(sort_parts) >= 2:
                field_name = sort_parts[0]
                direction = sort_parts[1].upper()
                reverse = direction == "DESC"

                # Validate sort field
                if field_name not in ALLOWED_TASK_SORT_FIELDS:
                    allowed = ", ".join(sorted(ALLOWED_TASK_SORT_FIELDS))
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Invalid sort field '{field_name}'. "
                        f"Allowed fields: {allowed}",
                    )

                # Sort by field - handle None values properly
                task_items.sort(
                    key=lambda x: (
                        getattr(x, field_name) is None,
                        getattr(x, field_name) or 0,
                    ),
                    reverse=reverse,
                )

        # Calculate pagination
        total = len(task_items)

        # Validate pagination parameters
        if start_result >= total and total > 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"start_result {start_result} exceeds total results {total}",
            )

        total_pages = math.ceil(total / max_results) if max_results > 0 else 0
        page = (start_result // max_results) + 1 if max_results > 0 else 1

        # Apply pagination
        end_result = start_result + max_results
        paginated_tasks = task_items[start_result:end_result]

        return TaskListResponse(
            tasks=paginated_tasks,
            total=total,
            page=page,
            per_page=max_results,
            total_pages=total_pages,
        )

    except (ItemNotFoundError, VelosimPermissionError, HTTPException):
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving tasks: {str(e)}",
        )


@router.get("/{sim_id}/drivers", response_model=DriverListResponse)
def get_simulation_drivers(
    sim_id: str,
    max_results: int = Query(
        default=MAX_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE, alias="maxResults"
    ),
    start_result: int = Query(default=0, ge=0, alias="startResult"),
    state: str = Query(default=None),
    expand: str = Query(default=None),
    order: str = Query(default="id ASC"),
    db: Session = Depends(get_db),
    requesting_user: int = Depends(get_user_id),
) -> DriverListResponse:
    """Get paginated list of drivers for a simulation.

    ProgressionLIVE-compatible endpoint for listing drivers with filtering,
    expansion, sorting, and pagination.

    Args:
        sim_id: ID of the simulation instance (UUID string).
        max_results: Maximum results per page (1-500, default 500).
        start_result: Pagination offset (default 0).
        state: Filter by driver state(s), comma-separated
               (IDLE, ON_ROUTE, EXECUTING_TASK, CHARGING).
        expand: Expand related entities, comma-separated (tasks, vehicle).
        order: Sort order (e.g., "id ASC").
        db: Database session.
        requesting_user: ID of the authenticated user.

    Returns:
        DriverListResponse with filtered drivers and pagination info.

    Raises:
        HTTPException: 404 if simulation not found, 403 if unauthorized.
    """
    try:
        # Get simulation and check authorization
        if sim_id in simulation_service.active_simulations:
            sim_data = simulation_service.active_simulations[sim_id]
            db_id: int = sim_data["db_id"]
        else:
            sim_instance = sim_instance_crud.get_by_uuid(db, sim_id)
            if not sim_instance:
                raise ItemNotFoundError("Simulation not found")
            db_id = sim_instance.id

        sim_instance = sim_instance_crud.get(db, db_id)
        if not sim_instance:
            raise ItemNotFoundError("Simulation instance not found")

        user = user_crud.get(db, requesting_user)
        if not user:
            raise ItemNotFoundError("User not found")

        if sim_instance.user_id != user.id and not user.is_admin:
            raise VelosimPermissionError(
                "Unauthorized to access this simulation's drivers"
            )

        # Get latest keyframe
        latest_keyframe = sim_keyframe_crud.get_last_keyframe(db, db_id)
        frame_data = latest_keyframe.frame_data

        # Extract drivers, tasks, and vehicles from frame data
        drivers_data = frame_data.get("drivers", [])
        tasks_data = {t.get("id"): t for t in frame_data.get("tasks", [])}
        vehicles_data = {v.get("id"): v for v in frame_data.get("vehicles", [])}

        # Parse expand parameter
        expand_set = set()
        if expand:
            expand_set = {e.strip() for e in expand.split(",")}

        # Apply filtering BEFORE building full objects to reduce overhead
        if state:
            states = [s.strip().upper() for s in state.split(",")]
            # Validate states against allowed values
            invalid_states = set(states) - VALID_DRIVER_STATES
            if invalid_states:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid driver states: {', '.join(invalid_states)}. "
                    f"Valid states: {', '.join(sorted(VALID_DRIVER_STATES))}",
                )
            drivers_data = [
                d for d in drivers_data if d.get("state", "IDLE").upper() in states
            ]

        # Build driver items from filtered data
        driver_items = []
        for driver in drivers_data:
            # Get driver's task IDs
            driver_tasks = driver.get("tasks", [])
            current_task = driver.get("currentTask")

            # Expand tasks if requested
            if "tasks" in expand_set:
                tasks_expanded = []
                for task_id in driver_tasks:
                    task_info = tasks_data.get(task_id)
                    if task_info:
                        tasks_expanded.append(
                            DriverTask(
                                id=task_info.get("id"),
                                state=task_info.get("state", "OPEN"),
                                station_id=task_info.get("stationId"),
                            )
                        )
                driver_task_list = tasks_expanded
            else:
                driver_task_list = driver_tasks

            # Expand vehicle if requested
            vehicle_expanded = None
            vehicle_id = driver.get("vehicleId")
            if "vehicle" in expand_set and vehicle_id:
                vehicle_info = vehicles_data.get(vehicle_id)
                if vehicle_info:
                    vehicle_expanded = DriverVehicle(
                        id=vehicle_info.get("id"),
                        battery_count=vehicle_info.get("batteryCount", 0),
                        battery_capacity=vehicle_info.get("batteryCapacity", 100),
                    )

            driver_item = DriverItem(
                id=driver.get("id"),
                state=driver.get("state", "IDLE"),
                position=driver.get("position", [0.0, 0.0]),
                vehicle_id=vehicle_id,
                tasks=driver_task_list,
                current_task=current_task,
                battery_level=driver.get("batteryLevel"),
                vehicle=vehicle_expanded,
            )
            driver_items.append(driver_item)

        # Apply sorting
        if order:
            sort_parts = order.split()
            if len(sort_parts) >= 2:
                field_name = sort_parts[0]
                direction = sort_parts[1].upper()
                reverse = direction == "DESC"

                # Validate sort field
                if field_name not in ALLOWED_DRIVER_SORT_FIELDS:
                    allowed = ", ".join(sorted(ALLOWED_DRIVER_SORT_FIELDS))
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Invalid sort field '{field_name}'. "
                        f"Allowed fields: {allowed}",
                    )

                # Sort by field - handle None values properly
                driver_items.sort(
                    key=lambda x: (
                        getattr(x, field_name) is None,
                        getattr(x, field_name) or 0,
                    ),
                    reverse=reverse,
                )

        # Calculate pagination
        total = len(driver_items)

        # Validate pagination parameters
        if start_result >= total and total > 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"start_result {start_result} exceeds total results {total}",
            )

        total_pages = math.ceil(total / max_results) if max_results > 0 else 0
        page = (start_result // max_results) + 1 if max_results > 0 else 1

        # Apply pagination
        end_result = start_result + max_results
        paginated_drivers = driver_items[start_result:end_result]

        return DriverListResponse(
            drivers=paginated_drivers,
            total=total,
            page=page,
            per_page=max_results,
            total_pages=total_pages,
        )

    except (ItemNotFoundError, VelosimPermissionError, HTTPException):
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving drivers: {str(e)}",
        )
