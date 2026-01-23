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
from back.crud.sim_frame import sim_frame_crud
from back.schemas.sim_frame import SimFrameCreate
from back.core.config import settings
from grafana_logging.logger import get_logger

logger = get_logger(__name__)


class FramePersistenceSubscriber(Subscriber):
    """Async subscriber that persists all simulation frames to the database.

    This subscriber receives all frames from the simulation (both keyframes
    and diff frames) and asynchronously persists them to the database using
    a queue-based worker pattern with idempotent upsert operations.
    """

    def _validate_frame(self, frame: Frame) -> bool:
        """Validate frame has required fields. Returns True if valid."""
        if frame.is_key is None:
            error_msg = (
                f"Frame seq={getattr(frame, 'seq_number', '?')} has is_key=None. "
                "This indicates a potential problem in the simulation "
                "frame generation."
            )
            logger.error(
                f"Invalid frame for sim_instance_id="
                f"{self.sim_instance_id}: {error_msg}"
            )
            return False
        return True

    def __init__(self, sim_instance_id: int):
        """Initialize the frame persistence subscriber.

        Args:
            sim_instance_id: Database ID of the simulation instance.
        """
        try:
            self.sim_instance_id = sim_instance_id
            self.queue_max_size = settings.KEYFRAME_QUEUE_MAX_SIZE

            # Async queue for frame data
            self.frame_queue: asyncio.Queue[Optional[Frame]] = asyncio.Queue(
                maxsize=self.queue_max_size
            )

            # Event loop and worker task - create our own event loop in a
            # background thread
            self.loop: Optional[asyncio.AbstractEventLoop] = None
            self.loop_thread: Optional[threading.Thread] = None
            self.worker_task: Optional[concurrent.futures.Future] = None
            self.closed = False

            # Executor for immediate/synchronous persistence requests (keyframes)
            # Use a single-worker executor to serialize immediate writes and avoid
            # creating/shutting down many threads.
            self._immediate_executor = concurrent.futures.ThreadPoolExecutor(
                max_workers=1
            )

            # Track highest persisted sequence number to avoid duplicate persistence
            # on immediate writes or shutdown re-queueing.
            self.highest_persisted_seq: int = -1
            self._seq_lock = threading.Lock()

            # Metrics counters
            self.persist_success_count = 0
            self.persist_failure_count = 0
            self.queue_drop_count = 0

            # Track last keyframe for final persistence on shutdown
            self.last_keyframe: Optional[Frame] = None

            logger.info(
                "FramePersistenceSubscriber initialized for "
                + f"sim_instance_id={sim_instance_id}, "
                + f"queue_max_size={self.queue_max_size}"
            )
        except Exception:
            if hasattr(self, "_immediate_executor"):
                self._immediate_executor.shutdown(wait=False)
            raise

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
                "Created background event loop for frame persistence "
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
                "FramePersistenceSubscriber worker started for "
                + f"sim_instance_id={self.sim_instance_id}"
            )

    async def _persistence_worker(self) -> None:
        """Async worker that processes frames from the queue and persists them."""
        logger.info(
            "Frame persistence worker running for "
            f"sim_instance_id={self.sim_instance_id}"
        )
        # Batch configuration (fallbacks currently match config defaults)
        batch_size = getattr(settings, "FRAME_PERSIST_BATCH_SIZE", 32)
        batch_timeout = getattr(settings, "FRAME_PERSIST_BATCH_TIMEOUT", 0.5)

        while not self.closed:
            batch = []
            try:
                # Wait for first frame (short timeout so we can check closed flag)
                first_frame = await asyncio.wait_for(
                    self.frame_queue.get(), timeout=1.0
                )

                if first_frame is None:
                    # Shutdown signal received
                    break

                batch.append(first_frame)

                # Collect additional frames up to batch_size or until batch_timeout
                batch_start = time.time()
                while len(batch) < batch_size:
                    remaining = batch_timeout - (time.time() - batch_start)
                    if remaining <= 0:
                        break
                    try:
                        item = await asyncio.wait_for(
                            self.frame_queue.get(), timeout=remaining
                        )
                        if item is None:
                            # Re-queue shutdown marker for other potential
                            # consumers and stop collecting
                            try:
                                self.frame_queue.put_nowait(None)
                            except Exception:
                                pass
                            break
                        batch.append(item)
                    except asyncio.TimeoutError:
                        break

                # Persist the collected batch in a single DB operation
                if batch:
                    loop = self.loop if self.loop else asyncio.get_running_loop()

                    # Build SimFrameCreate objects for the batch
                    frame_datas = []
                    for f in batch:
                        if not self._validate_frame(f):
                            self.persist_failure_count += 1
                            continue  # Skip this frame
                        sim_seconds_elapsed = 0.0
                        if "clock" in f.payload_dict:
                            sim_seconds_elapsed = f.payload_dict["clock"].get(
                                "simSecondsPassed", 0.0
                            )
                        frame_datas.append(
                            SimFrameCreate(
                                sim_instance_id=self.sim_instance_id,
                                seq_number=f.seq_number,
                                sim_seconds_elapsed=sim_seconds_elapsed,
                                frame_data=f.payload_dict,
                                is_key=bool(f.is_key),
                            )
                        )

                    # Execute bulk upsert in threadpool; DB session is created
                    # inside the synchronous helper to avoid cross-thread sessions.
                    if frame_datas:
                        await loop.run_in_executor(
                            None, self._upsert_many_sync, frame_datas
                        )
                        self.persist_success_count += len(frame_datas)
                        # Update highest persisted sequence based on keyframes
                        # in this batch
                        try:
                            key_seqs = [
                                f.seq_number
                                for f in batch
                                if getattr(f, "is_key", False)
                            ]
                            if key_seqs:
                                max_key_seq = max(key_seqs)
                                with self._seq_lock:
                                    if max_key_seq > self.highest_persisted_seq:
                                        self.highest_persisted_seq = max_key_seq
                        except Exception as e:
                            logger.debug(
                                f"Non-critical error updating "
                                f"highest_persisted_seq for "
                                f"sim_instance_id={self.sim_instance_id}: {e}"
                            )

                        logger.info(
                            f"Persisted batch of {len(frame_datas)} frames for "
                            f"sim_instance_id={self.sim_instance_id}, "
                            f"total_success={self.persist_success_count}"
                        )

            except asyncio.TimeoutError:
                # No frame available, continue loop to check closed flag
                continue
            except Exception as e:
                # If a batch was being processed, attribute failures to the batch size
                failed = len(batch) if batch else 1
                self.persist_failure_count += failed
                logger.error(
                    "Unexpected error in persistence worker for "
                    + f"sim_instance_id={self.sim_instance_id}: {e}. "
                    + f"Marked {failed} failures."
                )

        logger.info(
            "Frame persistence worker stopped for "
            f"sim_instance_id={self.sim_instance_id}. Stats: "
            f"success={self.persist_success_count}, "
            f"failures={self.persist_failure_count}, "
            f"drops={self.queue_drop_count}"
        )

    def _upsert_many_sync(self, frame_datas: list[SimFrameCreate]) -> int:
        """Synchronous helper run inside a ThreadPoolExecutor.

        Creates its own DB session and performs the bulk upsert.
        Returns the number of frames upserted.
        """
        db = SessionLocal()
        try:
            return sim_frame_crud.upsert_many(db, frame_datas)
        finally:
            try:
                db.close()
            except Exception:
                pass

    def _upsert_sync(self, frame_data: SimFrameCreate) -> int:
        """Synchronous helper run inside a ThreadPoolExecutor for a single frame."""
        db = SessionLocal()
        try:
            sim_frame_crud.upsert(db, frame_data)
            return 1
        finally:
            try:
                db.close()
            except Exception:
                pass

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

            # Build frame_data and submit to executor helper which creates its
            # own DB session inside the thread to avoid cross-thread sessions.
            # Validate is_key is set
            if frame.is_key is None:
                error_msg = (
                    f"Frame seq={frame.seq_number} has is_key=None. "
                    "This indicates a potential problem in the simulation "
                    "frame generation."
                )
                logger.error(
                    f"Invalid frame for sim_instance_id="
                    f"{self.sim_instance_id}: {error_msg}"
                )
                raise ValueError(error_msg)

            frame_data = SimFrameCreate(
                sim_instance_id=self.sim_instance_id,
                seq_number=frame.seq_number,
                sim_seconds_elapsed=sim_seconds_elapsed,
                frame_data=frame.payload_dict,
                is_key=frame.is_key,
            )

            loop = self.loop if self.loop else asyncio.get_running_loop()
            await loop.run_in_executor(None, self._upsert_sync, frame_data)

            self.persist_success_count += 1

            # If this was a keyframe, update highest persisted sequence
            try:
                if frame.is_key and frame.seq_number > self.highest_persisted_seq:
                    with self._seq_lock:
                        self.highest_persisted_seq = frame.seq_number
            except Exception as e:
                logger.debug(
                    f"Non-critical error updating highest_persisted_seq for "
                    f"sim_instance_id={self.sim_instance_id}: {e}"
                )

            frame_type = "keyframe" if frame.is_key else "diff"
            logger.info(
                f"Persisted {frame_type} for "
                f"sim_instance_id={self.sim_instance_id}, "
                f"seq={frame.seq_number}, "
                f"sim_seconds={sim_seconds_elapsed:.2f}, "
                f"total_success={self.persist_success_count}"
            )

        except Exception as e:
            self.persist_failure_count += 1
            logger.error(
                "Failed to persist frame for "
                f"sim_instance_id={self.sim_instance_id}: {e}. "
                f"Total failures: {self.persist_failure_count}"
            )

    def on_frame(self, frame: Frame) -> None:
        """Handle incoming frame from simulation (called from simulation thread).

        Persists ALL frames (both keyframes and diffs) for full replay capability.

        Args:
            frame: The frame received from the simulation.

        Returns:
            None
        """
        if self.closed:
            return

        # Track last keyframe for final persistence on shutdown
        if frame.is_key:
            self.last_keyframe = frame

        # Try to queue the frame (no interval filtering - persist all frames)
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
                "Frame persistence queue full for "
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

        # Must be a keyframe. This also verifies that is_key is not None
        if not frame.is_key:
            logger.warning(
                f"force_persist_keyframe called with non-keyframe "
                f"(seq={frame.seq_number}) for sim_instance_id={self.sim_instance_id}"
            )
            return

        # Track as last keyframe
        self.last_keyframe = frame

        # If we've already persisted this sequence, skip immediate write/queue
        try:
            if frame.seq_number <= self.highest_persisted_seq:
                logger.info(
                    f"Keyframe seq={frame.seq_number} already persisted for "
                    f"sim_instance_id={self.sim_instance_id}, skipping"
                )
                return
        except Exception as e:
            logger.debug(
                f"Non-critical error updating highest_persisted_seq for "
                f"sim_instance_id={self.sim_instance_id}: {e}"
            )

        # Build SimFrameCreate for immediate persistence
        sim_seconds_elapsed = 0.0
        if "clock" in frame.payload_dict:
            sim_seconds_elapsed = frame.payload_dict["clock"].get(
                "simSecondsPassed", 0.0
            )

        frame_data = SimFrameCreate(
            sim_instance_id=self.sim_instance_id,
            seq_number=frame.seq_number,
            sim_seconds_elapsed=sim_seconds_elapsed,
            frame_data=frame.payload_dict,
            is_key=frame.is_key,
        )

        # Try immediate synchronous persistence via the executor and wait
        # briefly for completion. If it fails or times out, fall back to
        # queueing the frame so it will be persisted by the batch worker.
        future = self._immediate_executor.submit(self._upsert_sync, frame_data)
        try:
            # Wait up to configured timeout for immediate persistence
            result = future.result(timeout=settings.PERSIST_IMMEDIATE_TIMEOUT)
            self.persist_success_count += result
            # Update highest persisted seq
            try:
                if frame.seq_number > self.highest_persisted_seq:
                    self.highest_persisted_seq = frame.seq_number
            except Exception as e:
                logger.debug(
                    f"Non-critical error updating highest_persisted_seq for "
                    f"sim_instance_id={self.sim_instance_id}: {e}"
                )

            logger.info(
                f"Immediately persisted keyframe seq={frame.seq_number} for "
                f"sim_instance_id={self.sim_instance_id} (immediate)"
            )
            return
        except concurrent.futures.TimeoutError:
            logger.warning(
                f"Immediate keyframe persist timed out for "
                f"sim_instance_id={self.sim_instance_id}, seq={frame.seq_number}; "
                f"queueing instead"
            )
        except Exception as e:
            logger.warning(
                f"Immediate keyframe persist failed for "
                f"sim_instance_id={self.sim_instance_id}, seq={frame.seq_number}: "
                f"{e}; queueing instead"
            )

        # Fall back to queueing the keyframe for the batch worker
        try:
            self.frame_queue.put_nowait(frame)
            logger.info(
                f"Queued keyframe for batched persistence: "
                f"sim_instance_id={self.sim_instance_id}, seq={frame.seq_number}"
            )
        except asyncio.QueueFull:
            logger.error(
                f"Could not queue keyframe (queue full) for "
                f"sim_instance_id={self.sim_instance_id}, seq={frame.seq_number}"
            )

    async def shutdown(self) -> None:
        """Gracefully shutdown the persistence subscriber.

        Returns:
            None
        """
        if self.closed:
            return

        # Mark closed to stop accepting new frames
        self.closed = True
        logger.info(
            "Shutting down FramePersistenceSubscriber for "
            f"sim_instance_id={self.sim_instance_id}"
        )

        # Immediately persist the last keyframe synchronously (best-effort).
        # This avoids relying on the batch worker to flush remaining diffs
        # after the sim disconnects.
        if self.last_keyframe is not None:
            try:
                sim_seconds_elapsed = self.last_keyframe.payload_dict.get(
                    "clock", {}
                ).get("simSecondsPassed", 0.0)

                # Validate is_key is not None before creating SimFrameCreate
                if self.last_keyframe.is_key is None:
                    logger.error(
                        f"Last keyframe has is_key=None for "
                        f"sim_instance_id={self.sim_instance_id}, "
                        f"seq={self.last_keyframe.seq_number}"
                    )
                else:
                    frame_data = SimFrameCreate(
                        sim_instance_id=self.sim_instance_id,
                        seq_number=self.last_keyframe.seq_number,
                        sim_seconds_elapsed=sim_seconds_elapsed,
                        frame_data=self.last_keyframe.payload_dict,
                        is_key=self.last_keyframe.is_key,
                    )
                    # Submit to immediate executor and wait briefly
                    fut = self._immediate_executor.submit(self._upsert_sync, frame_data)
                    try:
                        res = fut.result(
                            timeout=settings.PERSIST_FINAL_KEYFRAME_TIMEOUT
                        )
                        self.persist_success_count += res
                        if self.last_keyframe.seq_number > self.highest_persisted_seq:
                            with self._seq_lock:
                                if (
                                    self.last_keyframe.seq_number
                                    > self.highest_persisted_seq
                                ):
                                    self.highest_persisted_seq = (
                                        self.last_keyframe.seq_number
                                    )
                        logger.info(
                            f"Persisted final keyframe for "
                            f"sim_instance_id={self.sim_instance_id} "
                            f"seq={self.last_keyframe.seq_number}"
                        )
                    except concurrent.futures.TimeoutError:
                        logger.warning(
                            f"Timeout persisting final keyframe for "
                            f"sim_instance_id={self.sim_instance_id} "
                            f"seq={self.last_keyframe.seq_number}"
                        )
                    except Exception as e:
                        logger.warning(
                            f"Error persisting final keyframe for "
                            f"sim_instance_id={self.sim_instance_id} "
                            f"seq={self.last_keyframe.seq_number}: {e}"
                        )
            except Exception:
                logger.exception(
                    "Unexpected error during immediate final keyframe persist"
                )

        # Gracefully signal the worker to exit and wait for it to finish
        if self.loop:
            try:
                # Put shutdown sentinel into the worker's queue on its event loop
                put_fut = asyncio.run_coroutine_threadsafe(
                    self.frame_queue.put(None), self.loop
                )
                put_fut.result(timeout=settings.PERSIST_SHUTDOWN_SENTINEL_TIMEOUT)
            except Exception as e:
                logger.warning(f"Failed to enqueue shutdown sentinel: {e}")

        # Wait for the worker coroutine to finish (scheduled with
        # run_coroutine_threadsafe)
        if self.worker_task:
            try:
                # This will wait for the coroutine to finish executing
                self.worker_task.result(timeout=settings.PERSIST_WORKER_TASK_TIMEOUT)
            except concurrent.futures.TimeoutError:
                logger.warning(
                    "Timeout waiting for persistence worker to finish; "
                    "attempting cancel"
                )
                try:
                    self.worker_task.cancel()
                except Exception:
                    pass
            except Exception as e:
                logger.warning(f"Error waiting for persistence worker: {e}")

        # Stop the event loop if we created it and join the thread
        if self.loop and self.loop_thread:
            try:
                self.loop.call_soon_threadsafe(self.loop.stop)
            except Exception:
                pass
            try:
                self.loop_thread.join(timeout=settings.PERSIST_LOOP_THREAD_JOIN_TIMEOUT)
            except Exception:
                pass

        # Persist any remaining frames in the queue before draining, using the
        # event loop thread for thread safety
        drained_items = []

        def drain_queue() -> None:
            """Drain all items from the frame queue into drained_items list.

            This helper is used during shutdown to collect any remaining frames
            from the queue for final persistence.

            Returns:
                None
            """
            while True:
                try:
                    item = self.frame_queue.get_nowait()
                    drained_items.append(item)
                except asyncio.QueueEmpty:
                    break

        if self.loop:
            try:
                self.loop.call_soon_threadsafe(drain_queue)
                time.sleep(0.1)  # Give the event loop time to run the drain
            except Exception as e:
                logger.error(f"Error draining queue: {e}")

        if drained_items:
            logger.info(
                f"Persisting {len(drained_items)} remaining frames in queue "
                f"during shutdown for sim_instance_id={self.sim_instance_id}"
            )
            # Persist in batches for efficiency
            batch_size = getattr(settings, "FRAME_PERSIST_BATCH_SIZE", 32)
            for i in range(0, len(drained_items), batch_size):
                batch = drained_items[i : i + batch_size]
                frame_datas = []
                for f in batch:
                    if f is None:
                        continue
                    if not self._validate_frame(f):
                        self.persist_failure_count += 1
                        continue
                    sim_seconds_elapsed = 0.0
                    if hasattr(f, "payload_dict") and "clock" in f.payload_dict:
                        sim_seconds_elapsed = f.payload_dict["clock"].get(
                            "simSecondsPassed", 0.0
                        )
                    frame_datas.append(
                        SimFrameCreate(
                            sim_instance_id=self.sim_instance_id,
                            seq_number=f.seq_number,
                            sim_seconds_elapsed=sim_seconds_elapsed,
                            frame_data=f.payload_dict,
                            is_key=bool(f.is_key),
                        )
                    )
                if frame_datas:
                    try:
                        self._upsert_many_sync(frame_datas)
                        self.persist_success_count += len(frame_datas)
                    except Exception as e:
                        self.persist_failure_count += len(frame_datas)
                        logger.error(
                            f"Failed to persist shutdown batch for "
                            f"sim_instance_id={self.sim_instance_id}: {e}"
                        )

        logger.info(
            "FramePersistenceSubscriber shutdown complete for "
            f"sim_instance_id={self.sim_instance_id}. "
            f"Final stats: success={self.persist_success_count}, "
            f"failures={self.persist_failure_count}, "
            f"drops={self.queue_drop_count}"
        )

        # Shutdown immediate executor
        try:
            self._immediate_executor.shutdown(wait=False)
            logger.info(
                f"Shutdown immediate persistence executor for "
                f"sim_instance_id={self.sim_instance_id}"
            )
        except Exception:
            pass
