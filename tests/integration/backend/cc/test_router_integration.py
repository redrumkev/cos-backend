"""Integration tests for router endpoints using PostgreSQL.

These tests verify API endpoints with real database operations.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from src.backend.cc.models import HealthStatus

# Phase 2: Integration testing enabled


class TestRouterIntegration:
    """Integration tests for router endpoints with PostgreSQL."""

    async def test_create_module_endpoint_integration(self, db_session: AsyncSession, async_client: Any) -> None:
        """Test module creation endpoint with real database."""
        module_data = {"name": "api_test_module", "version": "1.0.0", "config": '{"api_test": true}'}

        response = await async_client.post("/cc/modules", json=module_data)

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "api_test_module"
        assert data["version"] == "1.0.0"
        assert data["config"] == '{"api_test": true}'

    async def test_get_modules_endpoint_pagination(self, db_session: AsyncSession, async_client: Any) -> None:
        """Test modules listing endpoint with pagination."""
        # Create test modules through the API
        for i in range(12):
            module_data = {"name": f"api_pagination_module_{i:02d}", "version": "1.0.0"}
            await async_client.post("/cc/modules", json=module_data)

        # Test first page
        response1 = await async_client.get("/cc/modules?skip=0&limit=10")
        assert response1.status_code == 200
        data1 = response1.json()
        assert len(data1) == 10

        # Test second page
        response2 = await async_client.get("/cc/modules?skip=10&limit=10")
        assert response2.status_code == 200
        data2 = response2.json()
        assert len(data2) == 2

    async def test_get_module_by_id_endpoint(self, db_session: AsyncSession, async_client: Any) -> None:
        """Test getting a specific module by ID through API."""
        # Create a module
        module_data = {"name": "api_get_test_module", "version": "1.0.0"}
        create_response = await async_client.post("/cc/modules", json=module_data)
        assert create_response.status_code == 201
        created_module = create_response.json()

        # Get it by ID
        get_response = await async_client.get(f"/cc/modules/{created_module['id']}")
        assert get_response.status_code == 200
        retrieved_module = get_response.json()
        assert retrieved_module["id"] == created_module["id"]
        assert retrieved_module["name"] == "api_get_test_module"

    async def test_update_module_endpoint(self, db_session: AsyncSession, async_client: Any) -> None:
        """Test module update endpoint."""
        # Create a module
        module_data = {"name": "api_update_test_module", "version": "1.0.0"}
        create_response = await async_client.post("/cc/modules", json=module_data)
        assert create_response.status_code == 201
        created_module = create_response.json()

        # Update it
        update_data = {"version": "2.0.0", "config": '{"updated_via_api": true}'}
        update_response = await async_client.patch(f"/cc/modules/{created_module['id']}", json=update_data)
        assert update_response.status_code == 200
        updated_module = update_response.json()
        assert updated_module["version"] == "2.0.0"
        assert updated_module["config"] == '{"updated_via_api": true}'

    async def test_health_endpoint_integration(self, db_session: AsyncSession, async_client: Any) -> None:
        """Test health endpoint with real database data."""
        # Create health status record directly in database
        health_record = HealthStatus(
            id=uuid4(),
            module="api_health_test",
            status="healthy",
            last_updated=datetime.now(UTC),
            details="API integration test",
        )
        db_session.add(health_record)
        await db_session.commit()

        # Test health endpoint
        response = await async_client.get("/cc/health")
        assert response.status_code == 200
        data = response.json()
        assert data["module"] == "api_health_test"
        assert data["status"] == "healthy"
        assert data["details"] == "API integration test"

    async def test_error_handling_integration(self, db_session: AsyncSession, async_client: Any) -> None:
        """Test API error handling with database constraints."""
        # Create a module
        module_data = {"name": "duplicate_test_module", "version": "1.0.0"}
        response1 = await async_client.post("/cc/modules", json=module_data)
        assert response1.status_code == 201

        # Try to create another with the same name (should fail due to unique constraint)
        response2 = await async_client.post("/cc/modules", json=module_data)
        assert response2.status_code == 409  # Conflict status code for constraint violations

    async def test_module_not_found_integration(self, db_session: AsyncSession, async_client: Any) -> None:
        """Test API response for non-existent module."""
        fake_id = str(uuid4())
        response = await async_client.get(f"/cc/modules/{fake_id}")
        assert response.status_code == 404
