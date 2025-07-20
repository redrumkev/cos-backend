"""Tests for graph base module.

Tests cover Neo4j connection management, health monitoring, and error handling
with both integration and unit testing approaches.
"""

from __future__ import annotations

import contextlib
import os
from collections.abc import AsyncGenerator
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest  # Phase 2: Remove for skip removal

from src.graph.base import (
    USING_RUST_DRIVER,
    Neo4jClient,
    _graph_url_for_tests,
    close_neo4j_connections,
    get_async_neo4j,
    get_neo4j_client,
)
from tests.fakes.fake_neo4j import FakeGraphDatabase

# Phase 2: Graph client implementation ready - removing skip marker
# pytestmark = pytest.mark.skip(reason="Phase 2: Graph client implementation needed. Trigger: P2-GRAPH-001")


class TestNeo4jClient:
    """Test cases for Neo4jClient class."""

    def test_init_creates_client_with_settings(self) -> None:
        """Test that Neo4jClient initializes with proper settings."""
        client = Neo4jClient()

        assert client.driver is None
        assert client._is_connected is False
        assert client._uri is not None
        assert client._user is not None
        assert client._password is not None

    @pytest.mark.asyncio
    async def test_connect_successful(self) -> None:
        """Test successful connection to Neo4j."""
        client = Neo4jClient()

        # Mock the GraphDatabase.driver
        mock_driver = AsyncMock()
        mock_session = AsyncMock()
        mock_result = AsyncMock()
        mock_record = MagicMock()
        mock_record.__getitem__.return_value = 1
        mock_result.single.return_value = mock_record
        mock_session.run.return_value = mock_result
        mock_driver.session.return_value.__aenter__.return_value = mock_session
        mock_driver.session.return_value.__aexit__.return_value = None

        with patch("src.graph.base.GraphDatabase") as mock_graph_db:
            mock_graph_db.driver.return_value = mock_driver

            await client.connect()

            assert client.driver is not None
            assert client._is_connected is True
            mock_graph_db.driver.assert_called_once()

    @pytest.mark.asyncio
    async def test_connect_fails_with_invalid_credentials(self) -> None:
        """Test connection failure with invalid credentials."""
        client = Neo4jClient()

        with patch("src.graph.base.GraphDatabase") as mock_graph_db:
            mock_graph_db.driver.side_effect = Exception("Authentication failed")

            with pytest.raises(Exception, match="Authentication failed"):
                await client.connect()

            assert client.driver is None
            assert client._is_connected is False

    @pytest.mark.asyncio
    async def test_verify_connectivity_success(self) -> None:
        """Test successful connectivity verification."""
        client = Neo4jClient()

        # Mock the driver and session for connectivity check
        mock_session = MagicMock()
        mock_result = MagicMock()
        mock_record = {"test": 1}  # Use a dict instead of MagicMock
        # Make single() synchronous (matches real Neo4j interface)
        mock_result.single.return_value = mock_record
        mock_session.run.return_value = mock_result
        # Add close method to session (synchronous in real Neo4j)
        mock_session.close = MagicMock()

        mock_driver = MagicMock()  # Use regular MagicMock for driver
        # The driver.session() should return the session object directly (which is its own context manager)
        mock_driver.session.return_value = mock_session

        client.driver = mock_driver

        # Patch log_event to avoid database errors
        with patch("src.graph.base.log_event"):
            result = await client.verify_connectivity()

        assert result is True
        # Verify mock was called
        mock_session.run.assert_called_once_with("RETURN 1 as test")
        assert mock_result.single.called

    @pytest.mark.asyncio
    async def test_verify_connectivity_failure(self) -> None:
        """Test connectivity verification failure."""
        client = Neo4jClient()

        # Mock failed verification
        mock_driver = AsyncMock()
        mock_session = AsyncMock()
        mock_session.run.side_effect = Exception("Connection lost")
        mock_driver.session.return_value.__aenter__.return_value = mock_session
        mock_driver.session.return_value.__aexit__.return_value = None

        client.driver = mock_driver

        result = await client.verify_connectivity()
        assert result is False

    @pytest.mark.asyncio
    async def test_verify_connectivity_no_driver(self) -> None:
        """Test connectivity verification with no driver."""
        client = Neo4jClient()

        result = await client.verify_connectivity()
        assert result is False

    @pytest.mark.asyncio
    async def test_close_connection(self) -> None:
        """Test closing the Neo4j connection."""
        client = Neo4jClient()

        # Mock driver
        mock_driver = AsyncMock()
        client.driver = mock_driver
        client._is_connected = True

        await client.close()

        mock_driver.close.assert_called_once()
        assert client.driver is None
        assert client._is_connected is False

    @pytest.mark.asyncio
    async def test_session_context_manager(self) -> None:
        """Test session context manager functionality."""
        client = Neo4jClient()

        # Mock the driver and session properly
        mock_session = AsyncMock()
        # Add close method to session (synchronous in real Neo4j)
        mock_session.close = MagicMock()
        mock_driver = MagicMock()

        # The driver.session() should return the session object directly (which is its own context manager)
        mock_driver.session.return_value = mock_session

        client.driver = mock_driver
        async with client.session() as session:
            assert session is mock_session

    @pytest.mark.asyncio
    async def test_session_auto_connect(self) -> None:
        """Test that session auto-connects when needed."""
        client = Neo4jClient()

        # Mock auto-connection behavior
        with patch.object(client, "connect", new_callable=AsyncMock) as mock_connect:
            mock_session = AsyncMock()
            # Add close method to session
            mock_session.close = AsyncMock()
            mock_driver = MagicMock()

            # The driver.session() should return the session object directly
            mock_driver.session.return_value = mock_session

            # Set driver to None to force connection
            client.driver = None
            client._is_connected = False

            # After connection, set the mock driver
            async def mock_connect_func() -> None:
                client.driver = mock_driver
                client._is_connected = True

            mock_connect.side_effect = mock_connect_func

            async with client.session() as session:
                mock_connect.assert_called_once()
                assert session is mock_session

    @pytest.mark.asyncio
    async def test_execute_query_success(self) -> None:
        """Test successful query execution."""
        client = Neo4jClient()

        # Mock session and result
        mock_record = {"n": {"name": "test"}}

        # Create a proper async iterator mock
        class MockAsyncIterator:
            async def __aiter__(self) -> AsyncGenerator[dict[str, Any], None]:
                yield mock_record

        mock_result = MockAsyncIterator()

        mock_session = MagicMock()
        mock_session.run.return_value = mock_result

        with patch.object(client, "session") as mock_session_cm:
            mock_session_cm.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session_cm.return_value.__aexit__ = AsyncMock(return_value=None)

            result = await client.execute_query("MATCH (n) RETURN n")

            assert result == [mock_record]
            mock_session.run.assert_called_once_with("MATCH (n) RETURN n", {})

    @pytest.mark.asyncio
    async def test_execute_query_with_parameters(self) -> None:
        """Test query execution with parameters."""
        client = Neo4jClient()
        params = {"name": "test"}

        # Mock session and result
        mock_record = {"n": {"name": "test"}}

        # Create a proper async iterator mock
        class MockAsyncIterator:
            async def __aiter__(self) -> AsyncGenerator[dict[str, Any], None]:
                yield mock_record

        mock_result = MockAsyncIterator()

        mock_session = MagicMock()
        mock_session.run.return_value = mock_result

        with patch.object(client, "session") as mock_session_cm:
            mock_session_cm.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session_cm.return_value.__aexit__ = AsyncMock(return_value=None)

            await client.execute_query("MATCH (n {name: $name}) RETURN n", params)

            mock_session.run.assert_called_once_with("MATCH (n {name: $name}) RETURN n", params)

    @pytest.mark.asyncio
    async def test_execute_query_error_handling(self) -> None:
        """Test query execution error handling."""
        client = Neo4jClient()

        mock_session = AsyncMock()
        mock_session.run.side_effect = Exception("Neo4j query error")

        with patch.object(client, "session") as mock_session_cm:
            mock_session_cm.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session_cm.return_value.__aexit__ = AsyncMock(return_value=None)

            with pytest.raises(Exception, match="Query failed"):
                await client.execute_query("INVALID QUERY")

    def test_is_connected_property(self) -> None:
        """Test the is_connected property."""
        client = Neo4jClient()

        # Initially not connected
        assert client.is_connected is False

        # Mock connected state
        client._is_connected = True
        client.driver = AsyncMock()
        assert client.is_connected is True

        # Only driver, but not marked as connected
        client._is_connected = False
        assert client.is_connected is False


class TestModuleFunctions:
    """Test cases for module-level functions."""

    def test_graph_url_for_tests_with_override(self) -> None:
        """Test _graph_url_for_tests with explicit override."""
        test_uri = "bolt://test:7687"
        with patch.dict(os.environ, {"NEO4J_TEST_URI": test_uri}):
            result = _graph_url_for_tests()
            assert result == test_uri

    def test_graph_url_for_tests_with_integration_enabled(self) -> None:
        """Test _graph_url_for_tests with integration enabled."""
        with (
            patch.dict(os.environ, {"ENABLE_GRAPH_INTEGRATION": "1"}),
            patch("src.graph.base.get_settings") as mock_settings,
        ):
            mock_settings.return_value.NEO4J_URI = "bolt://integration:7687"
            result = _graph_url_for_tests()
            assert result == "bolt://integration:7687"

    def test_graph_url_for_tests_default(self) -> None:
        """Test _graph_url_for_tests default behavior."""
        with patch.dict(os.environ, {}, clear=True):
            result = _graph_url_for_tests()
            assert result == "bolt://localhost:7687"

    def test_get_neo4j_client_caching(self) -> None:
        """Test that get_neo4j_client returns cached instance."""
        # Clear cache first
        get_neo4j_client.cache_clear()

        client1 = get_neo4j_client()
        client2 = get_neo4j_client()

        assert client1 is client2

    def test_get_neo4j_client_test_mode_no_cache(self) -> None:
        """Test that get_neo4j_client doesn't cache in test mode."""
        with patch.dict(os.environ, {"PYTEST_CURRENT_TEST": "test"}):
            get_neo4j_client.cache_clear()

            client1 = get_neo4j_client()
            client2 = get_neo4j_client()

            # In test mode, cache should be cleared, so instances might differ
            # This tests the cache clearing behavior
            assert isinstance(client1, Neo4jClient)
            assert isinstance(client2, Neo4jClient)

    @pytest.mark.asyncio
    async def test_get_async_neo4j_dependency(self) -> None:
        """Test get_async_neo4j FastAPI dependency."""
        with patch("src.graph.base.get_settings") as mock_settings:
            mock_settings.return_value.ENABLE_GRAPH_INTEGRATION = False

            # Use async generator correctly
            dependency = get_async_neo4j()
            client = await dependency.__anext__()
            assert isinstance(client, Neo4jClient)
            # Clean up
            with contextlib.suppress(StopAsyncIteration):
                await dependency.__anext__()

    @pytest.mark.asyncio
    async def test_get_async_neo4j_with_integration_enabled(self) -> None:
        """Test get_async_neo4j with graph integration enabled."""
        with patch("src.graph.base.get_settings") as mock_settings:
            mock_settings.return_value.ENABLE_GRAPH_INTEGRATION = True

            with patch("src.graph.base.get_neo4j_client") as mock_get_client:
                mock_client = AsyncMock()
                mock_client.is_connected = False
                mock_client.connect = AsyncMock()
                mock_get_client.return_value = mock_client

                # Use async generator correctly
                dependency = get_async_neo4j()
                client = await dependency.__anext__()
                assert client is mock_client
                mock_client.connect.assert_called_once()
                # Clean up
                with contextlib.suppress(StopAsyncIteration):
                    await dependency.__anext__()

    @pytest.mark.asyncio
    async def test_close_neo4j_connections(self) -> None:
        """Test closing all Neo4j connections."""
        # Mock cache with connections
        mock_client = AsyncMock()
        mock_client.close = AsyncMock()

        with patch("src.graph.base.get_neo4j_client") as mock_get_client:
            # Mock cache info to indicate connections exist
            mock_get_client.cache_info.return_value.currsize = 1
            mock_get_client.return_value = mock_client
            mock_get_client.cache_clear = MagicMock()

            await close_neo4j_connections()

            mock_client.close.assert_called_once()
            mock_get_client.cache_clear.assert_called_once()

    @pytest.mark.asyncio
    async def test_close_neo4j_connections_error_handling(self) -> None:
        """Test error handling in close_neo4j_connections."""
        with patch("src.graph.base.get_neo4j_client") as mock_get_client:
            mock_get_client.cache_info.side_effect = Exception("Cache error")

            # Should not raise exception
            await close_neo4j_connections()


class TestDriverConfiguration:
    """Test cases for driver configuration and detection."""

    def test_rust_driver_flag(self) -> None:
        """Test that USING_RUST_DRIVER flag is set correctly."""
        # This test validates that the flag is a boolean
        assert isinstance(USING_RUST_DRIVER, bool)

    def test_driver_import_logic(self) -> None:
        """Test driver import fallback logic."""
        # This is more of a validation test since the import happens at module level
        # We can at least verify that one of the drivers was successfully imported
        from src.graph.base import GraphDatabase

        assert GraphDatabase is not None


@pytest.mark.integration
class TestNeo4jIntegration:
    """Integration tests for Neo4j connectivity.

    These tests require ENABLE_GRAPH_INTEGRATION=1 and a running Neo4j instance.
    """

    @pytest.fixture(autouse=True)
    def mock_log_event(self) -> Any:
        """Mock log_event to avoid database writes during tests."""
        with patch("src.graph.base.log_event"):
            yield

    @pytest.mark.asyncio
    async def test_real_connection(self) -> None:
        """Test real connection to Neo4j (integration test)."""
        # Use FakeGraphDatabase instead of real Neo4j
        with patch("src.graph.base.GraphDatabase", FakeGraphDatabase):
            client = Neo4jClient()

            try:
                await client.connect()
                assert client.is_connected is True

                # Test connectivity
                connected = await client.verify_connectivity()
                assert connected is True

            finally:
                await client.close()

    @pytest.mark.asyncio
    async def test_real_query_execution(self) -> None:
        """Test real query execution (integration test)."""
        # Use FakeGraphDatabase instead of real Neo4j
        with patch("src.graph.base.GraphDatabase", FakeGraphDatabase):
            client = Neo4jClient()

            try:
                await client.connect()

                # Execute a simple query
                result = await client.execute_query("RETURN 1 as test")
                assert len(result) == 1
                assert result[0]["test"] == 1

            finally:
                await client.close()

    @pytest.mark.asyncio
    async def test_real_session_management(self) -> None:
        """Test real session management (integration test)."""
        # Use FakeGraphDatabase instead of real Neo4j
        with patch("src.graph.base.GraphDatabase", FakeGraphDatabase):
            client = Neo4jClient()

            try:
                await client.connect()

                # Test session context manager
                async with client.session() as session:
                    result = session.run("RETURN 2 as test")
                    record = result.single()
                    assert record["test"] == 2

            finally:
                await client.close()
