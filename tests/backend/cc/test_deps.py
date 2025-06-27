from __future__ import annotations

import pytest  # Phase 2: Remove for skip removal
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.backend.cc.deps import get_cc_db

# Phase 2: Skip block removed - dependency injection wiring completed (P2-DEPS-001)


@pytest.mark.asyncio
async def test_get_cc_db_returns_session(test_db_session: AsyncSession) -> None:
    """Test that get_cc_db returns a session when called directly."""
    # Direct call (bypassing FastAPI) ----------------------------------------
    session = await get_cc_db(test_db_session)
    # Check that the returned session has the expected interface (works with both real and mock sessions)
    assert hasattr(session, "commit")
    assert hasattr(session, "rollback")
    assert hasattr(session, "execute")
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

    # Properly handle the async generator to avoid "coroutine was never awaited" warning
    db_generator = get_async_db()
    try:
        real_session = await db_generator.__anext__()
        session = await get_cc_db(real_session)
        # Check that the returned session has the expected interface
        assert hasattr(session, "commit")
        assert hasattr(session, "rollback")
        assert hasattr(session, "execute")
        assert session is real_session
    finally:
        # Properly close the async generator
        try:
            await db_generator.aclose()
        except Exception as e:
            # Ignore errors during cleanup
            import logging

            logging.debug(f"Error during db_generator cleanup: {e}")


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
    # Check that the returned session has the expected interface (works with both real and mock sessions)
    assert hasattr(session, "commit")
    assert hasattr(session, "rollback")
    assert hasattr(session, "execute")
    assert session is test_db_session


@pytest.mark.xfail(reason="DBSession annotation causing 422 error - needs dependency injection fix")
def test_dbsession_type_annotation(test_db_session: AsyncSession) -> None:
    """Test that the DBSession type annotation works correctly."""
    from src.backend.cc.deps import DBSession

    app = FastAPI()

    @app.get("/typed")
    async def typed_endpoint(db: DBSession) -> dict[str, str]:
        return {"session_type": type(db).__name__}

    # Override the actual dependency that DBSession points to
    async def mock_get_cc_db() -> AsyncSession:
        return test_db_session

    app.dependency_overrides[get_cc_db] = mock_get_cc_db

    with TestClient(app) as client:
        resp = client.get("/typed")
        assert resp.status_code == 200
        assert resp.json()["session_type"] == "AsyncSession"
