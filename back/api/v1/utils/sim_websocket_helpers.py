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
from back.exceptions import ItemNotFoundError, VelosimPermissionError
from back.exceptions.websocket_auth_error import WebSocketAuthError
from back.services import simulation_service
from sim.entities.frame import Frame
from sim.simulator import RunInfo
from sim.utils.subscriber import Subscriber
from back.core.config import settings
from sqlalchemy.orm import Session
from back.grafana_logging.logger import get_logger

logger = get_logger(__name__)


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


async def accept_websocket_connection(websocket: WebSocket) -> bool:
    """
    Attempts to accept an incoming WebSocket connection.
    Returns True if connection accepted successfully and False otherwise.
    """
    try:
        await websocket.accept()
        return True
    except WebSocketAuthError as e:
        await e.websocket.close(code=e.code)
        return False


async def send_error_and_close(websocket: WebSocket, error_message: str) -> None:
    """
    Send error message to client and close the connection.
    """
    await websocket.send_json({"type": "error", "message": error_message})
    await websocket.close()


async def verify_simulation_access(
    websocket: WebSocket, db: Session, sim_id: str, requesting_user: int
) -> bool:
    """
    Verify user has access to the simulation.
    Returns True if access granted, False if access denied (error sent to client).
    """
    try:
        has_access = simulation_service.verify_access(db, sim_id, requesting_user)
        if not has_access:
            await send_error_and_close(
                websocket, "Unauthorized access to this simulation."
            )
            return False
        return True
    except ItemNotFoundError as e:
        await send_error_and_close(websocket, str(e))
        return False
    except VelosimPermissionError as e:
        await send_error_and_close(websocket, str(e))
        return False


async def handle_client_message(websocket: WebSocket, msg: dict) -> None:
    """
    Process incoming client message.
    """
    if msg.get("action") != "ping":
        # Send warning for unrecognized actions (ping is for liveness checks)
        await safe_send_json(
            websocket,
            {
                "type": "warning",
                "event": "unknown_action",
                "message": "Unrecognized action.",
            },
        )


async def run_message_loop(websocket: WebSocket) -> None:
    """
    Run the main WebSocket message receiving loop. The loop continues until
    the WebSocket connection breaks or when an invalid message is received.
    """
    while True:
        try:
            msg = await websocket.receive_json()
            await handle_client_message(websocket, msg)
        except Exception:
            # Connection closed or error receiving message
            break


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


def _close_subscriber(subscriber: WebSocketSubscriber) -> None:
    """
    Close a single subscriber to stop it from sending frames.
    """
    subscriber.close()


def _detach_subscriber_from_emitter(
    subscriber: WebSocketSubscriber, sim_info: RunInfo
) -> None:
    """
    Detach a subscriber from the simulation emitter.
    """
    sim_info["emitter"].detach(subscriber)


def _remove_subscriber_from_sim_data(sim_data: dict) -> None:
    """
    Remove the subscriber reference from simulation data.
    """
    sim_data.pop("ws_subscriber", None)


def _cleanup_old_subscribers(sim_data: dict, sim_info: RunInfo) -> None:
    """
    Clean up all existing WebSocket subscribers.

    The cleanup process is as follows:
    1. Close subscribers to stop frame transmission
    2. Detach them from the emitter
    3. Remove references from sim_data
    """
    # Clean up primary subscriber if it exists
    old_sub: Optional[WebSocketSubscriber] = sim_data.get("ws_subscriber")
    if old_sub:
        _close_subscriber(old_sub)
        _detach_subscriber_from_emitter(old_sub, sim_info)

    # Every possible subscriber is cleaned up to prevent duplicates
    # This handles edge cases where cleanup could have not run properly
    for sub in list(sim_info["emitter"].subscribers):
        if isinstance(sub, WebSocketSubscriber):
            _close_subscriber(sub)
            _detach_subscriber_from_emitter(sub, sim_info)


def _create_subscriber(websocket: WebSocket) -> WebSocketSubscriber:
    """
    Create a new WebSocketSubscriber instance.
    """
    return WebSocketSubscriber(websocket)


def _attach_subscriber_to_emitter(
    subscriber: WebSocketSubscriber, sim_info: RunInfo
) -> None:
    """
    Attach a subscriber to the simulation emitter.
    """
    sim_info["emitter"].attach(subscriber)


def _store_subscriber_in_sim_data(
    subscriber: WebSocketSubscriber, sim_data: dict
) -> None:
    """
    Store the subscriber reference in simulation data.
    """
    sim_data["ws_subscriber"] = subscriber


def _setup_new_subscriber(
    sim_data: dict, sim_info: RunInfo, websocket: WebSocket
) -> WebSocketSubscriber:
    """
    Set up a new WebSocket subscriber for the simulation.
    Returns the WebSocket subscriber.
    """
    # Create the subscriber instance
    subscriber = _create_subscriber(websocket)
    # Attach it to the emitter
    _attach_subscriber_to_emitter(subscriber, sim_info)
    # Store the reference in sim_data
    _store_subscriber_in_sim_data(subscriber, sim_data)
    return subscriber


def _cancel_shutdown_task(sim_data: dict) -> None:
    """
    Cancel the existing shutdown task if present.
    """
    old_task = sim_data.get("shutdown_task")
    if old_task:
        old_task.cancel()


def _create_shutdown_task(sim_id: str, sim_data: dict, user_id: int) -> asyncio.Task:
    """
    Create a new auto-shutdown task.
    """
    return asyncio.create_task(auto_shutdown_simulation(sim_id, sim_data, user_id))


def _store_shutdown_task(shutdown_task: asyncio.Task, sim_data: dict) -> None:
    """
    Store the shutdown task reference in simulation data.
    """
    sim_data["shutdown_task"] = shutdown_task


def _schedule_auto_shutdown(sim_id: str, sim_data: dict, user_id: int) -> asyncio.Task:
    """
    Schedule an auto-shutdown task for the simulation.
    Returns the shutdown Task.
    """
    # Cancel any existing shutdown task
    _cancel_shutdown_task(sim_data)
    # Create a new shutdown task
    shutdown_task = _create_shutdown_task(sim_id, sim_data, user_id)
    # Store the task reference
    _store_shutdown_task(shutdown_task, sim_data)
    return shutdown_task


def attach_ws_subscriber(
    sim_id: str,
    sim_data: dict,
    sim_info: RunInfo,
    websocket: WebSocket,
) -> WebSocketSubscriber:
    """
    Attach a new WebSocketSubscriber to the simulation emitter.
    Returns the newly attached WebSocketSubscriber.
    """
    # Verify the user_id before proceeding
    user_id = sim_data.get("user_id")
    if user_id is None:
        raise ValueError("user_id must be present in sim_data")

    # Detach and close any previous subscriber(s)
    _cleanup_old_subscribers(sim_data, sim_info)

    # Set up a new subscriber
    subscriber = _setup_new_subscriber(sim_data, sim_info, websocket)

    # Schedule an auto-shutdown task for when the connection is idle
    _schedule_auto_shutdown(sim_id, sim_data, user_id)

    return subscriber


def _is_simulation_not_started(sim_info: RunInfo) -> bool:
    """
    Check if a simulation thread has not entered its 'started' state.
    """
    return sim_info["thread"] is None


def _is_simulation_paused(sim_info: RunInfo) -> bool:
    """
    Check if a simulation is currently in its paused state.
    """
    driver = sim_info["simController"].realTimeDriver
    return not driver.running


def _start_simulation(sim_id: str, requesting_user: int) -> None:
    """
    Start a new simulation thread.
    """
    db = next(get_db())
    simulation_service.start_simulation(db, sim_id, requesting_user)


def _resume_simulation(sim_info: RunInfo) -> None:
    """
    Resume a paused simulation.
    """
    driver = sim_info["simController"].realTimeDriver
    driver.resume()


async def _notify_simulation_started(websocket: WebSocket, sim_id: str) -> None:
    """
    Send a notification that the simulation has started.
    """
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


async def _notify_simulation_resumed(websocket: WebSocket, sim_id: str) -> None:
    """
    Send a notification that the simulation has resumed.
    """
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


async def _notify_connection_established(websocket: WebSocket, sim_id: str) -> None:
    """
    Send a notification that the WebSocket connection has been established.
    """
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


async def start_or_resume_simulation(
    sim_info: RunInfo, sim_id: str, websocket: WebSocket, requesting_user: int
) -> None:
    """
    Start or resume simulation based on current state and notify the client.
    """
    if _is_simulation_not_started(sim_info):
        _start_simulation(sim_id, requesting_user)
        await _notify_simulation_started(websocket, sim_id)
    elif _is_simulation_paused(sim_info):
        _resume_simulation(sim_info)
        await _notify_simulation_resumed(websocket, sim_id)
    else:
        await _notify_connection_established(websocket, sim_id)


def _pause_simulation(sim_info: RunInfo) -> None:
    """
    Pause the simulation execution.
    """
    driver = sim_info["simController"].realTimeDriver
    driver.pause()


async def _close_websocket_connection(websocket: WebSocket) -> None:
    """
    Safely close the WebSocket connection.
    """
    if websocket.client_state != WebSocketState.DISCONNECTED:
        try:
            await websocket.close(code=1000)
        except Exception:
            # Silently ignore close errors (connection may already be closed)
            pass


async def cleanup_simulation(
    sim_id: str,
    sim_data: dict,
    sim_info: RunInfo,
    subscriber: WebSocketSubscriber,
    websocket: WebSocket,
) -> None:
    """
    Clean up simulation resources following WebSocket disconnection.
    """
    # Clean up subscriber
    _close_subscriber(subscriber)
    _detach_subscriber_from_emitter(subscriber, sim_info)
    _remove_subscriber_from_sim_data(sim_data)

    # Pause simulation execution
    _pause_simulation(sim_info)

    # Schedule shutdown after idle timeout
    user_id = sim_data["user_id"]
    _schedule_auto_shutdown(sim_id, sim_data, user_id)

    # Close WebSocket connection
    await _close_websocket_connection(websocket)


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
        logger.info(f"Simulation {sim_id} stopped due to disconnect timeout.")
    except Exception as e:
        logger.error(f"Failed to stop {sim_id}: {e}")
