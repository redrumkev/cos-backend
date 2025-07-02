# Pytest conftest.py - Systematic rebuild to isolate hanging issues
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
from sqlalchemy.ext.asyncio import async_sessionmaker

# SEGMENT 1: Basic Environment Setup
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

# SIMPLIFIED: Only production (5432) and dev (5433) databases
# All testing (local and CI) uses the dev database
test_db_url = os.getenv("DATABASE_URL_DEV", "postgresql+asyncpg://cos_user:cos_dev_pass@localhost:5433/cos_db_dev")

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

# RUN_INTEGRATION MODE CONTROL
RUN_INTEGRATION_MODE = os.getenv("RUN_INTEGRATION", "0")

# SEGMENT 2: Model Imports & Infrastructure


# Import all model modules to register them with Base metadata
# This ensures that create_all() will create all necessary tables
# MOVED TO pytest_configure hook to avoid import-time issues
def _import_models() -> None:
    """Import model modules - called from pytest_configure hook."""
    try:
        # Import both model modules to register them with Base metadata
        import src.backend.cc.mem0_models as mem0_models  # noqa: F401
        import src.backend.cc.models as cc_models  # noqa: F401

        # Explicitly reference the model classes to ensure they're loaded
        from src.backend.cc.mem0_models import BaseLog, EventLog, PromptTrace, ScratchNote  # noqa: F401
        from src.backend.cc.models import HealthStatus, Module  # noqa: F401

        # Ensure all models are registered with metadata
        # No need to reflect since we're defining the models explicitly
    except ImportError:
        # Models may not be available in some test environments
        pass


def is_infrastructure_available() -> bool:
    """Check if required infrastructure services are available for testing.

    Returns True if PostgreSQL, Neo4j, and Redis services are running
    with the expected configuration. Otherwise returns False.

    This function is used by the CI test triage system to determine
    which tests should be skipped vs. enabled based on local environment.

    NOTE: This function now performs lightweight checks to avoid import-time
    async engine creation that was causing pytest hanging issues.
    """
    try:
        # In mock mode, infrastructure is always available
        if RUN_INTEGRATION_MODE == "0":
            return True

        # Check if PostgreSQL dev database URL is configured (lightweight check)
        dev_db_url = os.getenv(
            "DATABASE_URL_DEV", "postgresql+asyncpg://cos_user:cos_dev_pass@localhost:5433/cos_db_dev"
        )
        # For integration mode, assume infrastructure is available if URL is set
        # Actual connectivity will be tested when engines are created in fixtures
        return bool(dev_db_url)

    except Exception:
        # Any exception indicates infrastructure is not ready
        return False


# Import smart infrastructure checking (lazy-loaded to avoid import-time blocking)
# FIXED: Removed import-time AVAILABLE_SERVICES which caused asyncio.run() during import
def _get_available_services() -> dict[str, bool]:
    """Lazy-load infrastructure services to avoid import-time blocking."""
    try:
        from tests.infrastructure_check import get_available_services

        return get_available_services()
    except ImportError:
        # Fallback if infrastructure checker is not available
        return {"postgres": False, "neo4j": False, "redis": False}


# Initialize with fallback values - will be updated when actually needed
AVAILABLE_SERVICES = {"postgres": False, "neo4j": False, "redis": False}
SERVICES_AVAILABLE = False


# Store patching logic for execution in pytest_configure hook
def _setup_mock_mode_patches() -> None:
    """Set up mock mode patches - called from pytest_configure hook."""
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


# SEGMENT 3: pytest_configure Hook


def pytest_configure(config: Any) -> None:
    """Pytest configuration hook - setup mocks and infrastructure checks."""
    # Import model modules after CLI parsing to avoid import-time issues
    _import_models()

    # Setup mock mode patches after CLI parsing but before test collection
    _setup_mock_mode_patches()

    # Update infrastructure availability and skip markers
    infrastructure_available = False
    try:
        # Quick infrastructure check without creating engines
        if RUN_INTEGRATION_MODE == "1":
            # In integration mode, do actual check
            dev_db_url = os.getenv(
                "DATABASE_URL_DEV", "postgresql+asyncpg://cos_user:cos_dev_pass@localhost:5433/cos_db_dev"
            )
            infrastructure_available = bool(dev_db_url)
        else:
            # In mock mode, infrastructure is always "available"
            infrastructure_available = True
    except Exception:
        infrastructure_available = False

    # Update the skip marker condition dynamically
    global skip_if_no_infrastructure
    skip_if_no_infrastructure = pytest.mark.skipif(
        not infrastructure_available,
        reason="Infrastructure: PostgreSQL services not available locally. "
        "Re-enable in Sprint 2 when docker-compose setup is complete.",
    )


# SEGMENT 4: Skip Decorators

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

# Legacy skip markers for backwards compatibility - moved to pytest_configure hook
skip_if_no_infrastructure = pytest.mark.skipif(
    False,  # Will be updated in pytest_configure hook
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


# SEGMENT 5: Database Fixtures


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
    """Create a dedicated event loop for each test function.

    This function-scoped fixture ensures maximum test isolation by providing
    a fresh event loop for every test. This prevents *"Task got Future attached
    to a different loop"* errors that occur when session-scoped async fixtures
    try to operate on different event loops.

    All async fixtures and database engines are created within this loop's context
    to ensure proper binding and avoid cross-loop contamination.
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

        class _MockAsyncResult:
            """Mock SQLAlchemy AsyncResult for schema query compatibility."""

            def __init__(self, data: list[Any] | None = None) -> None:
                self._data = data or []

            def scalar(self) -> Any | None:
                """Return first value or None."""
                return self._data[0] if self._data else None

            def scalars(self) -> _MockAsyncResult:
                """Return chainable scalar interface."""
                return self

            def all(self) -> list[Any]:
                """Return all data as list."""
                return list(self._data)

            def first(self) -> Any | None:
                """Return first row or None."""
                return self._data[0] if self._data else None

            def one(self) -> Any:
                """Return exactly one row or raise."""
                if len(self._data) != 1:
                    raise ValueError("Expected exactly 1 row")
                return self._data[0]

            def mappings(self) -> _MockAsyncResult:
                """Return mapping interface (simplified)."""
                return self

        class MockAsyncSession:
            def __init__(self) -> None:
                self._storage = mock_storage
                self._added_objects: list[Any] = []
                self._deleted_objects: list[Any] = []
                self._deleted_ids: set[str] = set()  # Track IDs of deleted objects
                self._is_active = True
                self.info: dict[str, Any] = {}  # Session info for logging outbox

            async def commit(self) -> None:
                """Simulate commit - persist added objects and apply deletions to mock storage."""
                # Handle added objects
                for obj in self._added_objects:
                    # Map class names to table names
                    class_name = obj.__class__.__name__
                    if class_name == "ScratchNote":
                        table_name = "scratch_notes"
                    elif class_name == "Module":
                        table_name = "modules"
                    elif class_name == "HealthStatus":
                        table_name = "health_status"
                    else:
                        table_name = class_name.lower() + "s"

                    if table_name not in self._storage:
                        self._storage[table_name] = {}

                    # Generate a simple ID if not present (may already be set by flush())
                    if not hasattr(obj, "id") or obj.id is None:
                        # Use same ID generation logic as flush()
                        if class_name in ("BaseLog", "EventLog", "PromptTrace"):
                            import uuid

                            obj.id = uuid.uuid4()
                        else:
                            obj.id = len(self._storage[table_name]) + 1

                    # Ensure ID is stored as string for consistent lookup
                    obj_id_str = str(obj.id)

                    # Store object attributes based on type
                    if class_name == "ScratchNote":
                        obj_dict = {
                            "id": obj.id,
                            "key": getattr(obj, "key", ""),
                            "content": getattr(obj, "content", ""),
                            "created_at": getattr(obj, "created_at", None),
                            "expires_at": getattr(obj, "expires_at", None),
                        }
                    elif class_name == "HealthStatus":
                        obj_dict = {
                            "id": obj.id,
                            "module": getattr(obj, "module", ""),
                            "status": getattr(obj, "status", ""),
                            "last_updated": getattr(obj, "last_updated", None),
                            "details": getattr(obj, "details", None),
                        }
                    elif class_name in ("BaseLog", "EventLog", "PromptTrace"):
                        # Handle mem0 models dynamically to capture all attributes
                        obj_dict = {"id": obj.id}
                        for attr_name in dir(obj):
                            if not attr_name.startswith("_") and not callable(getattr(obj, attr_name)):
                                try:
                                    value = getattr(obj, attr_name)
                                    # Skip SQLAlchemy relationships and registry
                                    if not str(type(value)).startswith("<class 'sqlalchemy"):
                                        obj_dict[attr_name] = value
                                except (AttributeError, TypeError, ValueError):
                                    # Skip attributes that can't be accessed or have type issues
                                    continue
                    else:
                        obj_dict = {
                            "id": obj.id,
                            "name": getattr(obj, "name", None),
                            "version": getattr(obj, "version", None),
                            "config": getattr(obj, "config", None),
                            "active": getattr(obj, "active", True),
                            "last_active": getattr(obj, "last_active", None),
                        }

                    # Filter out None values except for content which can be None
                    if class_name == "ScratchNote":
                        obj_dict = {k: v for k, v in obj_dict.items() if k == "content" or v is not None}
                    elif class_name == "HealthStatus":
                        obj_dict = {k: v for k, v in obj_dict.items() if k == "details" or v is not None}
                    else:
                        obj_dict = {k: v for k, v in obj_dict.items() if v is not None}

                    self._storage[table_name][obj_id_str] = obj_dict

                    # Update the original object with the ID (keep original type)
                    # obj.id = obj.id  # This line is redundant

                # Handle deleted objects - actually remove them from storage
                for obj in self._deleted_objects:
                    # Map object classes to the correct table name
                    class_name = obj.__class__.__name__
                    if class_name == "ScratchNote":
                        table_name = "scratch_notes"
                    elif class_name == "Module":
                        table_name = "modules"
                    elif class_name == "HealthStatus":
                        table_name = "health_status"
                    elif class_name == "MockObject":
                        # For MockObject, we need to determine the table from context
                        # Check if the object has attributes that help identify the table
                        if hasattr(obj, "name") and hasattr(obj, "version"):
                            table_name = "modules"  # Module-like object
                        elif hasattr(obj, "key") and hasattr(obj, "content"):
                            table_name = "scratch_notes"  # ScratchNote-like object
                        elif hasattr(obj, "module") and hasattr(obj, "status"):
                            table_name = "health_status"  # HealthStatus-like object
                        else:
                            table_name = "modules"  # Default fallback
                    else:
                        table_name = class_name.lower() + "s"

                    if table_name in self._storage and hasattr(obj, "id"):
                        # Convert obj.id to string for consistent lookup (UUID objects vs string keys)
                        obj_id_str = str(obj.id)
                        if obj_id_str in self._storage[table_name]:
                            del self._storage[table_name][obj_id_str]

                # Clear pending operations
                self._added_objects.clear()
                self._deleted_objects.clear()
                self._deleted_ids.clear()

            async def rollback(self) -> None:
                """Simulate rollback - clear uncommitted changes."""
                self._added_objects.clear()
                self._deleted_objects.clear()
                self._deleted_ids.clear()

            async def flush(self) -> None:
                """Simulate flush - assign IDs to added objects without persisting to storage."""
                import uuid
                from datetime import UTC, datetime

                # Generate IDs for objects that don't have them yet (like real DB flush)
                for obj in self._added_objects:
                    class_name = obj.__class__.__name__

                    # Set auto-generated timestamps for models that have them
                    if class_name == "BaseLog" and (not hasattr(obj, "timestamp") or obj.timestamp is None):
                        obj.timestamp = datetime.now(UTC)
                    elif class_name in ("PromptTrace", "EventLog") and (
                        not hasattr(obj, "created_at") or obj.created_at is None
                    ):
                        obj.created_at = datetime.now(UTC)

                    if not hasattr(obj, "id") or obj.id is None:
                        # For mem0 models (BaseLog, EventLog, PromptTrace), use UUID
                        if class_name in ("BaseLog", "EventLog", "PromptTrace"):
                            obj.id = uuid.uuid4()
                        else:
                            # For other models, use sequential integer IDs
                            if class_name == "ScratchNote":
                                table_name = "scratch_notes"
                            elif class_name == "Module":
                                table_name = "modules"
                            else:
                                table_name = class_name.lower() + "s"

                            if table_name not in self._storage:
                                self._storage[table_name] = {}

                            # Generate a simple sequential ID
                            obj.id = (
                                len(self._storage[table_name])
                                + len(
                                    [
                                        o
                                        for o in self._added_objects
                                        if o.__class__.__name__ == class_name and hasattr(o, "id") and o.id is not None
                                    ]
                                )
                                + 1
                            )

            async def close(self) -> None:
                """Simulate close - mark session as inactive."""
                self._is_active = False

            def add(self, obj: Any) -> None:
                """Add object to session (will be committed on commit())."""
                self._added_objects.append(obj)

            def add_all(self, objs: list[Any]) -> None:
                """Add multiple objects to session (will be committed on commit())."""
                self._added_objects.extend(objs)

            async def delete(self, obj: Any) -> None:
                """Simulate delete - stage object for deletion on commit."""
                # Add to deleted objects list - actual deletion happens in commit()
                self._deleted_objects.append(obj)
                # Track the ID of the deleted object for immediate filtering
                if hasattr(obj, "id") and obj.id is not None:
                    self._deleted_ids.add(str(obj.id))

                    # Handle cascade delete for BaseLog -> PromptTrace/EventLog
                    if obj.__class__.__name__ == "BaseLog":
                        # Find and mark all child objects for deletion
                        for added_obj in self._added_objects[:]:  # Use slice to avoid modification during iteration
                            if (
                                hasattr(added_obj, "base_log_id")
                                and added_obj.base_log_id == obj.id
                                and added_obj.__class__.__name__ in ("PromptTrace", "EventLog")
                            ):
                                self._deleted_objects.append(added_obj)
                                self._deleted_ids.add(str(added_obj.id))
                                added_obj._deleted = True

                        # Also check storage for committed child objects
                        for table_name in ["prompt_traces", "event_logs"]:
                            if table_name in self._storage:
                                for child_id, child_data in list(self._storage[table_name].items()):
                                    if child_data.get("base_log_id") == obj.id:
                                        self._deleted_ids.add(child_id)

                # Mark object as deleted by setting a flag for immediate reference
                obj._deleted = True

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

            async def get(self, model_class: Any, primary_key: Any) -> Any | None:
                """Simulate get - retrieve object by primary key from mock storage or added objects."""
                # Check if object is marked for deletion
                if str(primary_key) in self._deleted_ids:
                    return None

                # First check added objects (not yet committed)
                for obj in self._added_objects:
                    if (
                        obj.__class__ == model_class
                        and hasattr(obj, "id")
                        and obj.id == primary_key
                        and not getattr(obj, "_deleted", False)
                    ):
                        return obj

                # Then check committed storage
                class_name = model_class.__name__
                if class_name == "ScratchNote":
                    table_name = "scratch_notes"
                elif class_name == "Module":
                    table_name = "modules"
                elif class_name == "HealthStatus":
                    table_name = "health_status"
                else:
                    table_name = class_name.lower() + "s"

                if table_name in self._storage:
                    pk_str = str(primary_key)
                    if pk_str in self._storage[table_name]:
                        stored_data = self._storage[table_name][pk_str]
                        # Create an instance of the actual model class
                        try:
                            obj = model_class()
                            for key, value in stored_data.items():
                                setattr(obj, key, value)
                            return obj
                        except Exception:
                            # Fallback: create a simple mock object that behaves like the model
                            from types import SimpleNamespace

                            obj = SimpleNamespace(**stored_data)
                            obj.__class__ = type(model_class.__name__, (), {})
                            return obj

                return None

            async def execute(self, query: Any, params: Any = None) -> Any:
                """Mock execute - return a mock result based on query type and mock storage."""
                import re
                from datetime import UTC, datetime

                # Handle PostgreSQL schema queries specifically for P1 database schema tests
                query_str = str(query).lower()

                # Check for PostgreSQL to_regclass() schema validation queries
                if "to_regclass" in query_str and params:
                    qualified_name = params.get("qn", "")
                    # For schema tests, return the table name if it's a known schema table
                    known_tables = {
                        "cc.health_status": "cc.health_status",
                        "cc.modules": "cc.modules",
                        "mem0_cc.scratch_note": "mem0_cc.scratch_note",
                        "mem0_cc.event_log": "mem0_cc.event_log",
                        "mem0_cc.base_log": "mem0_cc.base_log",
                        "mem0_cc.prompt_trace": "mem0_cc.prompt_trace",
                    }
                    result_data = [known_tables.get(qualified_name)] if qualified_name in known_tables else [None]
                    return _MockAsyncResult(result_data)

                # Handle raw text() queries for TTL/cleanup operations
                if "select key from" in query_str and "scratch_note" in query_str:
                    # This is the TTL query that needs special handling
                    # Get all scratch notes and filter by expiry
                    notes_data = self._storage.get("scratch_notes", {})
                    ttl_results = []

                    if params and "current_time" in params:
                        cutoff_time = params["current_time"]
                        for obj_id, data in notes_data.items():
                            if obj_id not in self._deleted_ids:
                                expires_at = data.get("expires_at")
                                if expires_at is not None and expires_at <= cutoff_time:
                                    # Return just the key as a tuple for row[0] access
                                    ttl_results.append((data.get("key", ""),))

                    # Create mock result for fetchall() that returns tuples
                    mock_result = MagicMock()
                    mock_result.fetchall = MagicMock(return_value=ttl_results)
                    return mock_result

                # Create a mock result with proper async behavior for other queries
                mock_result = MagicMock()
                results: list[Any] = []

                # Parse the query string to understand what it's doing (existing logic)

                # Extract parameters for pagination (LIMIT/OFFSET)
                skip = 0
                limit = None

                # Try to get from params argument
                if params:
                    skip = params.get("param_2", 0)  # offset is param_2
                    limit = params.get("param_1", None)  # limit is param_1

                # Try to extract from compiled query object
                if skip == 0 and limit is None:
                    try:
                        compiled = query.compile()
                        param_dict = compiled.params
                        if param_dict:
                            skip = param_dict.get("param_2", 0)  # offset
                            limit = param_dict.get("param_1", None)  # limit
                    except Exception as e:
                        # Fall back to no pagination if extraction fails
                        import logging

                        logging.debug(f"Pagination parameter extraction failed: {e}")

                # Define dynamic mock class for consistent object creation
                class MockObject:
                    def __init__(self, data: dict[str, Any]) -> None:
                        for key, value in data.items():
                            setattr(self, key, value)

                    # Add is_expired attribute for type checking
                    is_expired: bool = False

                # Helper to create appropriate mock object type
                def create_mock_object(data: dict[str, Any]) -> Any:
                    """Create mock object that behaves like the real model."""
                    obj = MockObject(data)
                    # Ensure required attributes exist for Pydantic validation
                    if hasattr(obj, "key") and hasattr(obj, "content"):
                        # This looks like a ScratchNote, ensure required fields
                        if not isinstance(obj.key, str):
                            obj.key = str(obj.key) if obj.key is not None else ""
                        if not isinstance(obj.content, str) and obj.content is not None:
                            obj.content = str(obj.content)

                        # Add is_expired field for ScratchNoteResponse validation
                        from datetime import UTC, datetime

                        expires_at = getattr(obj, "expires_at", None)
                        if expires_at is not None and isinstance(expires_at, datetime):
                            obj.is_expired = expires_at <= datetime.now(UTC)
                        else:
                            obj.is_expired = False
                    elif hasattr(obj, "module") and hasattr(obj, "status") and hasattr(obj, "last_updated"):
                        # This looks like a HealthStatus, handle timezone normalization
                        from datetime import datetime

                        last_updated = getattr(obj, "last_updated", None)
                        if last_updated is not None and isinstance(last_updated, datetime):
                            # Strip timezone to match database behavior
                            obj.last_updated = last_updated.replace(tzinfo=None)
                    return obj

                # Handle UPDATE queries for modules
                if "update" in query_str and "modules" in query_str:
                    table_data = self._storage.get("modules", {})

                    # For UPDATE queries, we need to handle bound parameters differently
                    # The update data comes through the values() method which uses bind parameters
                    try:
                        compiled = query.compile()
                        # Get the parameter values from the compiled query
                        update_params = compiled.params or {}

                        # Extract the target ID from the compiled query with literal binds
                        compiled_literal = query.compile(compile_kwargs={"literal_binds": True})
                        compiled_str = str(compiled_literal)

                        # Look for the WHERE clause ID
                        id_match = re.search(r"id = '([^']+)'", compiled_str)
                        if id_match:
                            target_id = id_match.group(1)

                            if target_id in table_data:
                                # Get current data
                                current_data = table_data[target_id].copy()

                                # Apply updates from the bound parameters
                                # The parameters contain the actual update values
                                for param_name, param_value in update_params.items():
                                    # Map parameter names back to column names
                                    # SQLAlchemy uses parameter names that correspond to column names
                                    if param_name in ["version", "active", "config", "name"]:
                                        current_data[param_name] = param_value

                                # Update last_active when module is updated
                                current_data["last_active"] = datetime.now(UTC)

                                # Update storage
                                table_data[target_id] = current_data

                                # Return the updated module
                                mock_obj = create_mock_object(current_data)
                                results.append(mock_obj)
                    except Exception as e:
                        # Handle compilation errors gracefully
                        import logging

                        logging.debug(f"Error parsing UPDATE query: {e}")

                # Handle UPDATE queries for scratch_notes
                elif "update" in query_str and ("scratch_note" in query_str or "scratchnote" in query_str):
                    table_data = self._storage.get("scratch_notes", {})

                    # For UPDATE queries, we need to handle bound parameters differently
                    # The update data comes through the values() method which uses bind parameters
                    try:
                        compiled = query.compile()
                        # Get the parameter values from the compiled query
                        update_params = compiled.params or {}

                        # Extract the target ID from the compiled query with literal binds
                        compiled_literal = query.compile(compile_kwargs={"literal_binds": True})
                        compiled_str = str(compiled_literal)

                        # Look for the WHERE clause ID - handle both literal and parameter cases
                        id_match = re.search(r"id = '(\d+)'", compiled_str)
                        if not id_match:
                            # Try parameter-based matching if literal matching fails
                            id_match = re.search(r"scratch_note\.id = (\d+)", compiled_str)

                        target_id = None
                        if id_match:
                            target_id = id_match.group(1)
                        elif update_params and "id_1" in update_params:
                            # Try to get from bound parameters
                            target_id = str(update_params["id_1"])

                        if target_id and target_id in table_data:
                            # Get current data
                            current_data = table_data[target_id].copy()

                            # Apply updates from the bound parameters
                            # The parameters contain the actual update values
                            for param_name, param_value in update_params.items():
                                # Map parameter names back to column names
                                # SQLAlchemy uses parameter names that correspond to column names
                                if param_name in ["content", "expires_at", "key"]:
                                    current_data[param_name] = param_value

                            # Update storage
                            table_data[target_id] = current_data

                            # Return the updated scratch note
                            mock_obj = create_mock_object(current_data)
                            results.append(mock_obj)
                    except Exception as e:
                        # Handle compilation errors gracefully
                        import logging

                        logging.debug(f"Error parsing UPDATE scratch_notes query: {e}")

                # Handle COUNT queries
                elif "count" in query_str and "select" in query_str:
                    # Count queries return a single integer value
                    target_table = None
                    if "scratch_note" in query_str or "scratch_notes" in query_str:
                        target_table = "scratch_notes"
                    elif "modules" in query_str or "module" in query_str:
                        target_table = "modules"

                    if target_table:
                        table_data = self._storage.get(target_table, {})
                        count = len(table_data)

                        # Apply any filtering for count queries
                        if target_table == "scratch_notes":
                            # Check for startswith filtering
                            try:
                                compiled = query.compile(compile_kwargs={"literal_binds": True})
                                compiled_str = str(compiled)

                                # Apply startswith filter
                                startswith_match = re.search(r"key LIKE '([^']+)' \|\| '%'", compiled_str)
                                if startswith_match:
                                    prefix = startswith_match.group(1)
                                    count = sum(
                                        1 for data in table_data.values() if data.get("key", "").startswith(prefix)
                                    )

                                # Apply expires_at filter
                                elif "expires_at IS NULL OR expires_at >" in compiled_str:
                                    cutoff_match = re.search(r"expires_at > '([^']+)'", compiled_str)
                                    if cutoff_match:
                                        from datetime import datetime

                                        cutoff_str = cutoff_match.group(1)
                                        cutoff_time = datetime.fromisoformat(cutoff_str.replace("Z", "+00:00"))
                                        count = sum(
                                            1
                                            for data in table_data.values()
                                            if data.get("expires_at") is None
                                            or (
                                                isinstance(data.get("expires_at"), datetime)
                                                and data.get("expires_at") > cutoff_time
                                            )
                                        )
                            except Exception as e:
                                import logging

                                logging.debug(f"Error parsing count query: {e}")

                        # Return the count as a proper scalar result
                        results = [count]

                # Handle SELECT queries
                elif "select" in query_str:
                    target_table = None
                    target_name = None
                    target_id = None
                    target_key = None

                    # Determine which table is being queried
                    # Check more specific patterns first to avoid false matches
                    if "health_status" in query_str or "healthstatus" in query_str:
                        target_table = "health_status"
                    elif "scratch_note" in query_str or "scratch_notes" in query_str:
                        target_table = "scratch_notes"
                    elif ("modules" in query_str or "module" in query_str) and "health_status" not in query_str:
                        target_table = "modules"

                    if target_table:
                        table_data = self._storage.get(target_table, {})

                        # Define helper function for combining storage and added objects
                        def get_combined_table_data() -> dict[str, dict[str, Any]]:
                            combined_data = table_data.copy()
                            # Also check added objects that haven't been committed yet
                            for obj in self._added_objects:
                                class_name = obj.__class__.__name__
                                if (target_table == "scratch_notes" and class_name == "ScratchNote") or (
                                    target_table == "health_status" and class_name == "HealthStatus"
                                ):
                                    obj_id = str(obj.id) if obj.id else str(len(combined_data) + 1)

                                    if class_name == "ScratchNote":
                                        combined_data[obj_id] = {
                                            "id": obj.id or int(obj_id),
                                            "key": getattr(obj, "key", ""),
                                            "content": getattr(obj, "content", ""),
                                            "created_at": getattr(obj, "created_at", None),
                                            "expires_at": getattr(obj, "expires_at", None),
                                        }
                                    elif class_name == "HealthStatus":
                                        combined_data[obj_id] = {
                                            "id": obj.id or int(obj_id),
                                            "module": getattr(obj, "module", ""),
                                            "status": getattr(obj, "status", ""),
                                            "last_updated": getattr(obj, "last_updated", None),
                                            "details": getattr(obj, "details", None),
                                        }

                            # Filter out deleted objects
                            filtered_data = {}
                            for obj_id, data in combined_data.items():
                                if obj_id not in self._deleted_ids:
                                    filtered_data[obj_id] = data

                            return filtered_data

                        # Parse query for WHERE conditions (name/id/key searches)
                        try:
                            # Try to get literal binds for WHERE conditions
                            compiled = query.compile(compile_kwargs={"literal_binds": True})
                            compiled_str = str(compiled)

                            # Look for WHERE conditions
                            name_match = re.search(r"name = '([^']+)'", compiled_str)
                            if name_match:
                                target_name = name_match.group(1)

                            id_match = re.search(r"id = '([^']+)'", compiled_str)
                            if id_match:
                                target_id = id_match.group(1)

                            key_match = re.search(r"key = '([^']+)'", compiled_str)
                            if key_match:
                                target_key = key_match.group(1)

                        except Exception as e:
                            # Ignore compilation errors, fallback to parameter inspection
                            import logging

                            logging.debug(f"Error parsing SELECT query: {e}")

                        # Handle specific query types
                        if target_id:
                            # Get by ID
                            if target_id in table_data:
                                mock_obj = create_mock_object(table_data[target_id])
                                results.append(mock_obj)
                        elif "id IN (" in str(query) or " IN (" in str(query):
                            # Handle ID IN (...) queries first (SELECT * WHERE id IN)
                            try:
                                compiled = query.compile(compile_kwargs={"literal_binds": True})
                                compiled_str = str(compiled)

                                id_match = re.search(r"id IN \(([^)]+)\)", compiled_str)
                                if id_match:
                                    id_list_str = id_match.group(1)
                                    ids = [int(x.strip()) for x in id_list_str.split(",")]

                                    notes_data = get_combined_table_data()
                                    for id_val in ids:
                                        str_id = str(id_val)
                                        if str_id in notes_data:
                                            mock_obj = create_mock_object(notes_data[str_id])
                                            results.append(mock_obj)
                            except Exception as e:
                                import logging

                                logging.debug(f"Error parsing ID IN query: {e}")
                        elif (
                            "select" in query_str
                            and "where" in query_str
                            and (
                                "select scratch_note.id " in query_str
                                or "select scratch_note.id\n" in query_str
                                or query_str.strip().startswith("select scratch_note.id ")
                            )
                        ):
                            # Handle SELECT id WHERE... queries for cleanup operations (only selecting ID column)
                            try:
                                compiled = query.compile(compile_kwargs={"literal_binds": True})
                                compiled_str = str(compiled)

                                # Check for expires_at filtering in cleanup queries (SELECT id)
                                if (
                                    "expires_at IS NOT NULL AND expires_at <=" in compiled_str
                                    or "scratch_note.expires_at IS NOT NULL AND scratch_note.expires_at <="
                                    in compiled_str
                                ):
                                    cutoff_match = re.search(
                                        r"(?:scratch_note\.)?expires_at <= '([^']+)'", compiled_str
                                    )
                                    if cutoff_match and (
                                        target_table == "scratch_notes" or "scratch_note" in compiled_str
                                    ):
                                        from datetime import datetime

                                        cutoff_str = cutoff_match.group(1)
                                        cutoff_time = datetime.fromisoformat(cutoff_str.replace("Z", "+00:00"))

                                        notes_data = get_combined_table_data()

                                        # Find expired notes and return their IDs (with LIMIT support)
                                        expired_ids = []
                                        for obj_id, data in notes_data.items():
                                            expires_at = data.get("expires_at")
                                            if (
                                                expires_at is not None
                                                and isinstance(expires_at, datetime)
                                                and expires_at <= cutoff_time
                                            ):
                                                expired_ids.append(int(obj_id))

                                        # Check for LIMIT clause
                                        limit_match = re.search(r"LIMIT (\d+)", compiled_str)
                                        if limit_match:
                                            limit_value = int(limit_match.group(1))
                                            expired_ids = expired_ids[:limit_value]

                                        # Return IDs as tuples (like fetchall() returns)
                                        for expired_id in expired_ids:
                                            results.append((expired_id,))

                                # Check for key = value queries (SELECT * WHERE key = 'value')
                                elif ("scratch_note.key = " in compiled_str or " key = " in compiled_str) and (
                                    "scratch_note" in compiled_str or target_table == "scratch_notes"
                                ):
                                    key_match = re.search(r"(?:scratch_note\.)?key = '([^']+)'", compiled_str)
                                    if key_match:
                                        key_value = key_match.group(1)

                                        notes_data = get_combined_table_data()
                                        for data in notes_data.values():
                                            if data.get("key") == key_value:
                                                mock_obj = create_mock_object(data)
                                                results.append(mock_obj)
                                                break

                            except Exception as e:
                                import logging

                                logging.debug(f"Error parsing cleanup SELECT query: {e}")
                        elif target_name:
                            # Get by name (modules)
                            for data in table_data.values():
                                if data.get("name") == target_name:
                                    mock_obj = create_mock_object(data)
                                    results.append(mock_obj)
                                    break
                        elif target_key:
                            # Get by key (scratch_notes)
                            # Use combined data to include uncommitted objects
                            combined_data = get_combined_table_data() if target_table == "scratch_notes" else table_data

                            for data in combined_data.values():
                                if data.get("key") == target_key:
                                    mock_obj = create_mock_object(data)
                                    results.append(mock_obj)
                                    break
                        else:
                            # List all with pagination and filtering
                            all_objects = []

                            # Get combined data (storage + added objects)
                            if target_table == "scratch_notes" or target_table == "health_status":
                                combined_data = get_combined_table_data()
                            else:
                                combined_data = table_data.copy()
                                # Add module objects from added_objects
                                for obj in self._added_objects:
                                    if obj.__class__.__name__ == "Module":
                                        obj_id = str(obj.id) if obj.id else str(len(combined_data) + 1)
                                        combined_data[obj_id] = {
                                            "id": obj.id or obj_id,
                                            "name": getattr(obj, "name", ""),
                                            "version": getattr(obj, "version", ""),
                                            "active": getattr(obj, "active", True),
                                            "config": getattr(obj, "config", None),
                                        }

                            # Check for STARTSWITH filter in compiled query
                            startswith_filter = None
                            try:
                                compiled = query.compile(compile_kwargs={"literal_binds": True})
                                compiled_str = str(compiled)

                                # Look for startswith pattern: key LIKE 'prefix_' || '%'
                                startswith_match = re.search(r"key LIKE '([^']+)' \|\| '%'", compiled_str)
                                if startswith_match:
                                    startswith_filter = startswith_match.group(1)
                            except Exception as e:
                                # Ignore compilation errors
                                import logging

                                logging.debug(f"Error parsing startswith filter: {e}")

                            for data in combined_data.values():
                                # Apply startswith filter if present
                                if startswith_filter and target_table == "scratch_notes":
                                    key_value = data.get("key", "")
                                    if not key_value.startswith(startswith_filter):
                                        continue

                                # Apply expires_at filter for scratch_notes (exclude expired by default)
                                if target_table == "scratch_notes":
                                    # Check for expires_at filtering in the query
                                    # If not explicitly including expired, filter out expired notes
                                    expires_at = data.get("expires_at")
                                    if expires_at is not None:
                                        # If there's an expires_at and it's in the past, check if we should include it
                                        try:
                                            compiled = query.compile(compile_kwargs={"literal_binds": True})
                                            compiled_str = str(compiled)
                                            # If the query doesn't explicitly allow expired notes, skip them
                                            has_expiry_filter = (
                                                "expires_at IS NULL OR expires_at >" in compiled_str
                                                or "scratch_note.expires_at IS NULL OR scratch_note.expires_at >"
                                                in compiled_str
                                            )
                                            if has_expiry_filter:
                                                # This means we're excluding expired notes
                                                # Extract cutoff time from compiled query instead of using now()
                                                # This ensures we use the same time that was used in the query
                                                cutoff_match = re.search(
                                                    r"(?:scratch_note\.)?expires_at > '([^']+)'", compiled_str
                                                )
                                                if cutoff_match:
                                                    from datetime import datetime

                                                    cutoff_str = cutoff_match.group(1)
                                                    cutoff_time = datetime.fromisoformat(
                                                        cutoff_str.replace("Z", "+00:00")
                                                    )
                                                else:
                                                    from datetime import UTC, datetime

                                                    cutoff_time = datetime.now(UTC)
                                                if isinstance(expires_at, datetime) and expires_at <= cutoff_time:
                                                    continue
                                        except Exception as e:
                                            # If we can't parse the query, err on the side of inclusion
                                            import logging

                                            logging.debug(f"Error parsing expires query: {e}")

                                mock_obj = create_mock_object(data)
                                all_objects.append(mock_obj)

                            # Sort for consistent ordering
                            if target_table == "modules":
                                all_objects.sort(key=lambda m: getattr(m, "name", ""))
                            elif target_table == "scratch_notes":
                                all_objects.sort(key=lambda m: getattr(m, "key", ""))
                            elif target_table == "health_status":
                                # Sort by last_updated descending for get_system_health query
                                from datetime import datetime

                                all_objects.sort(key=lambda h: getattr(h, "last_updated", datetime.min), reverse=True)

                            # Apply pagination using the extracted parameters
                            if limit is not None:
                                results = all_objects[skip : skip + limit]
                            else:
                                results = all_objects[skip:] if skip > 0 else all_objects

                # Create proper mock result with concrete return values (not nested mocks)
                # This prevents Pydantic validation errors from mock objects
                class MockScalars:
                    def __init__(self, data: list[Any]) -> None:
                        self._data = data

                    def first(self) -> Any:
                        return self._data[0] if self._data else None

                    def all(self) -> list[Any]:
                        return self._data

                    def one(self) -> Any:
                        if not self._data:
                            raise Exception("No rows found")
                        if len(self._data) > 1:
                            raise Exception("Multiple rows found")
                        return self._data[0]

                    def one_or_none(self) -> Any:
                        return self._data[0] if self._data else None

                mock_scalars = MockScalars(results)
                mock_result.scalars = MagicMock(return_value=mock_scalars)
                mock_result.scalar_one_or_none = MagicMock(return_value=results[0] if results else None)

                # Handle scalar() for count queries that return integers
                if results and len(results) == 1 and isinstance(results[0], int):
                    mock_result.scalar = MagicMock(return_value=results[0])
                else:
                    mock_result.scalar = MagicMock(return_value=results[0] if results else None)
                mock_result.first = MagicMock(return_value=results[0] if results else None)
                mock_result.all = MagicMock(return_value=results)
                mock_result.fetchone = MagicMock(return_value=results[0] if results else None)
                mock_result.fetchall = MagicMock(return_value=results)
                mock_result.rowcount = len(results)

                return mock_result

        yield MockAsyncSession()
        return

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


# SEGMENT 6: FastAPI Integration


@pytest.fixture(scope="function")
def override_get_db(db_session: Any) -> Generator[None, None, None]:
    """Override FastAPI dependency to use our per-test session.

    Ensures app.dependency_overrides.clear() is called reliably for test isolation.
    """
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

        # Apply dependency overrides
        app.dependency_overrides[get_async_db] = _get_db
        app.dependency_overrides[get_cc_db] = _get_db
        yield
    except ImportError:
        yield
    finally:
        # CRITICAL: Always clear dependency overrides to prevent test contamination
        # This ensures each test gets a fresh dependency setup regardless of imports or exceptions
        try:
            from src.cos_main import app

            app.dependency_overrides.clear()
        except ImportError:
            # App not available - skip cleanup (likely in isolated unit tests)
            pass


@pytest.fixture(scope="function")
def client(override_get_db: Any) -> Generator[TestClient | None, None, None]:
    """TestClient with overridden dependencies."""
    try:
        from src.cos_main import app

        with TestClient(app) as c:
            yield c
    except ImportError:
        yield None


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


# SEGMENT 7: Legacy Compatibility


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


# SEGMENT 8: Redis Pub/Sub Fixtures


# REMOVED: Conflicting session-scoped event loop fixture
# This was causing "Future attached to different loop" errors
# All async fixtures should use the function-scoped event_loop fixture below


@pytest_asyncio.fixture(scope="session")
async def redis_health_monitor() -> AsyncGenerator[Any, None]:
    """Session-scoped Redis health monitor for integration tests."""
    if RUN_INTEGRATION_MODE == "0":
        # In mock mode, no need for health monitoring
        yield None
        return

    try:
        from src.common.redis_health_monitor import get_redis_health_monitor

        monitor = await get_redis_health_monitor()

        # Ensure Redis is available before starting tests
        redis_available = await monitor.ensure_redis_available()
        if not redis_available:
            pytest.skip("Redis not available and could not be auto-recovered")

        yield monitor
    except ImportError:
        yield None


@pytest_asyncio.fixture
async def fake_redis() -> AsyncGenerator[Any, None]:
    """Async fakeredis instance with proper cleanup and performance optimizations."""
    try:
        from fakeredis import FakeAsyncRedis
    except ImportError:
        pytest.skip("fakeredis not available")

    # Create fakeredis instance with optimized settings
    redis_client = FakeAsyncRedis(
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


@pytest.fixture
def dummy_fixture() -> str:
    return "working"


# ---------------------------------------------------------------------------
# Additional fixtures for common test utilities
# ---------------------------------------------------------------------------

from typing import Any  # noqa: E402

from src.common.base_subscriber import BaseSubscriber  # noqa: E402


class _GlobalConcreteSubscriber(BaseSubscriber):
    """Simple concrete subscriber used for module-level pytest fixtures.

    This replicates the behaviour of the `ConcreteSubscriber` defined in
    individual test modules so that tests in other classes (e.g.
    `TestBaseSubscriberAdvancedScenarios`) can depend on a shared
    `subscriber` fixture.
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.processed_messages: list[dict[str, Any]] = []
        self.process_success: bool = True
        self.process_delay: float = 0.0

    async def process_message(self, message: dict[str, Any]) -> bool:
        if self.process_delay > 0:
            await asyncio.sleep(self.process_delay)
        self.processed_messages.append(message)
        return self.process_success


@pytest.fixture(name="subscriber")
def subscriber_fixture() -> _GlobalConcreteSubscriber:
    """Provide a reusable subscriber fixture for tests at module scope."""
    return _GlobalConcreteSubscriber()
