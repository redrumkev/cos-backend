"""Tests for service layer operations in the Control Center module.

This file contains tests for business logic services, ensuring that
service functions work correctly with various scenarios and error conditions.
"""

from __future__ import annotations

from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.backend.cc.services import (
    create_module,
    delete_module,
    get_module,
    get_module_by_name,
    get_modules,
    update_module,
)


class TestModuleServices:
    """Test cases for Module service operations."""

    async def test_create_module_success(self, test_db_session: AsyncSession, unique_test_id: str) -> None:
        """Test creating a module successfully via service layer."""
        module_name = f"test_module_{unique_test_id}"
        module = await create_module(test_db_session, module_name, "1.0.0")

        assert module.name == module_name
        assert module.version == "1.0.0"
        assert module.active is True
        assert module.config is None

    async def test_create_module_with_config(self, test_db_session: AsyncSession, unique_test_id: str) -> None:
        """Test creating a module with configuration via service layer."""
        module_name = f"test_module_{unique_test_id}"
        config = '{"setting1": "value1"}'
        module = await create_module(test_db_session, module_name, "1.0.0", config)

        assert module.name == module_name
        assert module.version == "1.0.0"
        assert module.config == config

    async def test_create_module_duplicate_name_error(self, test_db_session: AsyncSession, unique_test_id: str) -> None:
        """Test creating a module with duplicate name raises ValueError."""
        module_name = f"test_module_{unique_test_id}"
        # Create first module
        await create_module(test_db_session, module_name, "1.0.0")

        # Try to create second module with same name
        with pytest.raises(ValueError, match=f"Module with name '{module_name}' already exists"):
            await create_module(test_db_session, module_name, "2.0.0")

    async def test_get_module_exists(self, test_db_session: AsyncSession, unique_test_id: str) -> None:
        """Test getting a module that exists."""
        # Create a module first
        module_name = f"test_module_{unique_test_id}"
        created_module = await create_module(test_db_session, module_name, "1.0.0")

        # Get it via service
        retrieved_module = await get_module(test_db_session, str(created_module.id))

        assert retrieved_module is not None
        assert retrieved_module.id == created_module.id
        assert retrieved_module.name == module_name

    async def test_get_module_not_exists(self, test_db_session: AsyncSession) -> None:
        """Test getting a module that doesn't exist."""
        fake_id = str(uuid4())
        result = await get_module(test_db_session, fake_id)
        assert result is None

    async def test_get_module_by_name_exists(self, test_db_session: AsyncSession, unique_test_id: str) -> None:
        """Test getting a module by name that exists."""
        # Create a module first
        module_name = f"test_module_{unique_test_id}"
        await create_module(test_db_session, module_name, "1.0.0")

        # Get it by name via service
        retrieved_module = await get_module_by_name(test_db_session, module_name)

        assert retrieved_module is not None
        assert retrieved_module.name == module_name

    async def test_get_module_by_name_not_exists(self, test_db_session: AsyncSession, unique_test_id: str) -> None:
        """Test getting a module by name that doesn't exist."""
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

    async def test_update_module_success(self, test_db_session: AsyncSession, unique_test_id: str) -> None:
        """Test updating a module successfully."""
        # Create a module first
        module_name = f"test_module_{unique_test_id}"
        created_module = await create_module(test_db_session, module_name, "1.0.0")

        # Update it via service
        update_data = {"version": "1.1.0", "active": False}
        updated_module = await update_module(test_db_session, str(created_module.id), update_data)

        assert updated_module is not None
        assert updated_module.version == "1.1.0"
        assert updated_module.active is False
        assert updated_module.name == module_name  # Unchanged

    async def test_update_module_not_exists(self, test_db_session: AsyncSession) -> None:
        """Test updating a module that doesn't exist."""
        fake_id = str(uuid4())
        update_data = {"version": "1.1.0"}
        result = await update_module(test_db_session, fake_id, update_data)
        assert result is None

    async def test_update_module_name_conflict(self, test_db_session: AsyncSession, unique_test_id: str) -> None:
        """Test updating a module name to one that already exists."""
        # Create two modules
        module1_name = f"module_1_{unique_test_id}"
        module2_name = f"module_2_{unique_test_id}"
        module1 = await create_module(test_db_session, module1_name, "1.0.0")
        await create_module(test_db_session, module2_name, "1.0.0")

        # Try to update module1's name to module2's name
        with pytest.raises(ValueError, match=f"Module with name '{module2_name}' already exists"):
            await update_module(test_db_session, str(module1.id), {"name": module2_name})

    async def test_update_module_same_name(self, test_db_session: AsyncSession, unique_test_id: str) -> None:
        """Test updating a module to the same name (should work)."""
        # Create a module
        module_name = f"test_module_{unique_test_id}"
        created_module = await create_module(test_db_session, module_name, "1.0.0")

        # Update with same name but different version
        update_data = {"name": module_name, "version": "1.1.0"}
        updated_module = await update_module(test_db_session, str(created_module.id), update_data)

        assert updated_module is not None
        assert updated_module.name == module_name
        assert updated_module.version == "1.1.0"

    async def test_delete_module_success(self, test_db_session: AsyncSession, unique_test_id: str) -> None:
        """Test deleting a module successfully."""
        # Create a module first
        module_name = f"test_module_{unique_test_id}"
        created_module = await create_module(test_db_session, module_name, "1.0.0")

        # Delete it via service
        deleted_module = await delete_module(test_db_session, str(created_module.id))

        assert deleted_module is not None
        assert deleted_module.id == created_module.id

        # Verify it's actually deleted
        retrieved_module = await get_module(test_db_session, str(created_module.id))
        assert retrieved_module is None

    async def test_delete_module_not_exists(self, test_db_session: AsyncSession) -> None:
        """Test deleting a module that doesn't exist."""
        fake_id = str(uuid4())
        result = await delete_module(test_db_session, fake_id)
        assert result is None
