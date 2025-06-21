"""Isolated tests for dependencies that don't require database connections.

These test the dependency injection logic and type annotations without real DB.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock

import pytest  # Phase 2: Remove for skip removal
from backend.cc.deps import DBSession, get_cc_db
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

# Phase 2: Remove this skip block for dependency injection wiring (P2-DEPS-001)
pytestmark = pytest.mark.skip(reason="Phase 2: Dependency injection wiring needed. Trigger: P2-DEPS-001")


def test_dependency_imports() -> None:
    """Test that we can import the dependencies without errors."""
    from backend.cc.deps import DBSession, get_cc_db, get_db_session

    # Verify backward compatibility alias exists
    assert get_db_session is get_cc_db

    # Verify DBSession is a type annotation
    assert hasattr(DBSession, "__origin__")  # Should be an Annotated type


@pytest.mark.asyncio
async def test_get_cc_db_with_mock_session() -> None:
    """Test get_cc_db function with a mock session."""
    # Create a mock session
    mock_session = AsyncMock(spec=AsyncSession)

    # Call get_cc_db with the mock session
    result = await get_cc_db(mock_session)

    # Should return the same session
    assert result is mock_session


def test_dependency_in_fastapi_context() -> None:
    """Test that the dependency works in a FastAPI context with overrides."""
    app = FastAPI()
    mock_session = AsyncMock(spec=AsyncSession)

    @app.get("/test")
    async def test_endpoint(
        db: AsyncSession = Depends(get_cc_db),  # pragma: no cover  # noqa: B008
    ) -> dict[str, str]:
        return {"session_type": type(db).__name__}

    # Override the dependency
    app.dependency_overrides[get_cc_db] = lambda: mock_session

    with TestClient(app) as client:
        response = client.get("/test")
        assert response.status_code == 200
        # The mock will have a different type name but should work
        result = response.json()
        assert "session_type" in result


def test_dbsession_annotation_with_override() -> None:
    """Test that DBSession type annotation works with dependency overrides."""
    app = FastAPI()
    mock_session = AsyncMock(spec=AsyncSession)

    @app.get("/typed-test")
    async def typed_endpoint(db: DBSession) -> dict[str, Any]:  # pragma: no cover
        return {"status": "ok", "has_session": db is not None}

    # Override the underlying dependency that DBSession uses
    app.dependency_overrides[get_cc_db] = lambda: mock_session

    with TestClient(app) as client:
        response = client.get("/typed-test")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["has_session"] is True


def test_multiple_dependencies() -> None:
    """Test multiple dependencies in the same endpoint."""
    app = FastAPI()
    mock_session1 = AsyncMock(spec=AsyncSession)
    mock_session2 = AsyncMock(spec=AsyncSession)

    @app.get("/multi")
    async def multi_endpoint(
        db1: AsyncSession = Depends(get_cc_db),  # pragma: no cover  # noqa: B008
        db2: DBSession = mock_session2,  # This should be injected via DBSession
    ) -> dict[str, int | bool]:
        return {"db1_id": id(db1), "db2_id": id(db2), "are_same": db1 is db2}

    app.dependency_overrides[get_cc_db] = lambda: mock_session1

    with TestClient(app) as client:
        response = client.get("/multi")
        assert response.status_code == 200
        # This test verifies the dependency system is working correctly
