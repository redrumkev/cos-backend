"""Test the logger shim import for backwards compatibility.

This test verifies that the Strangler Fig migration pattern (ADR-001)
is working correctly for the logger module.
"""

from __future__ import annotations

import logging
from typing import Any
from unittest.mock import patch


class TestLoggerShimImport:
    """Test that the logger shim import maintains backwards compatibility."""

    def test_import_from_common_logger_works(self) -> None:
        """Test that imports from common.logger still work."""
        # Import from the old location
        from src.common.logger import (
            _demo,
            get_logger,
            log_event,
            log_event_async,
            logger,
            mem,
        )

        # Verify all imports are available
        assert callable(get_logger)
        assert callable(log_event)
        assert callable(log_event_async)
        assert callable(_demo)
        assert isinstance(logger, logging.Logger)
        assert mem is None  # mem placeholder should be None

    def test_import_from_core_v2_works(self) -> None:
        """Test that imports from core_v2.utils.logger work."""
        # Import from the new location
        from core_v2.utils.logger import (
            _demo,
            get_logger,
            log_event,
            log_event_async,
            logger,
            mem,
        )

        # Verify all imports are available
        assert callable(get_logger)
        assert callable(log_event)
        assert callable(log_event_async)
        assert callable(_demo)
        assert isinstance(logger, logging.Logger)
        assert mem is None

    def test_common_and_core_v2_imports_are_same(self) -> None:
        """Test that both import paths reference the same objects."""
        # Import from both locations
        from core_v2.utils.logger import get_logger as core_v2_get_logger
        from core_v2.utils.logger import log_event as core_v2_log_event
        from core_v2.utils.logger import logger as core_v2_logger

        from src.common.logger import get_logger as common_get_logger
        from src.common.logger import log_event as common_log_event
        from src.common.logger import logger as common_logger

        # Verify they are the same objects
        assert common_get_logger is core_v2_get_logger
        assert common_log_event is core_v2_log_event
        assert common_logger is core_v2_logger

    def test_get_logger_functionality(self) -> None:
        """Test that get_logger works correctly from both import paths."""
        from core_v2.utils.logger import get_logger as core_v2_get_logger

        from src.common.logger import get_logger as common_get_logger

        # Test from common import
        common_test_logger = common_get_logger("test_module")
        assert common_test_logger.name == "cos.test_module"

        # Test from core_v2 import
        core_v2_test_logger = core_v2_get_logger("test_module")
        assert core_v2_test_logger.name == "cos.test_module"

        # They should return the same logger instance
        assert common_test_logger is core_v2_test_logger

    def test_log_event_functionality(self) -> None:
        """Test that log_event works correctly from both import paths."""
        from core_v2.utils.logger import log_event as core_v2_log_event

        from src.common.logger import log_event as common_log_event

        # Test from common import (with None memo to avoid DB)
        common_result = common_log_event(source="test", data={"test": "data"}, memo=None)
        assert common_result["status"] == "mem0_stub"
        assert common_result["memo"] is None

        # Test from core_v2 import
        core_v2_result = core_v2_log_event(source="test", data={"test": "data"}, memo=None)
        assert core_v2_result["status"] == "mem0_stub"
        assert core_v2_result["memo"] is None

    @patch("core_v2.utils.logger.logger.info")
    def test_demo_function(self, mock_logger_info: Any) -> None:
        """Test that _demo function works from both imports."""
        from core_v2.utils.logger import _demo as core_v2_demo

        from src.common.logger import _demo as common_demo

        # They should be the same function
        assert common_demo is core_v2_demo

        # Test functionality
        result = common_demo()
        assert isinstance(result, dict)
        assert "status" in result
        assert "id" in result

    def test_type_hints_available(self) -> None:
        """Test that enhanced type hints are available in core_v2."""
        from core_v2.utils.logger import LogEventResponse

        # Verify the type is available
        assert LogEventResponse is not None

        # Test that it can be used in type annotations
        def test_func() -> LogEventResponse:
            return {"status": "test", "id": "test-id", "data": "test-data"}

        result = test_func()
        assert result["status"] == "test"
