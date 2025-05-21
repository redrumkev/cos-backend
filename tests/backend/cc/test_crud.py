"""Tests for the Control Center CRUD operations.

This file contains unit tests for the database operations in the CC module.
"""

# MDC: cc_module
from typing import Any
from unittest.mock import AsyncMock

import pytest

from src.backend.cc.crud import (
    get_active_modules,
    get_system_health,
    update_module_status,
)


@pytest.mark.asyncio
async def test_get_system_health() -> Any:
    """Test the get_system_health CRUD function."""
    # Mock the database session
    mock_db = AsyncMock()

    # Call the function
    result = await get_system_health(mock_db)

    # Verify the result structure
    assert isinstance(result, list)
    assert len(result) > 0
    assert "module" in result[0]
    assert "status" in result[0]
    assert "last_updated" in result[0]

    # Verify at least one module is included
    modules = [item["module"] for item in result]
    assert "cc" in modules


@pytest.mark.asyncio
async def test_update_module_status() -> Any:
    """Test the update_module_status CRUD function."""
    # Mock the database session
    mock_db = AsyncMock()

    # Call the function
    module_name = "cc"
    new_status = "degraded"
    result = await update_module_status(mock_db, module_name, new_status)

    # Verify the result structure
    assert isinstance(result, dict)
    assert "module" in result
    assert "status" in result
    assert "last_updated" in result

    # Verify the status was updated
    assert result["module"] == module_name
    assert result["status"] == new_status


@pytest.mark.asyncio
async def test_get_active_modules() -> Any:
    """Test the get_active_modules CRUD function."""
    # Mock the database session
    mock_db = AsyncMock()

    # Call the function
    result = await get_active_modules(mock_db)

    # Verify the result structure
    assert isinstance(result, list)
    assert len(result) > 0

    # Verify cc module is included
    assert "cc" in result
