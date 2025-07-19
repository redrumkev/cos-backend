"""Pattern: Database Operations - COS Gold Standard Implementation.

Version: 2025-07-18 (Production Ready)
ADR: ADR-002 (Living Patterns System)
Status: Implemented - Production Ready Database Operations Pattern

Purpose: Define comprehensive patterns for async database operations with SQLAlchemy 2.0+
When to use: ALL database interactions including queries, transactions, migrations, and health monitoring
When NOT to use: Cache operations or non-relational data stores (use Redis patterns instead)

Research Sources:
- SQLAlchemy 2.0.36+ Official Documentation (Context7)
- 2024-2025 FastAPI + SQLAlchemy Best Practices (Tavily Research)
- Modern async session management patterns from DEV Community
- PostgreSQL connection pooling optimization strategies
- Circuit breaker and resilience patterns for database operations

Anti-patterns:
- Manual session commit/rollback without context managers
- Creating sessions without proper lifecycle management
- N+1 query problems (use eager loading)
- Connection leaks from improper session cleanup
- Synchronous database operations in async contexts
- Hard-coded connection pool settings
- Missing error handling and retry logic
- Testing without proper transaction isolation

COS Constitutional Mandates:
- 100% Quality + 100% Efficiency (Dual Mandate)
- FORWARD Principles: Frictionless, Orchestrated, Real-Time, Wide-Angle, Adaptive, Relentless, Destiny-Driven
- KISS: Keep It Simple, Stupid
- Serves the 100+ book legacy vision through gold-standard database foundations
"""

import asyncio
import logging
import time
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from enum import Enum
from typing import Any, Generic, Protocol, TypeVar

from sqlalchemy import delete, func, select, text, update
from sqlalchemy.exc import OperationalError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload

logger = logging.getLogger(__name__)


class HasId(Protocol):
    """Protocol for models with an id attribute."""

    id: int | str


T = TypeVar("T", bound=HasId)


class CircuitBreakerState(Enum):
    """Circuit breaker states for database operations."""

    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Failing fast, not calling database
    HALF_OPEN = "half_open"  # Testing if database is back


class DatabaseError(Exception):
    """Base exception for database operation errors."""

    pass


class DatabaseConnectionError(DatabaseError):
    """Connection-related database errors."""

    pass


class TransactionError(DatabaseError):
    """Transaction-related database errors."""

    pass


class CircuitBreakerOpenError(DatabaseError):
    """Raised when circuit breaker is open."""

    pass


# =============================================================================
# CORE TRANSACTION PATTERNS (CANONICAL IMPLEMENTATION)
# =============================================================================


@asynccontextmanager
async def transactional(session: AsyncSession) -> AsyncGenerator[AsyncSession, None]:
    """Modern SQLAlchemy 2.0 transaction context manager.

    Uses Session.begin() pattern for automatic commit/rollback.
    Follows SQLAlchemy 2.0 best practices for async session management.

    Usage:
        async with transactional(session) as tx_session:
            # All operations within this block are transactional
            await tx_session.add(some_object)
            # Automatic commit on success, rollback on exception
    """
    async with session.begin():
        try:
            yield session
        except Exception:
            # Session.begin() context manager handles rollback automatically
            raise


@asynccontextmanager
async def nested_transaction(session: AsyncSession) -> AsyncGenerator[AsyncSession, None]:
    """Nested transaction using savepoints for complex operations.

    Useful for operations that need to handle partial failures
    without rolling back the entire transaction.

    Usage:
        async with transactional(session) as tx_session:
            await tx_session.add(user)

            async with nested_transaction(tx_session) as nested_session:
                try:
                    await nested_session.add(profile)
                except IntegrityError:
                    # Only profile creation rolls back, user creation preserved
                    logger.warning("Profile creation failed, continuing without profile")
    """
    async with session.begin_nested():
        try:
            yield session
        except Exception:
            # begin_nested() context manager handles savepoint rollback
            raise


# =============================================================================
# CIRCUIT BREAKER IMPLEMENTATION
# =============================================================================


class DatabaseCircuitBreaker:
    """Circuit breaker for database operations.

    Prevents cascade failures by failing fast when database is unhealthy.
    Automatically recovers when database becomes available again.
    """

    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        expected_exception: type[Exception] = OperationalError,
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception
        self.failure_count = 0
        self.last_failure_time = 0.0
        self.state = CircuitBreakerState.CLOSED

    def _can_attempt_call(self) -> bool:
        """Check if we can attempt a database call."""
        if self.state == CircuitBreakerState.CLOSED:
            return True
        elif self.state == CircuitBreakerState.OPEN:
            if time.time() - self.last_failure_time >= self.recovery_timeout:
                self.state = CircuitBreakerState.HALF_OPEN
                return True
            return False
        elif self.state == CircuitBreakerState.HALF_OPEN:
            return True
        return False

    def _record_success(self) -> None:
        """Record successful database operation."""
        self.failure_count = 0
        self.state = CircuitBreakerState.CLOSED

    def _record_failure(self) -> None:
        """Record failed database operation."""
        self.failure_count += 1
        self.last_failure_time = time.time()

        if self.failure_count >= self.failure_threshold:
            self.state = CircuitBreakerState.OPEN

    async def call(self, func: Any, *args: Any, **kwargs: Any) -> Any:
        """Execute function with circuit breaker protection."""
        if not self._can_attempt_call():
            raise CircuitBreakerOpenError("Circuit breaker is OPEN")

        try:
            # Handle both real async functions and mocks
            if callable(func):
                if asyncio.iscoroutinefunction(func):
                    result = await func(*args, **kwargs)
                else:
                    # For mocks that aren't true coroutines
                    result = func(*args, **kwargs)
                    if hasattr(result, "__await__"):
                        result = await result
            else:
                result = await func(*args, **kwargs)

            # Special handling for test mode is now handled by MockAsyncSession.execute()
            # No need for circuit breaker override since mock session handles DELETE operations properly

            self._record_success()
            return result
        except self.expected_exception as e:
            self._record_failure()
            raise DatabaseConnectionError(f"Database operation failed: {e}") from e


# Global circuit breaker instance
circuit_breaker = DatabaseCircuitBreaker()


# =============================================================================
# RETRY LOGIC WITH EXPONENTIAL BACKOFF
# =============================================================================


async def with_retry(
    func: Any,
    *args: Any,
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    exponential_base: float = 2.0,
    jitter: bool = True,
    **kwargs: Any,
) -> Any:
    """Execute function with exponential backoff retry logic.

    Args:
    ----
        func: Async function to execute
        *args: Positional arguments for the function
        max_retries: Maximum number of retry attempts
        base_delay: Initial delay between retries (seconds)
        max_delay: Maximum delay between retries (seconds)
        exponential_base: Base for exponential backoff calculation
        jitter: Add random jitter to prevent thundering herd
        **kwargs: Keyword arguments for the function

    Returns:
    -------
        Result of the function call

    Raises:
    ------
        Last exception encountered if all retries exhausted

    """
    last_exception = None

    for attempt in range(max_retries + 1):
        try:
            return await func(*args, **kwargs)
        except (OperationalError, DatabaseConnectionError) as e:
            last_exception = e

            if attempt == max_retries:
                break

            delay = min(base_delay * (exponential_base**attempt), max_delay)
            if jitter:
                delay *= 0.5 + 0.5 * asyncio.get_event_loop().time() % 1

            logger.warning(
                f"Database operation failed (attempt {attempt + 1}/{max_retries + 1}), "
                f"retrying in {delay:.2f}s: {e}"
            )
            await asyncio.sleep(delay)

    raise last_exception  # type: ignore[misc]


# =============================================================================
# GENERIC REPOSITORY PATTERN (CANONICAL IMPLEMENTATION)
# =============================================================================


class BaseRepository(Generic[T]):
    """Generic repository pattern for database operations.

    Implements common CRUD operations with proper error handling,
    transaction management, and query optimization.

    Type-safe through Generic[T] parameter.
    """

    def __init__(self, session: AsyncSession, model_class: type[T]):
        self.session = session
        self.model_class = model_class

    async def get_by_id(self, record_id: int | str, *, eager_load: list[str] | None = None) -> T | None:
        """Get single record by ID with optional eager loading.

        Args:
        ----
            record_id: Primary key value
            eager_load: List of relationship names to eager load

        Returns:
        -------
            Model instance or None if not found

        """
        stmt = select(self.model_class).where(self.model_class.id == record_id)  # type: ignore[arg-type]

        if eager_load:
            for relationship in eager_load:
                stmt = stmt.options(selectinload(getattr(self.model_class, relationship)))

        result = await circuit_breaker.call(self.session.execute, stmt)
        return result.scalar_one_or_none()  # type: ignore[no-any-return]

    async def list_all(
        self,
        *,
        offset: int = 0,
        limit: int = 100,
        order_by: Any = None,
        eager_load: list[str] | None = None,
        filters: dict[str, Any] | None = None,
    ) -> list[T]:
        """List records with pagination, filtering, and eager loading.

        Args:
        ----
            offset: Number of records to skip
            limit: Maximum number of records to return
            order_by: Column to order by
            eager_load: List of relationship names to eager load
            filters: Dictionary of column:value filters

        Returns:
        -------
            List of model instances

        """
        stmt = select(self.model_class)

        # Apply filters
        if filters:
            for column, value in filters.items():
                stmt = stmt.where(getattr(self.model_class, column) == value)

        # Apply ordering
        stmt = stmt.order_by(order_by) if order_by is not None else stmt.order_by(self.model_class.id)  # type: ignore[arg-type]

        # Apply pagination
        stmt = stmt.offset(offset).limit(limit)

        # Apply eager loading
        if eager_load:
            for relationship in eager_load:
                stmt = stmt.options(selectinload(getattr(self.model_class, relationship)))

        result = await circuit_breaker.call(self.session.execute, stmt)
        return list(result.scalars().all())

    async def create(self, **kwargs: Any) -> T:
        """Create new record.

        Args:
        ----
            **kwargs: Field values for the new record

        Returns:
        -------
            Created model instance with ID populated

        """
        instance = self.model_class(**kwargs)
        self.session.add(instance)
        await circuit_breaker.call(self.session.flush)  # Get ID without committing
        return instance

    async def create_many(self, records: list[dict[str, Any]]) -> list[T]:
        """Bulk create multiple records efficiently.

        Args:
        ----
            records: List of dictionaries containing field values

        Returns:
        -------
            List of created model instances

        """
        instances = [self.model_class(**record) for record in records]
        self.session.add_all(instances)
        await circuit_breaker.call(self.session.flush)
        return instances

    async def update(self, record_id: int | str, **kwargs: Any) -> T | None:
        """Update existing record.

        Args:
        ----
            record_id: Primary key of record to update
            **kwargs: Fields to update

        Returns:
        -------
            Updated model instance or None if not found

        """
        # Use UPDATE statement for better performance
        stmt = (
            update(self.model_class)
            .where(self.model_class.id == record_id)  # type: ignore[arg-type]
            .values(**kwargs)
            .returning(self.model_class)
        )

        result = await circuit_breaker.call(self.session.execute, stmt)
        updated_instance = result.scalar_one_or_none()

        if updated_instance:
            await circuit_breaker.call(self.session.flush)

        return updated_instance  # type: ignore[no-any-return]

    async def delete(self, record_id: int | str) -> bool:
        """Delete record by ID.

        Args:
        ----
            record_id: Primary key of record to delete

        Returns:
        -------
            True if record was deleted, False if not found

        """
        stmt = delete(self.model_class).where(self.model_class.id == record_id)  # type: ignore[arg-type]
        result = await circuit_breaker.call(self.session.execute, stmt)
        return result.rowcount > 0  # type: ignore[no-any-return]

    async def count(self, *, filters: dict[str, Any] | None = None) -> int:
        """Count records with optional filtering.

        Args:
        ----
            filters: Dictionary of column:value filters

        Returns:
        -------
            Number of matching records

        """
        stmt = select(func.count(self.model_class.id))  # type: ignore[arg-type]

        if filters:
            for column, value in filters.items():
                stmt = stmt.where(getattr(self.model_class, column) == value)

        result = await circuit_breaker.call(self.session.execute, stmt)
        return result.scalar() or 0

    async def exists(self, record_id: int | str) -> bool:
        """Check if record exists by ID.

        Args:
        ----
            record_id: Primary key to check

        Returns:
        -------
            True if record exists, False otherwise

        """
        stmt = select(self.model_class.id).where(self.model_class.id == record_id)  # type: ignore[call-overload]
        result = await circuit_breaker.call(self.session.execute, stmt)
        return result.scalar_one_or_none() is not None


# =============================================================================
# QUERY OPTIMIZATION PATTERNS
# =============================================================================


class QueryOptimizer:
    """Advanced query optimization patterns for performance.

    Provides methods to prevent N+1 queries, optimize bulk operations,
    and implement efficient query patterns.
    """

    @staticmethod
    async def eager_load_relationships(
        session: AsyncSession, model_class: type[T], *relationships: str, filters: dict[str, Any] | None = None
    ) -> list[T]:
        """Eager load relationships to avoid N+1 queries.

        Args:
        ----
            session: Database session
            model_class: Model to query
            relationships: Relationship names to eager load
            filters: Optional filters to apply

        Returns:
        -------
            List of model instances with relationships loaded

        """
        stmt = select(model_class)

        # Apply filters
        if filters:
            for column, value in filters.items():
                stmt = stmt.where(getattr(model_class, column) == value)

        # Apply eager loading
        for rel in relationships:
            stmt = stmt.options(selectinload(getattr(model_class, rel)))

        result = await circuit_breaker.call(session.execute, stmt)
        return list(result.scalars().unique())

    @staticmethod
    async def joined_load_relationships(
        session: AsyncSession, model_class: type[T], *relationships: str, filters: dict[str, Any] | None = None
    ) -> list[T]:
        """Use joined loading for one-to-one relationships.

        More efficient than selectinload for 1:1 relationships.

        Args:
        ----
            session: Database session
            model_class: Model to query
            relationships: Relationship names to join load
            filters: Optional filters to apply

        Returns:
        -------
            List of model instances with relationships loaded

        """
        stmt = select(model_class)

        # Apply filters
        if filters:
            for column, value in filters.items():
                stmt = stmt.where(getattr(model_class, column) == value)

        # Apply joined loading
        for rel in relationships:
            stmt = stmt.options(joinedload(getattr(model_class, rel)))

        result = await circuit_breaker.call(session.execute, stmt)
        return list(result.scalars().unique())

    @staticmethod
    async def bulk_update(
        session: AsyncSession, model_class: type[T], updates: list[dict[str, Any]], key_column: str = "id"
    ) -> int:
        """Perform bulk update operations efficiently.

        Args:
        ----
            session: Database session
            model_class: Model to update
            updates: List of update dictionaries containing key and values
            key_column: Column name to match on (default: 'id')

        Returns:
        -------
            Number of rows updated

        """
        if not updates:
            return 0

        # Group updates by values to minimize statements
        update_groups: dict[tuple[Any, ...], list[Any]] = {}

        for update_data in updates:
            key_value = update_data.pop(key_column)
            values_tuple = tuple(sorted(update_data.items()))

            if values_tuple not in update_groups:
                update_groups[values_tuple] = []
            update_groups[values_tuple].append(key_value)

        total_updated = 0
        key_attr = getattr(model_class, key_column)

        for values_tuple, key_values in update_groups.items():
            values_dict = dict(values_tuple)
            stmt = update(model_class).where(key_attr.in_(key_values)).values(**values_dict)
            result = await circuit_breaker.call(session.execute, stmt)
            total_updated += result.rowcount

        return total_updated


# =============================================================================
# CONNECTION POOL OPTIMIZATION
# =============================================================================


class DatabaseConfig:
    """Optimized database configuration for production use.

    Based on research from SQLAlchemy documentation and production best practices.
    """

    # Connection Pool Settings (Production Optimized)
    POOL_SIZE = 20  # Core connections to maintain
    MAX_OVERFLOW = 40  # Additional connections under load
    POOL_TIMEOUT = 30  # Seconds to wait for connection
    POOL_RECYCLE = 3600  # Recycle connections every hour
    POOL_PRE_PING = True  # Health check before use

    # Performance Settings
    EXPIRE_ON_COMMIT = False  # Better async performance
    AUTOFLUSH = False  # Manual flush control

    # Retry Settings
    MAX_RETRIES = 3
    RETRY_BASE_DELAY = 1.0
    RETRY_MAX_DELAY = 60.0

    @classmethod
    def get_engine_options(cls) -> dict[str, Any]:
        """Get optimized engine configuration."""
        return {
            "pool_size": cls.POOL_SIZE,
            "max_overflow": cls.MAX_OVERFLOW,
            "pool_timeout": cls.POOL_TIMEOUT,
            "pool_recycle": cls.POOL_RECYCLE,
            "pool_pre_ping": cls.POOL_PRE_PING,
            "echo": False,  # Set to True for development SQL logging
        }

    @classmethod
    def get_session_options(cls) -> dict[str, Any]:
        """Get optimized session configuration."""
        return {
            "expire_on_commit": cls.EXPIRE_ON_COMMIT,
            "autoflush": cls.AUTOFLUSH,
        }


# =============================================================================
# HEALTH MONITORING
# =============================================================================


class DatabaseHealthMonitor:
    """Monitor database connection health and performance.

    Provides health checks, metrics collection, and alerting.
    """

    def __init__(self, session: AsyncSession):
        self.session = session

    async def health_check(self) -> dict[str, Any]:
        """Perform comprehensive database health check.

        Returns
        -------
            Dictionary containing health status and metrics

        """
        health_data = {
            "status": "unknown",
            "timestamp": time.time(),
            "connection_status": "unknown",
            "response_time_ms": None,
            "circuit_breaker_state": circuit_breaker.state.value,
            "circuit_breaker_failures": circuit_breaker.failure_count,
        }

        try:
            start_time = time.time()

            # Simple connectivity test
            result = await circuit_breaker.call(self.session.execute, text("SELECT 1 as health_check"))
            value = result.scalar()

            end_time = time.time()
            response_time_ms = (end_time - start_time) * 1000

            if value == 1:
                health_data.update(
                    {
                        "status": "healthy",
                        "connection_status": "connected",
                        "response_time_ms": response_time_ms,
                    }
                )
            else:
                health_data.update(
                    {
                        "status": "unhealthy",
                        "connection_status": "invalid_response",
                    }
                )

        except Exception as e:
            health_data.update(
                {
                    "status": "unhealthy",
                    "connection_status": "failed",
                    "error": str(e),
                }
            )

        return health_data

    async def get_pool_status(self) -> dict[str, Any]:
        """Get connection pool status and metrics.

        Returns
        -------
            Dictionary containing pool metrics

        """
        engine = self.session.get_bind()
        if hasattr(engine, "pool"):
            pool = engine.pool
            return {
                "pool_size": pool.size(),  # type: ignore[union-attr]
                "checked_in": pool.checkedin(),  # type: ignore[union-attr]
                "checked_out": pool.checkedout(),  # type: ignore[union-attr]
                "overflow": pool.overflow(),  # type: ignore[union-attr]
                "invalid": pool.invalid(),  # type: ignore[union-attr]
            }
        return {"error": "Pool information not available"}


# =============================================================================
# TESTING INFRASTRUCTURE
# =============================================================================


@asynccontextmanager
async def test_transaction(session: AsyncSession) -> AsyncGenerator[AsyncSession, None]:
    """Test transaction that always rolls back.

    Provides transaction isolation for tests while maintaining
    database state between tests.

    Usage in pytest:
        @pytest.fixture
        async def db_session(async_session):
            async with test_transaction(async_session) as session:
                yield session
    """
    async with session.begin():
        try:
            yield session
        finally:
            await session.rollback()


# =============================================================================
# USAGE EXAMPLES
# =============================================================================

"""
# 1. Basic Repository Usage
class UserRepository(BaseRepository[User]):
    async def get_by_email(self, email: str) -> User | None:
        stmt = select(self.model_class).where(self.model_class.email == email)
        result = await circuit_breaker.call(self.session.execute, stmt)
        return result.scalar_one_or_none()  # type: ignore[no-any-return]

# 2. Service Layer with Transactions
class UserService:
    def __init__(self, session: AsyncSession):
        self.user_repo = UserRepository(session, User)
        self.profile_repo = BaseRepository(session, Profile)

    async def create_user_with_profile(self, user_data: dict, profile_data: dict):
        async with transactional(self.user_repo.session) as tx_session:
            # Both operations in same transaction
            user = await self.user_repo.create(**user_data)
            profile_data["user_id"] = user.id
            profile = await self.profile_repo.create(**profile_data)
            return user, profile

    async def get_users_with_posts(self):
        # Avoid N+1 queries with eager loading
        return await QueryOptimizer.eager_load_relationships(
            self.user_repo.session,
            User,
            "posts",
            "profile"
        )

# 3. Database Configuration
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

engine = create_async_engine(
    DATABASE_URL,
    **DatabaseConfig.get_engine_options()
)

async_session_maker = async_sessionmaker(
    engine,
    **DatabaseConfig.get_session_options()
)

# 4. Health Monitoring
async def check_database_health(session: AsyncSession):
    monitor = DatabaseHealthMonitor(session)
    health = await monitor.health_check()
    pool_status = await monitor.get_pool_status()
    return {"health": health, "pool": pool_status}

# 5. Error Handling with Retry
async def resilient_database_operation():
    async with async_session_maker() as session:
        return await with_retry(
            some_database_function,
            session,
            max_retries=3,
            base_delay=1.0
        )

# 6. Testing Setup
@pytest.fixture
async def db_session():
    async with async_session_maker() as session:
        async with test_transaction(session) as tx_session:
            yield tx_session
"""

# =============================================================================
# MIGRATION NOTES FOR COS
# =============================================================================

"""
Migration Strategy for COS Database Operations:

1. FOUNDATION LAYER:
   - Update src/common/database.py with DatabaseConfig.get_engine_options()
   - Add circuit breaker and health monitoring to DatabaseResourceFactory
   - Maintain existing multi-schema support

2. PATTERN LAYER:
   - Refactor src/backend/cc/crud.py to use BaseRepository pattern
   - Replace manual commits with transactional() context managers
   - Add eager loading to prevent N+1 queries

3. APPLICATION LAYER:
   - Update src/backend/cc/mem0_crud.py with new patterns
   - Apply consistent patterns to src/graph/service.py
   - Ensure src/db/connection.py uses optimized settings

4. TESTING LAYER:
   - Use test_transaction() for all database tests
   - Add integration tests with testcontainers
   - Validate performance improvements

Performance Targets:
- Query latency: <1ms for simple operations
- Connection pool utilization: <80% under normal load
- Test coverage: 98%+ overall, 100% for database operations
- Zero connection leaks under all conditions

Quality Gates:
- All existing 2126 tests must pass
- Pre-commit hooks (ruff, mypy, bandit) must pass
- Performance benchmarks must meet or exceed current metrics
- Circuit breaker must prevent cascade failures
"""
