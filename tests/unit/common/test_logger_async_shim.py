"""Test async functionality works correctly with the logger shim.

This test verifies that async functions work properly with both
the old and new import paths.
"""

from __future__ import annotations

import asyncio
from typing import Any


class TestLoggerAsyncShim:
    """Test async functionality with logger shim."""

    async def test_async_log_event_from_common(self) -> None:
        """Test async log_event from common import."""
        from src.common.logger import log_event_async

        result = await log_event_async(
            source="async_test",
            data={"test": "async_data"},
            tags=["async", "test"],
            memo=None,  # Use None to avoid DB access
        )

        assert result["status"] == "mem0_stub"
        assert result["id"].startswith("log-async_test-")
        assert result["memo"] is None
        assert result["data"] == {"test": "async_data"}

    async def test_async_log_event_from_core_v2(self) -> None:
        """Test async log_event from core_v2 import."""
        from core_v2.utils.logger import log_event_async

        result = await log_event_async(
            source="async_test_v2", data={"test": "async_data_v2"}, tags=["async", "test", "v2"], memo=None
        )

        assert result["status"] == "mem0_stub"
        assert result["id"].startswith("log-async_test_v2-")
        assert result["memo"] is None
        assert result["data"] == {"test": "async_data_v2"}

    async def test_async_imports_are_same(self) -> None:
        """Test that async functions from both imports are the same."""
        from core_v2.utils.logger import log_event_async as core_v2_async

        from src.common.logger import log_event_async as common_async

        # They should be the same function
        assert common_async is core_v2_async

    def test_sync_in_async_context(self) -> None:
        """Test that sync log_event works when called from async context."""

        async def async_test() -> Any:
            from src.common.logger import log_event

            # This should handle the async context properly
            result = log_event(source="sync_in_async", data="test_data", memo=None)
            return result

        # Run the async test
        result = asyncio.run(async_test())

        assert result["status"] == "mem0_stub"
        assert result["memo"] is None
        assert result["data"] == "test_data"

    def test_type_safety_with_async(self) -> None:
        """Test that TypedDict works with async functions."""
        from core_v2.utils.logger import LogEventResponse, log_event_async

        async def typed_async_function() -> LogEventResponse:
            """Return a typed log event response."""
            return await log_event_async(source="typed_test", data={"typed": "data"}, memo=None)

        # Run and verify
        result = asyncio.run(typed_async_function())
        assert isinstance(result, dict)
        assert result["status"] == "mem0_stub"
