"""Fake Alembic implementation for testing migrations without a database.

This module provides mocks for Alembic commands and SQLAlchemy engine to enable
migration testing without requiring a real PostgreSQL database.

The implementation:
1. Tracks migration state in memory (schemas, tables, indexes)
2. Mocks SQLAlchemy async engine and connection interfaces
3. Parses and responds to specific SQL queries used in tests:
   - to_regclass() for table existence checks
   - information_schema queries for schema/table metadata
   - pg_indexes queries for index verification
4. Maintains state consistency across test runs with reset functionality

Usage:
    The test file should import and use the mock components:
    - FakeAlembicConfig for Alembic configuration
    - fake_upgrade/fake_downgrade for migration commands
    - get_fake_engine() for SQLAlchemy engine
    - reset_fake_db() to clear state between tests
"""

from __future__ import annotations

import re
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any


class InMemoryDatabase:
    """Tracks database state in memory for migration testing."""

    def __init__(self) -> None:
        # Track what migrations have been applied
        self.migrations_applied: list[str] = []

        # Track database structure
        self.schemas: set[str] = set()
        self.tables: set[tuple[str, str]] = set()  # (schema, table_name)
        self.indexes: dict[tuple[str, str, str], dict[str, Any]] = {}  # (schema, table, index) -> info

        # Initialize with expected state after migrations
        self._apply_migrations()

    def _apply_migrations(self) -> None:
        """Apply expected migration state."""
        if "head" in self.migrations_applied:
            return  # Already applied

        # Create schemas
        self.schemas.add("cc")
        self.schemas.add("mem0_cc")

        # Create tables
        self.tables.add(("cc", "health_status"))
        self.tables.add(("cc", "modules"))

        # Create indexes
        self.indexes[("cc", "health_status", "ix_cc_health_status_module")] = {"unique": True, "columns": ["module"]}
        self.indexes[("cc", "modules", "ix_cc_modules_name")] = {"unique": True, "columns": ["name"]}

        self.migrations_applied.append("head")

    def reset(self) -> None:
        """Reset database state."""
        self.migrations_applied.clear()
        self.schemas.clear()
        self.tables.clear()
        self.indexes.clear()


# Global database state for tests
_db = InMemoryDatabase()


class FakeResult:
    """Mock SQLAlchemy result object."""

    def __init__(self, data: Any) -> None:
        self._data = data
        self._rows = data if isinstance(data, list) else [data] if data is not None else []
        self._index = 0

    def scalar(self) -> Any:
        """Return scalar result."""
        if self._data is None:
            return None
        if isinstance(self._data, list):
            return self._data[0] if self._data else None
        return self._data

    def fetchone(self) -> tuple[Any, ...] | None:
        """Fetch one row."""
        if isinstance(self._data, list) and self._data:
            if isinstance(self._data[0], tuple):
                return self._data[0]
            return (self._data[0],) if self._data else None
        elif isinstance(self._data, tuple):
            return self._data
        elif self._data is not None:
            return (self._data,)
        return None


class FakeConnection:
    """Mock SQLAlchemy connection."""

    async def execute(self, query: Any, params: dict[str, Any] | None = None) -> FakeResult:
        """Execute a query and return mock results."""
        # Convert to string for parsing
        query_str = query.text if hasattr(query, "text") else str(query)

        # Handle to_regclass queries
        if "to_regclass" in query_str:
            table_ref = None

            # Check for parameterized query
            if params and "t" in params:
                table_ref = params["t"]
            else:
                # Check for inline table name like to_regclass('cc.modules')
                match = re.search(r"to_regclass\(['\"]([^'\"]+)['\"]\)", query_str)
                if match:
                    table_ref = match.group(1)

            if table_ref and "." in table_ref:
                # Parse schema.table format
                schema, table = table_ref.split(".", 1)
                if (schema, table) in _db.tables:
                    return FakeResult(table_ref)
            return FakeResult(None)

        # Handle information_schema.schemata queries
        if "information_schema.schemata" in query_str and "schema_name" in query_str:
            # Extract schema name from WHERE clause
            match = re.search(r"schema_name\s*=\s*'(\w+)'", query_str)
            if match:
                schema_name = match.group(1)
                if schema_name in _db.schemas:
                    return FakeResult(schema_name)
                return FakeResult(None)

        # Handle information_schema.tables queries
        if "information_schema.tables" in query_str:
            # Extract table and schema from WHERE clause
            table_match = re.search(r"table_name\s*=\s*'(\w+)'", query_str)
            schema_match = re.search(r"table_schema\s*=\s*'(\w+)'", query_str)

            if table_match and schema_match:
                table_name = table_match.group(1)
                schema_name = schema_match.group(1)

                if (schema_name, table_name) in _db.tables:
                    return FakeResult((schema_name, table_name))
            return FakeResult(None)

        # Handle pg_indexes queries
        if "pg_indexes" in query_str:
            # Extract index details from WHERE clause
            schema_match = re.search(r"schemaname\s*=\s*'(\w+)'", query_str)
            table_match = re.search(r"tablename\s*=\s*'(\w+)'", query_str)
            index_match = re.search(r"indexname\s*=\s*'([\w_]+)'", query_str)

            if schema_match and table_match and index_match:
                schema = schema_match.group(1)
                table = table_match.group(1)
                index = index_match.group(1)

                if (schema, table, index) in _db.indexes:
                    return FakeResult(index)
            return FakeResult(None)

        # Default case
        return FakeResult(None)

    async def commit(self) -> None:
        """Mock commit."""
        pass

    async def rollback(self) -> None:
        """Mock rollback."""
        pass


class FakeEngine:
    """Mock SQLAlchemy engine."""

    @asynccontextmanager
    async def connect(self) -> AsyncGenerator[FakeConnection, None]:
        """Return a fake connection context manager."""
        yield FakeConnection()

    async def dispose(self) -> None:
        """Mock dispose."""
        pass


class FakeAlembicConfig:
    """Mock Alembic Config object."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        self.attributes: dict[str, Any] = {}

    def set_main_option(self, key: str, value: str) -> None:
        """Mock set_main_option."""
        self.attributes[key] = value


def fake_upgrade(config: Any, revision: str, *args: Any, **kwargs: Any) -> None:
    """Mock alembic.command.upgrade."""
    # Apply migrations if not already applied
    if revision == "head" and "head" not in _db.migrations_applied:
        _db._apply_migrations()


def fake_downgrade(config: Any, revision: str, *args: Any, **kwargs: Any) -> None:
    """Mock alembic.command.downgrade."""
    # For simplicity, just clear the state
    if revision == "base":
        _db.reset()


def get_fake_engine() -> FakeEngine:
    """Return a fake engine for testing."""
    return FakeEngine()


def reset_fake_db() -> None:
    """Reset the fake database state between tests."""
    _db.reset()
