"""Fake Neo4j implementation for testing without real Neo4j infrastructure.

This module provides async-compatible mock implementations of Neo4j driver components
to enable graph database tests without requiring a real Neo4j instance.
"""

from __future__ import annotations

import re
from typing import Any


class FakeRecord(dict[str, Any]):
    """Mock implementation of a Neo4j record."""

    def __init__(self, data: dict[str, Any]) -> None:
        """Initialize with record data."""
        super().__init__(data)

    def __getitem__(self, key: str) -> Any:
        """Allow dict-style access."""
        return super().__getitem__(key)


class FakeAsyncResult:
    """Mock implementation of Neo4j async result."""

    def __init__(self, records: list[dict[str, Any]]) -> None:
        """Initialize with list of record data."""
        self._records = [FakeRecord(r) for r in records]
        self._index = 0

    async def single(self) -> FakeRecord | None:
        """Return the first record if exactly one exists."""
        if len(self._records) == 1:
            return self._records[0]
        return None

    def __aiter__(self) -> FakeAsyncResult:
        """Return self as async iterator."""
        return self

    async def __anext__(self) -> FakeRecord:
        """Return next record in async iteration."""
        if self._index >= len(self._records):
            raise StopAsyncIteration
        record = self._records[self._index]
        self._index += 1
        return record

    async def data(self) -> list[dict[str, Any]]:
        """Return all records as list of dicts."""
        return [dict(r) for r in self._records]


class FakeAsyncSessionContext:
    """Context manager for fake async session supporting both sync and async protocols."""

    def __init__(self, session: FakeAsyncSession) -> None:
        """Initialize with session."""
        self._session = session

    async def __aenter__(self) -> FakeAsyncSession:
        """Enter async context."""
        return self._session

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Exit async context."""
        pass

    def __enter__(self) -> FakeAsyncSession:
        """Enter sync context for compatibility."""
        return self._session

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Exit sync context for compatibility."""
        pass


class FakeAsyncSession:
    """Mock implementation of Neo4j async session."""

    def __init__(self, graph_store: InMemoryGraphStore) -> None:
        """Initialize with reference to graph store."""
        self._store = graph_store

    async def run(self, query: str, parameters: dict[str, Any] | None = None) -> FakeAsyncResult:
        """Execute a Cypher query and return results."""
        _ = parameters  # Currently unused but kept for API compatibility

        # Parse and execute simple queries for testing
        query_upper = query.upper().strip()

        # Handle RETURN queries
        if query_upper.startswith("RETURN"):
            # Extract what to return (e.g., "RETURN 1 as test")
            match = re.search(r"RETURN\s+(\d+)\s+AS\s+(\w+)", query, re.IGNORECASE)
            if match:
                value = int(match.group(1))
                key = match.group(2)
                return FakeAsyncResult([{key: value}])

            # Handle "RETURN 2 as test" pattern
            match = re.search(r"RETURN\s+(\d+)\s+as\s+(\w+)", query, re.IGNORECASE)
            if match:
                value = int(match.group(1))
                key = match.group(2)
                return FakeAsyncResult([{key: value}])

        # Handle MATCH queries
        elif query_upper.startswith("MATCH"):
            # For now, return empty results for MATCH queries
            return FakeAsyncResult([])

        # Handle CREATE queries
        elif query_upper.startswith("CREATE"):
            # Simple node creation
            if "CREATE (n:" in query:
                # Extract node label and properties
                match = re.search(r"CREATE \((\w+):(\w+)\s*(\{[^}]+\})?\)", query)
                if match:
                    var_name = match.group(1)
                    label = match.group(2)
                    props_str = match.group(3) or "{}"

                    # Simple property parsing (for testing)
                    props = {}
                    if props_str and props_str != "{}":
                        # Extract key-value pairs
                        prop_matches = re.findall(r"(\w+):\s*['\"]([^'\"]+)['\"]", props_str)
                        for key, value in prop_matches:
                            props[key] = value

                    # Create node in store
                    node_id = self._store.create_node(label, props)
                    return FakeAsyncResult([{var_name: {"id": node_id, **props}}])

        # Default: return empty results
        return FakeAsyncResult([])

    async def __aenter__(self) -> FakeAsyncSession:
        """Enter async context."""
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Exit async context."""
        pass


class FakeAsyncDriver:
    """Mock implementation of Neo4j async driver."""

    def __init__(self, uri: str, auth: tuple[str, str]) -> None:
        """Initialize with connection parameters."""
        self._uri = uri
        self._auth = auth
        self._store = InMemoryGraphStore()
        self._closed = False

    def session(self) -> FakeAsyncSessionContext:
        """Create a new session context manager."""
        if self._closed:
            raise RuntimeError("Driver is closed")
        return FakeAsyncSessionContext(FakeAsyncSession(self._store))

    async def close(self) -> None:
        """Close the driver."""
        self._closed = True

    async def verify_connectivity(self) -> None:
        """Verify driver connectivity (no-op for fake)."""
        if self._closed:
            raise RuntimeError("Driver is closed")


class InMemoryGraphStore:
    """Simple in-memory graph storage for testing."""

    def __init__(self) -> None:
        """Initialize empty graph store."""
        self._nodes: dict[int, dict[str, Any]] = {}
        self._relationships: list[dict[str, Any]] = []
        self._next_node_id = 1

    def create_node(self, label: str, properties: dict[str, Any]) -> int:
        """Create a node and return its ID."""
        node_id = self._next_node_id
        self._next_node_id += 1

        self._nodes[node_id] = {"id": node_id, "label": label, "properties": properties.copy()}

        return node_id

    def get_node(self, node_id: int) -> dict[str, Any] | None:
        """Get a node by ID."""
        return self._nodes.get(node_id)

    def create_relationship(
        self, from_id: int, to_id: int, rel_type: str, properties: dict[str, Any] | None = None
    ) -> None:
        """Create a relationship between nodes."""
        self._relationships.append({"from": from_id, "to": to_id, "type": rel_type, "properties": properties or {}})


class FakeGraphDatabase:
    """Mock implementation of Neo4j GraphDatabase."""

    @staticmethod
    def driver(
        uri: str,
        auth: tuple[str, str],
        max_connection_lifetime: int = 300,
        max_connection_pool_size: int = 50,
        connection_acquisition_timeout: int = 30,
        connection_timeout: int = 15,
    ) -> FakeAsyncDriver:
        """Create a fake driver instance."""
        return FakeAsyncDriver(uri, auth)
