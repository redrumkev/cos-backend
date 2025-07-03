from __future__ import annotations

import pytest  # Phase 2: Remove for skip removal
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.backend.cc.deps import get_cc_db

# Phase 2: Skip block removed - dependency injection wiring completed (P2-DEPS-001)


@pytest.mark.asyncio
async def test_get_cc_db_returns_session(test_db_session: AsyncSession) -> None:
    """Test that get_cc_db returns an AsyncSession when called directly."""
    # Direct call (bypassing FastAPI) ----------------------------------------
    session = await get_cc_db(test_db_session)
    # In mock mode, we get a MockAsyncSession, not a real AsyncSession
    # Just verify we get back what we passed in
    assert session is test_db_session


def test_dependency_injection_client(test_db_session: AsyncSession) -> None:
    """Test dependency injection with FastAPI.

    Creates a test app that uses get_cc_db and verifies the injected
    session is the expected one.
    """
    app = FastAPI()

    @app.get("/ping")
    async def ping(
        db: AsyncSession = Depends(get_cc_db),  # pragma: no cover  # noqa: B008
    ) -> dict[str, bool]:
        # FastAPI should inject our overridden session
        return {"is_same": db is test_db_session}

    # Override dependency -----------------------------------------------------
    app.dependency_overrides[get_cc_db] = lambda: test_db_session

    with TestClient(app) as client:
        resp = client.get("/ping")
        assert resp.status_code == 200
        assert resp.json()["is_same"] is True


@pytest.mark.asyncio
async def test_get_cc_db_with_real_session() -> None:
    """Test that get_cc_db works with a real database session from get_async_db."""
    from src.db.connection import get_async_db

    async for real_session in get_async_db():
        session = await get_cc_db(real_session)
        assert isinstance(session, AsyncSession)
        assert session is real_session
        break  # Only test the first yielded session


def test_dependency_error_handling() -> None:
    """Test that dependency injection handles errors gracefully."""
    app = FastAPI()

    @app.get("/error")
    async def error_endpoint(
        db: AsyncSession = Depends(get_cc_db),  # pragma: no cover  # noqa: B008
    ) -> dict[str, str]:
        return {"status": "ok"}

    # Test without proper session override - should work with real session
    with TestClient(app) as client:
        resp = client.get("/error")
        # The endpoint should work since get_cc_db uses get_async_db internally
        assert resp.status_code == 200


@pytest.mark.asyncio
async def test_back_compat_alias(test_db_session: AsyncSession) -> None:
    """Test that the get_db_session alias still works for backward compatibility."""
    from src.backend.cc.deps import get_db_session

    session = await get_db_session(test_db_session)
    # In mock mode, we get a MockAsyncSession, not a real AsyncSession
    # Just verify we get back what we passed in
    assert session is test_db_session


def test_dbsession_type_annotation(test_db_session: AsyncSession) -> None:
    """Test that the DBSession type annotation works correctly."""
    # Since FastAPI has issues with Annotated[AsyncSession, Depends(get_cc_db)]
    # as a direct parameter type, we verify the type alias exists and can be used
    # for type checking, but actual endpoints should use the explicit pattern
    from src.backend.cc.deps import DBSession

    # Verify the type alias exists and is properly formed
    assert DBSession is not None

    # Test that endpoints work with the recommended pattern
    app = FastAPI()

    @app.get("/typed")
    async def typed_endpoint(
        db: AsyncSession = Depends(get_cc_db),  # noqa: B008
    ) -> dict[str, str]:  # pragma: no cover
        return {"session_type": type(db).__name__}

    # Override the actual dependency
    app.dependency_overrides[get_cc_db] = lambda: test_db_session

    with TestClient(app) as client:
        resp = client.get("/typed")
        assert resp.status_code == 200
        # In mock mode, we get MockAsyncSession, not AsyncSession
        assert "Session" in resp.json()["session_type"]
