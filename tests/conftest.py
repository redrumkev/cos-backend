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
project_root = Path(__file__).parent.parent  # Should be g:\cos
src_path = project_root / "src"  # Should be g:\cos\src

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

# Type helpers
T = TypeVar("T", bound=Callable[..., Any])


@pytest_asyncio.fixture(scope="session", autouse=True)
async def setup_database() -> AsyncGenerator[None, None]:
    """Create all tables once at session start."""
    # Import all models to ensure they're registered with Base.metadata
    from src.backend.cc import models  # noqa: F401
    # Note: mem0_models.py doesn't exist yet, so we skip importing it

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def db_session() -> AsyncGenerator[Any, None]:
    """Provide a transactional session for each test."""
    async with engine.begin() as conn:
        # Start a savepoint
        trans = await conn.begin_nested()

        # Create session bound to this connection
        async with AsyncSessionLocal(bind=conn) as session:
            yield session

        # Rollback to savepoint after test
        await trans.rollback()


@pytest.fixture(scope="function")
def override_get_db(db_session: Any) -> Generator[None, None, None]:
    """Override FastAPI dependency."""

    async def _get_db() -> AsyncGenerator[Any, None]:
        yield db_session

    # Import the FastAPI app if available
    try:
        from src.backend.cc.deps import get_cc_db
        from src.cos_main import app

        # Import all possible db dependencies
        from src.db.connection import get_async_db

        # Override them all
        app.dependency_overrides[get_async_db] = _get_db
        app.dependency_overrides[get_cc_db] = _get_db

        yield

        # Clean up
        app.dependency_overrides.clear()
    except ImportError:
        # No app available, yield anyway for tests that don't need it
        yield


@pytest.fixture(scope="function")
def client(override_get_db: Any) -> Generator[TestClient | None, None, None]:
    """Test client with overridden db."""
    try:
        from src.cos_main import app

        with TestClient(app) as c:
            yield c
    except ImportError:
        # No app available, yield None for pure unit tests
        yield None


# Legacy aliases for backward compatibility
@pytest_asyncio.fixture(scope="function")
async def test_db_session(db_session: Any) -> AsyncGenerator[Any, None]:
    """Legacy alias for db_session."""
    yield db_session


@pytest_asyncio.fixture(scope="function")
async def mem0_db_session(db_session: Any) -> AsyncGenerator[Any, None]:
    """Legacy alias for db_session."""
    yield db_session


@pytest.fixture(scope="function")
def test_client(client: TestClient | None) -> TestClient:
    """Legacy alias for client."""
    if client is None:
        raise ValueError("FastAPI app is not available")
    return client


@pytest.fixture(scope="session")
def app() -> FastAPI | None:
    """Create main FastAPI application instance for testing or None if not available."""
    try:
        from src.cos_main import app as cos_app

        return cos_app
    except ImportError:
        return None


@pytest.fixture(scope="function")
def unique_test_id() -> str:
    """Generate a unique ID for this test to avoid data conflicts."""
    import uuid

    return str(uuid.uuid4())[:8]


# Session-scoped environment setup fixtures
@pytest.fixture(scope="session")
def mock_env_settings() -> Generator[None, None, None]:
    """Fixture to set required environment variables for tests using Settings."""
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
    """Mark that we're in test mode."""
    os.environ["PYTEST_CURRENT_TEST"] = "1"
    yield
    os.environ.pop("PYTEST_CURRENT_TEST", None)
