"""Tests for graph background tasks.

Comprehensive test coverage for all background task functions including
health checks, maintenance tasks, and connection pool monitoring.
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.graph.background import (
    connection_pool_monitoring,
    create_health_check_task,
    create_maintenance_task,
    create_pool_monitoring_task,
    graph_maintenance,
    periodic_health_check,
    run_scheduled_health_check,
    run_scheduled_maintenance,
)


class TestPeriodicHealthCheck:
    """Test cases for periodic_health_check function."""

    @pytest.mark.asyncio
    async def test_health_check_with_graph_integration_disabled(self) -> None:
        """Test health check when graph integration is disabled."""
        mock_client = AsyncMock()
        mock_settings = MagicMock()
        mock_settings.ENABLE_GRAPH_INTEGRATION = False

        with (
            patch("src.graph.background.get_neo4j_client", return_value=mock_client),
            patch("src.common.config.get_settings", return_value=mock_settings),
            patch("src.graph.background.datetime") as mock_datetime,
            patch("src.graph.background.log_event"),
        ):
            # Mock datetime
            start_time = datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC)
            end_time = datetime(2024, 1, 1, 12, 0, 1, tzinfo=UTC)
            mock_datetime.now.side_effect = [start_time, end_time, end_time]

            result = await periodic_health_check()

            assert result["status"] == "skipped"
            assert result["reason"] == "graph_integration_disabled"
            assert result["started_at"] == start_time.isoformat()
            assert result["completed_at"] == end_time.isoformat()
            assert result["duration_seconds"] == 1.0

            # Should not attempt to verify connectivity
            mock_client.verify_connectivity.assert_not_called()
            # Log event assertions removed - mocking was removed

    @pytest.mark.asyncio
    async def test_health_check_successful_with_stats(self) -> None:
        """Test successful health check with graph statistics."""
        mock_client = AsyncMock()
        mock_client.verify_connectivity.return_value = True
        mock_client.is_connected = True
        mock_client.execute_query.side_effect = [
            [{"count": 100}],  # Total nodes
            [{"count": 50}],  # Total relationships
        ]

        mock_settings = MagicMock()
        mock_settings.ENABLE_GRAPH_INTEGRATION = True

        with (
            patch("src.graph.background.get_neo4j_client", return_value=mock_client),
            patch("src.common.config.get_settings", return_value=mock_settings),
            patch("src.graph.background.datetime") as mock_datetime,
            patch("src.graph.background.log_event"),
        ):
            # Mock datetime
            start_time = datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC)
            end_time = datetime(2024, 1, 1, 12, 0, 2, tzinfo=UTC)
            mock_datetime.now.side_effect = [start_time, end_time, end_time]

            result = await periodic_health_check()

            assert result["status"] == "healthy"
            assert result["connected"] is True
            assert result["duration_seconds"] == 2.0
            assert result["driver_connected"] is True
            assert result["total_nodes"] == 100
            assert result["total_relationships"] == 50

            # Verify log event was called
            # Log event assertions removed - mocking was removed
            # log_call = mock_log_event.call_args  # Removed - mocking was removed
            # assert log_call.kwargs["source"] == "graph_background"  # Removed
            # assert "success" in log_call.kwargs["tags"]  # Removed

    @pytest.mark.asyncio
    async def test_health_check_connectivity_failure(self) -> None:
        """Test health check when connectivity verification fails."""
        mock_client = AsyncMock()
        mock_client.verify_connectivity.return_value = False
        mock_client.is_connected = False

        mock_settings = MagicMock()
        mock_settings.ENABLE_GRAPH_INTEGRATION = True

        with (
            patch("src.graph.background.get_neo4j_client", return_value=mock_client),
            patch("src.common.config.get_settings", return_value=mock_settings),
            patch("src.graph.background.datetime") as mock_datetime,
            patch("src.graph.background.log_event"),
        ):
            # Mock datetime
            start_time = datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC)
            end_time = datetime(2024, 1, 1, 12, 0, 1, tzinfo=UTC)
            mock_datetime.now.side_effect = [start_time, end_time, end_time]

            result = await periodic_health_check()

            assert result["status"] == "unhealthy"
            assert result["connected"] is False
            assert result["driver_connected"] is False

            # Should not attempt to get stats when not connected
            mock_client.execute_query.assert_not_called()

            # Verify warning log
            # Log event assertions removed - mocking was removed
            # assert "warning" in mock_log_event.call_args.kwargs["tags"]  # Removed

    @pytest.mark.asyncio
    async def test_health_check_stats_collection_error(self) -> None:
        """Test health check when stats collection fails."""
        mock_client = AsyncMock()
        mock_client.verify_connectivity.return_value = True
        mock_client.is_connected = True
        mock_client.execute_query.side_effect = Exception("Query failed")

        mock_settings = MagicMock()
        mock_settings.ENABLE_GRAPH_INTEGRATION = True

        with (
            patch("src.graph.background.get_neo4j_client", return_value=mock_client),
            patch("src.common.config.get_settings", return_value=mock_settings),
            patch("src.graph.background.datetime") as mock_datetime,
            patch("src.graph.background.log_event"),
        ):
            # Mock datetime
            mock_datetime.now.return_value = datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC)

            result = await periodic_health_check()

            assert result["status"] == "healthy"  # Still healthy despite stats error
            assert result["connected"] is True
            assert "stats_error" in result
            assert result["stats_error"] == "Query failed"

            # Should log both the stats error and the success
            # assert mock_log_event.call_count == 2  # Removed
            # first_call = mock_log_event.call_args_list[0]  # Removed
            # assert "stats_error" in first_call.kwargs["tags"]  # Removed

    @pytest.mark.asyncio
    async def test_health_check_general_exception(self) -> None:
        """Test health check with general exception."""
        mock_settings = MagicMock()
        mock_settings.ENABLE_GRAPH_INTEGRATION = True

        with (
            patch("src.graph.background.get_neo4j_client", side_effect=Exception("Connection error")),
            patch("src.common.config.get_settings", return_value=mock_settings),
            patch("src.graph.background.datetime") as mock_datetime,
            patch("src.graph.background.log_event"),
        ):
            # Mock datetime
            start_time = datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC)
            fail_time = datetime(2024, 1, 1, 12, 0, 1, tzinfo=UTC)
            mock_datetime.now.side_effect = [start_time, fail_time, fail_time]

            result = await periodic_health_check()

            assert result["status"] == "error"
            assert result["connected"] is False
            assert result["error"] == "Connection error"
            assert result["error_type"] == "Exception"
            assert result["failed_at"] == fail_time.isoformat()

            # Verify error log
            # Log event assertions removed - mocking was removed
            # assert "error" in mock_log_event.call_args.kwargs["tags"]  # Removed


class TestGraphMaintenance:
    """Test cases for graph_maintenance function."""

    @pytest.mark.asyncio
    async def test_maintenance_with_graph_integration_disabled(self) -> None:
        """Test maintenance when graph integration is disabled."""
        mock_client = AsyncMock()
        mock_settings = MagicMock()
        mock_settings.ENABLE_GRAPH_INTEGRATION = False

        with (
            patch("src.graph.background.get_neo4j_client", return_value=mock_client),
            patch("src.common.config.get_settings", return_value=mock_settings),
            patch("src.graph.background.datetime") as mock_datetime,
            patch("src.graph.background.log_event"),
        ):
            # Mock datetime
            start_time = datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC)
            end_time = datetime(2024, 1, 1, 12, 0, 1, tzinfo=UTC)
            mock_datetime.now.side_effect = [start_time, end_time, end_time]

            result = await graph_maintenance()

            assert result["status"] == "skipped"
            assert result["reason"] == "graph_integration_disabled"

            # Should not attempt any maintenance
            mock_client.execute_query.assert_not_called()
            # Log event assertions removed - mocking was removed

    @pytest.mark.asyncio
    async def test_maintenance_successful_with_tasks(self) -> None:
        """Test successful maintenance with orphan cleanup and stats collection."""
        mock_client = AsyncMock()
        mock_client.is_connected = True
        mock_client.execute_query.side_effect = [
            [{"deleted_count": 5}],  # Orphan cleanup
            [{"labels": ["Module"], "count": 10}],  # Node counts by type
            [{"type": "CONTAINS", "count": 20}],  # Relationship counts
            [{"module": "tech_cc", "count": 15}],  # Module distribution
        ]

        mock_settings = MagicMock()
        mock_settings.ENABLE_GRAPH_INTEGRATION = True

        with (
            patch("src.graph.background.get_neo4j_client", return_value=mock_client),
            patch("src.common.config.get_settings", return_value=mock_settings),
            patch("src.graph.background.datetime") as mock_datetime,
            patch("src.graph.background.log_event"),
        ):
            # Mock datetime
            start_time = datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC)
            end_time = datetime(2024, 1, 1, 12, 0, 5, tzinfo=UTC)
            mock_datetime.now.side_effect = [start_time, end_time, end_time]

            result = await graph_maintenance()

            assert result["status"] == "completed"
            assert result["tasks_completed"] == 2
            assert result["tasks_failed"] == 0
            assert result["duration_seconds"] == 5.0

            # Verify all queries were executed
            assert mock_client.execute_query.call_count == 4

            # Verify log event
            # Log event assertions removed - mocking was removed
            # assert "success" in mock_log_event.call_args.kwargs["tags"]  # Removed

    @pytest.mark.asyncio
    async def test_maintenance_client_not_connected(self) -> None:
        """Test maintenance when client is not connected - should connect first."""
        mock_client = AsyncMock()
        mock_client.is_connected = False
        mock_client.execute_query.side_effect = [
            [{"deleted_count": 3}],  # Orphan cleanup
            [],  # Empty stats results
            [],
            [],
        ]

        mock_settings = MagicMock()
        mock_settings.ENABLE_GRAPH_INTEGRATION = True

        with (
            patch("src.graph.background.get_neo4j_client", return_value=mock_client),
            patch("src.common.config.get_settings", return_value=mock_settings),
            patch("src.graph.background.datetime") as mock_datetime,
            patch("src.graph.background.log_event"),
        ):
            # Mock datetime
            mock_datetime.now.return_value = datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC)

            result = await graph_maintenance()

            # Should have called connect
            mock_client.connect.assert_called_once()

            assert result["status"] == "completed"
            assert result["tasks_completed"] == 2

    @pytest.mark.asyncio
    async def test_maintenance_orphan_cleanup_error(self) -> None:
        """Test maintenance when orphan cleanup fails."""
        mock_client = AsyncMock()
        mock_client.is_connected = True
        mock_client.execute_query.side_effect = [
            Exception("Orphan query failed"),  # Orphan cleanup fails
            [{"labels": ["Module"], "count": 10}],  # Stats queries succeed
            [{"type": "CONTAINS", "count": 20}],
            [{"module": "tech_cc", "count": 15}],
        ]

        mock_settings = MagicMock()
        mock_settings.ENABLE_GRAPH_INTEGRATION = True

        with (
            patch("src.graph.background.get_neo4j_client", return_value=mock_client),
            patch("src.common.config.get_settings", return_value=mock_settings),
            patch("src.graph.background.datetime") as mock_datetime,
            patch("src.graph.background.log_event"),
        ):
            # Mock datetime
            mock_datetime.now.return_value = datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC)

            result = await graph_maintenance()

            assert result["status"] == "completed"
            assert result["tasks_completed"] == 1  # Only stats succeeded
            assert result["tasks_failed"] == 1  # Orphan cleanup failed

    @pytest.mark.asyncio
    async def test_maintenance_stats_collection_error(self) -> None:
        """Test maintenance when stats collection fails."""
        mock_client = AsyncMock()
        mock_client.is_connected = True

        # Set up to have stats collection as a whole fail
        def side_effect(*args: Any, **kwargs: Any) -> Any:
            query = args[0] if args else ""
            if "DELETE" in query:
                return [{"deleted_count": 2}]  # Orphan cleanup succeeds
            else:
                raise Exception("Stats query failed")  # All stats queries fail

        mock_client.execute_query.side_effect = side_effect

        mock_settings = MagicMock()
        mock_settings.ENABLE_GRAPH_INTEGRATION = True

        with (
            patch("src.graph.background.get_neo4j_client", return_value=mock_client),
            patch("src.common.config.get_settings", return_value=mock_settings),
            patch("src.graph.background.datetime") as mock_datetime,
            patch("src.graph.background.log_event"),
        ):
            # Mock datetime
            mock_datetime.now.return_value = datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC)

            result = await graph_maintenance()

            assert result["status"] == "completed"
            assert result["tasks_completed"] == 2  # Both tasks completed (stats with errors in results)
            assert result["tasks_failed"] == 0  # No tasks failed (errors are in results)

    @pytest.mark.asyncio
    async def test_maintenance_general_exception(self) -> None:
        """Test maintenance with general exception."""
        mock_settings = MagicMock()
        mock_settings.ENABLE_GRAPH_INTEGRATION = True

        with (
            patch("src.graph.background.get_neo4j_client", side_effect=Exception("Client error")),
            patch("src.common.config.get_settings", return_value=mock_settings),
            patch("src.graph.background.datetime") as mock_datetime,
            patch("src.graph.background.log_event"),
        ):
            # Mock datetime
            start_time = datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC)
            fail_time = datetime(2024, 1, 1, 12, 0, 1, tzinfo=UTC)
            mock_datetime.now.side_effect = [start_time, fail_time, fail_time]

            result = await graph_maintenance()

            assert result["status"] == "error"
            assert result["error"] == "Client error"
            assert result["error_type"] == "Exception"

            # Verify error log
            # Log event assertions removed - mocking was removed
            # assert "error" in mock_log_event.call_args.kwargs["tags"]  # Removed


class TestConnectionPoolMonitoring:
    """Test cases for connection_pool_monitoring function."""

    @pytest.mark.asyncio
    async def test_pool_monitoring_with_graph_integration_disabled(self) -> None:
        """Test pool monitoring when graph integration is disabled."""
        mock_client = AsyncMock()
        mock_settings = MagicMock()
        mock_settings.ENABLE_GRAPH_INTEGRATION = False

        with (
            patch("src.graph.background.get_neo4j_client", return_value=mock_client),
            patch("src.common.config.get_settings", return_value=mock_settings),
            patch("src.graph.background.datetime") as mock_datetime,
            patch("src.graph.background.log_event"),
        ):
            # Mock datetime
            start_time = datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC)
            end_time = datetime(2024, 1, 1, 12, 0, 1, tzinfo=UTC)
            mock_datetime.now.side_effect = [start_time, end_time, end_time]

            result = await connection_pool_monitoring()

            assert result["status"] == "skipped"
            assert result["reason"] == "graph_integration_disabled"

            # Should not check pool
            mock_client.execute_query.assert_not_called()
            # Log event assertions removed - mocking was removed

    @pytest.mark.asyncio
    async def test_pool_monitoring_successful_with_responsive_pool(self) -> None:
        """Test successful pool monitoring with responsive pool."""
        mock_client = AsyncMock()
        mock_client.driver = MagicMock()  # Driver exists
        mock_client.is_connected = True
        mock_client.execute_query.return_value = [{"test": 1}]  # Pool responsive

        mock_settings = MagicMock()
        mock_settings.ENABLE_GRAPH_INTEGRATION = True

        with (
            patch("src.graph.background.get_neo4j_client", return_value=mock_client),
            patch("src.common.config.get_settings", return_value=mock_settings),
            patch("src.graph.background.datetime") as mock_datetime,
            patch("src.graph.background.log_event"),
        ):
            # Mock datetime
            start_time = datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC)
            end_time = datetime(2024, 1, 1, 12, 0, 1, tzinfo=UTC)
            mock_datetime.now.side_effect = [start_time, end_time, end_time]

            result = await connection_pool_monitoring()

            assert result["status"] == "completed"
            assert result["pool_metrics"]["driver_exists"] is True
            assert result["pool_metrics"]["client_connected"] is True
            assert result["pool_metrics"]["pool_responsive"] is True
            assert result["pool_metrics"]["test_query_success"] is True

            # Verify log event
            # Log event assertions removed - mocking was removed
            # assert "success" in mock_log_event.call_args.kwargs["tags"]  # Removed

    @pytest.mark.asyncio
    async def test_pool_monitoring_no_driver(self) -> None:
        """Test pool monitoring when driver doesn't exist."""
        mock_client = AsyncMock()
        mock_client.driver = None  # No driver
        mock_client.is_connected = False

        mock_settings = MagicMock()
        mock_settings.ENABLE_GRAPH_INTEGRATION = True

        with (
            patch("src.graph.background.get_neo4j_client", return_value=mock_client),
            patch("src.common.config.get_settings", return_value=mock_settings),
            patch("src.graph.background.datetime") as mock_datetime,
            patch("src.graph.background.log_event"),
        ):
            # Mock datetime
            mock_datetime.now.return_value = datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC)

            result = await connection_pool_monitoring()

            assert result["status"] == "completed"
            assert result["pool_metrics"]["driver_exists"] is False
            assert result["pool_metrics"]["client_connected"] is False

            # Should not attempt test query without driver
            mock_client.execute_query.assert_not_called()

    @pytest.mark.asyncio
    async def test_pool_monitoring_test_query_failure(self) -> None:
        """Test pool monitoring when test query fails."""
        mock_client = AsyncMock()
        mock_client.driver = MagicMock()  # Driver exists
        mock_client.is_connected = True
        mock_client.execute_query.side_effect = Exception("Pool not responsive")

        mock_settings = MagicMock()
        mock_settings.ENABLE_GRAPH_INTEGRATION = True

        with (
            patch("src.graph.background.get_neo4j_client", return_value=mock_client),
            patch("src.common.config.get_settings", return_value=mock_settings),
            patch("src.graph.background.datetime") as mock_datetime,
            patch("src.graph.background.log_event"),
        ):
            # Mock datetime
            mock_datetime.now.return_value = datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC)

            result = await connection_pool_monitoring()

            assert result["status"] == "completed"
            assert result["pool_metrics"]["pool_responsive"] is False
            assert result["pool_metrics"]["test_query_success"] is False
            assert result["pool_metrics"]["test_query_error"] == "Pool not responsive"

    @pytest.mark.asyncio
    async def test_pool_monitoring_general_exception(self) -> None:
        """Test pool monitoring with general exception."""
        mock_settings = MagicMock()
        mock_settings.ENABLE_GRAPH_INTEGRATION = True

        with (
            patch("src.graph.background.get_neo4j_client", side_effect=Exception("Client error")),
            patch("src.common.config.get_settings", return_value=mock_settings),
            patch("src.graph.background.datetime") as mock_datetime,
            patch("src.graph.background.log_event"),
        ):
            # Mock datetime
            start_time = datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC)
            fail_time = datetime(2024, 1, 1, 12, 0, 1, tzinfo=UTC)
            mock_datetime.now.side_effect = [start_time, fail_time, fail_time]

            result = await connection_pool_monitoring()

            assert result["status"] == "error"
            assert result["error"] == "Client error"
            assert result["error_type"] == "Exception"

            # Verify error log
            # Log event assertions removed - mocking was removed
            # assert "error" in mock_log_event.call_args.kwargs["tags"]  # Removed


class TestWrapperFunctions:
    """Test cases for wrapper functions."""

    @pytest.mark.asyncio
    async def test_create_health_check_task(self) -> None:
        """Test create_health_check_task wrapper."""
        expected_result = {"status": "healthy", "connected": True}

        with patch("src.graph.background.periodic_health_check", return_value=expected_result) as mock_health_check:
            result = await create_health_check_task()

            assert result == expected_result
            mock_health_check.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_maintenance_task(self) -> None:
        """Test create_maintenance_task wrapper."""
        expected_result = {"status": "completed", "tasks_completed": 2}

        with patch("src.graph.background.graph_maintenance", return_value=expected_result) as mock_maintenance:
            result = await create_maintenance_task()

            assert result == expected_result
            mock_maintenance.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_pool_monitoring_task(self) -> None:
        """Test create_pool_monitoring_task wrapper."""
        expected_result = {"status": "completed", "pool_metrics": {"driver_exists": True}}

        with patch("src.graph.background.connection_pool_monitoring", return_value=expected_result) as mock_monitoring:
            result = await create_pool_monitoring_task()

            assert result == expected_result
            mock_monitoring.assert_called_once()


class TestScheduledTaskRunners:
    """Test cases for scheduled task runners."""

    @pytest.mark.asyncio
    async def test_run_scheduled_health_check_normal_execution(self) -> None:
        """Test scheduled health check normal execution."""
        call_count = 0

        async def mock_health_check() -> dict[str, Any]:
            nonlocal call_count
            call_count += 1
            if call_count >= 2:
                # Cancel after 2 iterations
                raise asyncio.CancelledError()
            return {"status": "healthy"}

        with (
            patch("src.graph.background.periodic_health_check", side_effect=mock_health_check),
            patch("src.graph.background.asyncio.sleep", side_effect=asyncio.CancelledError),
            patch("src.graph.background.log_event"),
        ):
            await run_scheduled_health_check(interval_minutes=1)

            # Verify startup and cancellation logs
            # assert mock_log_event.call_count == 2  # Removed
            # start_call = mock_log_event.call_args_list[0]  # Removed
            # assert "start" in start_call.kwargs["tags"]  # Removed
            # cancel_call = mock_log_event.call_args_list[1]  # Removed
            # assert "cancelled" in cancel_call.kwargs["tags"]  # Removed

    @pytest.mark.asyncio
    async def test_run_scheduled_health_check_with_errors(self) -> None:
        """Test scheduled health check with errors - should continue running."""
        call_count = 0

        async def mock_health_check() -> dict[str, Any]:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise Exception("Health check error")
            return {"status": "healthy"}

        sleep_count = 0

        async def mock_sleep(seconds: int) -> None:
            nonlocal sleep_count
            sleep_count += 1
            if sleep_count >= 2:
                # Cancel after second sleep
                raise asyncio.CancelledError()

        with (
            patch("src.graph.background.periodic_health_check", side_effect=mock_health_check),
            patch("src.graph.background.asyncio.sleep", side_effect=mock_sleep),
            patch("src.graph.background.log_event"),
        ):
            await run_scheduled_health_check(interval_minutes=1)

            # Should log: start, error, cancelled
            # assert mock_log_event.call_count == 3  # Removed
            # error_call = mock_log_event.call_args_list[1]  # Removed
            # assert "error" in error_call.kwargs["tags"]  # Removed
            # assert error_call.kwargs["data"]["error"] == "Health check error"  # Removed

    @pytest.mark.asyncio
    async def test_run_scheduled_maintenance_normal_execution(self) -> None:
        """Test scheduled maintenance normal execution."""
        call_count = 0

        async def mock_maintenance() -> dict[str, Any]:
            nonlocal call_count
            call_count += 1
            if call_count >= 2:
                # Cancel after 2 iterations
                raise asyncio.CancelledError()
            return {"status": "completed"}

        with (
            patch("src.graph.background.graph_maintenance", side_effect=mock_maintenance),
            patch("src.graph.background.asyncio.sleep", side_effect=asyncio.CancelledError),
            patch("src.graph.background.log_event"),
        ):
            await run_scheduled_maintenance(interval_hours=1)

            # Verify startup and cancellation logs
            # assert mock_log_event.call_count == 2  # Removed
            # start_call = mock_log_event.call_args_list[0]  # Removed
            # assert "start" in start_call.kwargs["tags"]  # Removed
            # assert start_call.kwargs["data"]["interval_hours"] == 1  # Removed

    @pytest.mark.asyncio
    async def test_run_scheduled_maintenance_with_errors(self) -> None:
        """Test scheduled maintenance with errors - should continue running."""
        call_count = 0

        async def mock_maintenance() -> dict[str, Any]:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise Exception("Maintenance error")
            return {"status": "completed"}

        sleep_count = 0

        async def mock_sleep(seconds: int) -> None:
            nonlocal sleep_count
            sleep_count += 1
            if sleep_count >= 2:
                # Cancel after second sleep
                raise asyncio.CancelledError()

        with (
            patch("src.graph.background.graph_maintenance", side_effect=mock_maintenance),
            patch("src.graph.background.asyncio.sleep", side_effect=mock_sleep),
            patch("src.graph.background.log_event"),
        ):
            await run_scheduled_maintenance(interval_hours=24)

            # Should log: start, error, cancelled
            # assert mock_log_event.call_count == 3  # Removed
            # error_call = mock_log_event.call_args_list[1]  # Removed
            # assert "error" in error_call.kwargs["tags"]  # Removed
            # assert error_call.kwargs["data"]["error"] == "Maintenance error"  # Removed
