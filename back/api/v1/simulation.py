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
    safe_send_json,
    start_or_resume_simulation,
)
from back.api.v1.utils.sim_websocket_helpers import attach_ws_subscriber
from back.exceptions.websocket_auth_error import WebSocketAuthError
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
async def initialize_simulation(
    scenario: dict | None = Body(None),
    scenario_id: int | None = Query(None),
    db: Session = Depends(get_db),
    requesting_user: int = Depends(get_user_id),
) -> SimulationResponse:
    """Initialize a new simulation and return a confirmation response."""
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
        return simulation_service.initialize_simulation(
            db, requesting_user, scenario_params
        )

    except VelosimPermissionError as err:
        raise HTTPException(status_code=403, detail=str(err))
    except ItemNotFoundError as ve:
        raise HTTPException(
            status_code=404 if "not found" in str(ve) else 400, detail=str(ve)
        )
    except Exception as err:
        raise HTTPException(status_code=500, detail=str(err))


@router.post("/stop/{sim_id}", response_model=SimulationResponse)
async def stop_simulation(
    sim_id: str,
    db: Session = Depends(get_db),
    requesting_user: int = Depends(get_user_id),
) -> SimulationResponse:
    """Stop a specific simulation."""
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
async def list_my_simulations(
    skip: int = Query(0, ge=0, description="Number of simulations to skip"),
    limit: int = Query(
        10, ge=1, le=100, description="Number of simulations to retrieve"
    ),
    db: Session = Depends(get_db),
    requesting_user: int = Depends(get_user_id),
) -> SimulationListResponse:
    """List active simulations owned by the requesting user with pagination."""
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
async def list_all_simulations(
    skip: int = Query(0, ge=0, description="Number of simulations to skip"),
    limit: int = Query(
        10, ge=1, le=100, description="Number of simulations to retrieve"
    ),
    db: Session = Depends(get_db),
    requesting_user: int = Depends(get_user_id),
) -> SimulationListResponse:
    """List all active simulations globally (admin-only) with pagination."""
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
async def get_simulation_status(
    sim_id: str,
    db: Session = Depends(get_db),
    requesting_user: int = Depends(get_user_id),
) -> Dict[str, str]:
    """Get the status of a specific simulation."""
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
async def stop_all_simulations(
    db: Session = Depends(get_db),
    requesting_user: int = Depends(get_user_id),
) -> Dict[str, str]:
    """
    Stop all running simulations.

    This is an admin-only operation that stops all simulations and cleans up
    database records.
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
async def get_playback_speed(
    sim_id: str,
    db: Session = Depends(get_db),
    requesting_user: int = Depends(get_user_id),
) -> PlaybackSpeedResponse:
    """Get the playback status and playback speed of an in-memory simulation."""
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
async def set_playback_speed(
    sim_id: str,
    playback_speed: PlaybackSpeedBase,
    db: Session = Depends(get_db),
    requesting_user: int = Depends(get_user_id),
) -> PlaybackSpeedResponse:
    """Set the playback speed for a specified in-memory simulation."""
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
    """Assign a task to a resource in a running simulation."""
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
    """Unassign a task from a resource in a running simulation."""
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
    """Reassign a task from one resource to another in a running simulation."""
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
    """Reorder tasks in a resource's task list within a running simulation."""
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
    """
    try:
        await websocket.accept()
    except WebSocketAuthError as e:
        await e.websocket.close(code=e.code)
        return

    try:
        has_access = simulation_service.verify_access(db, sim_id, requesting_user)
        if not has_access:
            await websocket.send_json(
                {"type": "error", "message": "Unauthorized access to this simulation."}
            )
            await websocket.close()
            return
    except ItemNotFoundError as e:
        await websocket.send_json({"type": "error", "message": str(e)})
        await websocket.close()
        return
    except VelosimPermissionError as e:
        await websocket.send_json({"type": "error", "message": str(e)})
        await websocket.close()
        return

    result = await get_simulation_or_error(sim_id, websocket)
    if result is None:
        return
    sim_data, sim_info = result

    # Attach subscriber
    subscriber = attach_ws_subscriber(sim_id, sim_data, sim_info, websocket)

    # Start a simulation (or resume a simulation in the event of reconnection)
    await start_or_resume_simulation(sim_info, sim_id, websocket, requesting_user)

    try:
        while True:
            try:
                msg = await websocket.receive_json()
            except Exception:
                break

            if msg.get("action") != "ping":
                # send a warning for any client-side message received that is not
                # a "ping" (which is used to check the liveness of the connection)
                await safe_send_json(
                    websocket,
                    {
                        "type": "warning",
                        "event": "unknown_action",
                        "message": "Unrecognized action.",
                    },
                )
    finally:
        await cleanup_simulation(sim_id, sim_data, sim_info, subscriber, websocket)
