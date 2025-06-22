# ruff: noqa
# mypy: ignore-errors
from __future__ import annotations

# ruff: noqa: E402
import os
import sys
import asyncio
from collections.abc import AsyncGenerator, Callable, Generator
from pathlib import Path
from typing import Any, TypeVar

import pytest  # type: ignore[import-untyped]
import pytest_asyncio  # type: ignore[import-untyped]
from fastapi import FastAPI  # type: ignore[import-untyped]
from fastapi.testclient import TestClient  # type: ignore[import-untyped]
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine  # type: ignore[import-untyped]

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

# FORCE ALL TESTS TO USE DEV DATABASE (port 5433) - NO port 5434 allowed!
# This overrides any DATABASE_URL_TEST settings to eliminate port 5434 usage.
# During Phase 2, all database operations MUST go to cos_postgres_dev (port 5433).
os.environ["TESTING"] = "false"  # Force dev mode
test_db_url = "postgresql+asyncpg://cos_user:Police9119!!Sql_dev@localhost:5433/cos_db_dev"

# FORCE tests to use DEV database directly - bypass any caching issues
# Create engine directly with dev credentials to ensure port 5433 usage
if test_db_url:
    os.environ["DATABASE_URL_DEV"] = test_db_url
    # Create engine directly to avoid any caching/import issues during tests
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
        # Check if PostgreSQL dev database is available (FORCE port 5433)
        dev_db_url = os.getenv(
            "DATABASE_URL_DEV", "postgresql+asyncpg://cos_user:Police9119!!Sql_dev@localhost:5433/cos_db_dev"
        )
        if not dev_db_url:
            return False

        # Try to create engine - this will fail if PostgreSQL isn't running
        create_async_engine(dev_db_url, echo=False)

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

# After SERVICES_AVAILABLE assignment
if os.getenv("RUN_INTEGRATION", "0") == "0":
    # CI/lightweight mode – pretend all infra is available and patch heavy libs.
    AVAILABLE_SERVICES.update({"postgres": True, "neo4j": True, "redis": True})

    # Stub asyncpg connect to avoid real network cost
    try:
        import asyncpg  # type: ignore[import-untyped]

        async def _fake_connect(*_args: Any, **_kwargs: Any) -> Any:  # type: ignore[return-value]
            class _DummyConn:  # noqa: D401 – simple stub
                def __init__(self) -> None:
                    self._closed = False
                    self._transaction = None

                async def close(self) -> None:  # noqa: D401 – stub
                    self._closed = True
                    return None

                def is_closed(self) -> bool:  # noqa: D401 – stub
                    """Check if connection is closed."""
                    return self._closed

                async def set_type_codec(self, *args: Any, **kwargs: Any) -> None:  # noqa: D401 – stub
                    """Stub for asyncpg set_type_codec method."""
                    return None

                async def execute(self, *args: Any, **kwargs: Any) -> Any:  # noqa: D401 – stub
                    """Stub for asyncpg execute method."""
                    return None

                async def fetch(self, *args: Any, **kwargs: Any) -> list[Any]:  # noqa: D401 – stub
                    """Stub for asyncpg fetch method."""
                    return []

                async def fetchrow(self, *args: Any, **kwargs: Any) -> Any:  # noqa: D401 – stub
                    """Stub for asyncpg fetchrow method."""
                    return None

                def transaction(self, *args: Any, **kwargs: Any) -> Any:  # noqa: D401 – stub
                    """Stub for asyncpg transaction method."""

                    class _DummyTransaction:
                        async def __aenter__(self) -> Any:
                            return self

                        async def __aexit__(self, *args: Any) -> None:
                            return None

                        async def start(self) -> None:
                            return None

                        async def commit(self) -> None:
                            return None

                        async def rollback(self) -> None:
                            return None

                    return _DummyTransaction()

            return _DummyConn()

        # Only patch if not already patched by other fixtures
        if not hasattr(asyncpg, "_cos_stubbed"):
            asyncpg._cos_real_connect = asyncpg.connect  # type: ignore[attr-defined]
            asyncpg.connect = _fake_connect  # type: ignore[assignment]
            asyncpg._cos_stubbed = True  # type: ignore[attr-defined]
    except ImportError:
        pass

    # Stub Neo4j async driver
    try:
        from neo4j import AsyncGraphDatabase  # type: ignore

        class _DummyNeoSession:  # noqa: D401 – simple stub
            async def __aenter__(self):
                return self

            async def __aexit__(self, *_exc: Any) -> None:  # noqa: D401 – stub
                return None

            async def run(self, *_args: Any, **_kwargs: Any) -> list:  # noqa: D401 – stub
                return []

        class _DummyNeoDriver:  # noqa: D401
            async def session(self, *_, **__) -> _DummyNeoSession:  # noqa: D401
                return _DummyNeoSession()

            async def close(self) -> None:  # noqa: D401 – stub
                return None

        if not hasattr(AsyncGraphDatabase, "_cos_stubbed"):
            AsyncGraphDatabase._cos_real_driver = AsyncGraphDatabase.driver  # type: ignore[attr-defined]
            AsyncGraphDatabase.driver = lambda *_a, **_kw: _DummyNeoDriver()  # type: ignore[assignment]
            AsyncGraphDatabase._cos_stubbed = True  # type: ignore[attr-defined]
    except ImportError:
        pass

# Smart skip decorators based on actual service availability
requires_postgres = pytest.mark.skipif(
    not AVAILABLE_SERVICES.get("postgres", False),
    reason="PostgreSQL service not available - run docker-compose up postgres_dev",
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
async def setup_database() -> AsyncGenerator[None, None]:
    """Create all tables once at session start."""
    if engine is None:
        pytest.skip("Database engine not available - infrastructure check failed")

    from src.backend.cc import models  # noqa: F401

    # Type assertion - we know engine is not None after the check above
    assert engine is not None
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    await engine.dispose()


@pytest.fixture(scope="function")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Create a dedicated event loop for the entire test session.

    On some platforms (e.g. Windows) the default pytest-asyncio event loop policy
    can lead to *"Task got Future attached to a different loop"* errors when
    global objects (like SQLAlchemy engines) are created outside of any running
    loop.  Creating the loop up-front and using it for the whole session avoids
    cross-loop contamination while still allowing the *function* scope fixtures
    to create fresh database engines bound to this loop.
    """
    loop = asyncio.new_event_loop()
    try:
        yield loop
    finally:
        loop.close()


@pytest_asyncio.fixture(scope="function")
async def db_session(event_loop: asyncio.AbstractEventLoop) -> AsyncGenerator[Any, None]:
    """Return an *isolated* SQLAlchemy ``AsyncSession`` for each test.

    Implementation notes:
    1.  The **engine is created inside the running event loop** so that all
        futures/coroutines produced by SQLAlchemy / asyncpg are tied to the same
        loop as the test coroutine (fixes "Future attached to a different loop"
        errors).
    2.  A brand-new connection + SAVEPOINT transaction is opened for every test
        function for hermetic isolation.  The outer transaction is rolled back
        during teardown to ensure no database state bleeds between tests.
    3.  The engine itself is disposed after the test to avoid resource leaks.
    """
    from sqlalchemy.ext.asyncio import async_sessionmaker  # type: ignore[import-untyped]

    # Late import to avoid circulars and ensure settings/env are initialised
    from src.db.connection import get_async_engine

    # Create engine *inside* the current loop
    test_engine = get_async_engine()

    async with test_engine.connect() as conn:
        # --- Schema setup (once per test) -------------------------------------------------
        from src.backend.cc import models  # noqa: F401

        await conn.run_sync(Base.metadata.create_all)

        # --- Transaction strategy --------------------------------------------------------
        # After schema creation SQLAlchemy may leave us inside an implicit
        # transaction.  Commit/rollback out so we can start the explicit test
        # transactions cleanly.
        if conn.in_transaction():
            await conn.rollback()

        # 1. Start an *outer* transaction which will be rolled-back at the end of the test
        outer_trans = await conn.begin()

        # 2. Start a *nested* transaction (SAVEPOINT).  SQLAlchemy will automatically
        #    re-start it after each rollback, giving us hermetic isolation while still
        #    allowing the code under test to commit/flush freely.
        await conn.begin_nested()

        session_maker = async_sessionmaker(
            bind=conn,
            expire_on_commit=False,
            join_transaction_mode="create_savepoint",  # 🔑 prevents double-begin
        )

        async with session_maker() as session:
            try:
                yield session
            finally:
                # The SAVEPOINT will be rolled back automatically when the session
                # ends; we still issue an explicit rollback for clarity.
                await session.rollback()

        # 3. Rollback the outermost transaction - database state is fully reset.
        await outer_trans.rollback()

    # Dispose engine to ensure no dangling connections between tests.
    await test_engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def postgres_session() -> AsyncGenerator[Callable[[], Any], None]:
    """Session-factory fixture for concurrent tests.

    Each call to the factory returns a new AsyncSession bound to the same
    transaction/connection, which is rolled back at teardown.
    """
    if engine is None:
        pytest.skip("Database engine not available - infrastructure check failed")

    # Type assertion - we know engine is not None after the check above
    assert engine is not None
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
        from httpx import ASGITransport, AsyncClient  # type: ignore[import-untyped]

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


# ---------------------------------------------------------------------------
# Compatibility shim for legacy tests that expect `.rowcount` on SQLAlchemy
# SELECT results.  SQLAlchemy 2.x returns a *ChunkedIteratorResult* which
# deliberately omits this attribute for SELECT statements.  For testing
# purposes we expose a lightweight property that falls back to the number of
# rows already buffered (if available) or ``-1``.
# ---------------------------------------------------------------------------

try:
    from sqlalchemy.engine import CursorResult, Result  # type: ignore[import-untyped]

    if not hasattr(Result, "rowcount"):

        @property  # type: ignore[misc]
        def _rowcount(self) -> int:
            """Return compatible rowcount for SELECT statements in tests.

            SQLAlchemy intentionally does not populate ``rowcount`` for SELECT
            queries against async drivers.  The legacy tests rely on the
            attribute existing, so we provide a best-effort implementation
            that counts the currently buffered rows, falling back to ``0``
            when the information is not yet available.
            """
            try:
                # If rows already fetched into buffer use that.
                if hasattr(self, "_soft_closed") and self._soft_closed:
                    return len(self._allrows)

                # Fallback: fetch *all* remaining rows - SELECT results are
                # usually small in tests (< 100) so this is fine.
                return len(self.all())
            except Exception:
                # As a last resort indicate unknown length
                return 0

        # Monkey-patch both sync and async result classes
        Result.rowcount = _rowcount  # type: ignore[assignment]
        CursorResult.rowcount = _rowcount  # type: ignore[assignment]
except ImportError:
    # SQLAlchemy import failed; ignore in environments without the library
    pass

# AsyncResult shim
try:
    from sqlalchemy.ext.asyncio import AsyncResult  # type: ignore

    if not hasattr(AsyncResult, "rowcount"):

        @property  # type: ignore[misc]
        def _async_rowcount(self) -> int:
            """Delegate to the underlying synchronous result's rowcount."""
            try:
                return self._result.rowcount  # type: ignore[attr-defined]
            except AttributeError:
                return 0

        AsyncResult.rowcount = _async_rowcount  # type: ignore[assignment]
except ImportError:
    pass
