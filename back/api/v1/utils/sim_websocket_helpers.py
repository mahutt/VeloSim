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
import time

from back.database.session import get_db
from back.exceptions import ItemNotFoundError, VelosimPermissionError
from back.exceptions.websocket_auth_error import WebSocketAuthError
from back.services import simulation_service
from back.services.simulation_service import (
    ActiveSimulationData,
    SimulationLockManager,
)
from back.core.simulation_startup_monitor import simulation_startup_histogram
from sim.entities.frame import Frame
from sim.simulator import RunInfo
from sim.utils.subscriber import Subscriber
from back.core.config import settings
from sqlalchemy.orm import Session
from back.grafana_logging.logger import get_logger

logger = get_logger(__name__)


class WebSocketSubscriber(Subscriber):
    """WebSocket subscriber for simulation frame updates."""

    def __init__(self, websocket: WebSocket):
        self.websocket = websocket
        """WebSocket connection for he current running loop."""
        try:
            # Extract sim_id from the WebSocket's path, which is part of the ASGI scope
            self.sim_id = websocket.scope["path"].split("/")[-1]
        except (KeyError, IndexError):
            # Provide a fallback for tests or unexpected scope structures
            self.sim_id = "unknown"
        try:
            self.loop = asyncio.get_running_loop()
        except RuntimeError:
            # No running loop - will be set manually (e.g., in tests)
            self.loop = None  # type: ignore
        self.closed = False
        self._first_frame_emitted = False
        """Flag to ensure startup time is only recorded once."""

    def set_event_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        """Set the event loop manually (primarily for testing).

        Args:
            loop: The asyncio event loop to use for running tasks.

        Returns:
            None
        """
        self.loop = loop

    def close(self) -> None:
        """Mark the subscriber as closed to prevent further frame sends.

        Returns:
            None
        """
        self.closed = True

    def on_frame(self, frame: Frame) -> None:
        """Handle incoming simulation frame and schedule it for sending via WebSocket.

        Args:
            frame: The simulation frame to send to the client.

        Returns:
            None
        """
        # Check if closed or websocket disconnected before scheduling
        if self.closed:
            return
        if self.websocket.client_state != WebSocketState.CONNECTED:
            return
            # On the first frame, check if we can record the total startup time.
        if not self._first_frame_emitted:
            self._first_frame_emitted = True
            sim_data = simulation_service.active_simulations.get(self.sim_id)
            # This metric is only recorded if the simulation was just initialized.
            if sim_data and (
                initialization_start_time := sim_data.pop(
                    "initialization_start_time", None
                )
            ):
                end_time = time.perf_counter()
                total_startup_time = end_time - initialization_start_time
                simulation_startup_histogram.record(
                    total_startup_time, {"simulation.id": self.sim_id}
                )
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
    """Send JSON through websocket and ignore if connection closed.

    Args:
        websocket: The WebSocket connection to send through.
        payload: The JSON payload to send.

    Returns:
        None
    """
    if websocket.client_state != WebSocketState.CONNECTED:
        # Socket already closed therefore do not attempt to send JSON
        return
    await websocket.send_json(payload)


async def accept_websocket_connection(websocket: WebSocket) -> bool:
    """
    Attempts to accept an incoming WebSocket connection.
    Returns True if connection accepted successfully and False otherwise.

    Args:
        websocket: The WebSocket connection to accept.

    Returns:
        bool: True if connection accepted successfully, False otherwise.
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

    Args:
        websocket: The WebSocket connection to send through and close.
        error_message: The error message to send to the client.

    Returns:
        None
    """
    await websocket.send_json({"type": "error", "message": error_message})
    await websocket.close()


async def verify_simulation_access(
    websocket: WebSocket, db: Session, sim_id: str, requesting_user: int
) -> bool:
    """
    Verify user has access to the simulation.
    Returns True if access granted, False if access denied (error sent to client).

    Args:
        websocket: The WebSocket connection for error messaging.
        db: Database session for checking simulation ownership.
        sim_id: The ID of the simulation to verify access for.
        requesting_user: The ID of the user requesting access.

    Returns:
        bool: True if access granted, False if access denied.
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

    Args:
        websocket: The WebSocket connection for sending responses.
        msg: The message received from the client.

    Returns:
        None
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

    Args:
        websocket: The WebSocket connection to receive messages from.

    Returns:
        None
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
) -> Optional[Tuple[ActiveSimulationData, RunInfo]]:
    """Fetch simulation info or send an error and close websocket.

    Args:
        sim_id: The ID of the simulation to retrieve.
        websocket: The WebSocket connection for error messaging.

    Returns:
        Optional[Tuple[dict, RunInfo]]: Tuple of sim_data and sim_info if
            found, None otherwise.
    """
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


def _remove_subscriber_from_sim_data(sim_data: ActiveSimulationData) -> None:
    """
    Remove the subscriber reference from simulation data.
    """
    sim_data.pop("ws_subscriber", None)


def _cleanup_old_subscribers(sim_data: ActiveSimulationData, sim_info: RunInfo) -> None:
    """
    Clean up all existing WebSocket subscribers.

    The cleanup process is as follows:
    1. Close subscribers to stop frame transmission
    2. Detach them from the emitter
    3. Remove references from sim_data
    """
    # Clean up primary subscriber if it exists
    old_sub = sim_data.get("ws_subscriber")
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
    subscriber: WebSocketSubscriber, sim_data: ActiveSimulationData
) -> None:
    """
    Store the subscriber reference in simulation data.
    """
    sim_data["ws_subscriber"] = subscriber


def _setup_new_subscriber(
    sim_data: ActiveSimulationData, sim_info: RunInfo, websocket: WebSocket
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


def _cancel_shutdown_task(sim_data: ActiveSimulationData) -> None:
    """
    Cancel the existing shutdown task if present.
    """
    old_task = sim_data.get("shutdown_task")
    if old_task:
        old_task.cancel()


def _create_shutdown_task(
    sim_id: str, sim_data: ActiveSimulationData, user_id: int
) -> asyncio.Task:
    """
    Create a new auto-shutdown task.
    """
    return asyncio.create_task(auto_shutdown_simulation(sim_id, sim_data, user_id))


def _store_shutdown_task(
    shutdown_task: asyncio.Task, sim_data: ActiveSimulationData
) -> None:
    """
    Store the shutdown task reference in simulation data.
    """
    sim_data["shutdown_task"] = shutdown_task


def _schedule_auto_shutdown(
    sim_id: str, sim_data: ActiveSimulationData, user_id: int
) -> asyncio.Task:
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


async def attach_ws_subscriber(
    sim_id: str,
    sim_data: ActiveSimulationData,
    sim_info: RunInfo,
    websocket: WebSocket,
) -> WebSocketSubscriber:
    """
    Attach a new WebSocketSubscriber to the simulation emitter.
    Returns the newly attached WebSocketSubscriber.

    Args:
        sim_id: The ID of the simulation to attach to.
        sim_data: Dictionary containing simulation data including user_id.
        sim_info: The simulation run information.
        websocket: The WebSocket connection to stream frames to.

    Returns:
        WebSocketSubscriber: The newly attached subscriber instance.
    """
    # Verify the user_id before proceeding
    user_id = sim_data.get("user_id")
    if user_id is None:
        raise ValueError("user_id must be present in sim_data")

    # Get lock for this simulation
    lock = SimulationLockManager.get_lock(sim_id)

    async with lock:
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
    db_gen = get_db()
    db = next(db_gen)
    try:
        simulation_service.start_simulation(db, sim_id, requesting_user)
    finally:
        try:
            next(db_gen)
        except StopIteration:
            pass


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

    Args:
        sim_info: The simulation run information.
        sim_id: The ID of the simulation to start or resume.
        websocket: The WebSocket connection for status notifications.
        requesting_user: The ID of the user requesting the start/resume.

    Returns:
        None
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
    sim_data: ActiveSimulationData,
    sim_info: RunInfo,
    subscriber: WebSocketSubscriber,
    websocket: WebSocket,
) -> None:
    """
    Clean up simulation resources following WebSocket disconnection.

    Args:
        sim_id: The ID of the simulation to clean up.
        sim_data: Dictionary containing simulation data.
        sim_info: The simulation run information.
        subscriber: The WebSocket subscriber to detach and close.
        websocket: The WebSocket connection to close.

    Returns:
        None
    """
    # Get lock for this simulation
    lock = SimulationLockManager.get_lock(sim_id)

    async with lock:
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
    sim_id: str, sim_data: ActiveSimulationData, requesting_user: int
) -> None:
    """
    Initiates a complete service shutdown (database cleanup and simulator stop)
    once the service has been idle for longer than the configured timeout.

    Args:
        sim_id: The ID of the simulation to shutdown.
        sim_data: Dictionary containing simulation data.
        requesting_user: The ID of the user who initiated the simulation.

    Returns:
        None
    """
    await asyncio.sleep(settings.SIMULATION_IDLE_TIMEOUT_SECONDS)

    # Get lock for this simulation
    lock = SimulationLockManager.get_lock(sim_id)

    async with lock:
        # Check if a subscriber exists - user may have reconnected during sleep
        if "ws_subscriber" in sim_data:
            return

        # Check if simulation still exists (may have been stopped by admin)
        if sim_id not in simulation_service.active_simulations:
            logger.info(f"Simulation {sim_id} already stopped, skipping auto-shutdown.")
            return

        # A shutdown is performed if no WebSocket subscriber is associated with
        # the running, in-memory simulation instance
        try:
            db_gen = get_db()
            db = next(db_gen)
            try:
                simulation_service.stop_simulation(db, sim_id, requesting_user)
                logger.info(f"Simulation {sim_id} stopped due to disconnect timeout.")
            finally:
                try:
                    next(db_gen)
                except StopIteration:
                    pass
        except ItemNotFoundError:
            # Simulation was already stopped (e.g., by admin) - this is expected
            logger.info(f"Simulation {sim_id} already stopped, skipping auto-shutdown.")
        except Exception as e:
            logger.error(f"Failed to stop {sim_id}: {e}")
