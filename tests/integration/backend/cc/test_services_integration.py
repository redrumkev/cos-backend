"""Integration tests for services using PostgreSQL.

These tests verify service layer functionality with real database operations.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest  # Phase 2: Remove for skip removal
from sqlalchemy.ext.asyncio import AsyncSession

from src.backend.cc.models import HealthStatus
from src.backend.cc.services import (
    create_module,
    get_module,
    get_modules,
    read_system_health,
    update_module,
)

# Phase 2: Remove this skip block for end-to-end integration testing (P2-INTEGRATION-001)
pytestmark = pytest.mark.skip(reason="Phase 2: End-to-end integration testing needed. Trigger: P2-INTEGRATION-001")


class TestServicesIntegration:
    """Integration tests for service layer with PostgreSQL."""

    async def test_create_module_service_integration(self, db_session: AsyncSession) -> None:
        """Test module creation through service layer."""
        result = await create_module(db_session, "integration_test_module", "1.0.0", '{"test": true}')

        assert result.name == "integration_test_module"
        assert result.version == "1.0.0"
        assert result.config == '{"test": true}'
        assert result.active is True

    async def test_get_modules_service_with_pagination(self, db_session: AsyncSession) -> None:
        """Test getting modules with pagination through service layer."""
        # Create test modules
        for i in range(15):
            await create_module(db_session, f"pagination_module_{i:02d}", "1.0.0")

        # Test pagination
        page1 = await get_modules(db_session, skip=0, limit=10)
        assert len(page1) == 10

        page2 = await get_modules(db_session, skip=10, limit=10)
        assert len(page2) == 5

    async def test_update_module_service_integration(self, db_session: AsyncSession) -> None:
        """Test module update through service layer."""
        # Create a module
        created_module = await create_module(db_session, "update_test_module", "1.0.0")

        # Update it
        update_data = {"version": "2.0.0", "config": '{"updated": true}'}
        updated_module = await update_module(db_session, str(created_module.id), update_data)

        assert updated_module is not None
        assert updated_module.version == "2.0.0"
        assert updated_module.config == '{"updated": true}'

    async def test_get_module_service_integration(self, db_session: AsyncSession) -> None:
        """Test getting a specific module through service layer."""
        # Create a module
        created_module = await create_module(db_session, "get_test_module", "1.0.0")

        # Retrieve it
        retrieved_module = await get_module(db_session, str(created_module.id))

        assert retrieved_module is not None
        assert retrieved_module.id == created_module.id
        assert retrieved_module.name == "get_test_module"

    async def test_system_health_service_integration(self, db_session: AsyncSession) -> None:
        """Test system health service with real database."""
        # Create health status record
        health_record = HealthStatus(
            id=uuid4(),
            module="integration_test",
            status="healthy",
            last_updated=datetime.now(UTC),
            details="Integration test health check",
        )
        db_session.add(health_record)
        await db_session.commit()

        # Get system health through service
        result = await read_system_health(db_session)

        assert result is not None
        assert result.module == "integration_test"
        assert result.status == "healthy"
        assert result.details == "Integration test health check"
