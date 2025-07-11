"""Tests for background task implementations in cc module.

Comprehensive test coverage for async background tasks including:
- Pattern Reference: async_handler.py v2025-07-08 (async testing patterns)
- Pattern Reference: error_handling.py v2025-07-08 v2.1.0 (error handling patterns)
- Pattern Reference: service.py v2025-07-08 (service layer patterns)

Tests all background task scenarios including success, error handling,
database connection failures, and scheduled task lifecycle.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from typing import Any
from unittest.mock import patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.backend.cc import background, mem0_service


@pytest.mark.asyncio
class TestPeriodicCleanup:
    """Test periodic cleanup task functionality."""

    async def test_periodic_cleanup_success(self, db_session: AsyncSession) -> None:
        """Test successful periodic cleanup execution."""
        # Mock mem0_service.run_cleanup to return expected result
        mock_cleanup_result = {
            "status": "completed",
            "deleted": 5,
            "batch_size": 100,
            "expired_before": 5,
            "total_before": 20,
            "remaining_after": 15,
            "timestamp": datetime.now(UTC).isoformat(),
            "execution_time_ms": 123.45,
        }

        with (
            patch.object(mem0_service, "run_cleanup", return_value=mock_cleanup_result) as mock_cleanup,
            patch("src.backend.cc.background.get_async_db") as mock_get_db,
        ):
            # Mock the async generator to yield our test session
            async def mock_async_generator() -> AsyncIterator[AsyncSession]:
                yield db_session

            mock_get_db.return_value = mock_async_generator()

            # Execute the cleanup
            result = await background.periodic_cleanup()

            # Verify the result includes timing information
            assert result["status"] == "completed"
            assert result["deleted"] == 5
            assert "duration_seconds" in result
            assert "started_at" in result
            assert "completed_at" in result
            assert isinstance(result["duration_seconds"], float)

            # Verify cleanup was called with correct session
            mock_cleanup.assert_called_once_with(db_session)

    async def test_periodic_cleanup_mem0_service_error(self, db_session: AsyncSession) -> None:
        """Test periodic cleanup when mem0_service raises an exception."""
        # Mock mem0_service.run_cleanup to raise an exception
        test_exception = ValueError("Test cleanup error")

        with (
            patch.object(mem0_service, "run_cleanup", side_effect=test_exception) as mock_cleanup,
            patch("src.backend.cc.background.get_async_db") as mock_get_db,
        ):
            # Mock the async generator to yield our test session
            async def mock_async_generator() -> AsyncIterator[AsyncSession]:
                yield db_session

            mock_get_db.return_value = mock_async_generator()

            # Execute the cleanup
            result = await background.periodic_cleanup()

            # Verify error result structure
            assert result["status"] == "error"
            assert result["error"] == "Test cleanup error"
            assert result["error_type"] == "ValueError"
            assert "started_at" in result
            assert "failed_at" in result
            assert "duration_seconds" in result
            assert isinstance(result["duration_seconds"], float)

            # Verify cleanup was called
            mock_cleanup.assert_called_once_with(db_session)

    async def test_periodic_cleanup_database_connection_error(self) -> None:
        """Test periodic cleanup when database connection fails."""
        # Mock get_async_db to raise an exception
        test_exception = ConnectionError("Database connection failed")

        with patch("src.backend.cc.background.get_async_db", side_effect=test_exception):
            # Execute the cleanup
            result = await background.periodic_cleanup()

            # Verify error result structure
            assert result["status"] == "error"
            assert "Database connection failed" in result["error"]
            assert result["error_type"] == "ConnectionError"
            assert "started_at" in result
            assert "failed_at" in result
            assert "duration_seconds" in result
            assert isinstance(result["duration_seconds"], float)

    async def test_periodic_cleanup_timing_accuracy(self, db_session: AsyncSession) -> None:
        """Test that cleanup timing measurements are accurate."""

        # Mock mem0_service.run_cleanup with a delay to test timing
        async def delayed_cleanup(db: AsyncSession) -> dict[str, Any]:
            await asyncio.sleep(0.1)  # 100ms delay
            return {"status": "completed", "deleted": 0}

        with (
            patch.object(mem0_service, "run_cleanup", side_effect=delayed_cleanup),
            patch("src.backend.cc.background.get_async_db") as mock_get_db,
        ):
            # Mock the async generator to yield our test session
            async def mock_async_generator() -> AsyncIterator[AsyncSession]:
                yield db_session

            mock_get_db.return_value = mock_async_generator()

            # Execute the cleanup
            result = await background.periodic_cleanup()

            # Verify timing is reasonable (should be at least 100ms)
            assert result["duration_seconds"] >= 0.1
            assert result["duration_seconds"] < 1.0  # Should complete quickly

            # Verify datetime parsing
            start_time = datetime.fromisoformat(result["started_at"])
            end_time = datetime.fromisoformat(result["completed_at"])
            assert end_time > start_time

    async def test_periodic_cleanup_fallback_return_path(self) -> None:
        """Test the fallback return path (edge case that shouldn't normally occur)."""

        # Mock get_async_db to return an empty async generator
        async def empty_async_generator() -> AsyncIterator[AsyncSession]:
            # This generator yields nothing, testing the fallback path
            return
            yield  # This line will never be reached  # type: ignore[unreachable]

        with patch("src.backend.cc.background.get_async_db", return_value=empty_async_generator()):
            # Execute the cleanup
            result = await background.periodic_cleanup()

            # Verify fallback error result
            assert result["status"] == "error"
            assert result["error"] == "No database connection available"
            assert result["error_type"] == "ConnectionError"
            assert "started_at" in result
            assert "failed_at" in result
            assert "duration_seconds" in result


@pytest.mark.asyncio
class TestGetScratchStats:
    """Test background statistics collection functionality."""

    async def test_get_scratch_stats_success(self, db_session: AsyncSession) -> None:
        """Test successful stats collection execution."""
        # Mock mem0_service.get_stats to return expected result
        mock_stats_result = {
            "total_notes": 25,
            "active_notes": 20,
            "expired_notes": 5,
            "timestamp": datetime.now(UTC).isoformat(),
            "ttl_settings": {
                "default_ttl_days": 7,
                "auto_cleanup_enabled": True,
                "cleanup_batch_size": 100,
            },
        }

        with (
            patch.object(mem0_service, "get_stats", return_value=mock_stats_result) as mock_stats,
            patch("src.backend.cc.background.get_async_db") as mock_get_db,
        ):
            # Mock the async generator to yield our test session
            async def mock_async_generator() -> AsyncIterator[AsyncSession]:
                yield db_session

            mock_get_db.return_value = mock_async_generator()

            # Execute stats collection
            result = await background.get_scratch_stats()

            # Verify the result includes timing information
            assert result["total_notes"] == 25
            assert result["active_notes"] == 20
            assert result["expired_notes"] == 5
            assert "collection_duration_seconds" in result
            assert "collection_started_at" in result
            assert isinstance(result["collection_duration_seconds"], float)

            # Verify stats was called with correct session
            mock_stats.assert_called_once_with(db_session)

    async def test_get_scratch_stats_service_error(self, db_session: AsyncSession) -> None:
        """Test stats collection when mem0_service raises an exception."""
        # Mock mem0_service.get_stats to raise an exception
        test_exception = RuntimeError("Stats collection failed")

        with (
            patch.object(mem0_service, "get_stats", side_effect=test_exception) as mock_stats,
            patch("src.backend.cc.background.get_async_db") as mock_get_db,
        ):
            # Mock the async generator to yield our test session
            async def mock_async_generator() -> AsyncIterator[AsyncSession]:
                yield db_session

            mock_get_db.return_value = mock_async_generator()

            # Execute stats collection
            result = await background.get_scratch_stats()

            # Verify error result structure
            assert result["status"] == "error"
            assert result["error"] == "Stats collection failed"
            assert result["error_type"] == "RuntimeError"
            assert "started_at" in result
            assert "failed_at" in result
            assert "duration_seconds" in result
            assert isinstance(result["duration_seconds"], float)

            # Verify stats was called
            mock_stats.assert_called_once_with(db_session)

    async def test_get_scratch_stats_database_connection_error(self) -> None:
        """Test stats collection when database connection fails."""
        # Mock get_async_db to raise an exception
        test_exception = ConnectionError("Database connection failed")

        with patch("src.backend.cc.background.get_async_db", side_effect=test_exception):
            # Execute stats collection
            result = await background.get_scratch_stats()

            # Verify error result structure
            assert result["status"] == "error"
            assert "Database connection failed" in result["error"]
            assert result["error_type"] == "ConnectionError"
            assert "started_at" in result
            assert "failed_at" in result
            assert "duration_seconds" in result
            assert isinstance(result["duration_seconds"], float)

    async def test_get_scratch_stats_fallback_return_path(self) -> None:
        """Test the fallback return path for stats collection."""

        # Mock get_async_db to return an empty async generator
        async def empty_async_generator() -> AsyncIterator[AsyncSession]:
            # This generator yields nothing, testing the fallback path
            return
            yield  # This line will never be reached  # type: ignore[unreachable]

        with patch("src.backend.cc.background.get_async_db", return_value=empty_async_generator()):
            # Execute stats collection
            result = await background.get_scratch_stats()

            # Verify fallback error result
            assert result["status"] == "error"
            assert result["error"] == "No database connection available"
            assert result["error_type"] == "ConnectionError"
            assert "started_at" in result
            assert "failed_at" in result
            assert "duration_seconds" in result


@pytest.mark.asyncio
class TestFastAPIHelpers:
    """Test FastAPI background task helper functions."""

    async def test_create_cleanup_task_success(self, db_session: AsyncSession) -> None:
        """Test cleanup task creation for FastAPI."""
        # Mock the periodic_cleanup function
        expected_result = {
            "status": "completed",
            "deleted": 3,
            "duration_seconds": 0.5,
            "started_at": datetime.now(UTC).isoformat(),
            "completed_at": datetime.now(UTC).isoformat(),
        }

        with patch("src.backend.cc.background.periodic_cleanup", return_value=expected_result) as mock_cleanup:
            # Execute the task creation
            result = await background.create_cleanup_task()

            # Verify it returns the cleanup result directly
            assert result == expected_result
            assert result["status"] == "completed"
            assert result["deleted"] == 3

            # Verify cleanup was called
            mock_cleanup.assert_called_once()

    async def test_create_cleanup_task_error(self) -> None:
        """Test cleanup task creation when cleanup fails."""
        # Mock the periodic_cleanup function to return error
        expected_result = {
            "status": "error",
            "error": "Mock cleanup error",
            "error_type": "ValueError",
            "started_at": datetime.now(UTC).isoformat(),
            "failed_at": datetime.now(UTC).isoformat(),
            "duration_seconds": 0.1,
        }

        with patch("src.backend.cc.background.periodic_cleanup", return_value=expected_result) as mock_cleanup:
            # Execute the task creation
            result = await background.create_cleanup_task()

            # Verify it returns the error result directly
            assert result == expected_result
            assert result["status"] == "error"
            assert result["error"] == "Mock cleanup error"

            # Verify cleanup was called
            mock_cleanup.assert_called_once()

    async def test_create_stats_task_success(self, db_session: AsyncSession) -> None:
        """Test stats task creation for FastAPI."""
        # Mock the get_scratch_stats function
        expected_result = {
            "total_notes": 15,
            "active_notes": 12,
            "expired_notes": 3,
            "collection_duration_seconds": 0.3,
            "collection_started_at": datetime.now(UTC).isoformat(),
        }

        with patch("src.backend.cc.background.get_scratch_stats", return_value=expected_result) as mock_stats:
            # Execute the task creation
            result = await background.create_stats_task()

            # Verify it returns the stats result directly
            assert result == expected_result
            assert result["total_notes"] == 15
            assert result["active_notes"] == 12

            # Verify stats was called
            mock_stats.assert_called_once()

    async def test_create_stats_task_error(self) -> None:
        """Test stats task creation when stats collection fails."""
        # Mock the get_scratch_stats function to return error
        expected_result = {
            "status": "error",
            "error": "Mock stats error",
            "error_type": "RuntimeError",
            "started_at": datetime.now(UTC).isoformat(),
            "failed_at": datetime.now(UTC).isoformat(),
            "duration_seconds": 0.2,
        }

        with patch("src.backend.cc.background.get_scratch_stats", return_value=expected_result) as mock_stats:
            # Execute the task creation
            result = await background.create_stats_task()

            # Verify it returns the error result directly
            assert result == expected_result
            assert result["status"] == "error"
            assert result["error"] == "Mock stats error"

            # Verify stats was called
            mock_stats.assert_called_once()


@pytest.mark.asyncio
class TestScheduledCleanup:
    """Test scheduled cleanup task functionality."""

    async def test_run_scheduled_cleanup_single_cycle(self) -> None:
        """Test scheduled cleanup runs one cycle and can be cancelled."""
        # Mock periodic_cleanup to return a result
        cleanup_result = {"status": "completed", "deleted": 2}

        with (
            patch("src.backend.cc.background.periodic_cleanup", return_value=cleanup_result) as mock_cleanup,
            patch("src.backend.cc.background.asyncio.sleep", side_effect=asyncio.CancelledError()) as mock_sleep,
        ):
            # Execute scheduled cleanup - it will handle the cancellation internally
            await background.run_scheduled_cleanup(interval_minutes=1)

            # Verify cleanup was called once
            mock_cleanup.assert_called_once()

            # Verify sleep was called with correct interval (1 minute = 60 seconds)
            mock_sleep.assert_called_once_with(60)

    async def test_run_scheduled_cleanup_custom_interval(self) -> None:
        """Test scheduled cleanup with custom interval."""
        # Mock periodic_cleanup to return a result
        cleanup_result = {"status": "completed", "deleted": 1}

        with (
            patch("src.backend.cc.background.periodic_cleanup", return_value=cleanup_result) as mock_cleanup,
            patch("src.backend.cc.background.asyncio.sleep", side_effect=asyncio.CancelledError()) as mock_sleep,
        ):
            # Execute scheduled cleanup with 30-minute interval
            await background.run_scheduled_cleanup(interval_minutes=30)

            # Verify cleanup was called once
            mock_cleanup.assert_called_once()

            # Verify sleep was called with correct interval (30 minutes = 1800 seconds)
            mock_sleep.assert_called_once_with(1800)

    async def test_run_scheduled_cleanup_handles_cleanup_errors(self) -> None:
        """Test scheduled cleanup continues after cleanup errors."""
        # Mock periodic_cleanup to raise an exception on first call, then be cancelled
        cleanup_side_effects = [
            RuntimeError("Cleanup failed"),
            {"status": "completed", "deleted": 1},  # Second call succeeds
        ]

        with (
            patch("src.backend.cc.background.periodic_cleanup", side_effect=cleanup_side_effects) as mock_cleanup,
            patch(
                "src.backend.cc.background.asyncio.sleep", side_effect=[None, asyncio.CancelledError()]
            ) as mock_sleep,
        ):
            # Execute scheduled cleanup and expect it to handle the error then be cancelled
            await background.run_scheduled_cleanup(interval_minutes=1)

            # Verify cleanup was called twice (once failed, once succeeded)
            assert mock_cleanup.call_count == 2

            # Verify sleep was called once for error recovery (60 seconds)
            mock_sleep.assert_called_with(60)

    async def test_run_scheduled_cleanup_cancellation_handling(self) -> None:
        """Test scheduled cleanup handles cancellation gracefully."""
        # Mock periodic_cleanup to be cancelled immediately
        with patch("src.backend.cc.background.periodic_cleanup", side_effect=asyncio.CancelledError()) as mock_cleanup:
            # Execute scheduled cleanup and expect graceful cancellation
            await background.run_scheduled_cleanup(interval_minutes=5)

            # Verify cleanup was called once before cancellation
            mock_cleanup.assert_called_once()

    async def test_run_scheduled_cleanup_error_recovery_sleep(self) -> None:
        """Test scheduled cleanup uses error recovery sleep interval."""
        # Mock periodic_cleanup to raise an exception, then succeed
        cleanup_side_effects = [
            ValueError("First cleanup failed"),
            {"status": "completed", "deleted": 1},  # Second call succeeds
        ]

        with (
            patch("src.backend.cc.background.periodic_cleanup", side_effect=cleanup_side_effects) as mock_cleanup,
            patch(
                "src.backend.cc.background.asyncio.sleep", side_effect=[None, asyncio.CancelledError()]
            ) as mock_sleep,
        ):
            # Execute scheduled cleanup
            await background.run_scheduled_cleanup(interval_minutes=10)

            # Verify cleanup was called twice
            assert mock_cleanup.call_count == 2

            # Verify sleep was called with error recovery interval (60 seconds)
            # The first sleep is the error recovery sleep (60 seconds)
            # The second sleep should be the normal interval but gets cancelled
            mock_sleep.assert_any_call(60)  # Error recovery sleep


@pytest.mark.asyncio
class TestLogEventIntegration:
    """Test log event integration in background tasks."""

    async def test_periodic_cleanup_logs_success(self, db_session: AsyncSession) -> None:
        """Test that periodic cleanup logs success events."""
        # Mock mem0_service.run_cleanup to return expected result
        mock_cleanup_result = {
            "status": "completed",
            "deleted": 3,
            "execution_time_ms": 150.0,
        }

        with (
            patch.object(mem0_service, "run_cleanup", return_value=mock_cleanup_result),
            patch("src.backend.cc.background.get_async_db") as mock_get_db,
            patch("src.backend.cc.background.log_event") as mock_log,
        ):
            # Mock the async generator to yield our test session
            async def mock_async_generator() -> AsyncIterator[AsyncSession]:
                yield db_session

            mock_get_db.return_value = mock_async_generator()

            # Execute the cleanup
            await background.periodic_cleanup()

            # Verify logging was called for success
            mock_log.assert_called_once()
            call_args = mock_log.call_args
            assert call_args[1]["source"] == "cc_background"
            assert call_args[1]["tags"] == ["background", "cleanup", "success"]
            assert "Background cleanup task completed successfully" in call_args[1]["memo"]

    async def test_periodic_cleanup_logs_errors(self, db_session: AsyncSession) -> None:
        """Test that periodic cleanup logs error events."""
        # Mock mem0_service.run_cleanup to raise an exception
        test_exception = ValueError("Test cleanup error")

        with (
            patch.object(mem0_service, "run_cleanup", side_effect=test_exception),
            patch("src.backend.cc.background.get_async_db") as mock_get_db,
            patch("src.backend.cc.background.log_event") as mock_log,
        ):
            # Mock the async generator to yield our test session
            async def mock_async_generator() -> AsyncIterator[AsyncSession]:
                yield db_session

            mock_get_db.return_value = mock_async_generator()

            # Execute the cleanup
            await background.periodic_cleanup()

            # Verify logging was called for error
            mock_log.assert_called_once()
            call_args = mock_log.call_args
            assert call_args[1]["source"] == "cc_background"
            assert call_args[1]["tags"] == ["background", "cleanup", "error"]
            assert "Background cleanup task failed" in call_args[1]["memo"]

    async def test_get_scratch_stats_logs_success(self, db_session: AsyncSession) -> None:
        """Test that stats collection logs success events."""
        # Mock mem0_service.get_stats to return expected result
        mock_stats_result = {
            "total_notes": 10,
            "active_notes": 8,
            "expired_notes": 2,
        }

        with (
            patch.object(mem0_service, "get_stats", return_value=mock_stats_result),
            patch("src.backend.cc.background.get_async_db") as mock_get_db,
            patch("src.backend.cc.background.log_event") as mock_log,
        ):
            # Mock the async generator to yield our test session
            async def mock_async_generator() -> AsyncIterator[AsyncSession]:
                yield db_session

            mock_get_db.return_value = mock_async_generator()

            # Execute stats collection
            await background.get_scratch_stats()

            # Verify logging was called for success
            mock_log.assert_called_once()
            call_args = mock_log.call_args
            assert call_args[1]["source"] == "cc_background"
            assert call_args[1]["tags"] == ["background", "stats", "success"]
            assert "Background stats collection completed successfully" in call_args[1]["memo"]

    async def test_run_scheduled_cleanup_logs_lifecycle(self) -> None:
        """Test that scheduled cleanup logs lifecycle events."""
        # Mock periodic_cleanup to be cancelled immediately
        with (
            patch("src.backend.cc.background.periodic_cleanup", side_effect=asyncio.CancelledError()),
            patch("src.backend.cc.background.log_event") as mock_log,
        ):
            # Execute scheduled cleanup
            await background.run_scheduled_cleanup(interval_minutes=15)

            # Verify logging was called twice (start and cancel)
            assert mock_log.call_count == 2

            # Check start log
            start_call = mock_log.call_args_list[0]
            assert start_call[1]["source"] == "cc_background"
            assert start_call[1]["tags"] == ["background", "scheduler", "start"]
            assert "Starting scheduled cleanup with 15 minute interval" in start_call[1]["memo"]

            # Check cancel log
            cancel_call = mock_log.call_args_list[1]
            assert cancel_call[1]["source"] == "cc_background"
            assert cancel_call[1]["tags"] == ["background", "scheduler", "cancelled"]
            assert "Scheduled cleanup task was cancelled" in cancel_call[1]["memo"]


@pytest.mark.asyncio
class TestBackgroundTaskEdgeCases:
    """Test edge cases and error conditions in background tasks."""

    async def test_periodic_cleanup_with_different_exception_types(self, db_session: AsyncSession) -> None:
        """Test periodic cleanup handles various exception types properly."""
        # Test with different exception types
        test_cases = [
            (ValueError("Value error"), "ValueError"),
            (RuntimeError("Runtime error"), "RuntimeError"),
            (ConnectionError("Connection error"), "ConnectionError"),
            (Exception("Generic error"), "Exception"),
        ]

        for exception, expected_type in test_cases:
            with (
                patch.object(mem0_service, "run_cleanup", side_effect=exception),
                patch("src.backend.cc.background.get_async_db") as mock_get_db,
            ):
                # Mock the async generator to yield our test session
                async def mock_async_generator() -> AsyncIterator[AsyncSession]:
                    yield db_session

                mock_get_db.return_value = mock_async_generator()

                # Execute the cleanup
                result = await background.periodic_cleanup()

                # Verify error handling for each exception type
                assert result["status"] == "error"
                assert result["error_type"] == expected_type
                assert isinstance(result["duration_seconds"], float)
                assert "started_at" in result
                assert "failed_at" in result

    async def test_datetime_serialization_consistency(self, db_session: AsyncSession) -> None:
        """Test that datetime serialization is consistent across success and error paths."""
        # Test success path
        mock_cleanup_result = {"status": "completed", "deleted": 1}

        with (
            patch.object(mem0_service, "run_cleanup", return_value=mock_cleanup_result),
            patch("src.backend.cc.background.get_async_db") as mock_get_db,
        ):
            # Mock the async generator to yield our test session
            async def mock_async_generator() -> AsyncIterator[AsyncSession]:
                yield db_session

            mock_get_db.return_value = mock_async_generator()

            # Execute cleanup
            success_result = await background.periodic_cleanup()

            # Verify datetime format consistency
            assert "started_at" in success_result
            assert "completed_at" in success_result

            # Test that dates are valid ISO format
            start_dt = datetime.fromisoformat(success_result["started_at"])
            end_dt = datetime.fromisoformat(success_result["completed_at"])
            assert isinstance(start_dt, datetime)
            assert isinstance(end_dt, datetime)

        # Test error path
        with (
            patch.object(mem0_service, "run_cleanup", side_effect=ValueError("Test error")),
            patch("src.backend.cc.background.get_async_db") as mock_get_db,
        ):
            # Mock the async generator to yield our test session
            async def mock_async_generator() -> AsyncIterator[AsyncSession]:
                yield db_session

            mock_get_db.return_value = mock_async_generator()

            # Execute cleanup
            error_result = await background.periodic_cleanup()

            # Verify datetime format consistency in error path
            assert "started_at" in error_result
            assert "failed_at" in error_result

            # Test that dates are valid ISO format
            start_dt = datetime.fromisoformat(error_result["started_at"])
            failed_dt = datetime.fromisoformat(error_result["failed_at"])
            assert isinstance(start_dt, datetime)
            assert isinstance(failed_dt, datetime)

    async def test_background_task_resource_cleanup(self, db_session: AsyncSession) -> None:
        """Test that background tasks properly handle resource cleanup."""
        # Mock mem0_service.run_cleanup to succeed
        mock_cleanup_result = {"status": "completed", "deleted": 2}

        with (
            patch.object(mem0_service, "run_cleanup", return_value=mock_cleanup_result),
            patch("src.backend.cc.background.get_async_db") as mock_get_db,
        ):
            # Mock the async generator to yield our test session
            async def mock_async_generator() -> AsyncIterator[AsyncSession]:
                yield db_session

            mock_get_db.return_value = mock_async_generator()

            # Execute cleanup
            result = await background.periodic_cleanup()

            # Verify the finally block was reached (session cleanup)
            # The finally block just passes, but we can verify the function completed
            assert result["status"] == "completed"
            assert "duration_seconds" in result

    async def test_multiple_concurrent_background_tasks(self, db_session: AsyncSession) -> None:
        """Test that multiple background tasks can run concurrently without interference."""
        # Mock services to return different results
        mock_cleanup_result = {"status": "completed", "deleted": 3}
        mock_stats_result = {"total_notes": 15, "active_notes": 12, "expired_notes": 3}

        with (
            patch.object(mem0_service, "run_cleanup", return_value=mock_cleanup_result),
            patch.object(mem0_service, "get_stats", return_value=mock_stats_result),
            patch("src.backend.cc.background.get_async_db") as mock_get_db,
        ):
            # Mock the async generator to yield our test session for both tasks
            async def mock_async_generator() -> AsyncIterator[AsyncSession]:
                yield db_session

            # Each task will get a separate instance of the generator
            mock_get_db.side_effect = lambda: mock_async_generator()

            # Run tasks concurrently
            cleanup_task = asyncio.create_task(background.periodic_cleanup())
            stats_task = asyncio.create_task(background.get_scratch_stats())

            # Wait for both tasks to complete
            cleanup_result, stats_result = await asyncio.gather(cleanup_task, stats_task)

            # Verify both tasks completed successfully
            assert cleanup_result["status"] == "completed"
            assert cleanup_result["deleted"] == 3

            # Stats result will have timing fields added by get_scratch_stats
            # The mock_stats_result is transformed in get_scratch_stats with timing info
            assert stats_result["total_notes"] == 15
            assert stats_result["active_notes"] == 12
            assert stats_result["expired_notes"] == 3
            assert "collection_duration_seconds" in stats_result
            assert "collection_started_at" in stats_result
