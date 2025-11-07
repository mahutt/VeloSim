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
from datetime import datetime, timedelta, timezone
from typing import Optional
from fastapi import WebSocket
from fastapi.websockets import WebSocketState

from back.database.session import get_db
from back.services.simulation_service import simulation_service
from sim.RealTimeDriver import RealTimeDriver
from sim.entities.frame import Frame
from sim.simulator import RunInfo
from sim.utils.subscriber import Subscriber


class WebSocketSubscriber(Subscriber):
    def __init__(
        self,
        websocket: WebSocket,
        sim_id: str,
        timeout: float = 5.0,
        initial_delay: float = 10.0,
    ):
        """
        Initialize a WebSocketSubscriber for streaming simulation frames to a client.

        Args:
            websocket (WebSocket): FastAPI WebSocket connection to the client.
            sim_id (str): UUID of the in-memory simulation being subscribed to.
            timeout (float, optional): Maximum allowed time (in seconds)
            between frames before closing the connection. Defaults to 5.0.
            initial_delay (float, optional): Time (in seconds) to wait before
            starting frame timeout monitoring. Defaults to 10.0.
        """
        self.websocket: WebSocket = websocket
        """WebSocket connection for sending JSON frames and status messages."""
        self.sim_id: str = sim_id
        """Simulation identifier used for tagging frames and messages."""
        self.timeout: float = timeout
        """
        Maximum allowed time between frames before the subscriber closes the
        connection.
        """
        self.initial_delay: float = initial_delay
        """Time to wait before starting periodic checks for missing frames."""
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        """Event loop used to run asynchronous tasks from synchronous callbacks."""
        self.last_frame_time: Optional[datetime] = None
        """Timestamp of the most recent frame received used to detect missing frames."""
        self._closed: bool = False
        """Internal flag indicating whether the WebSocket connection has been closed."""

    def set_event_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        self._loop = loop

    def on_frame(self, frame: Frame) -> None:
        self.last_frame_time = datetime.now(timezone.utc)
        if self._loop and not self._closed:
            asyncio.run_coroutine_threadsafe(
                self._send_frame(
                    {
                        "sim_id": self.sim_id,
                        "seq_numb": frame.seq_number,
                        "payload": frame.payload_str,
                        "timestamp": frame.timestamp_ms,
                    }
                ),
                self._loop,
            )

    async def _send_frame(self, frame_data: dict) -> None:
        try:
            if not self._closed:
                await self.websocket.send_json(frame_data)
        except Exception as err:
            print(f"Error sending frame: {err}")

    async def watch_for_no_frames(self) -> None:
        """Start checking after initial_delay, then periodically close if no frames."""
        await asyncio.sleep(self.initial_delay)
        while not self._closed:
            await asyncio.sleep(self.timeout)
            if self.last_frame_time is None:
                # No frames ever received, skip for now
                continue
            if datetime.now(timezone.utc) - self.last_frame_time > timedelta(
                seconds=self.timeout
            ):
                try:
                    await self.websocket.send_json(
                        {
                            "type": "status",
                            "event": "no_frames_detected",
                            "sim_id": self.sim_id,
                            "message": f"No frames received in {self.timeout} seconds.",
                        }
                    )
                    await self.websocket.close(
                        code=1000, reason="No more frames available"
                    )
                except Exception:
                    # Already closed or error sending, ignore
                    pass
                finally:
                    self._closed = True
                    break


async def safe_send_json(websocket: WebSocket, payload: dict) -> None:
    """Send JSON through websocket and ignore if connection closed."""
    try:
        await websocket.send_json(payload)
    except Exception:
        pass


async def get_simulation_or_error(
    sim_id: str, websocket: WebSocket
) -> Optional[RunInfo]:
    """Fetch simulation info or send an error and close websocket."""
    try:
        sim_info: RunInfo | None = simulation_service.get_simulator().get_sim_by_id(
            sim_id
        )
        return sim_info
    except Exception:
        await safe_send_json(
            websocket,
            {
                "type": "error",
                "event": "simulation_not_found",
                "sim_id": sim_id,
                "message": f"Simulation '{sim_id}' not found.",
            },
        )
        await websocket.close(code=4004)
        return None


def attach_subscriber(
    sim_info: RunInfo, websocket: WebSocket, sim_id: str
) -> WebSocketSubscriber:
    """Attach a WebSocketSubscriber to the simulation emitter."""
    subscriber = WebSocketSubscriber(websocket, sim_id)
    subscriber.set_event_loop(asyncio.get_event_loop())
    sim_info["emitter"].attach(subscriber)
    asyncio.create_task(subscriber.watch_for_no_frames())
    return subscriber


async def start_or_resume_simulation(
    sim_info: RunInfo, sim_id: str, requesting_user: int, websocket: WebSocket
) -> None:
    """Start or resume a running simulation."""
    driver: RealTimeDriver = sim_info["simController"].realTimeDriver
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
    sim_info: RunInfo, subscriber: Subscriber, websocket: WebSocket
) -> None:
    """Detach subscriber and pause simulation if websocket is active."""
    sim_info["emitter"].detach(subscriber)
    driver: RealTimeDriver = sim_info["simController"].realTimeDriver
    if websocket.client_state != WebSocketState.DISCONNECTED:
        driver.pause()
        try:
            await websocket.close(code=1000)
        except Exception:
            pass
