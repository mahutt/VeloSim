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

import asyncio
import math
from typing import Dict, List
from fastapi import (
    APIRouter,
    HTTPException,
    WebSocket,
    WebSocketDisconnect,
    Depends,
    Query,
)
from pydantic import BaseModel
from sqlalchemy.orm import Session

from back.auth.dependency import get_user_id
from back.exceptions import VelosimPermissionError, ItemNotFoundError
from back.schemas import PlaybackSpeedBase, PlaybackSpeedResponse
from back.schemas.sim_instance import SimInstanceResponse
from sim.entities.frame import Frame
from sim.utils.subscriber import Subscriber
from back.services.simulation_service import simulation_service
from back.database.session import get_db

router = APIRouter(prefix="/simulation", tags=["simulation"])


class WebSocketSubscriber(Subscriber):
    """Subscriber that forwards frames to a WebSocket connection."""

    def __init__(self, websocket: WebSocket, sim_id: str):
        self.websocket = websocket
        self.sim_id = sim_id
        self._loop: asyncio.AbstractEventLoop | None = None

    def set_event_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        """Set the event loop for async operations."""
        self._loop = loop

    def on_frame(self, frame: Frame) -> None:
        """Called when a new frame is available from the simulator."""
        if self._loop is None:
            return

        # Convert frame to dictionary for JSON serialization
        frame_data = {
            "sim_id": self.sim_id,
            "seq_numb": frame.seq_number,
            "payload": frame.payload_str,
            "timestamp": frame.timestamp_ms,
        }

        # Schedule the coroutine in the event loop
        asyncio.run_coroutine_threadsafe(self._send_frame(frame_data), self._loop)

    async def _send_frame(self, frame_data: Dict) -> None:
        """Send frame data over WebSocket."""
        try:
            await self.websocket.send_json(frame_data)
        except Exception as err:
            print(f"Error sending frame over WebSocket: {err}")


class SimulationResponse(BaseModel):
    """Response model for simulation operations"""

    sim_id: str
    db_id: int
    status: str


class SimulationListResponse(BaseModel):
    """Response model for listing simulations with pagination"""

    simulations: List[SimInstanceResponse]
    total: int
    page: int
    per_page: int
    total_pages: int


@router.post("/start", response_model=SimulationResponse)
async def start_simulation(
    db: Session = Depends(get_db),
    requesting_user: int = Depends(get_user_id),
) -> SimulationResponse:
    """Start a new simulation and return its ID."""
    try:
        sim_id, db_id = simulation_service.start_simulation(db, requesting_user)
        return SimulationResponse(sim_id=sim_id, db_id=db_id, status="started")
    except VelosimPermissionError as err:
        raise HTTPException(status_code=403, detail=str(err))
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


@router.websocket("/stream/{sim_id}")
async def websocket_simulation_stream(websocket: WebSocket, sim_id: str) -> None:
    """
    WebSocket endpoint for receiving real-time simulation frames.

    The frontend connects to this endpoint to receive frame updates
    from the running simulation via the FrameEmitter.
    """
    await websocket.accept()

    # Check if simulation exists
    if sim_id not in simulation_service.active_simulations:
        await websocket.send_json({"error": "Simulation not found", "sim_id": sim_id})
        await websocket.close(code=4004, reason="Simulation not found")
        return

    # Create a subscriber for this WebSocket connection
    subscriber = WebSocketSubscriber(websocket, sim_id)
    subscriber.set_event_loop(asyncio.get_event_loop())

    # Attach subscriber to the simulation's FrameEmitter
    # Access emitter through the simulator's thread pool
    simulator = simulation_service.get_simulator()

    # The emitter is stored in the thread_pool dictionary
    with simulator.thread_pool_lock:
        if sim_id not in simulator.thread_pool:
            await websocket.send_json(
                {"error": "Simulation not found in thread pool", "sim_id": sim_id}
            )
            await websocket.close(code=4004, reason="Simulation not active")
            return

        emitter = simulator.thread_pool[sim_id]["emitter"]

    emitter.attach(subscriber)

    try:
        # Send initial connection confirmation
        await websocket.send_json(
            {
                "type": "connection_established",
                "sim_id": sim_id,
                "message": "Connected to simulation frame stream",
            }
        )

        # Keep connection alive and handle incoming messages (if any)
        while True:
            # Wait for any messages from client (e.g., ping/pong)
            data = await websocket.receive_text()

            # Handle simple ping/pong for connection health
            if data == "ping":
                await websocket.send_json({"type": "pong"})

    except WebSocketDisconnect:
        print(f"WebSocket disconnected for sim {sim_id}")
    except Exception as err:
        print(f"WebSocket error for sim {sim_id}: {err}")
    finally:
        # Detach subscriber when connection closes
        emitter.detach(subscriber)
        print(f"Detached subscriber for sim {sim_id}")
