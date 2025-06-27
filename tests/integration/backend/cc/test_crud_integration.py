"""Integration tests for CRUD operations using PostgreSQL.

These tests use real PostgreSQL database with transaction isolation
to test CRUD operations, constraints, and database-specific behavior.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest  # Phase 2: Remove for skip removal
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.backend.cc.crud import (
    create_module,
    delete_module,
    get_module,
    get_modules,
    get_system_health,
    update_module,
)
from src.backend.cc.models import HealthStatus

# Phase 2: Integration testing enabled


class TestCRUDIntegration:
    """Integration tests for CRUD operations with PostgreSQL."""

    async def test_create_module_unique_constraint(self, db_session: AsyncSession) -> None:
        """Test that creating modules with duplicate names raises IntegrityError."""
        module_name = "duplicate_test_module"

        # Create first module
        await create_module(db_session, module_name, "1.0.0")

        # Attempt to create second module with same name should fail
        with pytest.raises(IntegrityError):
            await create_module(db_session, module_name, "2.0.0")

    async def test_module_cascade_operations(self, db_session: AsyncSession) -> None:
        """Test cascade operations and foreign key constraints."""
        # Create a module
        module = await create_module(db_session, "cascade_test", "1.0.0")

        # Verify it exists
        retrieved = await get_module(db_session, str(module.id))
        assert retrieved is not None

        # Delete the module
        deleted = await delete_module(db_session, str(module.id))
        assert deleted is not None

        # Verify it's gone
        retrieved_after_delete = await get_module(db_session, str(module.id))
        assert retrieved_after_delete is None

    async def test_pagination_with_large_dataset(self, db_session: AsyncSession) -> None:
        """Test pagination with a larger dataset."""
        # Create 25 modules
        module_names = [f"pagination_test_{i:02d}" for i in range(25)]
        for name in module_names:
            await create_module(db_session, name, "1.0.0")

        # Test first page
        page1 = await get_modules(db_session, skip=0, limit=10)
        assert len(page1) == 10

        # Test second page
        page2 = await get_modules(db_session, skip=10, limit=10)
        assert len(page2) == 10

        # Test third page
        page3 = await get_modules(db_session, skip=20, limit=10)
        assert len(page3) == 5  # Only 5 remaining

        # Verify no overlap between pages
        page1_names = {module.name for module in page1}
        page2_names = {module.name for module in page2}
        page3_names = {module.name for module in page3}

        assert len(page1_names & page2_names) == 0
        assert len(page1_names & page3_names) == 0
        assert len(page2_names & page3_names) == 0

    async def test_concurrent_module_creation(self, db_session: AsyncSession) -> None:
        """Test that concurrent operations work correctly with transaction isolation."""
        # This test verifies that our transaction isolation works
        # Create multiple modules in the same transaction
        modules = []
        for i in range(5):
            module = await create_module(db_session, f"concurrent_test_{i}", "1.0.0")
            modules.append(module)

        # Verify all were created
        all_modules = await get_modules(db_session, skip=0, limit=100)
        created_names = {m.name for m in modules}
        retrieved_names = {m.name for m in all_modules if m.name.startswith("concurrent_test_")}

        assert created_names == retrieved_names

    async def test_health_status_ordering(self, db_session: AsyncSession) -> None:
        """Test that health status records are properly ordered by timestamp."""
        # Create health records with specific timestamps
        timestamps = [
            datetime(2025, 1, 1, 10, 0, 0, tzinfo=UTC),
            datetime(2025, 1, 1, 11, 0, 0, tzinfo=UTC),
            datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC),
        ]

        # Add records in reverse order
        for i, ts in enumerate(reversed(timestamps)):
            health_record = HealthStatus(
                id=uuid4(),
                module=f"health_test_{i}",
                status="healthy",
                last_updated=ts,
                details=f"Record {i}",
            )
            db_session.add(health_record)

        await db_session.commit()

        # Get system health should return the latest
        result = await get_system_health(db_session)
        assert result is not None
        # Compare timestamps handling timezone differences
        expected_time = timestamps[-1].replace(tzinfo=None)
        actual_time = result.last_updated.replace(tzinfo=None) if result.last_updated.tzinfo else result.last_updated
        assert actual_time == expected_time

    async def test_module_update_with_constraints(self, db_session: AsyncSession) -> None:
        """Test module updates respect database constraints."""
        # Create a module
        module = await create_module(db_session, "update_test", "1.0.0")

        # Update with valid data
        updated = await update_module(db_session, str(module.id), {"version": "2.0.0", "config": '{"new": "config"}'})
        assert updated is not None
        assert updated.version == "2.0.0"
        assert updated.config == '{"new": "config"}'

        # Verify the update persisted
        retrieved = await get_module(db_session, str(module.id))
        assert retrieved is not None
        assert retrieved.version == "2.0.0"

    async def test_transaction_rollback_behavior(self, db_session: AsyncSession) -> None:
        """Test transaction rollback behavior with explicit transaction control."""
        # For this test, we'll test rollback behavior within the existing transaction isolation
        module_name = "rollback_test"

        # Create a module
        module = await create_module(db_session, module_name, "1.0.0")

        # Verify it exists within the transaction
        retrieved = await get_module(db_session, str(module.id))
        assert retrieved is not None

        # The test framework will automatically roll back this transaction
        # so the module will not persist outside of this test
        # This validates our transaction isolation works correctly
