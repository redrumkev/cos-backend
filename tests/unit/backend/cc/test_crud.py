"""Tests for CRUD operations in the Control Center module.

This file contains tests for database operations, ensuring that
CRUD functions work correctly with various database states.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from src.backend.cc.crud import (
    create_module,
    delete_module,
    get_module,
    get_module_by_name,
    get_modules,
    get_system_health,
    update_module,
)
from src.backend.cc.models import HealthStatus


class TestGetSystemHealth:
    """Test cases for the get_system_health CRUD function."""

    async def test_get_system_health_empty(self, test_db_session: AsyncSession) -> None:
        """Test get_system_health returns None when database is empty."""
        result = await get_system_health(test_db_session)
        assert result is None

    async def test_get_system_health_single_record(self, test_db_session: AsyncSession, unique_test_id: str) -> None:
        """Test get_system_health returns the single record when only one exists."""
        # Create a single health status record
        health_record = HealthStatus(
            id=uuid4(),
            module=f"cc_{unique_test_id}",
            status="healthy",
            last_updated=datetime.now(UTC),
            details="All systems operational",
        )
        test_db_session.add(health_record)
        await test_db_session.commit()

        # Test the function
        result = await get_system_health(test_db_session)

        assert result is not None
        assert result.module == f"cc_{unique_test_id}"
        assert result.status == "healthy"
        assert result.details == "All systems operational"

    async def test_get_system_health_returns_latest(self, test_db_session: AsyncSession, unique_test_id: str) -> None:
        """Test get_system_health returns the most recent record when multiple exist."""
        # Create multiple health status records with different timestamps
        older_time = datetime(2025, 1, 1, 10, 0, 0, tzinfo=UTC)
        newer_time = datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC)

        older_record = HealthStatus(
            id=uuid4(),
            module=f"cc_old_{unique_test_id}",
            status="degraded",
            last_updated=older_time,
            details="Some issues detected",
        )

        newer_record = HealthStatus(
            id=uuid4(),
            module=f"cc_new_{unique_test_id}",
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
        assert result.last_updated == newer_time.replace(tzinfo=None)

    async def test_get_system_health_multiple_records_order(
        self, test_db_session: AsyncSession, unique_test_id: str
    ) -> None:
        """Test get_system_health correctly orders by timestamp with multiple records."""
        # Create three records with specific timestamps
        time1 = datetime(2025, 1, 1, 9, 0, 0, tzinfo=UTC)
        time2 = datetime(2025, 1, 1, 10, 0, 0, tzinfo=UTC)
        time3 = datetime(2025, 1, 1, 11, 0, 0, tzinfo=UTC)

        record1 = HealthStatus(
            id=uuid4(),
            module=f"cc_1_{unique_test_id}",
            status="offline",
            last_updated=time1,
            details="System starting",
        )

        record2 = HealthStatus(
            id=uuid4(),
            module=f"cc_2_{unique_test_id}",
            status="degraded",
            last_updated=time2,
            details="Partial functionality",
        )

        record3 = HealthStatus(
            id=uuid4(),
            module=f"cc_3_{unique_test_id}",
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
        assert result.last_updated == time3.replace(tzinfo=None)


class TestModuleCRUD:
    """Test cases for Module CRUD operations."""

    async def test_create_module_success(self, test_db_session: AsyncSession, unique_test_id: str) -> None:
        """Test creating a module successfully."""
        module_name = f"test_module_{unique_test_id}"
        module = await create_module(test_db_session, module_name, "1.0.0")

        assert module.name == module_name
        assert module.version == "1.0.0"
        assert module.active is True
        assert module.config is None
        assert module.id is not None

    async def test_create_module_with_config(self, test_db_session: AsyncSession, unique_test_id: str) -> None:
        """Test creating a module with configuration."""
        module_name = f"test_module_{unique_test_id}"
        config = '{"setting1": "value1"}'
        module = await create_module(test_db_session, module_name, "1.0.0", config)

        assert module.name == module_name
        assert module.version == "1.0.0"
        assert module.config == config

    async def test_get_module_by_id_exists(self, test_db_session: AsyncSession, unique_test_id: str) -> None:
        """Test getting a module by ID when it exists."""
        # Create a module first
        module_name = f"test_module_{unique_test_id}"
        created_module = await create_module(test_db_session, module_name, "1.0.0")

        # Get it by ID
        retrieved_module = await get_module(test_db_session, str(created_module.id))

        assert retrieved_module is not None
        assert retrieved_module.id == created_module.id
        assert retrieved_module.name == module_name

    async def test_get_module_by_id_not_exists(self, test_db_session: AsyncSession) -> None:
        """Test getting a module by ID when it doesn't exist."""
        fake_id = str(uuid4())
        result = await get_module(test_db_session, fake_id)
        assert result is None

    async def test_get_module_by_name_exists(self, test_db_session: AsyncSession, unique_test_id: str) -> None:
        """Test getting a module by name when it exists."""
        # Create a module first
        module_name = f"test_module_{unique_test_id}"
        await create_module(test_db_session, module_name, "1.0.0")

        # Get it by name
        retrieved_module = await get_module_by_name(test_db_session, module_name)

        assert retrieved_module is not None
        assert retrieved_module.name == module_name

    async def test_get_module_by_name_not_exists(self, test_db_session: AsyncSession, unique_test_id: str) -> None:
        """Test getting a module by name when it doesn't exist."""
        nonexistent_name = f"nonexistent_module_{unique_test_id}"
        result = await get_module_by_name(test_db_session, nonexistent_name)
        assert result is None

    async def test_get_modules_empty(self, test_db_session: AsyncSession) -> None:
        """Test getting modules when database is empty."""
        modules = await get_modules(test_db_session)
        assert modules == []

    async def test_get_modules_with_data(self, test_db_session: AsyncSession, unique_test_id: str) -> None:
        """Test getting modules with data."""
        # Create multiple modules
        await create_module(test_db_session, f"module_a_{unique_test_id}", "1.0.0")
        await create_module(test_db_session, f"module_b_{unique_test_id}", "2.0.0")
        await create_module(test_db_session, f"module_c_{unique_test_id}", "1.5.0")

        modules = await get_modules(test_db_session)

        assert len(modules) == 3
        # Should be ordered by name
        module_names = [module.name for module in modules]
        expected_names = [f"module_a_{unique_test_id}", f"module_b_{unique_test_id}", f"module_c_{unique_test_id}"]
        assert module_names == expected_names

    async def test_get_modules_pagination(self, test_db_session: AsyncSession, unique_test_id: str) -> None:
        """Test getting modules with pagination."""
        # Create multiple modules
        for i in range(5):
            await create_module(test_db_session, f"module_{i:02d}_{unique_test_id}", "1.0.0")

        # Test first page
        modules_page1 = await get_modules(test_db_session, skip=0, limit=2)
        assert len(modules_page1) == 2
        assert modules_page1[0].name == f"module_00_{unique_test_id}"
        assert modules_page1[1].name == f"module_01_{unique_test_id}"

        # Test second page
        modules_page2 = await get_modules(test_db_session, skip=2, limit=2)
        assert len(modules_page2) == 2
        assert modules_page2[0].name == f"module_02_{unique_test_id}"
        assert modules_page2[1].name == f"module_03_{unique_test_id}"

        # Test last page
        modules_page3 = await get_modules(test_db_session, skip=4, limit=2)
        assert len(modules_page3) == 1
        assert modules_page3[0].name == f"module_04_{unique_test_id}"

    async def test_update_module_success(self, test_db_session: AsyncSession, unique_test_id: str) -> None:
        """Test updating a module successfully."""
        # Create a module first
        module_name = f"test_module_{unique_test_id}"
        created_module = await create_module(test_db_session, module_name, "1.0.0")

        # Update it
        update_data = {"version": "2.0.0", "active": False, "config": '{"new": "config"}'}
        updated_module = await update_module(test_db_session, str(created_module.id), update_data)

        assert updated_module is not None
        assert updated_module.version == "2.0.0"
        assert updated_module.active is False
        assert updated_module.config == '{"new": "config"}'
        assert updated_module.name == module_name  # Should remain unchanged

    async def test_update_module_not_exists(self, test_db_session: AsyncSession) -> None:
        """Test updating a module that doesn't exist."""
        fake_id = str(uuid4())
        update_data = {"version": "2.0.0"}
        result = await update_module(test_db_session, fake_id, update_data)
        assert result is None

    async def test_update_module_ignore_invalid_fields(
        self, test_db_session: AsyncSession, unique_test_id: str
    ) -> None:
        """Test updating a module ignores invalid fields."""
        # Create a module first
        module_name = f"test_module_{unique_test_id}"
        created_module = await create_module(test_db_session, module_name, "1.0.0")

        # Update with some invalid fields
        update_data = {"version": "2.0.0", "invalid_field": "should_be_ignored", "another_invalid": 123}
        updated_module = await update_module(test_db_session, str(created_module.id), update_data)

        assert updated_module is not None
        assert updated_module.version == "2.0.0"
        assert updated_module.name == module_name
        # Invalid fields should be ignored, not cause errors

    async def test_delete_module_success(self, test_db_session: AsyncSession, unique_test_id: str) -> None:
        """Test deleting a module successfully."""
        # Create a module first
        module_name = f"test_module_{unique_test_id}"
        created_module = await create_module(test_db_session, module_name, "1.0.0")

        # Delete it
        deleted_module = await delete_module(test_db_session, str(created_module.id))

        assert deleted_module is not None
        assert deleted_module.id == created_module.id

        # Verify it's actually deleted
        result = await get_module(test_db_session, str(created_module.id))
        assert result is None

    async def test_delete_module_not_exists(self, test_db_session: AsyncSession) -> None:
        """Test deleting a module that doesn't exist."""
        fake_id = str(uuid4())
        result = await delete_module(test_db_session, fake_id)
        assert result is None
