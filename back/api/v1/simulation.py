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
    ResourceTaskAssignRequest,
    ResourceTaskUnassignRequest,
    ResourceTaskReassignRequest,
    ResourceTaskReorderRequest,
    ResourceTaskAssignResponse,
    ResourceTaskUnassignResponse,
    ResourceTaskReassignResponse,
    ResourceTaskReorderResponse,
)
from sqlalchemy.orm import Session

from back.auth.dependency import get_user_id, get_user_id_over_websocket
from back.exceptions import VelosimPermissionError, ItemNotFoundError
from back.services.resource_service import resource_service
from back.schemas import PlaybackSpeedBase, PlaybackSpeedResponse
from back.schemas.sim_instance import (
    SimInstanceResponse,
    SimulationListResponse,
    SimulationResponse,
)
from back.services import simulation_service
from back.database.session import get_db
from sim.utils.json_parser_strategy import JsonParseStrategy


router = APIRouter(prefix="/simulation", tags=["simulation"])


@router.post("/initialize", response_model=SimulationResponse)
def initialize_simulation(
    scenario: dict | None = Body(None),
    scenario_id: int | None = Query(None),
    db: Session = Depends(get_db),
    requesting_user: int = Depends(get_user_id),
) -> SimulationResponse:
    """Initialize a new simulation and return a confirmation response.

    Args:
        scenario: Scenario content dictionary (mutually exclusive with
            scenario_id)
        scenario_id: ID of scenario to load from database (mutually
            exclusive with scenario)
        db: Database session dependency
        requesting_user: ID of the authenticated user

    Returns:
        SimulationResponse containing the initialized simulation details
    """
    """Initialize a new simulation and return a confirmation response."""
    start_time = time.perf_counter()  # Start timer for total startup metric
    if (scenario is None and scenario_id is None) or (
        scenario is not None and scenario_id is not None
    ):
        raise HTTPException(
            status_code=400,
            detail="Must provide 'scenario' or 'scenario_id', but not both.",
        )

    try:
        # if a scenario_id was provided then load the scenario the from the DB
        if scenario is None:
            db_scenario = db.query(Scenario).filter(Scenario.id == scenario_id).first()
            scenario = db_scenario.content  # type: ignore[union-attr]

        # Parse scenario into InputParameter
        json_parser = JsonParseStrategy()
        scenario_params = json_parser.parse(scenario)

        # Initialize simulation
        result = simulation_service.initialize_simulation(
            db, requesting_user, scenario_params
        )
        # Store the start time for the total startup metric
        sim_id = result.sim_id
        if sim_id in simulation_service.active_simulations:
            simulation_service.active_simulations[sim_id][
                "initialization_start_time"
            ] = start_time
        return result

    except VelosimPermissionError as err:
        raise HTTPException(status_code=403, detail=str(err))
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
    except VelosimPermissionError as err:
        raise HTTPException(status_code=403, detail=str(err))
    except ItemNotFoundError as err:
        raise HTTPException(status_code=404, detail=str(err))
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
    try:
        sims, total = simulation_service.get_active_user_simulations(
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
    except VelosimPermissionError as err:
        raise HTTPException(status_code=403, detail=str(err))


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
    try:
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
    except VelosimPermissionError as err:
        raise HTTPException(status_code=403, detail=str(err))


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
    except ItemNotFoundError as err:
        raise HTTPException(status_code=404, detail=str(err))
    except VelosimPermissionError as err:
        raise HTTPException(status_code=403, detail=str(err))
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
    except VelosimPermissionError as err:
        raise HTTPException(status_code=403, detail=str(err))
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
    except ItemNotFoundError as err:
        raise HTTPException(status_code=404, detail=str(err))
    except VelosimPermissionError as err:
        raise HTTPException(status_code=403, detail=str(err))
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
    except ItemNotFoundError as err:
        raise HTTPException(status_code=404, detail=str(err))
    except VelosimPermissionError as err:
        raise HTTPException(status_code=403, detail=str(err))
    except Exception as err:
        raise HTTPException(status_code=500, detail=str(err))


@router.post(
    "/{sim_id}/resources/assign",
    status_code=200,
    response_model=ResourceTaskAssignResponse,
)
def assign_task_to_resource(
    sim_id: str,
    task_assign_data: ResourceTaskAssignRequest,
    requesting_user: int = Depends(get_user_id),
    db: Session = Depends(get_db),
) -> ResourceTaskAssignResponse:
    """Assign a task to a resource in a running simulation.

    Args:
        sim_id: ID of the simulation
        task_assign_data: Task assignment request containing resource and task IDs
        requesting_user: ID of the authenticated user
        db: Database session dependency

    Returns:
        ResourceTaskAssignResponse confirming the task assignment
    """
    try:
        return resource_service.assign_task(
            db=db,
            sim_id=sim_id,
            requesting_user=requesting_user,
            task_assign_data=task_assign_data,
        )
    except ItemNotFoundError as err:
        raise HTTPException(status_code=404, detail=str(err))
    except VelosimPermissionError as err:
        raise HTTPException(status_code=403, detail=str(err))
    except RuntimeError as err:
        raise HTTPException(status_code=500, detail=str(err))


@router.post(
    "/{sim_id}/resources/unassign",
    status_code=200,
    response_model=ResourceTaskUnassignResponse,
)
def unassign_task_from_resource(
    sim_id: str,
    task_unassign_data: ResourceTaskUnassignRequest,
    requesting_user: int = Depends(get_user_id),
    db: Session = Depends(get_db),
) -> ResourceTaskUnassignResponse:
    """Unassign a task from a resource in a running simulation.

    Args:
        sim_id: ID of the simulation
        task_unassign_data: Task unassignment request containing resource and task IDs
        requesting_user: ID of the authenticated user
        db: Database session dependency

    Returns:
        ResourceTaskUnassignResponse confirming the task unassignment
    """
    try:
        return resource_service.unassign_task(
            db=db,
            sim_id=sim_id,
            requesting_user=requesting_user,
            task_unassign_data=task_unassign_data,
        )
    except ItemNotFoundError as err:
        raise HTTPException(status_code=404, detail=str(err))
    except VelosimPermissionError as err:
        raise HTTPException(status_code=403, detail=str(err))
    except RuntimeError as err:
        raise HTTPException(status_code=500, detail=str(err))


@router.post(
    "/{sim_id}/resources/reassign",
    status_code=200,
    response_model=ResourceTaskReassignResponse,
)
def reassign_task_between_resources(
    sim_id: str,
    task_reassign_data: ResourceTaskReassignRequest,
    requesting_user: int = Depends(get_user_id),
    db: Session = Depends(get_db),
) -> ResourceTaskReassignResponse:
    """Reassign a task from one resource to another in a running simulation.

    Args:
        sim_id: ID of the simulation
        task_reassign_data: Task reassignment request with source, target
            resources and task ID
        requesting_user: ID of the authenticated user
        db: Database session dependency

    Returns:
        ResourceTaskReassignResponse confirming the task reassignment
    """
    try:
        return resource_service.reassign_task(
            db=db,
            sim_id=sim_id,
            requesting_user=requesting_user,
            task_reassign_data=task_reassign_data,
        )
    except ItemNotFoundError as err:
        raise HTTPException(status_code=404, detail=str(err))
    except VelosimPermissionError as err:
        raise HTTPException(status_code=403, detail=str(err))
    except RuntimeError as err:
        raise HTTPException(status_code=500, detail=str(err))


@router.post(
    "/{sim_id}/resources/reorder-tasks",
    status_code=200,
    response_model=ResourceTaskReorderResponse,
)
def reorder_resource_tasks(
    sim_id: str,
    reorder_data: ResourceTaskReorderRequest,
    requesting_user: int = Depends(get_user_id),
    db: Session = Depends(get_db),
) -> ResourceTaskReorderResponse:
    """Reorder tasks in a resource's task list within a running simulation.

    Args:
        sim_id: ID of the simulation
        reorder_data: Task reorder request containing resource ID and new task order
        requesting_user: ID of the authenticated user
        db: Database session dependency

    Returns:
        ResourceTaskReorderResponse confirming the task reordering
    """
    try:
        return resource_service.reorder_tasks(
            db=db,
            sim_id=sim_id,
            requesting_user=requesting_user,
            reorder_data=reorder_data,
        )
    except ItemNotFoundError as err:
        raise HTTPException(status_code=404, detail=str(err))
    except VelosimPermissionError as err:
        raise HTTPException(status_code=403, detail=str(err))
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
