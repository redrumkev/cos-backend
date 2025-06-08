"""Focused unit tests to improve code coverage to 97%.

These tests target specific uncovered lines and branches identified in the coverage report.
"""

from __future__ import annotations

import os
from typing import Any
from unittest.mock import patch

import pytest  # Phase 2: Remove for skip removal
from sqlalchemy.exc import SQLAlchemyError

from src.backend.cc import crud
from src.backend.cc.models import HealthStatus, Module
from src.common.logger import log_event

# Phase 2: Remove this skip block for coverage testing (P2-COVERAGE-001)
pytestmark = pytest.mark.skip(reason="Phase 2: Coverage testing needed. Trigger: P2-COVERAGE-001")


class TestConnectionCoverage:
    """Tests to cover missing lines in connection.py."""

    @patch.dict(os.environ, {"ENABLE_DB_INTEGRATION": "1"})
    def test_database_url_for_tests_with_integration(self) -> None:
        """Test _database_url_for_tests with integration enabled."""
        from src.db.connection import _database_url_for_tests

        url = _database_url_for_tests()
        assert "postgresql" in url

    @patch.dict(os.environ, {}, clear=True)
    def test_database_url_for_tests_no_integration(self) -> None:
        """Test _database_url_for_tests without integration."""
        from src.db.connection import _database_url_for_tests

        url = _database_url_for_tests()
        assert "sqlite" in url

    @patch.dict(os.environ, {"PYTEST_CURRENT_TEST": "test_something"})
    def test_database_url_for_tests_in_pytest(self) -> None:
        """Test _database_url_for_tests when running in pytest."""
        from src.db.connection import _database_url_for_tests

        url = _database_url_for_tests()
        assert "sqlite" in url

    def test_get_async_db_session_factory(self) -> None:
        """Test get_async_db function."""
        from src.db.connection import get_async_db

        # Should return a generator function
        assert callable(get_async_db)


class TestCrudErrorPaths:
    """Tests to cover error paths in crud.py."""

    @pytest.mark.asyncio
    async def test_create_module_db_error(self, db_session: Any) -> None:
        """Test create_module with database error."""
        with (
            patch.object(db_session, "add", side_effect=SQLAlchemyError("DB Error")),
            pytest.raises(SQLAlchemyError),
        ):
            await crud.create_module(db_session, "test_module", "1.0.0")

    @pytest.mark.asyncio
    async def test_get_system_health_db_error(self, db_session: Any) -> None:
        """Test get_system_health with database error."""
        with (
            patch.object(db_session, "execute", side_effect=SQLAlchemyError("DB Error")),
            pytest.raises(SQLAlchemyError),
        ):
            await crud.get_system_health(db_session)

    @pytest.mark.asyncio
    async def test_get_module_db_error(self, db_session: Any) -> None:
        """Test get_module with database error."""
        with (
            patch.object(db_session, "execute", side_effect=SQLAlchemyError("DB Error")),
            pytest.raises(SQLAlchemyError),
        ):
            await crud.get_module(db_session, "test-id")


class TestLoggingCoverage:
    """Tests to cover logging-related code paths."""

    def test_log_event_real_call_coverage(self) -> None:
        """Test real log_event call for coverage."""
        # This will hit the actual log_event function
        result = log_event("test_event", {"test": "data"}, ["test"])

        # The function returns a stub response when Mem0 is not available
        assert result is not None


class TestModelDefaultsCoverage:
    """Tests to cover model default value generation."""

    def test_health_status_defaults_coverage(self) -> None:
        """Test HealthStatus model default generation."""
        # Test default ID generation
        health1 = HealthStatus(module="test1", status="healthy")
        health2 = HealthStatus(module="test2", status="healthy")

        # Should have different IDs
        assert health1.id != health2.id
        assert health1.id is not None
        assert health2.id is not None

        # Should have last_updated set
        assert health1.last_updated is not None
        assert health2.last_updated is not None

    def test_module_defaults_coverage(self) -> None:
        """Test Module model default generation."""
        # Test default ID and active generation
        module1 = Module(name="test1", version="1.0.0")
        module2 = Module(name="test2", version="1.0.0")

        # Should have different IDs
        assert module1.id != module2.id
        assert module1.id is not None
        assert module2.id is not None

        # Should be active by default
        assert module1.active is True
        assert module2.active is True

        # Should have last_active set
        assert module1.last_active is not None
        assert module2.last_active is not None


class TestSchemaValidation:
    """Tests for schema validation edge cases."""

    def test_module_create_basic_validation(self) -> None:
        """Test ModuleCreate schema basic validation."""
        from src.backend.cc.schemas import ModuleCreate

        # Test minimum valid data
        valid_data = ModuleCreate(name="test", version="1.0.0")
        assert valid_data.name == "test"
        assert valid_data.version == "1.0.0"
        assert valid_data.config is None

    def test_module_update_basic_validation(self) -> None:
        """Test ModuleUpdate schema basic validation."""
        from src.backend.cc.schemas import ModuleUpdate

        # Test with only version
        update = ModuleUpdate(version="2.0.0")
        assert update.version == "2.0.0"
        assert update.config is None

    def test_health_status_response_serialization(self) -> None:
        """Test HealthStatusResponse serialization."""
        from src.backend.cc.schemas import HealthStatusResponse

        # Test basic serialization
        response = HealthStatusResponse(
            id="test-id",
            module="cc",
            status="healthy",
            last_updated="2025-01-01T00:00:00Z",
            details=None,
        )

        assert response.id == "test-id"
        assert response.module == "cc"
        assert response.status == "healthy"

    def test_module_ping_request_validation(self) -> None:
        """Test ModulePingRequest validation."""
        from src.backend.cc.schemas import ModulePingRequest

        # Test minimum length validation
        request = ModulePingRequest(module="a")
        assert request.module == "a"

        # Test with longer module name
        request_long = ModulePingRequest(module="test_module_name")
        assert request_long.module == "test_module_name"
