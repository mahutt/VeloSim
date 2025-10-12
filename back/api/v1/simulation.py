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
from typing import Dict, List
from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel

from sim.entities.frame import Frame
from sim.utils.subscriber import Subscriber
from back.services.simulation_service import simulation_service

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
        except Exception as e:
            print(f"Error sending frame over WebSocket: {e}")


class SimulationResponse(BaseModel):
    """Response model for simulation operations"""

    sim_id: str
    status: str


class SimulationListResponse(BaseModel):
    """Response model for listing simulations"""

    active_simulations: List[str]


@router.post("/start", response_model=SimulationResponse)
async def start_simulation() -> SimulationResponse:
    """Start a new simulation and return its ID."""
    try:
        sim_id = simulation_service.start_simulation()
        return SimulationResponse(sim_id=sim_id, status="started")
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to start simulation: {str(e)}"
        )


@router.post("/stop/{sim_id}", response_model=SimulationResponse)
async def stop_simulation(sim_id: str) -> SimulationResponse:
    """Stop a specific simulation."""
    success = simulation_service.stop_simulation(sim_id)
    if not success:
        raise HTTPException(status_code=404, detail="Simulation not found")
    return SimulationResponse(sim_id=sim_id, status="stopped")


@router.get("/list", response_model=SimulationListResponse)
async def list_simulations() -> SimulationListResponse:
    """List all active simulations."""
    active = simulation_service.get_active_simulations()
    return SimulationListResponse(active_simulations=active)


@router.get("/status/{sim_id}")
async def get_simulation_status(sim_id: str) -> Dict[str, str]:
    """Get status of a specific simulation."""
    status = simulation_service.get_simulation_status(sim_id)
    if status == "not_found":
        raise HTTPException(status_code=404, detail="Simulation not found")
    return {"sim_id": sim_id, "status": status}


@router.post("/stop-all")
async def stop_all_simulations() -> Dict[str, str]:
    """Stop all running simulations."""
    simulation_service.stop_all_simulations()
    return {"message": "All simulations stopped"}


@router.websocket("/stream/{sim_id}")
async def websocket_simulation_stream(websocket: WebSocket, sim_id: str) -> None:
    """
    WebSocket endpoint for receiving real-time simulation frames.

    The frontend connects to this endpoint to receive frame updates
    from the running simulation via the FrameEmitter.
    """
    await websocket.accept()

    # Check if simulation exists
    status = simulation_service.get_simulation_status(sim_id)
    if status == "not_found":
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
    except Exception as e:
        print(f"WebSocket error for sim {sim_id}: {e}")
    finally:
        # Detach subscriber when connection closes
        emitter.detach(subscriber)
        print(f"Detached subscriber for sim {sim_id}")
