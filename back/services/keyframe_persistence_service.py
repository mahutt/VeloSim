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
import concurrent.futures
import random
import threading
import time
from typing import Optional
from sim.entities.frame import Frame
from sim.utils.subscriber import Subscriber
from back.database.session import SessionLocal
from back.crud.sim_keyframe import sim_keyframe_crud
from back.schemas.sim_keyframe import SimKeyframeCreate
from back.core.config import settings
from grafana_logging.logger import get_logger

logger = get_logger(__name__)


class KeyframePersistenceSubscriber(Subscriber):
    """Async subscriber that persists simulation keyframes to the database.

    This subscriber receives frames from the simulation, filters for keyframes
    based on the configured interval, and asynchronously persists them to the
    database using a queue-based worker pattern.
    """

    def __init__(self, sim_instance_id: int):
        """Initialize the keyframe persistence subscriber.

        Args:
            sim_instance_id: Database ID of the simulation instance.
        """
        self.sim_instance_id = sim_instance_id
        self.keyframe_counter = 0
        self.persist_interval = settings.KEYFRAME_PERSIST_INTERVAL
        self.queue_max_size = settings.KEYFRAME_QUEUE_MAX_SIZE

        # Async queue for frame data
        self.frame_queue: asyncio.Queue[Optional[Frame]] = asyncio.Queue(
            maxsize=self.queue_max_size
        )

        # Event loop and worker task - create our own event loop in a background thread
        self.loop: Optional[asyncio.AbstractEventLoop] = None
        self.loop_thread: Optional[threading.Thread] = None
        self.worker_task: Optional[concurrent.futures.Future] = None
        self.closed = False

        # Metrics counters
        self.persist_success_count = 0
        self.persist_failure_count = 0
        self.queue_drop_count = 0

        # Track last keyframe for final persistence on shutdown
        self.last_keyframe: Optional[Frame] = None

        logger.info(
            "KeyframePersistenceSubscriber initialized for"
            + f"sim_instance_id={sim_instance_id}, "
            + f"persist_interval={self.persist_interval}, "
            + f"queue_max_size={self.queue_max_size}"
        )

    def set_event_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        """Set the event loop manually (primarily for testing).

        Args:
            loop: The asyncio event loop to use.

        Returns:
            None
        """
        self.loop = loop

    def start(self) -> None:
        """Start the async worker task for persisting frames.

        Returns:
            None
        """
        if self.loop is None:
            # Create a new event loop in a background thread
            def run_event_loop(loop: asyncio.AbstractEventLoop) -> None:
                """Run event loop forever in background thread.

                Args:
                    loop: The asyncio event loop to run.

                Returns:
                    None
                """
                asyncio.set_event_loop(loop)
                loop.run_forever()

            self.loop = asyncio.new_event_loop()
            self.loop_thread = threading.Thread(
                target=run_event_loop, args=(self.loop,), daemon=True
            )
            self.loop_thread.start()
            logger.info(
                "Created background event loop for keyframe persistence "
                + f"sim_instance_id={self.sim_instance_id}"
            )

        if self.loop is not None and not self.loop.is_closed():
            # Schedule the coroutine but don't wait for it to complete
            future = asyncio.run_coroutine_threadsafe(
                self._persistence_worker(), self.loop
            )
            # Store as a task-like object we can cancel later
            self.worker_task = future
            logger.info(
                "KeyframePersistenceSubscriber worker started for "
                + f"sim_instance_id={self.sim_instance_id}"
            )

    async def _persistence_worker(self) -> None:
        """Async worker that processes frames from the queue and persists them."""
        logger.info(
            "Keyframe persistence worker running for "
            f"sim_instance_id={self.sim_instance_id}"
        )

        while not self.closed:
            try:
                # Wait for frame with timeout to allow checking closed flag
                frame = await asyncio.wait_for(self.frame_queue.get(), timeout=1.0)

                if frame is None:
                    # Shutdown signal received
                    break

                await self._persist_frame(frame)

            except asyncio.TimeoutError:
                # No frame available, continue loop to check closed flag
                continue
            except Exception as e:
                logger.error(
                    "Unexpected error in persistence worker for "
                    + f"sim_instance_id={self.sim_instance_id}: {e}"
                )

        logger.info(
            "Keyframe persistence worker stopped for "
            f"sim_instance_id={self.sim_instance_id}. Stats: "
            f"success={self.persist_success_count}, "
            f"failures={self.persist_failure_count}, "
            f"drops={self.queue_drop_count}"
        )

    async def _persist_frame(self, frame: Frame) -> None:
        """Persist a single frame to the database.

        Args:
            frame: The frame to persist.
        """
        try:
            # Extract sim time from frame payload
            sim_seconds_elapsed = 0.0
            if "clock" in frame.payload_dict:
                sim_seconds_elapsed = frame.payload_dict["clock"].get(
                    "simSecondsPassed", 0.0
                )

            # Create database session (run in executor to avoid blocking)
            db = SessionLocal()
            try:
                keyframe_data = SimKeyframeCreate(
                    sim_instance_id=self.sim_instance_id,
                    sim_seconds_elapsed=sim_seconds_elapsed,
                    frame_data=frame.payload_dict,
                )

                # Run DB operation in thread pool executor
                # Use self.loop if available, otherwise get the running loop
                loop = self.loop if self.loop else asyncio.get_running_loop()
                await loop.run_in_executor(
                    None, sim_keyframe_crud.create, db, keyframe_data
                )

                self.persist_success_count += 1

                logger.info(
                    f"Persisted keyframe for sim_instance_id={self.sim_instance_id}, "
                    f"sim_seconds={sim_seconds_elapsed:.2f}, "
                    f"total_success={self.persist_success_count}"
                )

            finally:
                db.close()

        except Exception as e:
            self.persist_failure_count += 1
            logger.error(
                "Failed to persist keyframe for "
                f"sim_instance_id={self.sim_instance_id}: {e}. "
                f"Total failures: {self.persist_failure_count}"
            )

    def on_frame(self, frame: Frame) -> None:
        """Handle incoming frame from simulation (called from simulation thread).

        Args:
            frame: The frame received from the simulation.

        Returns:
            None
        """
        if self.closed:
            return

        # Only process keyframes
        if not frame.is_key:
            return

        # Track last keyframe for final persistence on shutdown
        self.last_keyframe = frame

        # Apply interval filtering: persist frame 0, then every Nth frame
        # (0, N, 2N, 3N, ...)
        if self.keyframe_counter % self.persist_interval != 0:
            self.keyframe_counter += 1
            return

        self.keyframe_counter += 1

        # Try to queue the frame
        try:
            self.frame_queue.put_nowait(frame)
        except asyncio.QueueFull:
            # Queue is full - drop a random frame to avoid bias
            self.queue_drop_count += 1

            # Drop random element from queue
            try:
                # Create temporary list, remove random element, refill queue
                temp_items = []
                while not self.frame_queue.empty():
                    try:
                        temp_items.append(self.frame_queue.get_nowait())
                    except asyncio.QueueEmpty:
                        break

                if temp_items:
                    # Remove random element
                    random.shuffle(temp_items)
                    temp_items.pop()  # Drop one random frame

                    # Put items back
                    for item in temp_items:
                        try:
                            self.frame_queue.put_nowait(item)
                        except asyncio.QueueFull:
                            break

                    # Try to add new frame again
                    self.frame_queue.put_nowait(frame)

            except Exception as e:
                logger.error(
                    "Error handling queue overflow for "
                    f"sim_instance_id={self.sim_instance_id}: {e}"
                )

            logger.warning(
                "Keyframe persistence queue full for "
                f"sim_instance_id={self.sim_instance_id}. "
                f"Dropped random frame. Total drops: {self.queue_drop_count}"
            )

    def force_persist_keyframe(self, frame: Frame) -> None:
        """Force immediate persistence of a keyframe, bypassing interval filtering.

        Used for critical state changes like pausing or manual saves.

        Args:
            frame: The keyframe to persist immediately.

        Returns:
            None
        """
        if self.closed:
            return

        # Must be a keyframe
        if not frame.is_key:
            logger.warning(
                f"force_persist_keyframe called with non-keyframe "
                f"(seq={frame.seq_number}) for sim_instance_id={self.sim_instance_id}"
            )
            return

        # Track as last keyframe
        self.last_keyframe = frame

        # Queue immediately without interval check
        try:
            self.frame_queue.put_nowait(frame)
            logger.info(
                f"Force-queued keyframe for immediate persistence: "
                f"sim_instance_id={self.sim_instance_id}, seq={frame.seq_number}"
            )
        except asyncio.QueueFull:
            logger.error(
                f"Could not force-queue keyframe (queue full) for "
                f"sim_instance_id={self.sim_instance_id}, seq={frame.seq_number}"
            )

    async def shutdown(self) -> None:
        """Gracefully shutdown the persistence subscriber.

        Returns:
            None
        """
        if self.closed:
            return

        self.closed = True
        logger.info(
            "Shutting down KeyframePersistenceSubscriber for "
            f"sim_instance_id={self.sim_instance_id}"
        )

        # Force-queue the last keyframe to ensure final state is persisted
        if self.last_keyframe is not None:
            try:
                self.frame_queue.put_nowait(self.last_keyframe)
                logger.info(
                    f"Queued final keyframe for sim_instance_id={self.sim_instance_id} "
                    f"at seq_number={self.last_keyframe.seq_number}"
                )
            except asyncio.QueueFull:
                logger.warning(
                    f"Could not queue final keyframe for "
                    f"sim_instance_id={self.sim_instance_id} - queue full"
                )

        # Wait for queue to drain before sending shutdown signal
        drain_timeout = settings.KEYFRAME_DRAIN_TIMEOUT
        drain_start = time.time()

        while not self.frame_queue.empty():
            elapsed = time.time() - drain_start
            if elapsed >= drain_timeout:
                queue_size = self.frame_queue.qsize()
                logger.warning(
                    f"Keyframe queue drain timeout ({drain_timeout}s) "
                    f"for sim_instance_id={self.sim_instance_id}. "
                    f"Remaining queue size: {queue_size}"
                )
                break
            await asyncio.sleep(0.1)  # Brief sleep to allow queue processing

        # Send shutdown signal to worker
        try:
            await asyncio.wait_for(self.frame_queue.put(None), timeout=5.0)
        except asyncio.TimeoutError:
            logger.warning(
                "Timeout waiting to queue shutdown signal for "
                f"sim_instance_id={self.sim_instance_id}"
            )

        # Wait for worker to finish
        if self.worker_task and not self.worker_task.done():
            try:
                # worker_task is a concurrent.futures.Future, not an asyncio coroutine
                # Wait synchronously with timeout
                try:
                    # concurrent.futures.Future doesn't support timeout in result()
                    # We need to use wait() or just cancel if still running
                    done, _ = concurrent.futures.wait([self.worker_task], timeout=10.0)
                    if not done:
                        logger.warning(
                            "Timeout waiting for persistence worker to finish for "
                            f"sim_instance_id={self.sim_instance_id}"
                        )
                        self.worker_task.cancel()
                except Exception as wait_error:
                    logger.warning(f"Error waiting for worker: {wait_error}")
                    self.worker_task.cancel()
            except Exception as e:
                logger.error(f"Error during worker shutdown: {e}")
                if hasattr(self.worker_task, "cancel"):
                    self.worker_task.cancel()

        logger.info(
            "KeyframePersistenceSubscriber shutdown complete for "
            f"sim_instance_id={self.sim_instance_id}. "
            f"Final stats: success={self.persist_success_count}, "
            f"failures={self.persist_failure_count}, "
            f"drops={self.queue_drop_count}"
        )

        # Stop the event loop if we created it
        if self.loop and self.loop_thread:
            self.loop.call_soon_threadsafe(self.loop.stop)
            self.loop_thread.join(timeout=5.0)
            logger.info(
                "Stopped background event loop for "
                f"sim_instance_id={self.sim_instance_id}"
            )
