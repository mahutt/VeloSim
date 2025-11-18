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

from typing import Optional, Tuple
from fastapi import WebSocket
from fastapi.websockets import WebSocketState
import asyncio

from back.database.session import get_db
from back.services import simulation_service
from sim.entities.frame import Frame
from sim.simulator import RunInfo
from sim.utils.subscriber import Subscriber
from back.core.config import settings


class WebSocketSubscriber(Subscriber):
    def __init__(self, websocket: WebSocket):
        self.websocket = websocket
        """WebSocket connection for he current running loop."""
        try:
            self.loop = asyncio.get_running_loop()
        except RuntimeError:
            # No running loop - will be set manually (e.g., in tests)
            self.loop = None  # type: ignore
        """Event loop used to run asynchronous tasks from synchronous callbacks."""
        self.closed = False
        """Internal flag indicating whether the WebSocket connection has been closed."""

    def set_event_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        """Set the event loop manually (primarily for testing)."""
        self.loop = loop

    def close(self) -> None:
        """Mark the subscriber as closed to prevent further frame sends."""
        self.closed = True

    def on_frame(self, frame: Frame) -> None:
        # Check if closed or websocket disconnected before scheduling
        if self.closed:
            return
        if self.websocket.client_state != WebSocketState.CONNECTED:
            return
        if self.loop is not None and not self.loop.is_closed():
            # schedule the coroutine in the main event loop
            asyncio.run_coroutine_threadsafe(self._send_frame(frame), self.loop)

    async def _send_frame(self, frame: Frame) -> None:
        # Double-check state before attempting to send
        if self.closed:
            return
        if self.websocket.client_state != WebSocketState.CONNECTED:
            self.closed = True
            return

        try:
            await self.websocket.send_json(
                {
                    "seq": frame.seq_number,
                    "timestamp": frame.timestamp_ms,
                    "is_key": frame.is_key,
                    "payload": frame.payload_dict,
                }
            )
        except RuntimeError as e:
            # Silently catch ASGI message errors when connection is already closed
            # These occur when frames are queued but WebSocket
            # closes before they're sent
            if "websocket.send" in str(e) or "websocket.close" in str(e):
                self.closed = True
            else:
                # Re-raise unexpected RuntimeErrors
                raise
        except Exception:
            # Mark as closed to prevent further send attempts
            # Silently ignore other exceptions (e.g., connection errors)
            self.closed = True


async def safe_send_json(websocket: WebSocket, payload: dict) -> None:
    """Send JSON through websocket and ignore if connection closed."""
    if websocket.client_state != WebSocketState.CONNECTED:
        # Socket already closed therefore do not attempt to send JSON
        return
    await websocket.send_json(payload)


async def get_simulation_or_error(
    sim_id: str, websocket: WebSocket
) -> Optional[Tuple[dict, RunInfo]]:
    """Fetch simulation info or send an error and close websocket."""
    sim_data = simulation_service.active_simulations.get(sim_id)
    if not sim_data:
        await safe_send_json(
            websocket,
            {
                "type": "error",
                "event": "simulation_not_found",
                "sim_id": sim_id,
                "message": f"Simulation '{sim_id}' is not active.",
            },
        )
        await websocket.close(code=4004)
        return None

    sim_info: Optional[RunInfo] = simulation_service.simulator.get_sim_by_id(sim_id)
    if not sim_info:
        await safe_send_json(
            websocket,
            {
                "type": "error",
                "event": "simulation_not_found",
                "sim_id": sim_id,
                "message": f"Simulation '{sim_id}' not found in its simulator.",
            },
        )
        return None

    return sim_data, sim_info


def attach_ws_subscriber(
    sim_id: str,
    sim_data: dict,
    sim_info: RunInfo,
    websocket: WebSocket,
) -> WebSocketSubscriber:
    """
    Attach a new WebSocketSubscriber to the simulation emitter.
    Detach and close any previous subscriber first.

    Attachment activates an auto-shutdown task which used to stop the
    simulation if no subscriber reconnects within a grace period.
    """
    # Detach old subscriber if it exists
    old_sub: Optional[WebSocketSubscriber] = sim_data.get("ws_subscriber")
    if old_sub:
        old_sub.close()  # Mark old subscriber as closed to stop sending
        sim_info["emitter"].detach(old_sub)

    # Extra safety: close and detach ALL subscribers to prevent duplicates
    # This handles edge cases where cleanup didn't run properly
    for sub in list(sim_info["emitter"].subscribers):
        if isinstance(sub, WebSocketSubscriber):
            sub.close()
            sim_info["emitter"].detach(sub)

    # Create new subscriber and attach
    subscriber = WebSocketSubscriber(websocket)
    sim_info["emitter"].attach(subscriber)
    sim_data["ws_subscriber"] = subscriber

    # Cancel any previous shutdown task
    old_task = sim_data.get("shutdown_task")
    if old_task:
        old_task.cancel()

    # Schedule auto-shutdown if no subscriber reconnects
    user_id = sim_data.get("user_id")
    if user_id is None:
        raise ValueError("user_id must be present in sim_data")

    sim_data["shutdown_task"] = asyncio.create_task(
        auto_shutdown_simulation(sim_id, sim_data, user_id)
    )

    return subscriber


async def start_or_resume_simulation(
    sim_info: RunInfo, sim_id: str, websocket: WebSocket, requesting_user: int
) -> None:
    """Start or resume simulation and notify the client."""
    driver = sim_info["simController"].realTimeDriver

    if sim_info["thread"] is None:
        db = next(get_db())
        simulation_service.start_simulation(db, sim_id, requesting_user)
        await safe_send_json(
            websocket,
            {
                "type": "status",
                "event": "simulation_started",
                "sim_id": sim_id,
                "status": "running",
                "message": "Simulation started and streaming frames.",
            },
        )
    elif not driver.running:
        driver.resume()
        await safe_send_json(
            websocket,
            {
                "type": "status",
                "event": "simulation_resumed",
                "sim_id": sim_id,
                "status": "running",
                "message": "Simulation resumed and streaming frames.",
            },
        )
    else:
        await safe_send_json(
            websocket,
            {
                "type": "status",
                "event": "connection_established",
                "sim_id": sim_id,
                "status": "running",
                "message": "Connected. Simulation is already running.",
            },
        )


async def cleanup_simulation(
    sim_id: str,
    sim_data: dict,
    sim_info: RunInfo,
    subscriber: WebSocketSubscriber,
    websocket: WebSocket,
) -> None:
    """Detach subscriber, pause simulation, and schedule shutdown if needed."""
    subscriber.close()  # Stop the subscriber from attempting to send frames
    sim_info["emitter"].detach(subscriber)
    sim_data.pop("ws_subscriber", None)

    driver = sim_info["simController"].realTimeDriver
    driver.pause()

    # Cancel old shutdown task if present
    old_task = sim_data.get("shutdown_task")
    if old_task:
        old_task.cancel()

    # Schedule new shutdown task
    sim_data["shutdown_task"] = asyncio.create_task(
        auto_shutdown_simulation(sim_id, sim_data, sim_data["user_id"])
    )

    if websocket.client_state != WebSocketState.DISCONNECTED:
        try:
            await websocket.close(code=1000)
        except Exception:
            pass


async def auto_shutdown_simulation(
    sim_id: str, sim_data: dict, requesting_user: int
) -> None:
    """
    Initiates a complete service shutdown (database cleanup and simulator stop)
    once the service has been idle for longer than the configured timeout.
    """
    await asyncio.sleep(settings.SIMULATION_IDLE_TIMEOUT_SECONDS)

    # If a subscriber exists, the user has reconnected and there is no need
    # to shut down
    if "ws_subscriber" in sim_data:
        return

    # A shutdown is performed if no WebSocket subscriber is associated with
    # the running, in-memory simulation instance
    try:
        db = next(get_db())
        simulation_service.stop_simulation(db, sim_id, requesting_user)
        print(f"Simulation {sim_id} stopped due to disconnect timeout.")
    except Exception as e:
        print(f"Failed to stop {sim_id}: {e}")
