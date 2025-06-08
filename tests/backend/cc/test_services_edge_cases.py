"""Focused tests for services.py edge cases and missing coverage.

This file targets specific missing lines in services.py to achieve 95%+ coverage.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from unittest.mock import MagicMock, patch

import pytest  # Phase 2: Remove for skip removal

from src.backend.cc.services import (
    check_system_health,
    create_module,
    delete_module,
    get_cc_configuration,
    get_module,
    get_module_by_name,
    get_modules,
    get_status,
    ping_module,
    read_system_health,
    update_module,
)

# Phase 2: Remove this skip block for service layer implementation (P2-SERVICE-001)
pytestmark = pytest.mark.skip(reason="Phase 2: Service layer implementation needed. Trigger: P2-SERVICE-001")


class TestGetStatusFunction:
    """Test get_status function - covers lines 35-41."""

    @patch("src.backend.cc.services.log_event")
    def test_get_status_returns_correct_format(self, mock_log: Any) -> None:
        """Test get_status function returns correct format - covers lines 35-41."""
        result = get_status()

        # Verify return format
        assert result == {"cc": "online", "message": "Control Center active."}

        # Verify logging occurred
        mock_log.assert_called_once_with(
            source="cc",
            data={"msg": "Control Center status requested."},
            tags=["status", "heartbeat"],
            memo="Initial /status check",
        )


class TestReadSystemHealthFunction:
    """Test read_system_health function - covers line 62."""

    @patch("src.backend.cc.services.get_system_health")
    async def test_read_system_health_returns_health_record(self, mock_get_health: Any) -> None:
        """Test read_system_health returns health record - covers line 62."""
        # Mock database session
        mock_db = MagicMock()

        # Mock health record (using MagicMock instead of dict to match HealthStatus type)
        mock_health_record = MagicMock()
        mock_health_record.id = "test-id"
        mock_health_record.module = "cc"
        mock_health_record.status = "healthy"
        mock_health_record.last_updated = datetime.fromisoformat("2025-01-01T00:00:00+00:00")
        mock_get_health.return_value = mock_health_record

        # Call function
        result = await read_system_health(mock_db)

        # Verify result
        assert result == mock_health_record
        mock_get_health.assert_called_once_with(mock_db)

    @patch("src.backend.cc.services.get_system_health")
    async def test_read_system_health_returns_none(self, mock_get_health: Any) -> None:
        """Test read_system_health returns None when no record - covers line 62."""
        mock_db = MagicMock()
        mock_get_health.return_value = None

        result = await read_system_health(mock_db)

        assert result is None
        mock_get_health.assert_called_once_with(mock_db)


class TestCheckSystemHealthFunction:
    """Test check_system_health function - covers lines 83-105."""

    @patch("src.backend.cc.services.get_system_health")
    @patch("src.backend.cc.services.log_event")
    async def test_check_system_health_with_healthy_status(self, mock_log: Any, mock_get_health: Any) -> None:
        """Test check_system_health with healthy status - covers lines 83-105."""
        mock_db = MagicMock()

        # Mock healthy health record
        mock_health = MagicMock()
        mock_health.status = "healthy"
        mock_health.module = "cc"
        mock_get_health.return_value = mock_health

        result = await check_system_health(mock_db)

        # Verify overall status logic
        assert result["overall_status"] == "healthy"
        assert len(result["modules"]) == 1
        assert result["modules"][0]["module"] == "cc"
        assert result["modules"][0]["status"] == "healthy"
        assert "timestamp" in result

        # Verify logging
        mock_log.assert_called_once_with(
            source="cc",
            data={},
            tags=["service", "health"],
            memo="System health check initiated",
        )

    @patch("src.backend.cc.services.get_system_health")
    @patch("src.backend.cc.services.log_event")
    async def test_check_system_health_with_degraded_status(self, mock_log: Any, mock_get_health: Any) -> None:
        """Test check_system_health with degraded status - covers lines 83-105."""
        mock_db = MagicMock()

        # Mock degraded health record
        mock_health = MagicMock()
        mock_health.status = "degraded"
        mock_health.module = "cc"
        mock_get_health.return_value = mock_health

        result = await check_system_health(mock_db)

        # Verify degraded status logic
        assert result["overall_status"] == "degraded"
        assert len(result["modules"]) == 1
        assert result["modules"][0]["status"] == "degraded"

    @patch("src.backend.cc.services.get_system_health")
    @patch("src.backend.cc.services.log_event")
    async def test_check_system_health_with_no_health_record(self, mock_log: Any, mock_get_health: Any) -> None:
        """Test check_system_health with no health record - covers lines 83-105."""
        mock_db = MagicMock()
        mock_get_health.return_value = None

        result = await check_system_health(mock_db)

        # Verify unknown status logic
        assert result["overall_status"] == "unknown"
        assert result["modules"] == []
        assert "timestamp" in result


class TestGetCcConfigurationFunction:
    """Test get_cc_configuration function - covers lines 131-142."""

    @patch("src.backend.cc.services.get_active_modules")
    @patch("src.backend.cc.services.log_event")
    async def test_get_cc_configuration_returns_config(self, mock_log: Any, mock_get_active: Any) -> None:
        """Test get_cc_configuration returns correct config - covers lines 131-142."""
        mock_db = MagicMock()
        mock_active_modules = ["cc", "mem0"]
        mock_get_active.return_value = mock_active_modules

        result = await get_cc_configuration(mock_db)

        # Verify config format
        assert result["version"] == "0.1.0"
        assert result["modules_loaded"] == ["cc", "mem0"]
        assert result["environment"] == "development"

        # Verify logging
        mock_log.assert_called_once_with(
            source="cc",
            data={},
            tags=["service", "config"],
            memo="CC configuration requested",
        )

        # Verify active modules call
        mock_get_active.assert_called_once_with(mock_db)

    @patch("src.backend.cc.services.get_active_modules")
    @patch("src.backend.cc.services.log_event")
    async def test_get_cc_configuration_with_empty_modules(self, mock_log: Any, mock_get_active: Any) -> None:
        """Test get_cc_configuration with empty modules list - covers lines 131-142."""
        mock_db = MagicMock()
        mock_get_active.return_value = []

        result = await get_cc_configuration(mock_db)

        assert result["modules_loaded"] == []


class TestPingModuleFunction:
    """Test ping_module function - covers lines 168-183."""

    @patch("src.backend.cc.services.update_module_status")
    @patch("src.backend.cc.services.log_event")
    async def test_ping_module_known_cc_module(self, mock_log: Any, mock_update_status: Any) -> None:
        """Test ping_module with cc module - covers lines 168-183."""
        mock_db = MagicMock()

        result = await ping_module(mock_db, "cc")

        # Verify return format
        assert result["module"] == "cc"
        assert result["status"] == "healthy"
        assert result["latency_ms"] == 5

        # Verify logging
        mock_log.assert_called_once_with(
            source="cc",
            data={"module": "cc"},
            tags=["service", "ping"],
            memo="Pinging module cc",
        )

        # Verify status update
        mock_update_status.assert_called_once_with(mock_db, "cc", "healthy")

    @patch("src.backend.cc.services.update_module_status")
    @patch("src.backend.cc.services.log_event")
    async def test_ping_module_known_mem0_module(self, mock_log: Any, mock_update_status: Any) -> None:
        """Test ping_module with mem0 module - covers lines 168-183."""
        mock_db = MagicMock()

        result = await ping_module(mock_db, "mem0")

        assert result["module"] == "mem0"
        assert result["status"] == "healthy"
        mock_update_status.assert_called_once_with(mock_db, "mem0", "healthy")

    @patch("src.backend.cc.services.update_module_status")
    @patch("src.backend.cc.services.log_event")
    async def test_ping_module_unknown_module(self, mock_log: Any, mock_update_status: Any) -> None:
        """Test ping_module with unknown module - covers lines 168-183."""
        mock_db = MagicMock()

        result = await ping_module(mock_db, "unknown_module")

        # Verify unknown module logic
        assert result["module"] == "unknown_module"
        assert result["status"] == "unknown"
        assert result["latency_ms"] == 5

        # Verify status update with unknown
        mock_update_status.assert_called_once_with(mock_db, "unknown_module", "unknown")


class TestCreateModuleFunction:
    """Test create_module function for duplicate name validation."""

    @patch("src.backend.cc.services.crud_create_module")
    @patch("src.backend.cc.services.crud_get_module_by_name")
    @patch("src.backend.cc.services.log_event")
    async def test_create_module_success(self, mock_log: Any, mock_get_by_name: Any, mock_create: Any) -> None:
        """Test create_module success path."""
        mock_db = MagicMock()
        mock_get_by_name.return_value = None  # No existing module
        mock_created_module = MagicMock()
        mock_create.return_value = mock_created_module

        result = await create_module(mock_db, "new_module", "1.0.0", '{"config": "value"}')

        assert result == mock_created_module
        mock_log.assert_called_once()
        mock_get_by_name.assert_called_once_with(mock_db, "new_module")
        mock_create.assert_called_once_with(mock_db, "new_module", "1.0.0", '{"config": "value"}')

    @patch("src.backend.cc.services.crud_get_module_by_name")
    @patch("src.backend.cc.services.log_event")
    async def test_create_module_duplicate_name_raises_error(self, mock_log: Any, mock_get_by_name: Any) -> None:
        """Test create_module raises ValueError for duplicate names."""
        mock_db = MagicMock()
        mock_existing_module = MagicMock()
        mock_get_by_name.return_value = mock_existing_module

        with pytest.raises(ValueError, match="Module with name 'existing_module' already exists"):
            await create_module(mock_db, "existing_module", "1.0.0")


class TestUpdateModuleFunction:
    """Test update_module function for name conflict validation."""

    @patch("src.backend.cc.services.crud_update_module")
    @patch("src.backend.cc.services.crud_get_module_by_name")
    @patch("src.backend.cc.services.log_event")
    async def test_update_module_name_conflict_raises_error(
        self, mock_log: Any, mock_get_by_name: Any, mock_update: Any
    ) -> None:
        """Test update_module raises ValueError for name conflicts."""
        mock_db = MagicMock()
        module_id = "test-id-1"

        # Mock existing module with different ID
        mock_existing_module = MagicMock()
        mock_existing_module.id = "different-id"
        mock_get_by_name.return_value = mock_existing_module

        with pytest.raises(ValueError, match="Module with name 'conflicting_name' already exists"):
            await update_module(mock_db, module_id, {"name": "conflicting_name"})

    @patch("src.backend.cc.services.crud_update_module")
    @patch("src.backend.cc.services.crud_get_module_by_name")
    @patch("src.backend.cc.services.log_event")
    async def test_update_module_name_same_module_allowed(
        self, mock_log: Any, mock_get_by_name: Any, mock_update: Any
    ) -> None:
        """Test update_module allows updating name to same module's name."""
        mock_db = MagicMock()
        module_id = "test-id-1"

        # Mock existing module with same ID
        mock_existing_module = MagicMock()
        mock_existing_module.id = module_id
        mock_get_by_name.return_value = mock_existing_module

        mock_updated_module = MagicMock()
        mock_update.return_value = mock_updated_module

        result = await update_module(mock_db, module_id, {"name": "same_name"})

        assert result == mock_updated_module
        mock_update.assert_called_once_with(mock_db, module_id, {"name": "same_name"})

    @patch("src.backend.cc.services.crud_update_module")
    @patch("src.backend.cc.services.log_event")
    async def test_update_module_no_name_field(self, mock_log: Any, mock_update: Any) -> None:
        """Test update_module without name field (no conflict check)."""
        mock_db = MagicMock()
        module_id = "test-id-1"

        mock_updated_module = MagicMock()
        mock_update.return_value = mock_updated_module

        result = await update_module(mock_db, module_id, {"version": "2.0.0"})

        assert result == mock_updated_module
        mock_update.assert_called_once_with(mock_db, module_id, {"version": "2.0.0"})


class TestServiceLoggingCalls:
    """Test that all service functions call log_event properly."""

    @patch("src.backend.cc.services.crud_get_module")
    @patch("src.backend.cc.services.log_event")
    async def test_get_module_logs_properly(self, mock_log: Any, mock_crud_get: Any) -> None:
        """Test get_module logs properly."""
        mock_db = MagicMock()
        mock_crud_get.return_value = None

        await get_module(mock_db, "test-id")

        mock_log.assert_called_once_with(
            source="cc",
            data={"module_id": "test-id"},
            tags=["service", "module", "read"],
            memo="Retrieving module test-id",
        )

    @patch("src.backend.cc.services.crud_get_module_by_name")
    @patch("src.backend.cc.services.log_event")
    async def test_get_module_by_name_logs_properly(self, mock_log: Any, mock_crud_get: Any) -> None:
        """Test get_module_by_name logs properly."""
        mock_db = MagicMock()
        mock_crud_get.return_value = None

        await get_module_by_name(mock_db, "test_name")

        mock_log.assert_called_once_with(
            source="cc",
            data={"name": "test_name"},
            tags=["service", "module", "read"],
            memo="Retrieving module by name test_name",
        )

    @patch("src.backend.cc.services.crud_get_modules")
    @patch("src.backend.cc.services.log_event")
    async def test_get_modules_logs_properly(self, mock_log: Any, mock_crud_get: Any) -> None:
        """Test get_modules logs properly."""
        mock_db = MagicMock()
        mock_crud_get.return_value = []

        await get_modules(mock_db, skip=10, limit=50)

        mock_log.assert_called_once_with(
            source="cc",
            data={"skip": 10, "limit": 50},
            tags=["service", "module", "read"],
            memo="Retrieving modules with skip=10, limit=50",
        )

    @patch("src.backend.cc.services.crud_delete_module")
    @patch("src.backend.cc.services.log_event")
    async def test_delete_module_logs_properly(self, mock_log: Any, mock_crud_delete: Any) -> None:
        """Test delete_module logs properly."""
        mock_db = MagicMock()
        mock_crud_delete.return_value = None

        await delete_module(mock_db, "test-id")

        mock_log.assert_called_once_with(
            source="cc",
            data={"module_id": "test-id"},
            tags=["service", "module", "delete"],
            memo="Deleting module test-id",
        )
