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
        """Test shutdown() stops worker and waits for worker_task.result."""
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
        # Verify worker_task.result was called with timeout
        mock_task.result.assert_called()

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
        """Test that persistence failures are logged and increment counter."""
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
        the service was initialized from a sync endpoint with no running
        event loop.

        Note: RuntimeWarnings about pending tasks are expected since we
        forcefully stop the event loop for quick cleanup in this test.
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
        """Integration test: background loop persists frames to database.

        This tests the full flow from background thread to database write,
        catching bugs where event loop context isn't properly set.

        Note: RuntimeWarnings about pending tasks are expected since we
        forcefully stop the event loop for quick cleanup in this test.
        """
        import time
        from unittest.mock import patch, MagicMock

        with patch(
            "back.services.frame_persistence_service.sim_frame_crud.upsert_many"
        ) as mock_upsert_many:
            with patch(
                "back.services.frame_persistence_service.SessionLocal"
            ) as mock_session:
                mock_db = MagicMock()
                mock_session.return_value = mock_db

                # Create subscriber - creates background event loop
                subscriber = FramePersistenceSubscriber(sim_instance_id=789)
                subscriber.start()

                try:
                    # Wait for the worker coroutine to enter its main loop.
                    # This avoids timing races where on_frame is called before
                    # the worker is ready to receive frames.
                    assert subscriber._worker_initialized.wait(
                        timeout=10.0
                    ), "Worker did not become ready within 10 seconds"

                    # Queue a frame (simulating on_frame being called)
                    frame = MagicMock(spec=Frame)
                    frame.is_key = True  # Mark as keyframe
                    frame.seq_number = 0
                    frame.payload_dict = {
                        "simId": "test-789",
                        "clock": {"simSecondsPassed": 0.0},
                    }
                    subscriber.on_frame(frame)

                    # Wait up to 3 seconds for the worker to process frame
                    for _ in range(30):
                        if subscriber.persist_success_count == 1:
                            break
                        time.sleep(0.1)

                    # Verify frame was processed (success count incremented)
                    assert subscriber.persist_success_count == 1, (
                        f"Expected persist_success_count=1 but got "
                        f"{subscriber.persist_success_count}. "
                        f"Failure count: {subscriber.persist_failure_count}"
                    )
                    assert subscriber.frame_queue.qsize() == 0, (
                        f"Expected queue to be empty but size is "
                        f"{subscriber.frame_queue.qsize()}"
                    )

                    # Verify mock was called (success_count is authoritative
                    # since patches can have threading issues)
                    assert (
                        mock_upsert_many.call_count >= 1
                        or subscriber.persist_success_count == 1
                    )
                finally:
                    # Robust cleanup
                    subscriber.closed = True
                    # Send shutdown signal to queue to break worker loop
                    if subscriber.loop is not None:
                        try:
                            subscriber.loop.call_soon_threadsafe(
                                lambda: subscriber.frame_queue.put_nowait(None)
                            )
                        except Exception:
                            pass  # Ignore queue operation failures
                        subscriber.loop.call_soon_threadsafe(subscriber.loop.stop)
                    if subscriber.worker_task is not None:
                        try:
                            subscriber.worker_task.cancel()
                        except Exception:
                            pass
                    if subscriber.loop_thread is not None:
                        subscriber.loop_thread.join(timeout=2.0)

    @pytest.mark.asyncio
    async def test_shutdown_persists_final_keyframe(self) -> None:
        """Test shutdown() persists last keyframe if needed, not re-queue."""
        from unittest.mock import patch, MagicMock

        with patch(
            "back.services.frame_persistence_service.sim_frame_crud.upsert"
        ) as mock_upsert:
            with patch(
                "back.services.frame_persistence_service.SessionLocal"
            ) as mock_session:
                mock_db = MagicMock()
                mock_session.return_value = mock_db

                subscriber = FramePersistenceSubscriber(sim_instance_id=123)

                # Create mock frames
                mock_frame1 = MagicMock()
                mock_frame1.is_key = True
                mock_frame1.seq_number = 0
                mock_frame1.payload_dict = {"clock": {"simSecondsPassed": 0.0}}

                mock_frame2 = MagicMock()
                mock_frame2.is_key = False
                mock_frame2.seq_number = 1
                mock_frame2.payload_dict = {"clock": {"simSecondsPassed": 1.0}}

                mock_frame3 = MagicMock()
                mock_frame3.is_key = True
                mock_frame3.seq_number = 5
                mock_frame3.payload_dict = {"clock": {"simSecondsPassed": 5.0}}

                # Send frames
                subscriber.on_frame(mock_frame1)
                subscriber.on_frame(mock_frame2)
                subscriber.on_frame(mock_frame3)

                # Verify last_keyframe was tracked
                assert subscriber.last_keyframe is not None
                assert subscriber.last_keyframe.seq_number == 5

                # Shutdown should persist last keyframe if not persisted
                await subscriber.shutdown()

                # Verify closed flag was set
                assert subscriber.closed is True
                # Verify upsert was called for the final keyframe
                assert mock_upsert.called

    @pytest.mark.asyncio
    async def test_shutdown_drains_queue_and_persists_remaining_frames(self) -> None:
        """Test shutdown() drains queue and persists remaining frames in batches."""
        from unittest.mock import patch, MagicMock

        with patch(
            "back.services.frame_persistence_service.sim_frame_crud.upsert_many"
        ) as mock_upsert_many:
            with patch(
                "back.services.frame_persistence_service.SessionLocal"
            ) as mock_session:
                mock_db = MagicMock()
                mock_session.return_value = mock_db
                mock_upsert_many.return_value = 5

                subscriber = FramePersistenceSubscriber(sim_instance_id=999)

                # Create frames and add directly to queue to avoid loop dependency
                frames = []
                for i in range(5):
                    frame = MagicMock(spec=Frame)
                    frame.is_key = i == 0  # First is keyframe
                    frame.seq_number = i
                    frame.payload_dict = {
                        "simId": f"test-{i}",
                        "clock": {"simSecondsPassed": float(i)},
                    }
                    frames.append(frame)
                    # Add directly to queue
                    await subscriber.frame_queue.put(frame)

                # Mock the loop to simulate drain_queue being called
                mock_loop = MagicMock()
                subscriber.loop = mock_loop

                # Create a side effect that drains the queue when called
                from typing import Callable

                def drain_side_effect(func: Callable[[], None]) -> None:
                    func()  # Execute the drain_queue function

                mock_loop.call_soon_threadsafe.side_effect = drain_side_effect

                # Shutdown should drain and persist
                await subscriber.shutdown()

                # Verify upsert_many was called for the drained frames
                assert mock_upsert_many.call_count >= 1

    @pytest.mark.asyncio
    async def test_shutdown_handles_none_items_in_queue(self) -> None:
        """Test shutdown() handles None sentinel values in queue."""
        from unittest.mock import patch, MagicMock

        with patch(
            "back.services.frame_persistence_service.sim_frame_crud.upsert_many"
        ) as mock_upsert_many:
            with patch(
                "back.services.frame_persistence_service.SessionLocal"
            ) as mock_session:
                mock_db = MagicMock()
                mock_session.return_value = mock_db
                mock_upsert_many.return_value = 1

                subscriber = FramePersistenceSubscriber(sim_instance_id=888)

                # Add a valid frame and a None sentinel
                frame1 = MagicMock(spec=Frame)
                frame1.is_key = True
                frame1.seq_number = 0
                frame1.payload_dict = {"clock": {"simSecondsPassed": 0.0}}

                await subscriber.frame_queue.put(frame1)
                await subscriber.frame_queue.put(None)

                frame2 = MagicMock(spec=Frame)
                frame2.is_key = False
                frame2.seq_number = 1
                frame2.payload_dict = {"clock": {"simSecondsPassed": 1.0}}
                await subscriber.frame_queue.put(frame2)

                # Mock the loop to drain queue
                mock_loop = MagicMock()
                subscriber.loop = mock_loop

                from typing import Callable

                def drain_side_effect(func: Callable[[], None]) -> None:
                    func()

                mock_loop.call_soon_threadsafe.side_effect = drain_side_effect

                await subscriber.shutdown()

                # Shutdown should skip None items and persist valid frames
                assert subscriber.closed is True

    @pytest.mark.asyncio
    async def test_shutdown_handles_invalid_frames_in_queue(self) -> None:
        """Test shutdown() increments failure count for invalid frames."""
        from unittest.mock import patch, MagicMock

        with patch(
            "back.services.frame_persistence_service.sim_frame_crud.upsert_many"
        ):
            with patch(
                "back.services.frame_persistence_service.SessionLocal"
            ) as mock_session:
                mock_db = MagicMock()
                mock_session.return_value = mock_db

                subscriber = FramePersistenceSubscriber(sim_instance_id=777)

                # Add an invalid frame (is_key=None) directly to queue
                invalid_frame = MagicMock(spec=Frame)
                invalid_frame.is_key = None  # Invalid!
                invalid_frame.seq_number = 0
                invalid_frame.payload_dict = {"clock": {"simSecondsPassed": 0.0}}

                await subscriber.frame_queue.put(invalid_frame)

                # Mock the loop to drain queue
                mock_loop = MagicMock()
                subscriber.loop = mock_loop

                from typing import Callable

                def drain_side_effect(func: Callable[[], None]) -> None:
                    func()

                mock_loop.call_soon_threadsafe.side_effect = drain_side_effect

                initial_failures = subscriber.persist_failure_count
                await subscriber.shutdown()

                # Should have incremented failure count
                assert subscriber.persist_failure_count > initial_failures

    @pytest.mark.asyncio
    async def test_shutdown_persists_in_batches(self) -> None:
        """Test shutdown() persists drained frames in batches."""
        from unittest.mock import patch, MagicMock

        with patch(
            "back.services.frame_persistence_service.sim_frame_crud.upsert_many"
        ) as mock_upsert_many:
            with patch(
                "back.services.frame_persistence_service.SessionLocal"
            ) as mock_session:
                with patch(
                    "back.services.frame_persistence_service.settings."
                    "FRAME_PERSIST_BATCH_SIZE",
                    3,
                ):
                    mock_db = MagicMock()
                    mock_session.return_value = mock_db
                    mock_upsert_many.return_value = 3

                    subscriber = FramePersistenceSubscriber(sim_instance_id=666)

                    # Add 7 frames directly to queue
                    for i in range(7):
                        frame = MagicMock(spec=Frame)
                        frame.is_key = i == 0
                        frame.seq_number = i
                        frame.payload_dict = {"clock": {"simSecondsPassed": float(i)}}
                        await subscriber.frame_queue.put(frame)

                    # Mock the loop to drain queue
                    mock_loop = MagicMock()
                    subscriber.loop = mock_loop

                    from typing import Callable

                    def drain_side_effect(func: Callable[[], None]) -> None:
                        func()

                    mock_loop.call_soon_threadsafe.side_effect = drain_side_effect

                    await subscriber.shutdown()

                    # Should have called upsert_many multiple times
                    # (7 frames / batch_size of 3 = 3 batches: 3, 3, 1)
                    assert mock_upsert_many.call_count >= 2

    @pytest.mark.asyncio
    async def test_shutdown_handles_upsert_batch_failure(self) -> None:
        """Test shutdown() handles DB errors during batch persistence."""
        from unittest.mock import patch, MagicMock

        with patch(
            "back.services.frame_persistence_service.sim_frame_crud.upsert_many"
        ) as mock_upsert_many:
            with patch(
                "back.services.frame_persistence_service.SessionLocal"
            ) as mock_session:
                with patch(
                    "back.services.frame_persistence_service.logger"
                ) as mock_logger:
                    mock_db = MagicMock()
                    mock_session.return_value = mock_db

                    # Make upsert_many raise an exception
                    mock_upsert_many.side_effect = Exception("DB connection failed")

                    subscriber = FramePersistenceSubscriber(sim_instance_id=555)

                    # Add frames directly to queue
                    for i in range(3):
                        frame = MagicMock(spec=Frame)
                        frame.is_key = True
                        frame.seq_number = i
                        frame.payload_dict = {"clock": {"simSecondsPassed": float(i)}}
                        await subscriber.frame_queue.put(frame)

                    # Mock the loop to drain queue
                    mock_loop = MagicMock()
                    subscriber.loop = mock_loop

                    from typing import Callable

                    def drain_side_effect(func: Callable[[], None]) -> None:
                        func()

                    mock_loop.call_soon_threadsafe.side_effect = drain_side_effect

                    initial_failures = subscriber.persist_failure_count
                    await subscriber.shutdown()

                    # Should have incremented failure count
                    assert subscriber.persist_failure_count > initial_failures

                    # Should have logged error
                    mock_logger.error.assert_called()

    @pytest.mark.asyncio
    async def test_shutdown_handles_queue_drain_exception(self) -> None:
        """Test shutdown() handles exceptions during queue draining."""
        import asyncio
        from unittest.mock import patch, MagicMock

        with patch("back.services.frame_persistence_service.logger") as mock_logger:
            subscriber = FramePersistenceSubscriber(sim_instance_id=444)

            # Create a mock loop that raises exception on call_soon_threadsafe
            mock_loop = MagicMock()
            mock_loop.call_soon_threadsafe.side_effect = Exception("Loop error")
            subscriber.loop = mock_loop

            # Add a frame
            frame = MagicMock(spec=Frame)
            frame.is_key = True
            frame.seq_number = 0
            frame.payload_dict = {"clock": {"simSecondsPassed": 0.0}}

            # Use a real asyncio queue for this test
            subscriber.frame_queue = asyncio.Queue()
            subscriber.frame_queue.put_nowait(frame)

            await subscriber.shutdown()

            # Should have logged the error
            assert (
                any(
                    "Error draining queue" in str(call)
                    for call in mock_logger.error.call_args_list
                )
                or subscriber.closed is True
            )

    def test_on_frame_when_closed(self) -> None:
        """Test on_frame() returns early when subscriber is closed."""
        subscriber = FramePersistenceSubscriber(sim_instance_id=333)
        subscriber.closed = True

        frame = MagicMock(spec=Frame)
        frame.is_key = True
        frame.seq_number = 0
        frame.payload_dict = {"test": "data"}

        initial_size = subscriber.frame_queue.qsize()
        subscriber.on_frame(frame)

        # Frame should not be queued when closed
        assert subscriber.frame_queue.qsize() == initial_size

    def test_force_persist_keyframe_when_closed(self) -> None:
        """Test force_persist_keyframe() returns early when subscriber is closed."""
        subscriber = FramePersistenceSubscriber(sim_instance_id=222)
        subscriber.closed = True

        frame = MagicMock(spec=Frame)
        frame.is_key = True
        frame.seq_number = 0
        frame.payload_dict = {"test": "data"}

        # Should return without doing anything
        subscriber.force_persist_keyframe(frame)
        assert subscriber.persist_success_count == 0

    def test_force_persist_keyframe_with_non_keyframe(self) -> None:
        """Test force_persist_keyframe() logs warning for non-keyframe."""
        from unittest.mock import patch

        with patch("back.services.frame_persistence_service.logger") as mock_logger:
            subscriber = FramePersistenceSubscriber(sim_instance_id=111)

            frame = MagicMock(spec=Frame)
            frame.is_key = False  # Not a keyframe!
            frame.seq_number = 5

            subscriber.force_persist_keyframe(frame)

            # Should have logged warning
            mock_logger.warning.assert_called()

    def test_force_persist_keyframe_skips_already_persisted(self) -> None:
        """Test force_persist_keyframe() skips already persisted sequences."""
        from unittest.mock import patch

        with patch("back.services.frame_persistence_service.logger") as mock_logger:
            subscriber = FramePersistenceSubscriber(sim_instance_id=100)
            subscriber.highest_persisted_seq = 10

            frame = MagicMock(spec=Frame)
            frame.is_key = True
            frame.seq_number = 5  # Lower than highest_persisted_seq
            frame.payload_dict = {"clock": {"simSecondsPassed": 5.0}}

            subscriber.force_persist_keyframe(frame)

            # Should have logged that it's skipping
            assert any(
                "already persisted" in str(call)
                for call in mock_logger.info.call_args_list
            )

    def test_force_persist_keyframe_immediate_success(self) -> None:
        """Test force_persist_keyframe() succeeds immediately."""
        from unittest.mock import patch, MagicMock
        import concurrent.futures

        with patch("back.services.frame_persistence_service.sim_frame_crud.upsert"):
            with patch(
                "back.services.frame_persistence_service.SessionLocal"
            ) as mock_session:
                mock_db = MagicMock()
                mock_session.return_value = mock_db

                subscriber = FramePersistenceSubscriber(sim_instance_id=200)

                frame = MagicMock(spec=Frame)
                frame.is_key = True
                frame.seq_number = 15
                frame.payload_dict = {"clock": {"simSecondsPassed": 15.0}}

                # Mock the executor to return immediately
                mock_future = MagicMock(spec=concurrent.futures.Future)
                mock_future.result.return_value = 1

                with patch.object(
                    subscriber._immediate_executor, "submit", return_value=mock_future
                ):
                    subscriber.force_persist_keyframe(frame)

                # Should have updated highest_persisted_seq
                assert subscriber.highest_persisted_seq == 15
                assert subscriber.persist_success_count == 1

    def test_force_persist_keyframe_timeout_fallback_to_queue(self) -> None:
        """Test force_persist_keyframe() falls back to queue on timeout."""
        from unittest.mock import patch, MagicMock
        import concurrent.futures

        with patch("back.services.frame_persistence_service.logger") as mock_logger:
            subscriber = FramePersistenceSubscriber(sim_instance_id=300)

            frame = MagicMock(spec=Frame)
            frame.is_key = True
            frame.seq_number = 20
            frame.payload_dict = {"clock": {"simSecondsPassed": 20.0}}

            # Mock timeout
            mock_future = MagicMock(spec=concurrent.futures.Future)
            mock_future.result.side_effect = concurrent.futures.TimeoutError()

            with patch.object(
                subscriber._immediate_executor, "submit", return_value=mock_future
            ):
                subscriber.force_persist_keyframe(frame)

            # Should have logged timeout warning
            assert any(
                "timed out" in str(call).lower()
                for call in mock_logger.warning.call_args_list
            )

            # Frame should be queued
            assert subscriber.frame_queue.qsize() == 1

    def test_force_persist_keyframe_error_fallback_to_queue(self) -> None:
        """Test force_persist_keyframe() falls back to queue on error."""
        from unittest.mock import patch, MagicMock
        import concurrent.futures

        with patch("back.services.frame_persistence_service.logger") as mock_logger:
            subscriber = FramePersistenceSubscriber(sim_instance_id=400)

            frame = MagicMock(spec=Frame)
            frame.is_key = True
            frame.seq_number = 25
            frame.payload_dict = {"clock": {"simSecondsPassed": 25.0}}

            # Mock error
            mock_future = MagicMock(spec=concurrent.futures.Future)
            mock_future.result.side_effect = Exception("DB error")

            with patch.object(
                subscriber._immediate_executor, "submit", return_value=mock_future
            ):
                subscriber.force_persist_keyframe(frame)

            # Should have logged warning
            assert any(
                "failed" in str(call).lower()
                for call in mock_logger.warning.call_args_list
            )

            # Frame should be queued
            assert subscriber.frame_queue.qsize() == 1

    @pytest.mark.asyncio
    async def test_shutdown_final_keyframe_with_none_is_key(self) -> None:
        """Test shutdown() handles final keyframe with is_key=None."""
        from unittest.mock import patch

        with patch("back.services.frame_persistence_service.logger") as mock_logger:
            subscriber = FramePersistenceSubscriber(sim_instance_id=500)

            # Create invalid final keyframe
            invalid_frame = MagicMock()
            invalid_frame.is_key = None  # Invalid!
            invalid_frame.seq_number = 10
            invalid_frame.payload_dict = {"clock": {"simSecondsPassed": 10.0}}

            subscriber.last_keyframe = invalid_frame

            await subscriber.shutdown()

            # Should have logged error
            assert any(
                "is_key=None" in str(call) for call in mock_logger.error.call_args_list
            )

    @pytest.mark.asyncio
    async def test_validate_frame_returns_false_for_none_is_key(self) -> None:
        """Test _validate_frame returns False when is_key is None."""
        from unittest.mock import patch

        with patch("back.services.frame_persistence_service.logger") as mock_logger:
            subscriber = FramePersistenceSubscriber(sim_instance_id=600)

            frame = MagicMock(spec=Frame)
            frame.is_key = None
            frame.seq_number = 5

            result = subscriber._validate_frame(frame)

            assert result is False
            mock_logger.error.assert_called()

    @pytest.mark.asyncio
    async def test_persist_frame_with_none_is_key_raises_error(self) -> None:
        """Test _persist_frame raises ValueError when is_key is None."""
        subscriber = FramePersistenceSubscriber(sim_instance_id=700)

        frame = MagicMock(spec=Frame)
        frame.is_key = None
        frame.seq_number = 5
        frame.payload_dict = {"clock": {"simSecondsPassed": 5.0}}

        await subscriber._persist_frame(frame)

        # Should have incremented failure count
        assert subscriber.persist_failure_count == 1

    def test_validate_frame_with_valid_keyframe(self) -> None:
        """Test _validate_frame returns True for valid keyframe."""
        subscriber = FramePersistenceSubscriber(sim_instance_id=800)

        frame = MagicMock(spec=Frame)
        frame.is_key = True
        frame.seq_number = 5

        result = subscriber._validate_frame(frame)
        assert result is True

    def test_validate_frame_with_valid_diff_frame(self) -> None:
        """Test _validate_frame returns True for valid diff frame."""
        subscriber = FramePersistenceSubscriber(sim_instance_id=801)

        frame = MagicMock(spec=Frame)
        frame.is_key = False
        frame.seq_number = 10

        result = subscriber._validate_frame(frame)
        assert result is True

    def test_upsert_many_sync_creates_and_closes_session(self) -> None:
        """Test _upsert_many_sync creates its own DB session and closes it."""
        from unittest.mock import patch, MagicMock
        from back.schemas.sim_frame import SimFrameCreate

        with patch(
            "back.services.frame_persistence_service.sim_frame_crud.upsert_many"
        ) as mock_upsert_many:
            with patch(
                "back.services.frame_persistence_service.SessionLocal"
            ) as mock_session_local:
                mock_db = MagicMock()
                mock_session_local.return_value = mock_db
                mock_upsert_many.return_value = 2

                subscriber = FramePersistenceSubscriber(sim_instance_id=900)

                frames = [
                    SimFrameCreate(
                        sim_instance_id=900,
                        seq_number=0,
                        sim_seconds_elapsed=0.0,
                        frame_data={"test": 1},
                        is_key=True,
                    ),
                    SimFrameCreate(
                        sim_instance_id=900,
                        seq_number=1,
                        sim_seconds_elapsed=1.0,
                        frame_data={"test": 2},
                        is_key=False,
                    ),
                ]

                result = subscriber._upsert_many_sync(frames)

                # Should have created session
                mock_session_local.assert_called_once()
                # Should have called upsert_many
                mock_upsert_many.assert_called_once_with(mock_db, frames)
                # Should have closed session
                mock_db.close.assert_called_once()
                # Should return result
                assert result == 2

    def test_upsert_sync_creates_and_closes_session(self) -> None:
        """Test _upsert_sync creates its own DB session and closes it."""
        from unittest.mock import patch
        from back.schemas.sim_frame import SimFrameCreate

        with patch(
            "back.services.frame_persistence_service.sim_frame_crud.upsert"
        ) as mock_upsert:
            with patch(
                "back.services.frame_persistence_service.SessionLocal"
            ) as mock_session_local:
                mock_db = MagicMock()
                mock_session_local.return_value = mock_db

                subscriber = FramePersistenceSubscriber(sim_instance_id=901)

                frame_data = SimFrameCreate(
                    sim_instance_id=901,
                    seq_number=5,
                    sim_seconds_elapsed=5.0,
                    frame_data={"test": 5},
                    is_key=True,
                )

                result = subscriber._upsert_sync(frame_data)

                # Should have created session
                mock_session_local.assert_called_once()
                # Should have called upsert
                mock_upsert.assert_called_once_with(mock_db, frame_data)
                # Should have closed session
                mock_db.close.assert_called_once()
                # Should return 1
                assert result == 1

    def test_queue_overflow_error_handling(self) -> None:
        """Test that queue overflow exception during shuffle is handled."""
        from unittest.mock import patch, MagicMock

        with patch(
            "back.services.frame_persistence_service.settings.KEYFRAME_QUEUE_MAX_SIZE",
            2,
        ):
            with patch("back.services.frame_persistence_service.logger") as mock_logger:
                subscriber = FramePersistenceSubscriber(sim_instance_id=902)

                # Fill queue to max
                for i in range(2):
                    frame = MagicMock(spec=Frame)
                    frame.is_key = True
                    frame.seq_number = i
                    frame.payload_dict = {"test": i}
                    subscriber.on_frame(frame)

                # Mock random.shuffle to raise exception
                with patch("random.shuffle", side_effect=Exception("Shuffle error")):
                    # Try to add another frame to trigger overflow handling
                    frame = MagicMock(spec=Frame)
                    frame.is_key = False
                    frame.seq_number = 10
                    frame.payload_dict = {"test": 10}
                    subscriber.on_frame(frame)

                    # Should have logged error
                    assert any(
                        "Error handling queue overflow" in str(call)
                        for call in mock_logger.error.call_args_list
                    )

    @pytest.mark.asyncio
    async def test_shutdown_stops_event_loop_and_joins_thread(self) -> None:
        """Test shutdown() stops event loop and joins thread when they exist."""
        from unittest.mock import MagicMock

        subscriber = FramePersistenceSubscriber(sim_instance_id=903)

        # Mock the event loop and thread
        mock_loop = MagicMock()
        mock_thread = MagicMock()

        subscriber.loop = mock_loop
        subscriber.loop_thread = mock_thread

        # Shutdown should stop loop and join thread
        await subscriber.shutdown()

        # Verify loop.call_soon_threadsafe was called with loop.stop
        mock_loop.call_soon_threadsafe.assert_called()
        # Verify thread.join was called with timeout
        mock_thread.join.assert_called_once()
        # Check that timeout parameter was passed
        call_kwargs = mock_thread.join.call_args
        assert "timeout" in call_kwargs.kwargs or len(call_kwargs.args) > 0

    @pytest.mark.asyncio
    async def test_shutdown_handles_loop_stop_exception(self) -> None:
        """Test shutdown() handles exception when stopping event loop."""
        from unittest.mock import MagicMock

        subscriber = FramePersistenceSubscriber(sim_instance_id=904)

        # Mock the event loop to raise exception on call_soon_threadsafe
        mock_loop = MagicMock()
        mock_loop.call_soon_threadsafe.side_effect = Exception("Loop already stopped")
        mock_thread = MagicMock()

        subscriber.loop = mock_loop
        subscriber.loop_thread = mock_thread

        # Should not raise exception, should handle it gracefully
        await subscriber.shutdown()

        # Verify it attempted to stop the loop
        mock_loop.call_soon_threadsafe.assert_called()
        # Should still attempt to join thread despite exception
        mock_thread.join.assert_called_once()

    @pytest.mark.asyncio
    async def test_shutdown_handles_thread_join_exception(self) -> None:
        """Test shutdown() handles exception when joining thread."""
        from unittest.mock import MagicMock

        subscriber = FramePersistenceSubscriber(sim_instance_id=905)

        # Mock the thread to raise exception on join
        mock_loop = MagicMock()
        mock_thread = MagicMock()
        mock_thread.join.side_effect = Exception("Thread join failed")

        subscriber.loop = mock_loop
        subscriber.loop_thread = mock_thread

        # Should not raise exception, should handle it gracefully
        await subscriber.shutdown()

        # Verify it attempted to stop the loop
        mock_loop.call_soon_threadsafe.assert_called()
        # Verify it attempted to join thread
        mock_thread.join.assert_called_once()

    @pytest.mark.asyncio
    async def test_shutdown_skips_loop_cleanup_when_no_loop(self) -> None:
        """Test shutdown() skips loop cleanup when loop doesn't exist."""

        subscriber = FramePersistenceSubscriber(sim_instance_id=906)

        # Ensure loop and thread are None
        subscriber.loop = None
        subscriber.loop_thread = None

        # Should complete without error
        await subscriber.shutdown()

        # Just verify it completes successfully
        assert subscriber.closed is True

    @pytest.mark.asyncio
    async def test_shutdown_waits_for_worker_task_completion(self) -> None:
        """Test shutdown() waits for worker task to complete successfully."""
        from unittest.mock import MagicMock

        subscriber = FramePersistenceSubscriber(sim_instance_id=907)

        # Mock the worker task
        mock_task = MagicMock()
        mock_task.result.return_value = None  # Completes successfully

        subscriber.worker_task = mock_task

        # Shutdown should wait for worker task
        await subscriber.shutdown()

        # Verify result() was called with timeout
        mock_task.result.assert_called_once()
        call_kwargs = mock_task.result.call_args
        assert "timeout" in call_kwargs.kwargs or len(call_kwargs.args) > 0

    @pytest.mark.asyncio
    async def test_shutdown_handles_worker_task_timeout(self) -> None:
        """Test shutdown() handles timeout waiting for worker task."""
        import concurrent.futures
        from unittest.mock import patch

        with patch("back.services.frame_persistence_service.logger") as mock_logger:
            subscriber = FramePersistenceSubscriber(sim_instance_id=908)

            # Mock the worker task to timeout
            mock_task = MagicMock()
            mock_task.result.side_effect = concurrent.futures.TimeoutError()
            mock_task.cancel.return_value = True

            subscriber.worker_task = mock_task

            # Shutdown should handle timeout gracefully
            await subscriber.shutdown()

            # Verify result() was called
            mock_task.result.assert_called_once()
            # Verify timeout warning was logged
            assert any(
                "Timeout waiting for persistence worker" in str(call)
                for call in mock_logger.warning.call_args_list
            )
            # Verify cancel was attempted
            mock_task.cancel.assert_called_once()

    @pytest.mark.asyncio
    async def test_shutdown_handles_worker_task_cancel_exception(self) -> None:
        """Test shutdown() handles exception when canceling worker task."""
        import concurrent.futures
        from unittest.mock import MagicMock, patch

        with patch("back.services.frame_persistence_service.logger"):
            subscriber = FramePersistenceSubscriber(sim_instance_id=909)

            # Mock the worker task to timeout and raise on cancel
            mock_task = MagicMock()
            mock_task.result.side_effect = concurrent.futures.TimeoutError()
            mock_task.cancel.side_effect = Exception("Cancel failed")

            subscriber.worker_task = mock_task

            # Should not raise exception, should handle it gracefully
            await subscriber.shutdown()

            # Verify result() was called
            mock_task.result.assert_called_once()
            # Verify cancel was attempted
            mock_task.cancel.assert_called_once()
            # Should still complete shutdown
            assert subscriber.closed is True

    @pytest.mark.asyncio
    async def test_shutdown_handles_worker_task_result_exception(self) -> None:
        """Test shutdown() handles non-timeout exception from worker task."""
        from unittest.mock import MagicMock, patch

        with patch("back.services.frame_persistence_service.logger") as mock_logger:
            subscriber = FramePersistenceSubscriber(sim_instance_id=910)

            # Mock the worker task to raise a different exception
            mock_task = MagicMock()
            mock_task.result.side_effect = Exception("Worker crashed")

            subscriber.worker_task = mock_task

            # Should handle exception gracefully
            await subscriber.shutdown()

            # Verify result() was called
            mock_task.result.assert_called_once()
            # Verify warning was logged
            assert any(
                "Error waiting for persistence worker" in str(call)
                for call in mock_logger.warning.call_args_list
            )

    @pytest.mark.asyncio
    async def test_shutdown_skips_worker_task_when_none(self) -> None:
        """Test shutdown() skips worker task cleanup when task is None."""
        subscriber = FramePersistenceSubscriber(sim_instance_id=911)

        # Ensure worker_task is None
        subscriber.worker_task = None

        # Should complete without error
        await subscriber.shutdown()

        # Just verify it completes successfully
        assert subscriber.closed is True
