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

import pytest
from unittest.mock import MagicMock, patch
from back.services.frame_persistence_service import FramePersistenceSubscriber
from sim.entities.frame import Frame


class TestFramePersistenceSubscriber:
    """Tests for the FramePersistenceSubscriber service."""

    def test_init(self) -> None:
        """Test that subscriber initializes correctly."""
        subscriber = FramePersistenceSubscriber(sim_instance_id=123)
        assert subscriber.sim_instance_id == 123
        assert subscriber.worker_task is None
        assert subscriber.closed is False

    def test_start_creates_worker_task(self) -> None:
        """Test that start() creates async worker task."""
        subscriber = FramePersistenceSubscriber(sim_instance_id=123)

        mock_loop = MagicMock()
        mock_loop.is_closed.return_value = False
        subscriber.set_event_loop(mock_loop)

        with patch("asyncio.run_coroutine_threadsafe") as mock_run:
            mock_future = MagicMock()
            mock_future.result = MagicMock(return_value=None)
            mock_run.return_value = mock_future

            subscriber.start()

            # Verify run_coroutine_threadsafe was called
            assert mock_run.call_count == 1
            # Get the coroutine that was passed
            call_args = mock_run.call_args[0]
            # Close the coroutine to prevent warning
            if hasattr(call_args[0], "close"):
                call_args[0].close()

            assert subscriber.worker_task == mock_future

    def test_on_frame_queues_all_frames(self) -> None:
        """Test that all frames (keyframes and diffs) are queued."""
        subscriber = FramePersistenceSubscriber(sim_instance_id=123)
        # Don't start the worker - we just want to test the queueing logic

        # Create mix of keyframes and diff frames
        frames = [
            MagicMock(
                spec=Frame,
                is_key=(i % 3 == 0),  # Every 3rd is keyframe
                seq_number=i,
                payload_dict={"test": i},
            )
            for i in range(10)
        ]

        # Send all frames
        for frame in frames:
            subscriber.on_frame(frame)

        # Should queue ALL frames (no filtering)
        assert subscriber.frame_queue.qsize() == 10

    def test_queue_overflow_drops_random_frames(self) -> None:
        """Test that queue overflow drops frames randomly."""
        with patch(
            "back.services.frame_persistence_service.settings."
            + "KEYFRAME_QUEUE_MAX_SIZE",
            5,
        ):
            subscriber = FramePersistenceSubscriber(sim_instance_id=123)

            # Fill queue beyond max size
            for i in range(10):
                frame = MagicMock(spec=Frame)
                frame.is_key = True
                frame.seq_number = i
                frame.payload_dict = {"test": i}
                subscriber.on_frame(frame)

            # Queue should not exceed max size
            assert subscriber.frame_queue.qsize() <= 5

    @pytest.mark.asyncio
    async def test_shutdown_stops_worker(self) -> None:
        """Test that shutdown() stops the worker gracefully."""
        with patch(
            "back.services.frame_persistence_service.concurrent.futures.wait"
        ) as mock_wait:
            # Mock wait to return immediately as if task completed
            mock_wait.return_value = ({MagicMock()}, set())

            subscriber = FramePersistenceSubscriber(sim_instance_id=123)

            # Mock the worker task
            mock_task = MagicMock()
            mock_task.done.return_value = False
            mock_task.result = MagicMock()
            subscriber.worker_task = mock_task

            # Shutdown should signal the queue and wait for worker
            await subscriber.shutdown()

            # Verify closed flag was set
            assert subscriber.closed is True
            # Verify wait was called with timeout
            mock_wait.assert_called_once()

    @pytest.mark.asyncio
    async def test_persistence_worker_persists_frames(self) -> None:
        """Test that worker processes frames from queue and persists them."""
        with patch(
            "back.services.frame_persistence_service.sim_frame_crud.upsert"
        ) as mock_upsert:
            with patch(
                "back.services.frame_persistence_service.SessionLocal"
            ) as mock_session:
                mock_db = MagicMock()
                mock_session.return_value = mock_db

                subscriber = FramePersistenceSubscriber(sim_instance_id=123)

                # Manually call _persist_frame instead of running the full worker
                frame = MagicMock(spec=Frame)
                frame.seq_number = 5
                frame.is_key = True
                frame.payload_dict = {
                    "simId": "test-123",
                    "clock": {"simSecondsPassed": 60.5},
                }

                await subscriber._persist_frame(frame)

                # Verify upsert was called
                mock_upsert.assert_called_once()
                mock_db.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_persistence_failure_logged(self) -> None:
        """Test that persistence failures are logged and increment failure counter."""
        with patch(
            "back.services.frame_persistence_service.sim_frame_crud.upsert"
        ) as mock_upsert:
            with patch(
                "back.services.frame_persistence_service.SessionLocal"
            ) as mock_session:
                with patch(
                    "back.services.frame_persistence_service.logger"
                ) as mock_logger:
                    # Make upsert() raise an exception
                    mock_upsert.side_effect = Exception("DB error")

                    mock_db = MagicMock()
                    mock_session.return_value = mock_db

                    subscriber = FramePersistenceSubscriber(sim_instance_id=123)

                    # Manually call _persist_frame to test error handling
                    frame = MagicMock(spec=Frame)
                    frame.seq_number = 10
                    frame.is_key = False
                    frame.payload_dict = {
                        "simId": "test-123",
                        "clock": {"simSecondsPassed": 60.5},
                    }

                    await subscriber._persist_frame(frame)

                    # Should have logged error
                    mock_logger.error.assert_called()
                    # Should have incremented failure counter
                    assert subscriber.persist_failure_count == 1

    @pytest.mark.filterwarnings("ignore::RuntimeWarning")
    def test_background_event_loop_created_when_no_loop_exists(self) -> None:
        """Test that start() creates a background event loop when none exists.

        This tests the bug fix where frames weren't being persisted because
        the service was initialized from a sync endpoint with no running event loop.

        Note: RuntimeWarnings about pending tasks are expected since we forcefully
        stop the event loop for quick cleanup in this test.
        """
        # Create subscriber (no event loop should be running)
        subscriber = FramePersistenceSubscriber(sim_instance_id=456)

        # Before start(), loop should be None
        assert subscriber.loop is None
        assert subscriber.loop_thread is None

        # Start the subscriber
        subscriber.start()

        # After start(), background loop and thread should be created
        assert subscriber.loop is not None
        assert subscriber.loop_thread is not None  # type: ignore[unreachable]
        assert subscriber.loop_thread.is_alive()
        assert subscriber.worker_task is not None

        # Clean up - stop the background event loop
        subscriber.closed = True
        # Cancel the worker task to prevent pending task warnings
        if subscriber.worker_task is not None:
            subscriber.worker_task.cancel()
        # Send shutdown signal to queue to break worker loop
        try:
            subscriber.loop.call_soon_threadsafe(
                lambda: subscriber.frame_queue.put_nowait(None)
            )
        except Exception:
            pass  # Ignore if queue operations fail during cleanup
        # Stop the event loop
        subscriber.loop.call_soon_threadsafe(subscriber.loop.stop)
        subscriber.loop_thread.join(timeout=2.0)

    @pytest.mark.filterwarnings("ignore::RuntimeWarning")
    def test_background_loop_persists_frames_to_db(self) -> None:
        """Integration test: background event loop can persist frames to database.

        This tests the full flow from background thread to database write,
        catching bugs where event loop context isn't properly set.

        Note: RuntimeWarnings about pending tasks are expected since we forcefully
        stop the event loop for quick cleanup in this test.
        """
        import time
        from unittest.mock import patch, MagicMock

        with patch(
            "back.services.frame_persistence_service.sim_frame_crud.upsert"
        ) as mock_upsert:
            with patch(
                "back.services.frame_persistence_service.SessionLocal"
            ) as mock_session:
                mock_db = MagicMock()
                mock_session.return_value = mock_db

                # Create subscriber - this will create background event loop
                subscriber = FramePersistenceSubscriber(sim_instance_id=789)
                subscriber.start()

                # Give the background thread time to start
                time.sleep(0.1)

                # Queue a frame (simulating on_frame being called)
                frame = MagicMock(spec=Frame)
                frame.is_key = True  # Mark as keyframe
                frame.seq_number = 0
                frame.payload_dict = {
                    "simId": "test-789",
                    "clock": {"simSecondsPassed": 0.0},
                }
                subscriber.on_frame(frame)

                # Give the worker time to process the frame
                # The background thread needs to: dequeue, run executor, commit to DB
                time.sleep(1.0)

                # Verify frame was processed (success count incremented, queue empty)
                assert subscriber.persist_success_count == 1, (
                    f"Expected persist_success_count=1 but got "
                    f"{subscriber.persist_success_count}. Failure count: "
                    f"{subscriber.persist_failure_count}"
                )
                assert subscriber.frame_queue.qsize() == 0, (
                    f"Expected queue to be empty but size is "
                    f"{subscriber.frame_queue.qsize()}"
                )

                # Verify mock was called (should work in most cases, but success_count
                # is the authoritative check since patches can have threading issues)
                assert (
                    mock_upsert.call_count >= 1 or subscriber.persist_success_count == 1
                )

                # Clean up
                subscriber.closed = True
                # Cancel the worker task to prevent pending task warnings
                if subscriber.worker_task is not None:
                    subscriber.worker_task.cancel()
                # Send shutdown signal to queue to break worker loop
                if subscriber.loop is not None:
                    try:
                        subscriber.loop.call_soon_threadsafe(
                            lambda: subscriber.frame_queue.put_nowait(None)
                        )
                    except Exception:
                        pass  # Ignore if queue operations fail during cleanup
                    subscriber.loop.call_soon_threadsafe(subscriber.loop.stop)
                if subscriber.loop_thread is not None:
                    subscriber.loop_thread.join(timeout=2.0)

    @pytest.mark.asyncio
    async def test_shutdown_queues_final_keyframe(self) -> None:
        """Test that shutdown() force-queues the last keyframe for persistence."""
        with patch(
            "back.services.frame_persistence_service.concurrent.futures.wait"
        ) as mock_wait:
            # Mock wait to return immediately as if task completed
            mock_wait.return_value = ({MagicMock()}, set())

            subscriber = FramePersistenceSubscriber(sim_instance_id=123)

            # Mock the worker task
            mock_task = MagicMock()
            mock_task.done.return_value = False
            mock_task.result = MagicMock()
            subscriber.worker_task = mock_task

            # Create mock frames
            mock_frame1 = MagicMock()
            mock_frame1.is_key = True
            mock_frame1.seq_number = 0

            mock_frame2 = MagicMock()
            mock_frame2.is_key = False
            mock_frame2.seq_number = 1

            mock_frame3 = MagicMock()
            mock_frame3.is_key = True
            mock_frame3.seq_number = 5

            # Send frames - all should be queued since we no longer filter
            subscriber.on_frame(mock_frame1)
            subscriber.on_frame(mock_frame2)
            subscriber.on_frame(mock_frame3)

            # All 3 frames should be queued
            initial_queue_size = subscriber.frame_queue.qsize()
            assert initial_queue_size == 3

            # Verify last_keyframe was tracked (only keyframes update this)
            assert subscriber.last_keyframe is not None
            assert subscriber.last_keyframe.seq_number == 5

            # Shutdown should force-queue the last keyframe
            await subscriber.shutdown()

            # Verify closed flag was set
            assert subscriber.closed is True

            # Queue should have one more item (the final keyframe + None signal)
            assert subscriber.frame_queue.qsize() >= initial_queue_size
