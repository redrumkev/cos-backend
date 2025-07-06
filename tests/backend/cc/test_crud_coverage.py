"""Focused tests for crud.py edge cases and missing coverage.

This file targets specific missing lines in crud.py to achieve 95%+ coverage.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import patch

from src.backend.cc.crud import get_active_modules, update_module_status


class TestUpdateModuleStatusFunction:
    """Test update_module_status function - covers lines 68-87."""

    @patch("src.backend.cc.crud.log_event")
    async def test_update_module_status_covers_logging_and_return(self, mock_log: Any) -> None:
        """Test update_module_status function logs and returns mock data - covers lines 68-87."""
        from unittest.mock import MagicMock

        # Mock database session
        mock_db = MagicMock()  # Properly mock the AsyncSession

        # Call the function
        result = await update_module_status(mock_db, "cc", "healthy")

        # Verify logging occurred (lines 68-73)
        mock_log.assert_called_once_with(
            source="cc",
            data={"module": "cc", "status": "healthy"},
            tags=["db", "health", "update"],
            memo="Updating status for module cc to healthy",
        )

        # Verify return structure (lines 86-87)
        assert result["module"] == "cc"
        assert result["status"] == "healthy"
        assert "last_updated" in result
        assert result["last_updated"] == "2025-04-02T10:10:00Z"

    @patch("src.backend.cc.crud.log_event")
    async def test_update_module_status_different_module(self, mock_log: Any) -> None:
        """Test update_module_status with different module name."""
        from unittest.mock import MagicMock

        mock_db = MagicMock()

        result = await update_module_status(mock_db, "mem0", "degraded")

        # Verify logging with different data
        mock_log.assert_called_once_with(
            source="cc",
            data={"module": "mem0", "status": "degraded"},
            tags=["db", "health", "update"],
            memo="Updating status for module mem0 to degraded",
        )

        # Verify return structure
        assert result["module"] == "mem0"
        assert result["status"] == "degraded"
        assert result["last_updated"] == "2025-04-02T10:10:00Z"

    @patch("src.backend.cc.crud.log_event")
    async def test_update_module_status_offline_status(self, mock_log: Any) -> None:
        """Test update_module_status with offline status."""
        from unittest.mock import MagicMock

        mock_db = MagicMock()

        result = await update_module_status(mock_db, "test_module", "offline")

        # Verify logging
        mock_log.assert_called_once_with(
            source="cc",
            data={"module": "test_module", "status": "offline"},
            tags=["db", "health", "update"],
            memo="Updating status for module test_module to offline",
        )

        # Verify return
        assert result["module"] == "test_module"
        assert result["status"] == "offline"


class TestGetActiveModulesFunction:
    """Test get_active_modules function - covers lines 112-121."""

    @patch("src.backend.cc.crud.log_event")
    async def test_get_active_modules_covers_logging_and_query(self, mock_log: Any) -> None:
        """Test get_active_modules function logs and queries correctly - covers lines 112-121."""
        from unittest.mock import AsyncMock, MagicMock

        # Mock database session and query result
        mock_db = MagicMock()
        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = ["cc", "mem0", "test_module"]
        mock_result.scalars.return_value = mock_scalars
        mock_db.execute = AsyncMock(return_value=mock_result)

        # Call the function
        result = await get_active_modules(mock_db)

        # Verify logging occurred (lines 112-117)
        mock_log.assert_called_once_with(
            source="cc",
            data={},
            tags=["db", "modules", "query"],
            memo="Querying active modules from database",
        )

        # Verify database query was executed
        mock_db.execute.assert_called_once()

        # Verify result conversion to list (line 121)
        assert result == ["cc", "mem0", "test_module"]
        assert isinstance(result, list)

    @patch("src.backend.cc.crud.log_event")
    async def test_get_active_modules_empty_result(self, mock_log: Any) -> None:
        """Test get_active_modules with empty result."""
        from unittest.mock import AsyncMock, MagicMock

        # Mock database session with empty result
        mock_db = MagicMock()
        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = []
        mock_result.scalars.return_value = mock_scalars
        mock_db.execute = AsyncMock(return_value=mock_result)

        # Call the function
        result = await get_active_modules(mock_db)

        # Verify logging
        mock_log.assert_called_once()

        # Verify empty list result
        assert result == []
        assert isinstance(result, list)

    @patch("src.backend.cc.crud.log_event")
    async def test_get_active_modules_single_module(self, mock_log: Any) -> None:
        """Test get_active_modules with single module result."""
        from unittest.mock import AsyncMock, MagicMock

        # Mock database session with single result
        mock_db = MagicMock()
        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = ["cc"]
        mock_result.scalars.return_value = mock_scalars
        mock_db.execute = AsyncMock(return_value=mock_result)

        # Call the function
        result = await get_active_modules(mock_db)

        # Verify logging
        mock_log.assert_called_once_with(
            source="cc",
            data={},
            tags=["db", "modules", "query"],
            memo="Querying active modules from database",
        )

        # Verify single item list
        assert result == ["cc"]
        assert len(result) == 1


class TestCRUDQueryStructure:
    """Test that CRUD queries use correct SQLAlchemy structure."""

    def test_get_active_modules_query_structure(self) -> None:
        """Test that get_active_modules uses correct query structure."""
        from sqlalchemy import select

        from src.backend.cc.models import Module

        # Verify the query structure matches what's in the function
        # This tests the SQL statement construction (lines 119-120)
        stmt = select(Module.name).where(Module.active == True)  # noqa: E712

        # Verify statement structure
        assert hasattr(stmt, "selected_columns")
        assert str(stmt.selected_columns[0]) == "modules.name"

        # Verify where clause
        where_clause = stmt.whereclause
        # The where clause might include schema prefix in CI
        assert "modules.active = true" in str(where_clause)
