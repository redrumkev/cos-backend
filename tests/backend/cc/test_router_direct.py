"""Direct router function tests for achieving coverage.

This file tests router functions directly with mocked dependencies to achieve
specific line coverage without FastAPI framework overhead.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from src.backend.cc.schemas import ModuleCreate, ModuleUpdate
from tests.common.db_test_helpers import create_module_deps_mock


class TestRouterDirectCoverage:
    """Direct tests for router function coverage."""

    @patch("src.backend.cc.router.read_system_health")
    @patch("src.backend.cc.router.log_event")
    async def test_health_check_success_covers_lines_46_58(self, mock_log: Any, mock_health: Any) -> None:
        """Test health_check function success path - covers lines 46-58."""
        from src.backend.cc.router import health_check

        # Mock the health record with correct schema
        mock_health.return_value = {
            "id": "test-health-id",
            "module": "cc",
            "status": "healthy",
            "last_updated": datetime.fromisoformat("2025-01-01T00:00:00+00:00"),
            "details": "All systems operational",
        }

        # Create proper ModuleDeps mock with database session
        mock_db = MagicMock()
        mock_deps = create_module_deps_mock(db_session=mock_db)

        # Call the function directly
        result = await health_check(mock_deps)

        # Assertions
        assert result.status == "healthy"
        assert result.module == "cc"
        mock_log.assert_called_once()
        mock_health.assert_called_once_with(mock_db)

    @patch("src.backend.cc.router.read_system_health")
    @patch("src.backend.cc.router.log_event")
    async def test_health_check_no_record_covers_lines_53_58(self, mock_log: Any, mock_health: Any) -> None:
        """Test health_check function no record - covers exception lines 53-58."""
        from src.backend.cc.router import health_check
        from src.core_v2.patterns.error_handling import NotFoundError

        # Mock no health record found
        mock_health.return_value = None

        # Create proper ModuleDeps mock with database session
        mock_db = MagicMock()
        mock_deps = create_module_deps_mock(db_session=mock_db)

        # Call the function and expect exception
        with pytest.raises(NotFoundError) as exc_info:
            await health_check(mock_deps)

        # Assertions
        assert exc_info.value.details["resource"] == "Health record"
        assert exc_info.value.details["id"] == "system"
        assert "No health record available yet" in str(exc_info.value.user_message)
        mock_log.assert_called_once()

    @patch("src.backend.cc.router.log_event")
    async def test_get_config_covers_lines_72_78(self, mock_log: Any) -> None:
        """Test get_config function - covers lines 72-78."""
        from src.backend.cc.router import get_config

        # Mock config dependency
        mock_config = {"version": "1.0.0"}

        # Call the function directly
        result = await get_config(mock_config)

        # Assertions
        assert result.version == "1.0.0"
        assert "cc" in result.modules_loaded
        assert "mem0" in result.modules_loaded
        mock_log.assert_called_once()

    @patch("src.backend.cc.router.log_event")
    async def test_get_status_covers_logging(self, mock_log: Any) -> None:
        """Test get_status function - covers status logging."""
        from src.backend.cc.router import get_status

        # Call the function directly
        result = await get_status()

        # Assertions
        assert result == {"status": "ok"}
        mock_log.assert_called_once()

    @patch("src.backend.cc.router.log_event")
    async def test_ping_unknown_module_covers_lines_96_97(self, mock_log: Any) -> None:
        """Test ping function with unknown module - covers lines 96-97."""
        from src.backend.cc.router import ping
        from src.backend.cc.schemas import ModulePingRequest

        # Create request for unknown module
        request = ModulePingRequest(module="unknown")
        mock_db = MagicMock()

        # Call the function directly
        result = await ping(request, mock_db)

        # Assertions
        assert result.module == "unknown"
        assert result.status == "unknown"
        assert result.latency_ms == 0
        mock_log.assert_called_once()

    @patch("src.backend.cc.router.log_event")
    async def test_ping_known_module_covers_line_98(self, mock_log: Any) -> None:
        """Test ping function with known module - covers line 98."""
        from src.backend.cc.router import ping
        from src.backend.cc.schemas import ModulePingRequest

        # Create request for known module
        request = ModulePingRequest(module="mem0")
        mock_db = MagicMock()

        # Call the function directly
        result = await ping(request, mock_db)

        # Assertions
        assert result.module == "mem0"
        assert result.status == "healthy"
        assert result.latency_ms == 5
        mock_log.assert_called_once()

    @patch("src.backend.cc.router.log_event")
    async def test_system_health_report_covers_lines_120_128(self, mock_log: Any) -> None:
        """Test system_health_report function - covers lines 120-128."""
        from src.backend.cc.router import system_health_report

        # Mock database
        mock_db = MagicMock()

        # Call the function directly
        result = await system_health_report(mock_db)

        # Assertions
        assert result.overall_status == "healthy"
        assert len(result.modules) == 2
        assert any(module.module == "cc" for module in result.modules)
        assert any(module.module == "mem0" for module in result.modules)
        mock_log.assert_called_once()

    @patch("src.backend.cc.router.service_create_module")
    @patch("src.backend.cc.router.log_event")
    async def test_create_module_success_covers_lines_171_173(self, mock_log: Any, mock_create: Any) -> None:
        """Test create_module function success - covers lines 171-173."""
        # Mock the service response with correct schema
        import uuid

        from src.backend.cc.router import create_module

        test_uuid = str(uuid.uuid4())
        mock_create.return_value = {
            "id": test_uuid,
            "name": "test_module",
            "version": "1.0.0",
            "config": '{"setting": "value"}',  # String not dict
            "active": True,
            "last_active": datetime.fromisoformat("2025-01-01T00:00:00+00:00"),
        }

        # Create request data
        module_data = ModuleCreate(name="test_module", version="1.0.0", config='{"setting": "value"}')
        mock_db = MagicMock()

        # Call the function directly
        result = await create_module(module_data, mock_db)

        # Assertions
        assert result.name == "test_module"
        assert result.version == "1.0.0"
        mock_log.assert_called_once()
        mock_create.assert_called_once()

    @patch("src.backend.cc.router.service_create_module")
    @patch("src.backend.cc.router.log_event")
    async def test_create_module_value_error_covers_lines_172_173(self, mock_log: Any, mock_create: Any) -> None:
        """Test create_module function ValueError exception - covers lines 172-173."""
        from src.backend.cc.router import create_module
        from src.core_v2.patterns.error_handling import ValidationError

        # Mock ValueError from service
        mock_create.side_effect = ValueError("Invalid module data")

        # Create request data
        module_data = ModuleCreate(name="invalid_module", version="1.0.0")
        mock_db = MagicMock()
        mock_deps = create_module_deps_mock(db_session=mock_db)

        # Call the function and expect exception
        with pytest.raises(ValidationError) as exc_info:
            await create_module(module_data, mock_deps)

        # Assertions
        assert str(exc_info.value) == "Invalid module data"
        assert "Cannot create module" in str(exc_info.value.user_message)
        mock_log.assert_called_once()
        mock_create.assert_called_once()

    @patch("src.backend.cc.router.service_get_module")
    @patch("src.backend.cc.router.log_event")
    async def test_get_module_success_covers_line_197(self, mock_log: Any, mock_get: Any) -> None:
        """Test get_module function success - covers line 197."""
        # Mock the service response with correct schema
        import uuid

        from src.backend.cc.router import get_module

        test_uuid = str(uuid.uuid4())
        mock_get.return_value = {
            "id": test_uuid,
            "name": "test_module",
            "version": "1.0.0",
            "config": '{"setting": "value"}',  # String not dict
            "active": True,
            "last_active": datetime.fromisoformat("2025-01-01T00:00:00+00:00"),
        }

        mock_db = MagicMock()

        # Call the function directly
        result = await get_module(test_uuid, mock_db)

        # Assertions
        assert result.id == test_uuid
        assert result.name == "test_module"
        mock_log.assert_called_once()
        mock_get.assert_called_once()

    @patch("src.backend.cc.router.service_get_module")
    @patch("src.backend.cc.router.log_event")
    async def test_get_module_not_found_covers_404(self, mock_log: Any, mock_get: Any) -> None:
        """Test get_module function not found - covers 404 path."""
        from src.backend.cc.router import get_module
        from src.core_v2.patterns.error_handling import NotFoundError

        # Mock not found
        mock_get.return_value = None
        mock_db = MagicMock()
        mock_deps = create_module_deps_mock(db_session=mock_db)

        # Call the function and expect exception
        with pytest.raises(NotFoundError) as exc_info:
            await get_module("nonexistent", mock_deps)

        # Assertions
        assert exc_info.value.details["resource"] == "Module"
        assert exc_info.value.details["id"] == "nonexistent"
        mock_log.assert_called_once()

    @patch("src.backend.cc.router.service_get_modules")
    @patch("src.backend.cc.router.log_event")
    async def test_list_modules_covers_pagination(self, mock_log: Any, mock_get_modules: Any) -> None:
        """Test list_modules function with pagination."""
        from src.backend.cc.router import list_modules
        from src.core_v2.patterns.router import PaginationParams

        # Mock the service response
        mock_get_modules.return_value = []
        mock_db = MagicMock()
        mock_deps = create_module_deps_mock(db_session=mock_db)

        # Create pagination params
        pagination = PaginationParams(page=1, limit=10)

        # Call the router function directly
        result = await list_modules(pagination, mock_deps)

        # Assertions
        assert result == []
        mock_log.assert_called_once()
        mock_get_modules.assert_called_once_with(mock_db, skip=0, limit=10)

    @patch("src.backend.cc.router.service_update_module")
    @patch("src.backend.cc.router.log_event")
    async def test_update_module_success_covers_lines_251_256(self, mock_log: Any, mock_update: Any) -> None:
        """Test update_module function success - covers lines 251-256."""
        # Mock the service response with correct schema
        import uuid

        from src.backend.cc.router import update_module

        test_uuid = str(uuid.uuid4())
        mock_update.return_value = {
            "id": test_uuid,
            "name": "updated_module",
            "version": "2.0.0",
            "config": '{"setting": "new_value"}',  # String not dict
            "active": True,
            "last_active": datetime.fromisoformat("2025-01-01T01:00:00+00:00"),
        }

        # Create request data
        module_data = ModuleUpdate(version="2.0.0")
        mock_db = MagicMock()

        # Call the function directly
        result = await update_module(test_uuid, module_data, mock_db)

        # Assertions
        assert result.version == "2.0.0"
        mock_log.assert_called_once()
        mock_update.assert_called_once()

    @patch("src.backend.cc.router.service_update_module")
    @patch("src.backend.cc.router.log_event")
    async def test_update_module_not_found_covers_404(self, mock_log: Any, mock_update: Any) -> None:
        """Test update_module function not found - covers 404 path."""
        from src.backend.cc.router import update_module
        from src.core_v2.patterns.error_handling import NotFoundError

        # Mock not found
        mock_update.return_value = None
        mock_db = MagicMock()
        mock_deps = create_module_deps_mock(db_session=mock_db)
        module_data = ModuleUpdate(version="2.0.0")

        # Call the function and expect exception
        with pytest.raises(NotFoundError) as exc_info:
            await update_module("nonexistent", module_data, mock_deps)

        # Assertions
        assert exc_info.value.details["resource"] == "Module"
        assert exc_info.value.details["id"] == "nonexistent"
        mock_log.assert_called_once()

    @patch("src.backend.cc.router.service_update_module")
    @patch("src.backend.cc.router.log_event")
    async def test_update_module_value_error_covers_exception(self, mock_log: Any, mock_update: Any) -> None:
        """Test update_module function value error - covers exception path."""
        from src.backend.cc.router import update_module
        from src.core_v2.patterns.error_handling import ValidationError

        # Mock value error
        mock_update.side_effect = ValueError("Invalid data")
        mock_db = MagicMock()
        mock_deps = create_module_deps_mock(db_session=mock_db)
        module_data = ModuleUpdate(version="invalid")

        # Call the function and expect exception
        import uuid

        test_uuid = str(uuid.uuid4())
        with pytest.raises(ValidationError) as exc_info:
            await update_module(test_uuid, module_data, mock_deps)

        # Assertions
        assert str(exc_info.value) == "Invalid data"
        assert "Cannot update module" in str(exc_info.value.user_message)
        mock_log.assert_called_once()

    @patch("src.backend.cc.router.service_delete_module")
    @patch("src.backend.cc.router.log_event")
    async def test_delete_module_success_covers_lines_279_282(self, mock_log: Any, mock_delete: Any) -> None:
        """Test delete_module function success - covers lines 279-282."""
        # Mock the service response with correct schema
        import uuid

        from src.backend.cc.router import delete_module

        test_uuid = str(uuid.uuid4())
        mock_delete.return_value = {
            "id": test_uuid,
            "name": "deleted_module",
            "version": "1.0.0",
            "config": '{"setting": "value"}',  # String not dict
            "active": False,
            "last_active": datetime.fromisoformat("2025-01-01T00:00:00+00:00"),
        }

        mock_db = MagicMock()

        # Call the function directly
        result = await delete_module(test_uuid, mock_db)

        # Assertions
        assert result.id == test_uuid
        assert result.name == "deleted_module"
        mock_log.assert_called_once()
        mock_delete.assert_called_once()

    @patch("src.backend.cc.router.service_delete_module")
    @patch("src.backend.cc.router.log_event")
    async def test_delete_module_not_found_covers_404(self, mock_log: Any, mock_delete: Any) -> None:
        """Test delete_module function not found - covers 404 path."""
        from src.backend.cc.router import delete_module
        from src.core_v2.patterns.error_handling import NotFoundError

        # Mock not found
        mock_delete.return_value = None
        mock_db = MagicMock()
        mock_deps = create_module_deps_mock(db_session=mock_db)

        # Call the function and expect exception
        with pytest.raises(NotFoundError) as exc_info:
            await delete_module("nonexistent", mock_deps)

        # Assertions
        assert exc_info.value.details["resource"] == "Module"
        assert exc_info.value.details["id"] == "nonexistent"
        mock_log.assert_called_once()
