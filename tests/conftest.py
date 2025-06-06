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

# Determine database URL based on environment
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://test:Police9119!!Sql_test@127.0.0.1:5434/cos_db_test"
    if os.getenv("ENABLE_DB_INTEGRATION") == "1"
    else "sqlite+aiosqlite:///:memory:",
)

# Create engine once per test session
engine = create_async_engine(DATABASE_URL, echo=False)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)

T = TypeVar("T", bound=Callable[..., Any])


@pytest_asyncio.fixture(scope="session", autouse=True)
async def setup_database() -> AsyncGenerator[None, None]:
    """Create all tables once at session start."""
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
    os.environ["REDIS_HOST"] = "localhost"
    os.environ["REDIS_PORT"] = "6379"
    os.environ["REDIS_PASSWORD"] = os.environ.get("REDIS_PASSWORD", "test_password")
    yield
    for var in [
        "POSTGRES_DEV_URL",
        "POSTGRES_TEST_URL",
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
