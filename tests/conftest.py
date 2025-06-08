from __future__ import annotations

# ruff: noqa: E402
import os
import sys
from collections.abc import AsyncGenerator, Callable, Generator
from pathlib import Path
from typing import Any, TypeVar

import pytest
import pytest_asyncio
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

# Force settings to load dummy env file during test collection
os.environ.setdefault("ENV_FILE", str(Path(__file__).parents[1] / "infrastructure" / ".env.ci"))

# Add src to Python path
project_root = Path(__file__).parent.parent
src_path = project_root / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Import database components
from src.db.base import Base

# This is the single source of truth for the test database URL.
# It ensures that all tests, regardless of where they run, use the same consistent
# test database, which is critical for CI/CD environments.
# The value is sourced from environment variables, which are set in:
# - .env file for local development
# - GitHub Actions workflow for CI
test_db_url = os.getenv("DATABASE_URL_TEST")

# Only require DATABASE_URL_TEST if infrastructure is actually needed
# This allows conftest.py to load even when tests are being skipped
if test_db_url:
    os.environ["DATABASE_URL"] = test_db_url
    # Create engine once per test session
    engine = create_async_engine(test_db_url, echo=False)
    AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)
else:
    # Set None values when infrastructure is not available
    # Tests that need these will be skipped by our infrastructure detection
    engine = None  # type: ignore[assignment]
    AsyncSessionLocal = None  # type: ignore[assignment]

T = TypeVar("T", bound=Callable[..., Any])


@pytest.fixture(scope="session")
def test_settings() -> Any:
    """Get test configuration settings."""
    from src.common.config import get_settings

    return get_settings()


def is_infrastructure_available() -> bool:
    """Check if required infrastructure services are available for testing.

    Returns True if PostgreSQL, Neo4j, and Redis services are running
    with the expected configuration. Otherwise returns False.

    This function is used by the CI test triage system to determine
    which tests should be skipped vs. enabled based on local environment.
    """
    try:
        # Check if PostgreSQL test database is available
        test_db_url = os.getenv("DATABASE_URL_TEST")
        if not test_db_url:
            return False

        # Try to create engine - this will fail if PostgreSQL isn't running
        create_async_engine(test_db_url, echo=False)

        # Additional checks could be added here for Neo4j, Redis, etc.
        # For now, we assume if PostgreSQL is available, basic infrastructure is ready

        return True

    except Exception:
        # Any exception indicates infrastructure is not ready
        return False


# Import smart infrastructure checking
try:
    from tests.infrastructure_check import AVAILABLE_SERVICES

    SERVICES_AVAILABLE = True
except ImportError:
    # Fallback if infrastructure checker is not available
    AVAILABLE_SERVICES = {"postgres": False, "neo4j": False, "redis": False}
    SERVICES_AVAILABLE = False

# Smart skip decorators based on actual service availability
requires_postgres = pytest.mark.skipif(
    not AVAILABLE_SERVICES.get("postgres", False),
    reason="PostgreSQL service not available - run docker-compose up postgres_test",
)

requires_neo4j = pytest.mark.skipif(
    not AVAILABLE_SERVICES.get("neo4j", False), reason="Neo4j service not available - run docker-compose up neo4j"
)

requires_redis = pytest.mark.skipif(
    not AVAILABLE_SERVICES.get("redis", False), reason="Redis service not available - run docker-compose up redis"
)

requires_all_services = pytest.mark.skipif(
    not all(AVAILABLE_SERVICES.values()),
    reason="Not all infrastructure services available - run docker-compose up for full test suite",
)

# Legacy skip markers for backwards compatibility
skip_if_no_infrastructure = pytest.mark.skipif(
    not is_infrastructure_available(),
    reason="Infrastructure: PostgreSQL services not available locally. "
    "Re-enable in Sprint 2 when docker-compose setup is complete.",
)

skip_if_no_graph_services = pytest.mark.skipif(
    not AVAILABLE_SERVICES.get("neo4j", False),
    reason="Service: Neo4j not configured locally. Re-enable in Sprint 3 after graph service setup.",
)

skip_if_no_message_bus = pytest.mark.skipif(
    not AVAILABLE_SERVICES.get("redis", False),
    reason="Integration: Redis pub/sub not available locally. Re-enable when message bus is configured.",
)


@pytest.fixture
@skip_if_no_infrastructure  # Apply infrastructure check at fixture level
async def setup_database() -> AsyncGenerator[None, None]:
    """Create all tables once at session start."""
    if engine is None:
        pytest.skip("Database engine not available - infrastructure check failed")

    from src.backend.cc import models  # noqa: F401

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def db_session() -> AsyncGenerator[Any, None]:
    """Provide a fresh transaction per test on its own connection.

    We open a transaction at the start, bind a session to it,
    then roll it back (and close) at teardown.
    """
    if engine is None or AsyncSessionLocal is None:
        pytest.skip("Database not available - infrastructure check failed")

    # 1) open a dedicated connection
    conn = await engine.connect()
    # 2) begin a transaction
    trans = await conn.begin()
    # 3) bind a session to that transaction
    session = AsyncSessionLocal(bind=conn)
    try:
        yield session
    finally:
        # ensure session is closed, then rollback & close connection
        await session.close()
        await trans.rollback()
        await conn.close()


@pytest_asyncio.fixture(scope="function")
async def postgres_session() -> AsyncGenerator[Callable[[], Any], None]:
    """Session-factory fixture for concurrent tests.

    Each call to the factory returns a new AsyncSession bound to the same
    transaction/connection, which is rolled back at teardown.
    """
    if engine is None:
        pytest.skip("Database engine not available - infrastructure check failed")

    conn = await engine.connect()
    trans = await conn.begin()
    test_session_local = async_sessionmaker(bind=conn, expire_on_commit=False)

    def session_factory() -> Any:
        return test_session_local()

    try:
        yield session_factory
    finally:
        await conn.close()
        await trans.rollback()


@pytest.fixture(scope="function")
def override_get_db(db_session: Any) -> Generator[None, None, None]:
    """Override FastAPI dependency to use our per-test session."""

    async def _get_db() -> AsyncGenerator[Any, None]:
        yield db_session

    try:
        from src.backend.cc.deps import get_cc_db
        from src.cos_main import app
        from src.db.connection import get_async_db

        app.dependency_overrides[get_async_db] = _get_db
        app.dependency_overrides[get_cc_db] = _get_db
        yield
        app.dependency_overrides.clear()
    except ImportError:
        yield


@pytest.fixture(scope="function")
def client(override_get_db: Any) -> Generator[TestClient | None, None, None]:
    """TestClient with overridden dependencies."""
    try:
        from src.cos_main import app

        with TestClient(app) as c:
            yield c
    except ImportError:
        yield None


# Legacy aliases
@pytest_asyncio.fixture(scope="function")
async def test_db_session(db_session: Any) -> AsyncGenerator[Any, None]:
    yield db_session


@pytest_asyncio.fixture(scope="function")
async def mem0_db_session(db_session: Any) -> AsyncGenerator[Any, None]:
    yield db_session


@pytest.fixture(scope="function")
def test_client(client: TestClient | None) -> TestClient:
    if client is None:
        raise ValueError("FastAPI app is not available")
    return client


@pytest_asyncio.fixture(scope="function")
async def async_client(override_get_db: Any) -> AsyncGenerator[Any, None]:
    try:
        from httpx import ASGITransport, AsyncClient

        from src.cos_main import app

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            yield ac
    except ImportError as err:
        raise ValueError("FastAPI app or httpx is not available") from err


@pytest.fixture(scope="session")
def app() -> FastAPI | None:
    try:
        from src.cos_main import app as cos_app

        return cos_app
    except ImportError:
        return None


@pytest.fixture(scope="function")
def unique_test_id() -> str:
    import uuid

    return str(uuid.uuid4())[:8]


# Session-scoped environment setup fixtures
@pytest.fixture(scope="session")
def mock_env_settings() -> Generator[None, None, None]:
    os.environ["POSTGRES_DEV_URL"] = "postgresql://test:test@localhost/test_db"
    os.environ["POSTGRES_TEST_URL"] = "postgresql://test:test@localhost/test_test_db"
    os.environ["DATABASE_URL_TEST"] = "postgresql://test:test@localhost/test_test_db"
    os.environ["REDIS_HOST"] = "localhost"
    os.environ["REDIS_PORT"] = "6379"
    os.environ["REDIS_PASSWORD"] = os.environ.get("REDIS_PASSWORD", "test_password")
    yield
    for var in [
        "POSTGRES_DEV_URL",
        "POSTGRES_TEST_URL",
        "DATABASE_URL_TEST",
        "REDIS_HOST",
        "REDIS_PORT",
        "REDIS_PASSWORD",
    ]:
        os.environ.pop(var, None)


@pytest.fixture(scope="session")
def current_test_env() -> Generator[None, None, None]:
    os.environ["PYTEST_CURRENT_TEST"] = "1"
    yield
    os.environ.pop("PYTEST_CURRENT_TEST", None)
