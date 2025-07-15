"""Unit tests for database test helpers.

This module tests the Database Mock Chain Helper Foundation to ensure
it works correctly in isolation before applying it to fix other tests.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import BackgroundTasks, FastAPI, Request
from sqlalchemy.ext.asyncio import AsyncSession

from src.common.config import Settings, get_settings
from src.common.database import get_async_db, get_async_session_maker
from src.core_v2.patterns.router import ModuleDeps
from src.graph.registry import ModuleLabel

from .db_test_helpers import (
    create_async_mock_db,
    create_async_session_maker_override,
    create_crud_mock_db,
    create_fastapi_test_overrides,
    create_health_check_mock_db,
    create_module_deps_mock,
    create_test_db_override,
    mock_module_deps_context,
    test_db_context,
)


class TestDatabaseOverrides:
    """Test database override functions."""

    def test_create_test_db_override_with_mock_session(self) -> None:
        """Test creating database override with provided mock session."""
        app = FastAPI()
        mock_session = MagicMock(spec=AsyncSession)

        result = create_test_db_override(app, mock_session)

        assert result is mock_session
        assert get_async_db in app.dependency_overrides
        assert app.dependency_overrides[get_async_db]() is mock_session

    def test_create_test_db_override_without_mock_session(self) -> None:
        """Test creating database override without provided mock session."""
        app = FastAPI()

        result = create_test_db_override(app)

        assert isinstance(result, MagicMock)
        assert get_async_db in app.dependency_overrides
        assert app.dependency_overrides[get_async_db]() is result

    def test_create_async_session_maker_override_with_mock(self) -> None:
        """Test creating async session maker override with provided mock."""
        app = FastAPI()
        mock_session = MagicMock()

        result = create_async_session_maker_override(app, mock_session)

        assert result is mock_session
        assert get_async_session_maker in app.dependency_overrides
        assert app.dependency_overrides[get_async_session_maker]() is mock_session

    def test_create_async_session_maker_override_without_mock(self) -> None:
        """Test creating async session maker override without provided mock."""
        app = FastAPI()

        result = create_async_session_maker_override(app)

        assert isinstance(result, MagicMock)
        assert get_async_session_maker in app.dependency_overrides
        assert app.dependency_overrides[get_async_session_maker]() is result

    def test_test_db_context_with_mock_session(self) -> None:
        """Test database context manager with provided mock session."""
        app = FastAPI()
        mock_session = MagicMock(spec=AsyncSession)

        with test_db_context(app, mock_session) as session:
            assert session is mock_session
            assert get_async_db in app.dependency_overrides

        # Should clean up after context
        assert len(app.dependency_overrides) == 0

    def test_test_db_context_without_mock_session(self) -> None:
        """Test database context manager without provided mock session."""
        app = FastAPI()

        with test_db_context(app) as session:
            assert isinstance(session, MagicMock)
            assert get_async_db in app.dependency_overrides

        # Should clean up after context
        assert len(app.dependency_overrides) == 0

    def test_test_db_context_cleanup_on_exception(self) -> None:
        """Test that database context manager cleans up on exception."""
        app = FastAPI()
        mock_session = MagicMock(spec=AsyncSession)

        with pytest.raises(RuntimeError), test_db_context(app, mock_session):
            raise RuntimeError("Test exception")

        # Should still clean up after exception
        assert len(app.dependency_overrides) == 0


class TestModuleDepsCreation:
    """Test ModuleDeps mock creation functions."""

    def test_create_module_deps_mock_with_defaults(self) -> None:
        """Test creating ModuleDeps mock with default values."""
        deps = create_module_deps_mock()

        assert isinstance(deps, ModuleDeps)
        assert deps.module == ModuleLabel.TECH_CC
        assert isinstance(deps.request, MagicMock)
        assert isinstance(deps.db, MagicMock)
        assert isinstance(deps.settings, MagicMock)
        assert isinstance(deps.background_tasks, MagicMock)
        assert deps.request_id == "test-request-id"

    def test_create_module_deps_mock_with_custom_values(self) -> None:
        """Test creating ModuleDeps mock with custom values."""
        mock_request = MagicMock(spec=Request)
        mock_db = MagicMock(spec=AsyncSession)
        mock_settings = MagicMock(spec=Settings)
        mock_tasks = MagicMock(spec=BackgroundTasks)
        custom_request_id = "custom-request-id"

        deps = create_module_deps_mock(
            module=ModuleLabel.TECH_CC,
            request=mock_request,
            db_session=mock_db,
            settings=mock_settings,
            background_tasks=mock_tasks,
            request_id=custom_request_id,
        )

        assert deps.module == ModuleLabel.TECH_CC
        assert deps.request is mock_request
        assert deps.db is mock_db
        assert deps.settings is mock_settings
        assert deps.background_tasks is mock_tasks
        assert deps.request_id == custom_request_id

    def test_mock_module_deps_context(self) -> None:
        """Test module dependencies context manager."""
        mock_db = MagicMock(spec=AsyncSession)

        with mock_module_deps_context(db_session=mock_db) as deps:
            assert isinstance(deps, ModuleDeps)
            assert deps.db is mock_db
            assert deps.module == ModuleLabel.TECH_CC


class TestAsyncMockCreation:
    """Test async mock creation functions."""

    def test_create_async_mock_db(self) -> None:
        """Test creating async mock database."""
        mock_db = create_async_mock_db()

        assert isinstance(mock_db, AsyncMock)
        assert hasattr(mock_db, "execute")
        assert hasattr(mock_db, "commit")
        assert hasattr(mock_db, "rollback")
        assert hasattr(mock_db, "close")
        assert hasattr(mock_db, "refresh")
        assert hasattr(mock_db, "add")
        assert hasattr(mock_db, "add_all")
        assert hasattr(mock_db, "delete")
        assert hasattr(mock_db, "query")

        # Check that async methods are AsyncMock
        assert isinstance(mock_db.execute, AsyncMock)
        assert isinstance(mock_db.commit, AsyncMock)
        assert isinstance(mock_db.rollback, AsyncMock)
        assert isinstance(mock_db.close, AsyncMock)
        assert isinstance(mock_db.refresh, AsyncMock)

        # Check that sync methods are MagicMock
        assert isinstance(mock_db.add, MagicMock)
        assert isinstance(mock_db.add_all, MagicMock)
        assert isinstance(mock_db.delete, MagicMock)
        assert isinstance(mock_db.query, MagicMock)

    def test_create_health_check_mock_db(self) -> None:
        """Test creating health check specific mock database."""
        mock_db = create_health_check_mock_db()

        assert isinstance(mock_db, MagicMock)
        assert hasattr(mock_db, "execute")
        assert hasattr(mock_db, "scalar")
        assert isinstance(mock_db.execute, AsyncMock)
        assert isinstance(mock_db.scalar, AsyncMock)

    def test_create_crud_mock_db(self) -> None:
        """Test creating CRUD specific mock database."""
        mock_db = create_crud_mock_db()

        assert isinstance(mock_db, MagicMock)
        assert hasattr(mock_db, "execute")
        assert hasattr(mock_db, "scalar")
        assert hasattr(mock_db, "commit")
        assert hasattr(mock_db, "rollback")
        assert hasattr(mock_db, "add")
        assert hasattr(mock_db, "delete")
        assert hasattr(mock_db, "refresh")

        # Check async methods
        assert isinstance(mock_db.execute, AsyncMock)
        assert isinstance(mock_db.scalar, AsyncMock)
        assert isinstance(mock_db.commit, AsyncMock)
        assert isinstance(mock_db.rollback, AsyncMock)
        assert isinstance(mock_db.refresh, AsyncMock)

        # Check sync methods
        assert isinstance(mock_db.add, MagicMock)
        assert isinstance(mock_db.delete, MagicMock)


class TestFastAPITestOverrides:
    """Test FastAPI test override utilities."""

    def test_create_fastapi_test_overrides_with_db_session(self) -> None:
        """Test creating FastAPI overrides with database session."""
        mock_db = MagicMock(spec=AsyncSession)

        overrides = create_fastapi_test_overrides(db_session=mock_db)

        assert get_async_db in overrides
        assert get_async_session_maker in overrides
        assert overrides[get_async_db]() is mock_db
        assert overrides[get_async_session_maker]() is mock_db

    def test_create_fastapi_test_overrides_with_settings(self) -> None:
        """Test creating FastAPI overrides with settings."""
        mock_settings = MagicMock(spec=Settings)

        overrides = create_fastapi_test_overrides(settings=mock_settings)

        assert get_settings in overrides
        assert overrides[get_settings]() is mock_settings

    def test_create_fastapi_test_overrides_with_all_params(self) -> None:
        """Test creating FastAPI overrides with all parameters."""
        mock_db = MagicMock(spec=AsyncSession)
        mock_settings = MagicMock(spec=Settings)

        overrides = create_fastapi_test_overrides(
            db_session=mock_db,
            settings=mock_settings,
        )

        assert get_async_db in overrides
        assert get_async_session_maker in overrides
        assert get_settings in overrides
        assert overrides[get_async_db]() is mock_db
        assert overrides[get_async_session_maker]() is mock_db
        assert overrides[get_settings]() is mock_settings

    def test_create_fastapi_test_overrides_empty(self) -> None:
        """Test creating FastAPI overrides with no parameters."""
        overrides = create_fastapi_test_overrides()

        assert len(overrides) == 0
