"""Neo4j graph database connection management.

This module provides async Neo4j driver management with Rust adapter support
and fallback to the standard bolt driver. Follows the singleton pattern
established in src/db/connection.py.
"""

import os
import warnings
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from functools import lru_cache
from typing import Any

from src.common.config import get_settings
from src.common.logger import log_event

__all__ = [
    "USING_RUST_DRIVER",
    "GraphDatabase",
    "Neo4jClient",
    "close_neo4j_connections",
    "get_async_neo4j",
    "get_neo4j_client",
]

# Attempt to import the Rust-enhanced Neo4j driver, fallback to standard driver
try:
    from neo4j_rust_ext import AsyncDriver, AsyncSession, GraphDatabase

    USING_RUST_DRIVER = True
    log_event(
        source="graph",
        data={"driver_type": "rust"},
        tags=["initialization", "performance"],
        memo="Using Neo4j Rust-enhanced driver for optimized performance",
    )
except ImportError:
    try:
        from neo4j import AsyncDriver, AsyncSession, GraphDatabase

        USING_RUST_DRIVER = False
        warnings.warn(
            "Neo4j Rust driver not available, falling back to standard driver. "
            "Install neo4j-rust-ext for better performance.",
            UserWarning,
            stacklevel=2,
        )
        log_event(
            source="graph",
            data={"driver_type": "standard", "reason": "rust_driver_unavailable"},
            tags=["initialization", "fallback"],
            memo="Falling back to standard Neo4j driver",
        )
    except ImportError as e:
        raise ImportError(
            "Neither neo4j-rust-ext nor neo4j packages are available. "
            "Please install one of them: 'pip install neo4j-rust-ext' or 'pip install neo4j'"
        ) from e


class Neo4jClient:
    """Async Neo4j client with connection pooling and health monitoring."""

    def __init__(self) -> None:
        """Initialize the Neo4j client with settings from configuration."""
        self.settings = get_settings()
        self.driver: AsyncDriver | None = None
        self._uri = self.settings.NEO4J_URI
        self._user = self.settings.NEO4J_USER
        self._password = self.settings.NEO4J_PASSWORD
        self._is_connected = False

    async def connect(self) -> None:
        """Establish connection to Neo4j database."""
        if self.driver is None:
            try:
                self.driver = GraphDatabase.driver(
                    self._uri,
                    auth=(self._user, self._password),
                    max_connection_lifetime=300,  # 5 minutes
                    max_connection_pool_size=50,
                    connection_acquisition_timeout=30,
                    connection_timeout=15,
                )

                # Verify connectivity
                await self.verify_connectivity()
                self._is_connected = True

                log_event(
                    source="graph",
                    data={
                        "uri": self._uri.split("@")[-1] if "@" in self._uri else self._uri,  # Hide credentials
                        "driver_type": "rust" if USING_RUST_DRIVER else "standard",
                    },
                    tags=["connection", "success"],
                    memo="Successfully connected to Neo4j database",
                )
            except Exception as e:
                log_event(
                    source="graph",
                    data={"error": str(e), "uri": self._uri.split("@")[-1] if "@" in self._uri else self._uri},
                    tags=["connection", "error"],
                    memo="Failed to connect to Neo4j database",
                )
                raise

    async def close(self) -> None:
        """Close the driver connection."""
        if self.driver:
            await self.driver.close()
            self.driver = None
            self._is_connected = False
            log_event(
                source="graph",
                data={},
                tags=["connection", "close"],
                memo="Neo4j driver connection closed",
            )

    async def verify_connectivity(self) -> bool:
        """Verify that the driver can connect to the database."""
        if not self.driver:
            return False

        try:
            async with self.driver.session() as session:
                result = await session.run("RETURN 1 as test")
                record = await result.single()
                return record is not None and record["test"] == 1
        except Exception as e:
            log_event(
                source="graph",
                data={"error": str(e)},
                tags=["health_check", "error"],
                memo="Neo4j connectivity verification failed",
            )
            return False

    @asynccontextmanager
    async def session(self) -> AsyncGenerator[AsyncSession, None]:
        """Get an async session from the driver pool."""
        if not self.driver:
            await self.connect()

        if not self.driver:
            raise RuntimeError("Failed to establish Neo4j connection")

        async with self.driver.session() as session:
            try:
                yield session
            except Exception as e:
                log_event(
                    source="graph",
                    data={"error": str(e)},
                    tags=["session", "error"],
                    memo="Error during Neo4j session operation",
                )
                raise

    async def execute_query(self, query: str, parameters: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        """Execute a Cypher query and return results as a list of dictionaries."""
        async with self.session() as session:
            try:
                result = await session.run(query, parameters or {})
                records = [dict(record) async for record in result]

                log_event(
                    source="graph",
                    data={
                        "query_type": query.strip().split()[0].upper(),
                        "record_count": len(records),
                        "has_parameters": bool(parameters),
                    },
                    tags=["query", "success"],
                    memo=f"Executed Cypher query successfully: {query[:50]}...",
                )

                return records
            except Exception as e:
                log_event(
                    source="graph",
                    data={
                        "error": str(e),
                        "query": query[:100],  # Log first 100 chars of query
                        "parameters": bool(parameters),
                    },
                    tags=["query", "error"],
                    memo="Failed to execute Cypher query",
                )
                raise

    @property
    def is_connected(self) -> bool:
        """Check if the client is connected."""
        return self._is_connected and self.driver is not None


def _graph_url_for_tests() -> str:
    """Return Neo4j connection URI based on environment configuration."""
    # Check for explicit NEO4J_TEST_URI override (used by conftest.py)
    if "NEO4J_TEST_URI" in os.environ:
        return os.environ["NEO4J_TEST_URI"]

    if os.getenv("ENABLE_GRAPH_INTEGRATION", "0") == "1":
        settings = get_settings()
        return settings.NEO4J_URI

    # For testing without integration, return a mock URI
    return "bolt://localhost:7687"


@lru_cache
def get_neo4j_client() -> Neo4jClient:
    """Get Neo4j client instance with caching disabled in test mode."""
    # In test mode, don't use cache to ensure fresh clients
    if "PYTEST_CURRENT_TEST" in os.environ:
        # Clear cache to get fresh instance for each test
        get_neo4j_client.cache_clear()

    client = Neo4jClient()
    # Override URI for tests if needed
    if "PYTEST_CURRENT_TEST" in os.environ:
        client._uri = _graph_url_for_tests()

    return client


async def get_async_neo4j() -> AsyncGenerator[Neo4jClient, None]:
    """FastAPI dependency for Neo4j client."""
    client = get_neo4j_client()

    # Only attempt connection if graph integration is enabled
    graph_enabled = get_settings().ENABLE_GRAPH_INTEGRATION or os.getenv("ENABLE_GRAPH_INTEGRATION", "0") == "1"
    if graph_enabled and not client.is_connected:
        await client.connect()

    try:
        yield client
    finally:
        # Don't close the client here as it's cached and may be reused
        # Connection will be closed on application shutdown
        pass


async def close_neo4j_connections() -> None:
    """Close all Neo4j connections. Call this on application shutdown."""
    try:
        # Clear the cache and close any open connections
        if get_neo4j_client.cache_info().currsize > 0:
            client = get_neo4j_client()
            await client.close()
            get_neo4j_client.cache_clear()

        log_event(
            source="graph",
            data={},
            tags=["shutdown", "cleanup"],
            memo="All Neo4j connections closed successfully",
        )
    except Exception as e:
        log_event(
            source="graph",
            data={"error": str(e)},
            tags=["shutdown", "error"],
            memo="Error closing Neo4j connections during shutdown",
        )
