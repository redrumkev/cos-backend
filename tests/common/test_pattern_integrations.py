"""Characterization tests for Living Patterns integration.

This module tests the Living Patterns integration in the three enhanced files:
- base_subscriber.py: ExecutionContext integration
- message_format.py: Error handling patterns
- ledger_view.py: Service pattern application

Pattern Reference: async_handler.py v2.1.0, error_handling.py v2.1.0, service.py v2.1.0
"""

import uuid
from datetime import UTC, datetime
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.common.base_subscriber import BaseSubscriber
from src.common.database import DatabaseExecutionContext
from src.common.ledger_view import LedgerViewService
from src.common.message_format import EventType, MessageEnvelope, build_message, parse_message
from src.core_v2.patterns.error_handling import COSError, ErrorCategory


class TestExecutionContextIntegration:
    """Test ExecutionContext integration in BaseSubscriber."""

    def test_execution_context_parameter_accepted(self) -> None:
        """Test that ExecutionContext parameter is accepted and stored."""
        mock_context = MagicMock()

        class ConcreteSubscriber(BaseSubscriber):
            async def process_message(self, message: dict[str, Any]) -> bool:
                return True

        subscriber = ConcreteSubscriber(execution_context=mock_context)
        assert subscriber._execution_context is mock_context

    def test_execution_context_default_creation(self) -> None:
        """Test that default ExecutionContext is created when none provided."""

        class ConcreteSubscriber(BaseSubscriber):
            async def process_message(self, message: dict[str, Any]) -> bool:
                return True

        subscriber = ConcreteSubscriber()
        assert subscriber._execution_context is not None
        assert isinstance(subscriber._execution_context, DatabaseExecutionContext)

    async def test_execution_context_cleanup_on_stop(self) -> None:
        """Test that ExecutionContext is cleaned up when stopping consumption."""
        mock_context = MagicMock()

        class ConcreteSubscriber(BaseSubscriber):
            async def process_message(self, message: dict[str, Any]) -> bool:
                return True

        subscriber = ConcreteSubscriber(execution_context=mock_context)

        # Mock the subscribe_to_channel to avoid actual subscription
        with patch("src.common.base_subscriber.subscribe_to_channel") as mock_subscribe:
            mock_subscribe.return_value = AsyncMock()

            # Start and stop consuming
            await subscriber.start_consuming("test_channel")
            await subscriber.stop_consuming()

            # Verify context cleanup was called
            mock_context.close.assert_called_once()

    async def test_execution_context_cleanup_with_none_context(self) -> None:
        """Test that cleanup works when context is None."""

        class ConcreteSubscriber(BaseSubscriber):
            async def process_message(self, message: dict[str, Any]) -> bool:
                return True

        subscriber = ConcreteSubscriber()
        # Set context to None to test the None check
        subscriber._execution_context = None  # type: ignore[assignment]

        # Mock the subscribe_to_channel to avoid actual subscription
        with patch("src.common.base_subscriber.subscribe_to_channel") as mock_subscribe:
            mock_subscribe.return_value = AsyncMock()

            # Start and stop consuming - should not crash
            await subscriber.start_consuming("test_channel")
            await subscriber.stop_consuming()

    def test_execution_context_with_circuit_breaker(self) -> None:
        """Test ExecutionContext integration with circuit breaker."""
        mock_context = MagicMock()
        mock_circuit_breaker = MagicMock()

        class ConcreteSubscriber(BaseSubscriber):
            async def process_message(self, message: dict[str, Any]) -> bool:
                return True

        subscriber = ConcreteSubscriber(execution_context=mock_context, circuit_breaker=mock_circuit_breaker)

        # Verify both are set
        assert subscriber._execution_context is mock_context
        assert subscriber._circuit_breaker is mock_circuit_breaker


class TestErrorHandlingPatterns:
    """Test error handling patterns in message_format.py."""

    def test_parse_message_invalid_json_raises_cos_error(self) -> None:
        """Test that invalid JSON raises COSError with proper category."""
        invalid_json = '{"invalid": json syntax}'

        with pytest.raises(COSError) as exc_info:
            parse_message(invalid_json)

        error = exc_info.value
        assert error.category == ErrorCategory.VALIDATION
        assert "parse_message" in error.details["operation"]

    def test_parse_message_invalid_bytes_raises_cos_error(self) -> None:
        """Test that invalid bytes raise COSError with proper category."""
        invalid_bytes = b"\xff\xfe\xfd"  # Invalid UTF-8

        with pytest.raises(COSError) as exc_info:
            parse_message(invalid_bytes)

        error = exc_info.value
        assert error.category == ErrorCategory.VALIDATION
        assert "parse_message" in error.details["operation"]

    def test_build_message_invalid_enum_raises_cos_error(self) -> None:
        """Test that invalid enum values raise COSError."""
        with pytest.raises(COSError) as exc_info:
            build_message(
                base_log_id=uuid.uuid4(),
                source_module="test",
                timestamp=datetime.now(UTC),
                trace_id="trace-123",
                request_id="req-456",
                event_type="INVALID_EVENT_TYPE",  # type: ignore[arg-type]
                data={"test": "data"},
            )

        error = exc_info.value
        assert error.category == ErrorCategory.VALIDATION

    def test_message_envelope_serialization_error_handling(self) -> None:
        """Test that MessageEnvelope serialization errors are handled properly."""
        envelope = MessageEnvelope(
            base_log_id=uuid.uuid4(),
            source_module="test",
            timestamp=datetime.now(UTC),
            trace_id="trace-123",
            request_id="req-456",
            event_type=EventType.PROMPT_TRACE,
            data={"test": "data"},
        )

        # Mock model_dump to raise an exception
        with (
            patch.object(envelope, "model_dump", side_effect=ValueError("Serialization error")),
            pytest.raises(COSError) as exc_info,
        ):
            envelope.model_dump_json()

        error = exc_info.value
        assert error.category == ErrorCategory.VALIDATION
        assert "model_dump_json" in error.details["operation"]

    def test_successful_message_operations_still_work(self) -> None:
        """Test that successful message operations still work with error handling."""
        # Test successful build_message
        json_str = build_message(
            base_log_id=uuid.uuid4(),
            source_module="test",
            timestamp=datetime.now(UTC),
            trace_id="trace-123",
            request_id="req-456",
            event_type=EventType.PROMPT_TRACE,
            data={"test": "data"},
        )

        # Test successful parse_message
        envelope = parse_message(json_str)
        assert envelope.event_type == EventType.PROMPT_TRACE
        assert envelope.data == {"test": "data"}

    def test_orjson_fallback_path(self) -> None:
        """Test the orjson fallback path in model_dump_json."""
        envelope = MessageEnvelope(
            base_log_id=uuid.uuid4(),
            source_module="test",
            timestamp=datetime.now(UTC),
            trace_id="trace-123",
            request_id="req-456",
            event_type=EventType.PROMPT_TRACE,
            data={"test": "data"},
        )

        # Test the fallback path by patching orjson availability
        from src.common import message_format

        original_has_orjson = message_format.HAS_ORJSON

        try:
            # Test without orjson
            message_format.HAS_ORJSON = False
            json_str = envelope.model_dump_json()
            assert isinstance(json_str, str)

            # Test with orjson
            message_format.HAS_ORJSON = True
            json_str = envelope.model_dump_json()
            assert isinstance(json_str, str)

        finally:
            # Restore original value
            message_format.HAS_ORJSON = original_has_orjson

    def test_build_message_timezone_handling(self) -> None:
        """Test timezone handling in build_message."""
        # Test with timezone-aware datetime
        tz_aware = datetime.now(UTC)
        json_str = build_message(
            base_log_id=uuid.uuid4(),
            source_module="test",
            timestamp=tz_aware,
            trace_id="trace-123",
            request_id="req-456",
            event_type=EventType.PROMPT_TRACE,
            data={"test": "data"},
        )
        envelope = parse_message(json_str)
        assert envelope.timestamp.tzinfo is not None

        # Test with timezone-naive datetime (should be converted to UTC)
        naive_dt = datetime.now()
        json_str = build_message(
            base_log_id=uuid.uuid4(),
            source_module="test",
            timestamp=naive_dt,
            trace_id="trace-123",
            request_id="req-456",
            event_type=EventType.PROMPT_TRACE,
            data={"test": "data"},
        )
        envelope = parse_message(json_str)
        assert envelope.timestamp.tzinfo is not None

    def test_parse_message_general_exception_handling(self) -> None:
        """Test general exception handling in parse_message."""
        # Test with data that causes validation error
        with pytest.raises(COSError) as exc_info:
            parse_message('{"invalid": "structure"}')

        error = exc_info.value
        assert error.category == ErrorCategory.VALIDATION
        assert "parse_message" in error.details["operation"]


class TestServicePatternIntegration:
    """Test service pattern integration in LedgerViewService."""

    def test_service_inherits_from_base_service(self) -> None:
        """Test that LedgerViewService inherits from BaseService."""
        from src.core_v2.patterns.service import BaseService

        service = LedgerViewService()
        assert isinstance(service, BaseService)

    def test_service_execution_context_integration(self) -> None:
        """Test that LedgerViewService integrates ExecutionContext."""
        mock_context = MagicMock()

        service = LedgerViewService(execution_context=mock_context)
        assert service._execution_context is mock_context

    def test_service_default_execution_context(self) -> None:
        """Test that default ExecutionContext is created when none provided."""
        service = LedgerViewService()
        assert service._execution_context is not None
        assert isinstance(service._execution_context, DatabaseExecutionContext)

    async def test_service_health_check_includes_memory_path(self) -> None:
        """Test that health check includes memory path information."""
        service = LedgerViewService()

        health = await service.health_check()

        # Check that memory path info is included
        assert "memory_path" in health
        assert "path_exists" in health
        assert "memory_files" in health
        assert health["service"] == "LedgerViewService"

    async def test_service_setup_warns_on_missing_path(self) -> None:
        """Test that _setup warns when memory path doesn't exist."""
        service = LedgerViewService()

        # Mock path to not exist
        with patch("src.common.ledger_view.MEMORY_PATH") as mock_path:
            mock_path.exists.return_value = False

            # Should not raise exception
            await service._setup()

    def test_service_methods_delegate_to_functions(self) -> None:
        """Test that service methods delegate to the original functions."""
        service = LedgerViewService()

        # Test that methods exist and are callable
        assert hasattr(service, "load_memories")
        assert hasattr(service, "filter_memories")
        assert hasattr(service, "render_rich_table")
        assert hasattr(service, "render_plain")
        assert hasattr(service, "run_cli")

        # Test that they are callable
        assert callable(service.load_memories)
        assert callable(service.filter_memories)
        assert callable(service.render_rich_table)
        assert callable(service.render_plain)
        assert callable(service.run_cli)

    def test_service_method_calls_with_mocks(self) -> None:
        """Test that service methods delegate to the original functions with mocks."""
        service = LedgerViewService()

        # Mock the original functions and test delegation
        with (
            patch("src.common.ledger_view.load_memories") as mock_load,
            patch("src.common.ledger_view.filter_memories") as mock_filter,
            patch("src.common.ledger_view.render_rich_table") as mock_render_rich,
            patch("src.common.ledger_view.render_plain") as mock_render_plain,
            patch("src.common.ledger_view.main") as mock_main,
        ):
            # Test load_memories delegation
            service.load_memories()
            mock_load.assert_called_once()

            # Test filter_memories delegation
            memories: list[tuple[str, dict[str, Any]]] = [("test", {})]
            service.filter_memories(memories, source="test", tag="tag")
            mock_filter.assert_called_once_with(memories, "test", "tag")

            # Test render_rich_table delegation
            service.render_rich_table(memories)
            mock_render_rich.assert_called_once_with(memories)

            # Test render_plain delegation
            service.render_plain(memories)
            mock_render_plain.assert_called_once_with(memories)

            # Test run_cli delegation
            service.run_cli()
            mock_main.assert_called_once()


class TestPatternVersionMarkers:
    """Test that pattern version markers are present in all enhanced files."""

    def test_base_subscriber_has_pattern_markers(self) -> None:
        """Test that base_subscriber.py has pattern markers."""
        import src.common.base_subscriber

        docstring = src.common.base_subscriber.__doc__
        assert "Pattern Reference: async_handler.py v2.1.0" in docstring
        assert "Living Patterns System" in docstring
        assert "ExecutionContext" in docstring

    def test_message_format_has_pattern_markers(self) -> None:
        """Test that message_format.py has pattern markers."""
        import src.common.message_format

        docstring = src.common.message_format.__doc__
        assert "Pattern Reference: error_handling.py v2.1.0" in docstring
        assert "Living Patterns System" in docstring
        assert "COSError" in docstring

    def test_ledger_view_has_pattern_markers(self) -> None:
        """Test that ledger_view.py has pattern markers."""
        import src.common.ledger_view

        docstring = src.common.ledger_view.__doc__
        assert "Pattern Reference: service.py v2.1.0" in docstring
        assert "Living Patterns System" in docstring
        assert "BaseService" in docstring


class TestIntegrationCompatibility:
    """Test that the pattern integrations are backward compatible."""

    def test_base_subscriber_backward_compatibility(self) -> None:
        """Test that BaseSubscriber can still be used without ExecutionContext."""

        class ConcreteSubscriber(BaseSubscriber):
            async def process_message(self, message: dict[str, Any]) -> bool:
                return True

        # Should work without ExecutionContext parameter
        subscriber = ConcreteSubscriber()
        assert subscriber._execution_context is not None

        # Should work with other parameters
        subscriber = ConcreteSubscriber(concurrency=16, ack_timeout=10.0)
        assert subscriber._concurrency == 16
        assert subscriber._ack_timeout == 10.0

    def test_message_format_backward_compatibility(self) -> None:
        """Test that message format functions still work as expected."""
        # Test that the API remains the same
        json_str = build_message(
            base_log_id=uuid.uuid4(),
            source_module="test",
            timestamp=datetime.now(UTC),
            trace_id="trace-123",
            request_id="req-456",
            event_type=EventType.PROMPT_TRACE,
            data={"test": "data"},
        )

        # Should be a string
        assert isinstance(json_str, str)

        # Should be parseable
        envelope = parse_message(json_str)
        assert isinstance(envelope, MessageEnvelope)

    def test_ledger_view_backward_compatibility(self) -> None:
        """Test that ledger_view functions still work as expected."""
        # Test that the original functions still exist
        from src.common.ledger_view import filter_memories, load_memories

        # Should be callable
        assert callable(load_memories)
        assert callable(filter_memories)

        # Should return expected types
        memories = load_memories()
        assert isinstance(memories, list)

        filtered = filter_memories(memories)
        assert isinstance(filtered, list)
