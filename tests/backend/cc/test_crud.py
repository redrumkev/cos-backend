"""Tests for CRUD operations in the Control Center module.

This file contains tests for database operations, ensuring that
CRUD functions work correctly with various database states.
"""

from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from src.backend.cc.crud import get_system_health
from src.backend.cc.models import HealthStatus


class TestGetSystemHealth:
    """Test cases for the get_system_health CRUD function."""

    async def test_get_system_health_empty(self, test_db_session: AsyncSession) -> None:
        """Test get_system_health returns None when database is empty."""
        result = await get_system_health(test_db_session)
        assert result is None

    async def test_get_system_health_single_record(self, test_db_session: AsyncSession) -> None:
        """Test get_system_health returns the single record when only one exists."""
        # Create a single health status record
        health_record = HealthStatus(
            id=uuid4(),
            module="cc",
            status="healthy",
            last_updated=datetime.now(UTC),
            details="All systems operational",
        )
        test_db_session.add(health_record)
        await test_db_session.commit()

        # Test the function
        result = await get_system_health(test_db_session)

        assert result is not None
        assert result.module == "cc"
        assert result.status == "healthy"
        assert result.details == "All systems operational"

    async def test_get_system_health_returns_latest(self, test_db_session: AsyncSession) -> None:
        """Test get_system_health returns the most recent record when multiple exist."""
        # Create multiple health status records with different timestamps
        older_time = datetime(2025, 1, 1, 10, 0, 0, tzinfo=UTC)
        newer_time = datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC)

        older_record = HealthStatus(
            id=uuid4(),
            module="cc",
            status="degraded",
            last_updated=older_time,
            details="Some issues detected",
        )

        newer_record = HealthStatus(
            id=uuid4(),
            module="cc",
            status="healthy",
            last_updated=newer_time,
            details="Issues resolved",
        )

        # Add records in non-chronological order to test ordering
        test_db_session.add(newer_record)
        test_db_session.add(older_record)
        await test_db_session.commit()

        # Test the function
        result = await get_system_health(test_db_session)

        assert result is not None
        assert result.status == "healthy"
        assert result.details == "Issues resolved"
        assert result.last_updated == newer_time

    async def test_get_system_health_multiple_records_order(self, test_db_session: AsyncSession) -> None:
        """Test get_system_health correctly orders by timestamp with multiple records."""
        # Create three records with specific timestamps
        time1 = datetime(2025, 1, 1, 9, 0, 0, tzinfo=UTC)
        time2 = datetime(2025, 1, 1, 10, 0, 0, tzinfo=UTC)
        time3 = datetime(2025, 1, 1, 11, 0, 0, tzinfo=UTC)

        record1 = HealthStatus(
            id=uuid4(),
            module="cc",
            status="offline",
            last_updated=time1,
            details="System starting",
        )

        record2 = HealthStatus(
            id=uuid4(),
            module="cc",
            status="degraded",
            last_updated=time2,
            details="Partial functionality",
        )

        record3 = HealthStatus(
            id=uuid4(),
            module="cc",
            status="healthy",
            last_updated=time3,
            details="Fully operational",
        )

        # Add records in random order
        test_db_session.add(record2)
        test_db_session.add(record1)
        test_db_session.add(record3)
        await test_db_session.commit()

        # Test the function
        result = await get_system_health(test_db_session)

        # Should return the record with the latest timestamp (time3)
        assert result is not None
        assert result.status == "healthy"
        assert result.details == "Fully operational"
        assert result.last_updated == time3
