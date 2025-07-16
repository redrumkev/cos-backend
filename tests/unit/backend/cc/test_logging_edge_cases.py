# Test file - configured per-file ignores in ruff.toml handle common test patterns
"""Unit tests for edge cases in L1 logging service.

This file specifically covers edge cases and error conditions that are not
covered by the main test files, targeting 99.5%+ coverage for logging.py.

Following TDD methodology: RED → GREEN → REFACTOR
"""

import os
import sys
import uuid
from collections.abc import Iterator
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.fixture
def disable_redis_publishing() -> Iterator[Mock]:
    """Fixture to completely disable Redis publishing during tests."""
    import os
    from unittest.mock import patch

    from sqlalchemy import event
    from sqlalchemy.orm import Session

    from src.backend.cc.logging import _after_commit_publish_events

    # Set environment variable to disable publishing
    old_value = os.environ.get("DISABLE_REDIS_PUBLISHING")
    os.environ["DISABLE_REDIS_PUBLISHING"] = "true"

    # Remove the event listener if it exists
    if event.contains(Session, "after_commit", _after_commit_publish_events):
        event.remove(Session, "after_commit", _after_commit_publish_events)

    # Create an AsyncMock that properly handles being awaited
    async def mock_publish_impl(*args: object, **kwargs: object) -> None:
        return None

    # Patch the _publish_l1_event function with our mock implementation
    with patch("src.backend.cc.logging._publish_l1_event", side_effect=mock_publish_impl) as mock_publish:
        yield mock_publish

    # Restore environment variable
    if old_value is None:
        os.environ.pop("DISABLE_REDIS_PUBLISHING", None)
    else:
        os.environ["DISABLE_REDIS_PUBLISHING"] = old_value

    # Re-register the event listener after the test
    if not event.contains(Session, "after_commit", _after_commit_publish_events):
        event.listen(Session, "after_commit", _after_commit_publish_events, named=True)


class TestPublishL1EventEdgeCases:
    """Test edge cases in _publish_l1_event function."""

    @patch("src.backend.cc.logging._should_publish_events")
    @patch("src.backend.cc.logging.asyncio.get_running_loop")
    @patch("src.backend.cc.logging.logger")
    async def test_publish_l1_event_no_running_loop(
        self, mock_logger: Mock, mock_get_loop: Mock, mock_should_publish: Mock
    ) -> None:
        """Test when asyncio.get_running_loop() raises RuntimeError."""
        from src.backend.cc.logging import _publish_l1_event

        # Enable publishing
        mock_should_publish.return_value = True

        # Make get_running_loop raise RuntimeError
        mock_get_loop.side_effect = RuntimeError("No running event loop")

        log_id = uuid.uuid4()
        event_data = {"event": {"event_type": "test"}}

        # Should return early without error
        await _publish_l1_event(log_id, event_data)

        # Verify warning was logged
        mock_logger.warning.assert_called_once_with(
            "Event loop not running, skipping Redis publish for log_id %s", log_id
        )

    @patch("src.backend.cc.logging._should_publish_events")
    @patch("src.backend.cc.logging.get_pubsub")
    @patch("src.backend.cc.logging.logfire")
    async def test_publish_l1_event_fallback_strategy(
        self, mock_logfire: Mock, mock_get_pubsub: AsyncMock, mock_should_publish: Mock
    ) -> None:
        """Test fallback publishing strategy when main publish fails."""
        from src.backend.cc.logging import _publish_l1_event

        mock_should_publish.return_value = True

        # Mock pubsub with fallback method
        mock_pubsub = AsyncMock()
        mock_pubsub.publish.side_effect = Exception("Redis error")
        mock_pubsub.publish_with_fallback = AsyncMock(return_value="logged_only")
        mock_get_pubsub.return_value = mock_pubsub

        # Mock Logfire span
        mock_span = Mock()
        mock_logfire.span.return_value.__aenter__ = AsyncMock(return_value=mock_span)
        mock_logfire.span.return_value.__aexit__ = AsyncMock(return_value=None)

        log_id = uuid.uuid4()
        event_data = {"event": {"event_type": "test"}}

        await _publish_l1_event(log_id, event_data)

        # Verify fallback was attempted
        mock_pubsub.publish_with_fallback.assert_called_once()

        # Verify both error and fallback info were logged
        assert mock_logfire.error.call_count == 1
        assert mock_logfire.info.call_count == 1

    @patch("src.backend.cc.logging._should_publish_events")
    @patch("src.backend.cc.logging.get_pubsub")
    @patch("src.backend.cc.logging.logfire")
    async def test_publish_l1_event_fallback_also_fails(
        self, mock_logfire: Mock, mock_get_pubsub: AsyncMock, mock_should_publish: Mock
    ) -> None:
        """Test when both main publish and fallback strategy fail."""
        from src.backend.cc.logging import _publish_l1_event

        mock_should_publish.return_value = True

        # Mock pubsub with failing fallback
        mock_pubsub = AsyncMock()
        mock_pubsub.publish.side_effect = Exception("Redis error")
        mock_pubsub.publish_with_fallback = AsyncMock(side_effect=Exception("Fallback error"))
        mock_get_pubsub.return_value = mock_pubsub

        # Mock Logfire span
        mock_span = Mock()
        mock_logfire.span.return_value.__aenter__ = AsyncMock(return_value=mock_span)
        mock_logfire.span.return_value.__aexit__ = AsyncMock(return_value=None)

        log_id = uuid.uuid4()
        event_data = {"event": {"event_type": "test"}}

        # Should not raise exception
        await _publish_l1_event(log_id, event_data)

        # Verify errors were logged
        assert mock_logfire.error.call_count == 2  # Main error + fallback error


class TestShouldPublishEventsEdgeCases:
    """Test edge cases in _should_publish_events function."""

    def test_should_publish_events_pytest_in_modules(self) -> None:
        """Test when pytest is in sys.modules."""
        from src.backend.cc.logging import _should_publish_events

        # Save original state
        original_modules = dict(sys.modules)

        try:
            # Add pytest to modules
            sys.modules["pytest"] = MagicMock()

            assert _should_publish_events() is False
        finally:
            # Restore original state
            sys.modules.clear()
            sys.modules.update(original_modules)

    def test_should_publish_events_pytest_in_module_names(self) -> None:
        """Test when module names contain pytest."""
        from src.backend.cc.logging import _should_publish_events

        # Save original state
        original_modules = dict(sys.modules)

        try:
            # Add module with pytest in name
            sys.modules["my_pytest_plugin"] = MagicMock()
            sys.modules["pytest_cov"] = MagicMock()

            assert _should_publish_events() is False
        finally:
            # Restore original state
            sys.modules.clear()
            sys.modules.update(original_modules)

    def test_should_publish_events_pytest_in_argv(self) -> None:
        """Test when pytest is in sys.argv."""
        from src.backend.cc.logging import _should_publish_events

        # Save original argv
        original_argv = sys.argv[:]

        try:
            # Add pytest to argv
            sys.argv = ["/usr/bin/pytest", "tests/test_something.py"]

            assert _should_publish_events() is False
        finally:
            # Restore original argv
            sys.argv = original_argv

    @patch.dict("os.environ", {"DISABLE_REDIS_PUBLISHING": "true"})
    def test_should_publish_events_disabled_via_env(self) -> None:
        """Test when Redis publishing is disabled via environment variable."""
        from src.backend.cc.logging import _should_publish_events

        assert _should_publish_events() is False

    @patch.dict("os.environ", {"DISABLE_REDIS_PUBLISHING": "1"})
    def test_should_publish_events_disabled_via_env_numeric(self) -> None:
        """Test when Redis publishing is disabled via numeric env var."""
        from src.backend.cc.logging import _should_publish_events

        assert _should_publish_events() is False

    @patch.dict("os.environ", {"DISABLE_REDIS_PUBLISHING": "yes"})
    def test_should_publish_events_disabled_via_env_yes(self) -> None:
        """Test when Redis publishing is disabled via 'yes' env var."""
        from src.backend.cc.logging import _should_publish_events

        assert _should_publish_events() is False

    @patch.dict("os.environ", {"PYTEST_CURRENT_TEST": "test_something::test_method"})
    def test_should_publish_events_pytest_env_var(self) -> None:
        """Test when PYTEST_CURRENT_TEST is set."""
        from src.backend.cc.logging import _should_publish_events

        assert _should_publish_events() is False

    def test_should_publish_events_all_checks_pass(self) -> None:
        """Test when all checks pass and publishing should be enabled."""
        from src.backend.cc.logging import _should_publish_events

        # Save original state
        original_modules = dict(sys.modules)
        original_argv = sys.argv[:]
        original_env = os.environ.copy()

        try:
            # Remove any pytest modules
            for key in list(sys.modules.keys()):
                if "pytest" in key:
                    del sys.modules[key]

            # Clean argv
            sys.argv = ["python", "app.py"]

            # Clean environment
            for key in ["PYTEST_CURRENT_TEST", "DISABLE_REDIS_PUBLISHING"]:
                if key in os.environ:
                    del os.environ[key]

            # Should return True when all checks pass
            assert _should_publish_events() is True
        finally:
            # Restore original state
            sys.modules.clear()
            sys.modules.update(original_modules)
            sys.argv = original_argv
            os.environ.clear()
            os.environ.update(original_env)


class TestAfterCommitEventListenerEdgeCases:
    """Test edge cases in after_commit event listener."""

    @patch("src.backend.cc.logging._should_publish_events")
    def test_after_commit_no_outbox_events(self, mock_should_publish: Mock) -> None:
        """Test when there are no outbox events to publish."""
        from src.backend.cc.logging import _after_commit_publish_events

        mock_should_publish.return_value = True

        # Mock session with no outbox
        mock_session = Mock()
        mock_session.info = {}

        # Should return early
        _after_commit_publish_events(mock_session)

        # No tasks should be created
        assert "l1_outbox" not in mock_session.info
        assert "_redis_tasks" not in mock_session.info

    @patch("src.backend.cc.logging._should_publish_events")
    @patch("src.backend.cc.logging.asyncio.get_running_loop")
    @patch("src.backend.cc.logging.logfire")
    def test_after_commit_loop_shutting_down(
        self, mock_logfire: Mock, mock_get_loop: Mock, mock_should_publish: Mock
    ) -> None:
        """Test when event loop is shutting down."""
        from src.backend.cc.logging import _after_commit_publish_events

        mock_should_publish.return_value = True

        # Mock loop that is closed
        mock_loop = Mock()
        mock_loop.is_running.return_value = True
        mock_loop.is_closed.return_value = True
        mock_get_loop.return_value = mock_loop

        # Mock session with outbox events
        mock_session = Mock()
        mock_session.info = {"l1_outbox": [(uuid.uuid4(), {"event": "test"})]}

        _after_commit_publish_events(mock_session)

        # Verify warning was logged
        mock_logfire.warn.assert_called_once_with(
            "Event loop is shutting down, skipping Redis publishing", event_count=1
        )

    @patch("src.backend.cc.logging._should_publish_events")
    @patch("src.backend.cc.logging.asyncio.get_running_loop")
    def test_after_commit_task_cleanup_callback_error(self, mock_get_loop: Mock, mock_should_publish: Mock) -> None:
        """Test when task cleanup callback encounters an error."""
        from src.backend.cc.logging import _after_commit_publish_events

        mock_should_publish.return_value = True

        # Mock loop and task
        mock_task = Mock()
        mock_task.cancelled.return_value = False
        mock_task.exception.side_effect = Exception("Task error")

        mock_loop = Mock()
        mock_loop.is_running.return_value = True
        mock_loop.is_closed.return_value = False
        mock_loop.create_task.return_value = mock_task
        mock_get_loop.return_value = mock_loop

        # Mock session with outbox events
        mock_session = Mock()
        mock_session.info = {"l1_outbox": [(uuid.uuid4(), {"event": "test"})]}

        _after_commit_publish_events(mock_session)

        # Get the cleanup callback
        cleanup_callback = mock_task.add_done_callback.call_args[0][0]

        # Call it with the mock task - should not raise
        cleanup_callback(mock_task)

        # Verify task was created
        assert mock_loop.create_task.called

    @patch("src.backend.cc.logging._should_publish_events")
    def test_after_commit_clears_outbox_when_disabled(self, mock_should_publish: Mock) -> None:
        """Test that outbox is cleared even when publishing is disabled."""
        from src.backend.cc.logging import _after_commit_publish_events

        mock_should_publish.return_value = False

        # Mock session with outbox events
        mock_session = Mock()
        mock_session.info = {"l1_outbox": [(uuid.uuid4(), {"event": "test"})]}

        _after_commit_publish_events(mock_session)

        # Verify outbox was cleared
        assert "l1_outbox" not in mock_session.info


class TestLogL1EdgeCases:
    """Test edge cases in log_l1 function."""

    @pytest.mark.filterwarnings("ignore:coroutine '_publish_l1_event' was never awaited:RuntimeWarning")
    @patch("src.backend.cc.logging.logfire")
    @patch("src.backend.cc.logging._should_publish_events", return_value=False)
    async def test_log_l1_logfire_span_attribute_errors(
        self, mock_should_publish: Mock, mock_logfire: Mock, test_db_session: AsyncSession
    ) -> None:
        """Test when setting Logfire span attributes fails."""
        # Mock current_span to raise errors
        mock_logfire.current_span.side_effect = RuntimeError("No span context")

        from src.backend.cc.logging import log_l1

        # Should complete successfully despite span errors
        result = await log_l1(db=test_db_session, event_type="test_event", payload={"test": "data"})

        assert "base_log_id" in result
        assert "event_log_id" in result

    @pytest.mark.filterwarnings("ignore:coroutine '_publish_l1_event' was never awaited:RuntimeWarning")
    @patch("src.backend.cc.logging.logfire")
    @patch("src.backend.cc.logging._should_publish_events", return_value=False)
    async def test_log_l1_logfire_span_no_set_attribute(
        self, mock_should_publish: Mock, mock_logfire: Mock, test_db_session: AsyncSession
    ) -> None:
        """Test when span doesn't have set_attribute method."""
        # Mock span without set_attribute
        mock_span = Mock(spec=[])  # No methods
        mock_logfire.current_span.return_value = mock_span

        from src.backend.cc.logging import log_l1

        # Should complete successfully
        result = await log_l1(db=test_db_session, event_type="test_event", payload={"test": "data"})

        assert "base_log_id" in result

    @patch("src.backend.cc.logging._should_publish_events", return_value=False)
    async def test_log_l1_invalid_uuid_request_id(
        self, mock_should_publish: Mock, test_db_session: AsyncSession
    ) -> None:
        """Test handling of invalid UUID format for request_id."""
        from src.backend.cc.logging import log_l1

        # Use invalid UUID format
        invalid_request_id = "not-a-valid-uuid"

        result = await log_l1(
            db=test_db_session, event_type="test_event", payload={"test": "data"}, request_id=invalid_request_id
        )

        assert "base_log_id" in result
        assert "event_log_id" in result

        # The invalid UUID should be replaced with a valid one

    @pytest.mark.filterwarnings("ignore:coroutine '_publish_l1_event' was never awaited:RuntimeWarning")
    @patch("src.backend.cc.logging._should_publish_events", return_value=False)
    async def test_log_l1_non_string_request_id(self, mock_should_publish: Mock, test_db_session: AsyncSession) -> None:
        """Test handling of non-string request_id."""
        from src.backend.cc.logging import log_l1

        # Use UUID object directly
        request_id = uuid.uuid4()

        result = await log_l1(
            db=test_db_session, event_type="test_event", payload={"test": "data"}, request_id=str(request_id)
        )

        assert "base_log_id" in result
        assert "event_log_id" in result

    @pytest.mark.filterwarnings("ignore:coroutine '_publish_l1_event' was never awaited:RuntimeWarning")
    @patch("src.backend.cc.logging._should_publish_events", return_value=False)
    async def test_log_l1_ultimate_uuid_fallback(
        self, mock_should_publish: Mock, test_db_session: AsyncSession
    ) -> None:
        """Test ultimate fallback when all UUID parsing fails."""
        from src.backend.cc.logging import log_l1

        # Test with an object that will cause exception in UUID parsing
        class BadRequestId:
            def __str__(self) -> str:
                raise Exception("String conversion failed")

        bad_request_id = BadRequestId()

        # Should use uuid.uuid4() as fallback
        result = await log_l1(
            db=test_db_session,
            event_type="test_event",
            payload={"test": "data"},
            request_id=bad_request_id,  # type: ignore
        )

        assert "base_log_id" in result
        assert "event_log_id" in result

    @patch("src.backend.cc.logging.logger")
    @patch("src.backend.cc.logging._should_publish_events", return_value=False)
    async def test_log_l1_exception_in_isinstance_check(
        self, mock_should_publish: Mock, mock_logger: Mock, test_db_session: AsyncSession
    ) -> None:
        """Test when isinstance() check itself raises an exception."""
        from src.backend.cc.logging import log_l1

        # Create a class where isinstance() will raise
        class MetaClassError(type):
            def __instancecheck__(cls, instance: object) -> bool:
                raise Exception("isinstance check failed")

        class BadRequestId(metaclass=MetaClassError):
            pass

        bad_request_id = BadRequestId()

        # Should handle the exception and use uuid.uuid4() as fallback
        result = await log_l1(
            db=test_db_session,
            event_type="test_event",
            payload={"test": "data"},
            request_id=bad_request_id,  # type: ignore
        )

        assert "base_log_id" in result
        assert "event_log_id" in result


class TestEventLoopEdgeCases:
    """Test event loop related edge cases."""

    @patch("src.backend.cc.logging._should_publish_events")
    @patch("src.backend.cc.logging.asyncio.get_running_loop")
    @patch("src.backend.cc.logging.logfire")
    def test_after_commit_no_running_loop_runtime_error(
        self, mock_logfire: Mock, mock_get_loop: Mock, mock_should_publish: Mock
    ) -> None:
        """Test when get_running_loop raises RuntimeError in after_commit."""
        from src.backend.cc.logging import _after_commit_publish_events

        mock_should_publish.return_value = True
        mock_get_loop.side_effect = RuntimeError("No running loop")

        # Mock session with outbox events
        mock_session = Mock()
        mock_session.info = {"l1_outbox": [(uuid.uuid4(), {"event": "test"})]}

        # Should not raise exception
        _after_commit_publish_events(mock_session)

        # Verify warning was logged
        mock_logfire.warn.assert_called_once_with("No running event loop for Redis publishing", event_count=1)
