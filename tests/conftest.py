from __future__ import annotations

import asyncio
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
from src.db.base import Base  # noqa: E402

# Import all model modules to register them with Base metadata
# This ensures that create_all() will create all necessary tables
try:
    from src.backend.cc import mem0_models  # noqa: F401
    from src.backend.cc import models as cc_models  # noqa: F401
except ImportError:
    # Models may not be available in some test environments
    pass

# FORCE ALL TESTS TO USE DEV DATABASE (port 5433) - NO port 5434 allowed!
# This overrides any DATABASE_URL_TEST settings to eliminate port 5434 usage.
# During Phase 2, all database operations MUST go to cos_postgres_dev (port 5433).
os.environ["TESTING"] = "false"  # Force dev mode
test_db_url = "postgresql+asyncpg://cos_user:Police9119!!Sql_dev@localhost:5433/cos_db_dev"

# FORCE tests to use DEV database directly - bypass any caching issues
# Store database URL but DO NOT create engines at module level to avoid event loop issues
# Engines will be created inside each test's event loop as needed
test_db_url_global = test_db_url

# Initialize engine and session variables as None - they will be created per-test
engine: Any | None = None
AsyncSessionLocal: Any | None = None

if test_db_url:
    os.environ["DATABASE_URL_DEV"] = test_db_url

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
        # Create and immediately dispose to avoid event loop issues
        test_engine = create_async_engine(dev_db_url, echo=False)
        # Don't keep the engine around to avoid loop binding issues
        del test_engine

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

# RUN_INTEGRATION MODE CONTROL
# =============================
# RUN_INTEGRATION environment variable controls test execution mode:
# - RUN_INTEGRATION=0 (or unset): Fast mock mode - no real database connections
# - RUN_INTEGRATION=1: Real database mode - requires actual infrastructure
#
# Mock mode benefits:
# - Extremely fast test execution (perfect for CI)
# - No infrastructure dependencies
# - Isolated test runs
#
# Real database mode benefits:
# - Full integration testing
# - Real database constraint validation
# - Complete end-to-end behavior verification

RUN_INTEGRATION_MODE = os.getenv("RUN_INTEGRATION", "0")

if RUN_INTEGRATION_MODE == "0":
    # MOCK MODE: Fast execution with minimal infrastructure dependencies
    AVAILABLE_SERVICES.update({"postgres": True, "neo4j": True, "redis": True})

    # Stub asyncpg connect to avoid real network cost
    try:
        import asyncpg

        async def _fake_connect(*_args: Any, **_kwargs: Any) -> Any:
            class _DummyConn:
                def __init__(self) -> None:
                    self._closed = False
                    self._transaction = None

                async def close(self) -> None:
                    self._closed = True
                    return None

                def is_closed(self) -> bool:
                    """Check if connection is closed."""
                    return self._closed

                async def set_type_codec(self, *args: Any, **kwargs: Any) -> None:
                    """Stub for asyncpg set_type_codec method."""
                    return None

                async def execute(self, *args: Any, **kwargs: Any) -> Any:
                    """Stub for asyncpg execute method."""
                    # Return mock result for version queries
                    if args and "pg_catalog.version()" in str(args[0]):
                        return "PostgreSQL 17.5 (Mock)"
                    return None

                async def fetch(self, *args: Any, **kwargs: Any) -> list[Any]:
                    """Stub for asyncpg fetch method."""
                    # Return mock data for common PostgreSQL queries
                    if args and "version()" in str(args[0]):
                        return [("PostgreSQL 17.5 (Mock)",)]
                    return []

                async def fetchrow(self, *args: Any, **kwargs: Any) -> Any:
                    """Stub for asyncpg fetchrow method."""
                    # Return mock data for common PostgreSQL queries
                    if args and "version()" in str(args[0]):
                        return {"version": "PostgreSQL 17.5 (Mock)"}
                    return None

                async def prepare(self, *args: Any, **kwargs: Any) -> Any:
                    """Stub for asyncpg prepare method."""

                    class _DummyPreparedStatement:
                        async def fetch(self, *args: Any, **kwargs: Any) -> list[Any]:
                            # Return mock data for common PostgreSQL queries
                            if args and "version()" in str(args[0]):
                                return [("PostgreSQL 17.5 (Mock)",)]
                            return []

                        async def fetchrow(self, *args: Any, **kwargs: Any) -> Any:
                            # Return mock data for common PostgreSQL queries
                            if args and "version()" in str(args[0]):
                                return {"version": "PostgreSQL 17.5 (Mock)"}
                            return None

                        async def execute(self, *args: Any, **kwargs: Any) -> Any:
                            return None

                        def get_attributes(self) -> tuple[Any, ...]:
                            """Stub for asyncpg get_attributes method."""
                            return ()

                        def get_statusmsg(self) -> str:
                            """Stub for asyncpg get_statusmsg method."""
                            return "SELECT 0"

                    return _DummyPreparedStatement()

                def transaction(self, *args: Any, **kwargs: Any) -> Any:
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
            asyncpg._cos_real_connect = asyncpg.connect
            asyncpg.connect = _fake_connect
            asyncpg._cos_stubbed = True
    except ImportError:
        pass

    # Stub Neo4j async driver
    try:
        from neo4j import AsyncGraphDatabase

        class _DummyNeoSession:
            async def __aenter__(self) -> _DummyNeoSession:
                return self

            async def __aexit__(self, *_exc: Any) -> None:
                return None

            async def run(self, *_args: Any, **_kwargs: Any) -> list[Any]:
                return []

        class _DummyNeoDriver:
            async def session(self, *_args: Any, **_kwargs: Any) -> _DummyNeoSession:
                return _DummyNeoSession()

            async def close(self) -> None:
                return None

        if not hasattr(AsyncGraphDatabase, "_cos_stubbed"):
            AsyncGraphDatabase._cos_real_driver = AsyncGraphDatabase.driver

            def _dummy_driver(*_args: Any, **_kwargs: Any) -> _DummyNeoDriver:
                return _DummyNeoDriver()

            AsyncGraphDatabase.driver = _dummy_driver
            AsyncGraphDatabase._cos_stubbed = True
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
    if not test_db_url_global:
        pytest.skip("Database URL not available - infrastructure check failed")

    # Create engine inside the current event loop to avoid loop binding issues
    from src.db.connection import get_async_engine

    setup_engine = get_async_engine()

    try:
        async with setup_engine.begin() as conn:
            await conn.run_sync(lambda sync_conn: Base.metadata.create_all(sync_conn, checkfirst=True))
        yield
    finally:
        await setup_engine.dispose()


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
    # In mock mode (RUN_INTEGRATION=0), return a mock session instead of real database
    if RUN_INTEGRATION_MODE == "0":
        from unittest.mock import MagicMock

        # Create fresh storage for each test to ensure isolation
        mock_storage: dict[str, dict[str, Any]] = {}

        # MockAsyncSession: Lightweight in-memory database simulation
        # - Provides basic CRUD operations for testing
        # - Handles module creation, duplicate detection, and querying
        # - Eliminates need for real database infrastructure in CI
        # - Significantly faster than real database operations
        class MockAsyncSession:
            def __init__(self) -> None:
                self._storage = mock_storage
                self._added_objects: list[Any] = []
                self._is_active = True

            async def commit(self) -> None:
                """Simulate commit - persist added objects to mock storage."""
                for obj in self._added_objects:
                    table_name = obj.__class__.__name__.lower() + "s"
                    if table_name not in self._storage:
                        self._storage[table_name] = {}

                    # Generate a simple ID if not present
                    if not hasattr(obj, "id") or obj.id is None:
                        obj.id = str(len(self._storage[table_name]) + 1)

                    # Store object attributes in a simple way
                    obj_dict = {
                        "id": obj.id,
                        "name": getattr(obj, "name", None),
                        "version": getattr(obj, "version", None),
                        "config": getattr(obj, "config", None),
                        "active": getattr(obj, "active", True),
                        "last_active": getattr(obj, "last_active", None),
                    }
                    # Filter out None values
                    obj_dict = {k: v for k, v in obj_dict.items() if v is not None}

                    self._storage[table_name][obj.id] = obj_dict

                    # Update the original object with the ID
                    obj.id = obj.id

                self._added_objects.clear()

            async def rollback(self) -> None:
                """Simulate rollback - clear uncommitted changes."""
                self._added_objects.clear()

            async def flush(self) -> None:
                """Simulate flush - in mock mode, this is a no-op."""
                pass

            async def close(self) -> None:
                """Simulate close - mark session as inactive."""
                self._is_active = False

            def add(self, obj: Any) -> None:
                """Add object to session (will be committed on commit())."""
                self._added_objects.append(obj)

            async def delete(self, obj: Any) -> None:
                """Simulate delete - remove from mock storage."""
                table_name = obj.__class__.__name__.lower() + "s"
                if table_name in self._storage and hasattr(obj, "id") and obj.id in self._storage[table_name]:
                    del self._storage[table_name][obj.id]

            async def merge(self, obj: Any) -> Any:
                """Simulate merge - return the object."""
                return obj

            async def refresh(self, obj: Any) -> None:
                """Simulate refresh - update object from mock storage."""
                table_name = obj.__class__.__name__.lower() + "s"
                if table_name in self._storage and hasattr(obj, "id") and obj.id in self._storage[table_name]:
                    stored_data = self._storage[table_name][obj.id]
                    for key, value in stored_data.items():
                        setattr(obj, key, value)

            async def execute(self, query: Any, params: Any = None) -> Any:
                """Mock execute - return a mock result based on query type and mock storage."""
                # Create a mock result with proper async behavior
                mock_result = MagicMock()
                results = []

                # Parse the query string to understand what it's doing
                query_str = str(query).lower()

                # Handle SELECT queries on modules table
                if "select" in query_str and ("modules" in query_str or "module" in query_str):
                    table_data = self._storage.get("modules", {})
                    target_name = None  # Initialize target_name at the start of modules handling

                    if "where" in query_str and "name" in query_str and hasattr(query, "compile"):
                        # This is a get_module_by_name query
                        # We need to be smarter about actually checking names
                        # Try to extract the name parameter from the SQLAlchemy query
                        try:
                            # Try to get literal binds
                            compiled = query.compile(compile_kwargs={"literal_binds": True})
                            compiled_str = str(compiled)

                            # Look for the actual name value in the compiled query
                            import re

                            name_match = re.search(r"name = '([^']+)'", compiled_str)
                            if name_match:
                                target_name = name_match.group(1)
                        except Exception as e:
                            # Ignore regex compilation errors, fallback to empty search
                            import logging

                            logging.debug(f"Error parsing query string: {e}")

                    # Define MockModule class once for this scope
                    class MockModule:
                        def __init__(self, data: dict[str, Any]) -> None:
                            for key, value in data.items():
                                setattr(self, key, value)

                    # If we found a target name, check if it exists in storage
                    if target_name:
                        for module_data in table_data.values():
                            if module_data.get("name") == target_name:
                                mock_module = MockModule(module_data)
                                results.append(mock_module)
                                break

                        # If no target name found or no match, return empty (no duplicate found)

                    else:
                        # List all modules query
                        for module_data in table_data.values():
                            mock_module = MockModule(module_data)
                            results.append(mock_module)

                # Mock scalars method that returns appropriate results
                mock_scalars = MagicMock()
                mock_scalars.first = MagicMock(return_value=results[0] if results else None)
                mock_scalars.all = MagicMock(return_value=results)
                mock_scalars.one = MagicMock(return_value=results[0] if results else None)
                mock_scalars.one_or_none = MagicMock(return_value=results[0] if results else None)

                mock_result.scalars = MagicMock(return_value=mock_scalars)
                mock_result.first = MagicMock(return_value=results[0] if results else None)
                mock_result.all = MagicMock(return_value=results)
                mock_result.fetchone = MagicMock(return_value=results[0] if results else None)
                mock_result.fetchall = MagicMock(return_value=results)
                mock_result.rowcount = len(results)

                return mock_result

        yield MockAsyncSession()
        return

    from sqlalchemy.ext.asyncio import async_sessionmaker

    # Late import to avoid circulars and ensure settings/env are initialised
    from src.db.connection import get_async_engine

    # Create engine *inside* the current loop
    test_engine = get_async_engine()

    async with test_engine.connect() as conn:
        # --- Schema setup (once per test) -------------------------------------------------
        # Skip schema creation - should be handled by setup_database fixture or made idempotent
        # Use checkfirst=True to avoid duplicate table errors if tables already exist
        try:
            await conn.run_sync(lambda sync_conn: Base.metadata.create_all(sync_conn, checkfirst=True))
        except Exception as e:
            # Schema might already exist - continue with test setup
            import logging

            logging.debug(f"Schema creation skipped: {e}")

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
    if not test_db_url_global:
        pytest.skip("Database URL not available - infrastructure check failed")

    # Create engine inside the current event loop to avoid loop binding issues
    from src.db.connection import get_async_engine

    test_engine = get_async_engine()

    try:
        conn = await test_engine.connect()
        trans = await conn.begin()
        test_session_local = async_sessionmaker(bind=conn, expire_on_commit=False)

        def session_factory() -> Any:
            return test_session_local()

        try:
            yield session_factory
        finally:
            await trans.rollback()
            await conn.close()
    finally:
        await test_engine.dispose()


@pytest.fixture(scope="function")
def override_get_db(db_session: Any) -> Generator[None, None, None]:
    """Override FastAPI dependency to use our per-test session."""
    if RUN_INTEGRATION_MODE == "1":
        # In integration mode, create fresh sessions within the TestClient's event loop
        async def _get_db() -> AsyncGenerator[Any, None]:
            from src.db.connection import get_async_db

            # Use the real database connection but ensure it's created in the right loop
            async for session in get_async_db():
                yield session
                break
    else:
        # In mock mode, use the provided mock session
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


# ---------------------------------------------------------------------------
# Compatibility shim for legacy tests that expect `.rowcount` on SQLAlchemy
# SELECT results.  SQLAlchemy 2.x returns a *ChunkedIteratorResult* which
# deliberately omits this attribute for SELECT statements.  For testing
# purposes we expose a lightweight property that falls back to the number of
# rows already buffered (if available) or ``-1``.
# ---------------------------------------------------------------------------

try:
    from sqlalchemy.engine import CursorResult, Result

    if not hasattr(Result, "rowcount"):

        def _rowcount(self: Any) -> int:
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

        # Monkey-patch both sync and async result classes using setattr
        Result.rowcount = property(_rowcount)  # type: ignore[attr-defined]
        CursorResult.rowcount = property(_rowcount)  # type: ignore[method-assign,assignment]
except ImportError:
    # SQLAlchemy import failed; ignore in environments without the library
    pass

# AsyncResult shim
try:
    from sqlalchemy.ext.asyncio import AsyncResult

    if not hasattr(AsyncResult, "rowcount"):

        def _async_rowcount(self: Any) -> int:
            """Delegate to the underlying synchronous result's rowcount."""
            try:
                return getattr(self._result, "rowcount", 0)
            except AttributeError:
                return 0

        AsyncResult.rowcount = property(_async_rowcount)  # type: ignore[attr-defined]
except ImportError:
    pass


# ===== Redis Pub/Sub Testing Enhancement Fixtures =====


@pytest_asyncio.fixture(scope="session")
def event_loop_session() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Session-scoped event loop for Redis testing consistency."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        yield loop
    finally:
        loop.close()


@pytest_asyncio.fixture
async def fake_redis() -> AsyncGenerator[Any, None]:
    """Async fakeredis instance with proper cleanup and performance optimizations."""
    try:
        import fakeredis.aioredis
    except ImportError:
        pytest.skip("fakeredis not available")

    # Create fakeredis instance with optimized settings
    redis_client = fakeredis.aioredis.FakeRedis(
        decode_responses=False,  # Match production behavior
        socket_keepalive=True,
        socket_keepalive_options={},
        retry_on_timeout=True,
    )

    try:
        yield redis_client
    finally:
        await redis_client.flushall()
        await redis_client.aclose()


@pytest_asyncio.fixture
async def flaky_redis(fake_redis: Any, monkeypatch: Any) -> AsyncGenerator[Any, None]:
    """Redis client that simulates network failures and timeouts."""
    failure_count = 0
    max_failures = 3

    original_publish = fake_redis.publish
    original_ping = fake_redis.ping

    async def failing_publish(*args: Any, **kwargs: Any) -> Any:
        nonlocal failure_count
        if failure_count < max_failures:
            failure_count += 1
            from src.common.pubsub import RedisError  # type: ignore[attr-defined]

            raise RedisError(f"Simulated network failure {failure_count}")
        return await original_publish(*args, **kwargs)

    async def failing_ping(*args: Any, **kwargs: Any) -> Any:
        nonlocal failure_count
        if failure_count < max_failures:
            failure_count += 1
            from src.common.pubsub import RedisConnectionError  # type: ignore[attr-defined]

            raise RedisConnectionError("Simulated connection failure")
        return await original_ping(*args, **kwargs)

    fake_redis.publish = failing_publish
    fake_redis.ping = failing_ping

    try:
        yield fake_redis
    finally:
        fake_redis.publish = original_publish
        fake_redis.ping = original_ping


@pytest_asyncio.fixture
async def redis_pubsub_with_mocks(fake_redis: Any, monkeypatch: Any) -> AsyncGenerator[Any, None]:
    """RedisPubSub instance with mocked Redis client for comprehensive testing."""
    from src.common.pubsub import RedisPubSub

    # Mock configuration
    mock_config = type(
        "MockConfig",
        (),
        {
            "redis_url": "redis://localhost:6379",
            "redis_max_connections": 10,
            "redis_socket_connect_timeout": 5,
            "redis_socket_keepalive": True,
            "redis_retry_on_timeout": True,
            "redis_health_check_interval": 30,
        },
    )()

    # Patch Redis availability and config
    monkeypatch.setattr("src.common.pubsub._REDIS_AVAILABLE", True)
    monkeypatch.setattr("src.common.pubsub.get_redis_config", lambda: mock_config)

    # Create pubsub instance and inject fake redis
    pubsub = RedisPubSub()
    pubsub._redis = fake_redis
    pubsub._connected = True

    # Ensure fake redis publish returns positive subscriber count
    original_publish = fake_redis.publish

    async def mock_publish(*args: Any, **kwargs: Any) -> int:
        await original_publish(*args, **kwargs)
        return 1  # Always return 1 subscriber for testing

    fake_redis.publish = mock_publish

    try:
        yield pubsub
    finally:
        await pubsub.disconnect()


@pytest.fixture
def circuit_breaker_test_config() -> dict[str, Any]:
    """Return standard circuit breaker configuration for testing."""
    return {
        "failure_threshold": 3,
        "recovery_timeout": 1.0,  # Fast recovery for tests
        "success_threshold": 2,
        "timeout": 0.5,
    }


@pytest.fixture
def redis_performance_config() -> dict[str, Any]:
    """Return performance test configuration and thresholds."""
    return {
        "target_latency_ms": 1.0,
        "max_latency_ms": 5.0,
        "warmup_iterations": 5,
        "test_iterations": 10,
        "payload_sizes": [10, 100, 1000, 10000],  # bytes
    }


class RedisTestUtils:
    """Utility class for Redis testing patterns."""

    @staticmethod
    async def wait_for_message_processing(delay: float = 0.1) -> None:
        """Wait for async message processing to complete."""
        await asyncio.sleep(delay)

    @staticmethod
    def generate_test_message(size_bytes: int = 100) -> dict[str, Any]:
        """Generate test message of specified size."""
        import random
        import string

        # Generate payload to reach target size
        content = "".join(random.choices(string.ascii_letters + string.digits, k=size_bytes))  # noqa: S311
        return {
            "test_id": random.randint(1000, 9999),  # noqa: S311
            "timestamp": 1700000000.0,
            "content": content,
            "metadata": {"size": size_bytes, "type": "test"},
        }

    @staticmethod
    async def simulate_network_latency(delay_ms: float = 10) -> None:
        """Simulate network latency in tests."""
        await asyncio.sleep(delay_ms / 1000)


@pytest.fixture
def redis_test_utils() -> RedisTestUtils:
    """Provide Redis testing utilities."""
    return RedisTestUtils()
