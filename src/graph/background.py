"""Background task implementations for graph layer.

Provides health monitoring and maintenance tasks for Neo4j connections,
following the background task patterns established in the cc module.
"""

import asyncio
from datetime import UTC, datetime
from typing import Any

from src.common.logger import log_event
from src.graph.base import get_neo4j_client


async def periodic_health_check() -> dict[str, Any]:
    """Run periodic health check on Neo4j connection."""
    start_time = datetime.now(UTC)

    try:
        client = get_neo4j_client()

        # Only perform health check if graph integration is enabled
        from src.common.config import get_settings

        settings = get_settings()

        if not settings.ENABLE_GRAPH_INTEGRATION:
            return {
                "status": "skipped",
                "reason": "graph_integration_disabled",
                "started_at": start_time.isoformat(),
                "completed_at": datetime.now(UTC).isoformat(),
                "duration_seconds": (datetime.now(UTC) - start_time).total_seconds(),
            }

        # Attempt to verify connectivity
        is_connected = await client.verify_connectivity()

        # Get basic graph statistics if connected
        stats = {}
        if is_connected:
            try:
                total_nodes_result = await client.execute_query("MATCH (n) RETURN count(n) as count")
                total_rels_result = await client.execute_query("MATCH ()-[r]->() RETURN count(r) as count")

                stats = {
                    "total_nodes": total_nodes_result[0]["count"] if total_nodes_result else 0,
                    "total_relationships": total_rels_result[0]["count"] if total_rels_result else 0,
                }
            except Exception as e:
                log_event(
                    source="graph_background",
                    data={"error": str(e)},
                    tags=["health_check", "stats_error"],
                    memo="Failed to collect graph statistics during health check",
                )
                stats = {"stats_error": str(e)}

        end_time = datetime.now(UTC)
        result = {
            "status": "healthy" if is_connected else "unhealthy",
            "connected": is_connected,
            "duration_seconds": (end_time - start_time).total_seconds(),
            "started_at": start_time.isoformat(),
            "completed_at": end_time.isoformat(),
            "driver_connected": client.is_connected,
            **stats,
        }

        log_event(
            source="graph_background",
            data=result,
            tags=["background", "health_check", "success" if is_connected else "warning"],
            memo=f"Graph health check completed: {'healthy' if is_connected else 'unhealthy'}",
        )

        return result

    except Exception as e:
        error_result = {
            "status": "error",
            "connected": False,
            "error": str(e),
            "error_type": type(e).__name__,
            "started_at": start_time.isoformat(),
            "failed_at": datetime.now(UTC).isoformat(),
            "duration_seconds": (datetime.now(UTC) - start_time).total_seconds(),
        }

        log_event(
            source="graph_background",
            data=error_result,
            tags=["background", "health_check", "error"],
            memo=f"Graph health check failed: {e!s}",
        )

        return error_result


async def graph_maintenance() -> dict[str, Any]:
    """Run graph maintenance tasks (cleanup, optimization, etc.)."""
    start_time = datetime.now(UTC)

    try:
        client = get_neo4j_client()

        # Only perform maintenance if graph integration is enabled
        from src.common.config import get_settings

        settings = get_settings()

        if not settings.ENABLE_GRAPH_INTEGRATION:
            return {
                "status": "skipped",
                "reason": "graph_integration_disabled",
                "started_at": start_time.isoformat(),
                "completed_at": datetime.now(UTC).isoformat(),
                "duration_seconds": (datetime.now(UTC) - start_time).total_seconds(),
            }

        if not client.is_connected:
            await client.connect()

        maintenance_tasks: list[dict[str, Any]] = []

        # Task 1: Remove orphaned nodes (nodes with no relationships)
        try:
            orphan_query = """
            MATCH (n)
            WHERE NOT (n)-[]-()
            AND NOT n:Module  // Keep Module nodes even if orphaned
            DELETE n
            RETURN count(n) as deleted_count
            """
            orphan_result = await client.execute_query(orphan_query)
            orphaned_deleted = orphan_result[0]["deleted_count"] if orphan_result else 0
            maintenance_tasks.append(
                {
                    "task": "orphan_cleanup",
                    "status": "completed",
                    "deleted_count": orphaned_deleted,
                }
            )
        except Exception as e:
            maintenance_tasks.append(
                {
                    "task": "orphan_cleanup",
                    "status": "failed",
                    "error": str(e),
                }
            )

        # Task 2: Collect detailed statistics for monitoring
        try:
            stats_queries = {
                "node_counts_by_type": """
                MATCH (n)
                RETURN labels(n) as labels, count(n) as count
                ORDER BY count DESC
                """,
                "relationship_counts_by_type": """
                MATCH ()-[r]->()
                RETURN type(r) as type, count(r) as count
                ORDER BY count DESC
                """,
                "module_distribution": """
                MATCH (n)
                WHERE size(labels(n)) > 1
                UNWIND labels(n) as label
                WITH label, count(n) as count
                WHERE label STARTS WITH 'tech_' OR label STARTS WITH 'content_' OR label STARTS WITH 'analytics_'
                RETURN label as module, count
                ORDER BY count DESC
                """,
            }

            stats_results: dict[str, Any] = {}
            for stat_name, query in stats_queries.items():
                try:
                    query_result = await client.execute_query(query)
                    stats_results[stat_name] = query_result
                except Exception as e:
                    stats_results[stat_name] = {"error": str(e)}

            maintenance_tasks.append(
                {
                    "task": "statistics_collection",
                    "status": "completed",
                    "results": stats_results,
                }
            )

        except Exception as e:
            maintenance_tasks.append(
                {
                    "task": "statistics_collection",
                    "status": "failed",
                    "error": str(e),
                }
            )

        end_time = datetime.now(UTC)
        result: dict[str, Any] = {
            "status": "completed",
            "tasks_completed": len([t for t in maintenance_tasks if t["status"] == "completed"]),
            "tasks_failed": len([t for t in maintenance_tasks if t["status"] == "failed"]),
            "duration_seconds": (end_time - start_time).total_seconds(),
            "started_at": start_time.isoformat(),
            "completed_at": end_time.isoformat(),
        }

        log_event(
            source="graph_background",
            data={
                "status": result["status"],
                "tasks_completed": result["tasks_completed"],
                "tasks_failed": result["tasks_failed"],
                "duration_seconds": result["duration_seconds"],
            },
            tags=["background", "maintenance", "success"],
            memo="Graph maintenance tasks completed",
        )

        return result

    except Exception as e:
        error_result = {
            "status": "error",
            "error": str(e),
            "error_type": type(e).__name__,
            "started_at": start_time.isoformat(),
            "failed_at": datetime.now(UTC).isoformat(),
            "duration_seconds": (datetime.now(UTC) - start_time).total_seconds(),
        }

        log_event(
            source="graph_background",
            data=error_result,
            tags=["background", "maintenance", "error"],
            memo=f"Graph maintenance failed: {e!s}",
        )

        return error_result


async def connection_pool_monitoring() -> dict[str, Any]:
    """Monitor Neo4j connection pool health and metrics."""
    start_time = datetime.now(UTC)

    try:
        client = get_neo4j_client()

        # Only monitor if graph integration is enabled
        from src.common.config import get_settings

        settings = get_settings()

        if not settings.ENABLE_GRAPH_INTEGRATION:
            return {
                "status": "skipped",
                "reason": "graph_integration_disabled",
                "started_at": start_time.isoformat(),
                "completed_at": datetime.now(UTC).isoformat(),
                "duration_seconds": (datetime.now(UTC) - start_time).total_seconds(),
            }

        # Basic connection status
        pool_metrics: dict[str, Any] = {
            "driver_exists": client.driver is not None,
            "client_connected": client.is_connected,
        }

        # Try to get more detailed metrics if driver supports it
        if client.driver:
            try:
                # Attempt a simple query to test pool
                test_result = await client.execute_query("RETURN 1 as test")
                pool_metrics["pool_responsive"] = test_result is not None and len(test_result) > 0
                pool_metrics["test_query_success"] = True
            except Exception as e:
                pool_metrics["pool_responsive"] = False
                pool_metrics["test_query_success"] = False
                pool_metrics["test_query_error"] = str(e)

        end_time = datetime.now(UTC)
        result = {
            "status": "completed",
            "pool_metrics": pool_metrics,
            "duration_seconds": (end_time - start_time).total_seconds(),
            "started_at": start_time.isoformat(),
            "completed_at": end_time.isoformat(),
        }

        log_event(
            source="graph_background",
            data=result,
            tags=["background", "pool_monitoring", "success"],
            memo="Connection pool monitoring completed",
        )

        return result

    except Exception as e:
        error_result = {
            "status": "error",
            "error": str(e),
            "error_type": type(e).__name__,
            "started_at": start_time.isoformat(),
            "failed_at": datetime.now(UTC).isoformat(),
            "duration_seconds": (datetime.now(UTC) - start_time).total_seconds(),
        }

        log_event(
            source="graph_background",
            data=error_result,
            tags=["background", "pool_monitoring", "error"],
            memo=f"Connection pool monitoring failed: {e!s}",
        )

        return error_result


# FastAPI background task helpers
def create_health_check_task() -> asyncio.Task[dict[str, Any]]:
    """Create background task for Neo4j health check."""
    return asyncio.create_task(periodic_health_check())


def create_maintenance_task() -> asyncio.Task[dict[str, Any]]:
    """Create background task for graph maintenance."""
    return asyncio.create_task(graph_maintenance())


def create_pool_monitoring_task() -> asyncio.Task[dict[str, Any]]:
    """Create background task for connection pool monitoring."""
    return asyncio.create_task(connection_pool_monitoring())


# Scheduled task runner (for future cron-like functionality)
async def run_scheduled_health_check(interval_minutes: int = 15) -> None:
    """Run health check task on a schedule - for future scheduler integration."""
    log_event(
        source="graph_background",
        data={"interval_minutes": interval_minutes},
        tags=["background", "scheduler", "start"],
        memo=f"Starting scheduled graph health check with {interval_minutes} minute interval",
    )

    while True:
        try:
            await periodic_health_check()
            await asyncio.sleep(interval_minutes * 60)  # Convert to seconds
        except asyncio.CancelledError:
            log_event(
                source="graph_background",
                data={},
                tags=["background", "scheduler", "cancelled"],
                memo="Scheduled graph health check cancelled",
            )
            break
        except Exception as e:
            log_event(
                source="graph_background",
                data={"error": str(e)},
                tags=["background", "scheduler", "error"],
                memo=f"Error in scheduled graph health check: {e!s}",
            )
            # Continue running even after errors
            await asyncio.sleep(interval_minutes * 60)


async def run_scheduled_maintenance(interval_hours: int = 24) -> None:
    """Run maintenance task on a schedule - for future scheduler integration."""
    log_event(
        source="graph_background",
        data={"interval_hours": interval_hours},
        tags=["background", "scheduler", "start"],
        memo=f"Starting scheduled graph maintenance with {interval_hours} hour interval",
    )

    while True:
        try:
            await graph_maintenance()
            await asyncio.sleep(interval_hours * 3600)  # Convert to seconds
        except asyncio.CancelledError:
            log_event(
                source="graph_background",
                data={},
                tags=["background", "scheduler", "cancelled"],
                memo="Scheduled graph maintenance cancelled",
            )
            break
        except Exception as e:
            log_event(
                source="graph_background",
                data={"error": str(e)},
                tags=["background", "scheduler", "error"],
                memo=f"Error in scheduled graph maintenance: {e!s}",
            )
            # Continue running even after errors
            await asyncio.sleep(interval_hours * 3600)
