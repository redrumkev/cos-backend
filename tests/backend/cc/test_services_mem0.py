"""Tests for CC services to ensure complete coverage.

This file contains additional tests specifically designed to achieve 100% coverage
by addressing edge cases and conditions not covered in the main test suite.
"""

from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.backend.cc.services import ping_module


class TestServicesCompleteCoverage:
    """Additional tests for CC services to reach 100% coverage."""

    @pytest.mark.asyncio
    async def test_ping_module_mem0(self) -> None:
        """Test ping_module function specifically for mem0 module.

        This test covers line 136 in services.py where module_name == "mem0".
        """
        # Mock database session
        mock_db = AsyncMock(spec=AsyncSession)

        # Mock log_event and update_module_status
        with (
            patch("src.backend.cc.services.log_event") as mock_log,
            patch("src.backend.cc.services.update_module_status") as mock_update,
        ):
            # Call the function for mem0 module
            result = await ping_module(mock_db, "mem0")

            # Verify log_event was called
            mock_log.assert_called_once()

            # Verify update_module_status was called with correct arguments
            mock_update.assert_called_once_with(mock_db, "mem0", "healthy")

            # Verify the result
            assert isinstance(result, dict)
            assert "module" in result
            assert result["module"] == "mem0"
            assert "status" in result
            assert result["status"] == "healthy"
            assert "latency_ms" in result
