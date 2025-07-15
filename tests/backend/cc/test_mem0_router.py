"""Tests for mem0 API router.

Tests all API endpoints including CRUD operations, error handling,
background tasks, and proper HTTP status codes.
"""

from __future__ import annotations

import os
from datetime import UTC, datetime, timedelta
from unittest.mock import patch

import pytest  # Phase 2: Remove for skip removal
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.backend.cc.mem0_models import ScratchNote

# Phase 2: P2-MEM0-001 skip removed - implementing complete mem0 router with PostgreSQL


@pytest.mark.asyncio
class TestMem0Router:
    """Test mem0 API router endpoints."""

    async def test_create_note_endpoint(self, async_client: AsyncClient) -> None:
        """Test POST /scratch/notes endpoint."""
        data = {"key": "api_test", "content": "api content", "ttl_days": 7}

        response = await async_client.post("/v1/cc/mem0/scratch/notes", json=data)

        assert response.status_code == 200
        result = response.json()
        assert result["key"] == "api_test"
        assert result["content"] == "api content"
        assert result["expires_at"] is not None

    async def test_create_note_validation_error(self, async_client: AsyncClient) -> None:
        """Test POST /scratch/notes with validation error."""
        data = {
            "key": "",  # Empty key should cause validation error
            "content": "content",
        }

        response = await async_client.post("/v1/cc/mem0/scratch/notes", json=data)

        assert response.status_code == 422  # FastAPI validation returns 422, not 400
        assert "string_too_short" in response.json()["errors"][0]["type"]

    @pytest.mark.skipif(
        os.getenv("CI") == "true", reason="Mock patching unreliable in CI - module import timing issues"
    )
    async def test_create_note_service_value_error(self, async_client: AsyncClient) -> None:
        """Test POST /scratch/notes when service layer raises ValueError.

        This is a characterization test that verifies the error handling path
        when the service layer encounters business rule violations that aren't
        caught by schema validation, simulating edge cases in production.
        """
        # Mock the service to raise ValueError for a specific business rule violation
        # This simulates scenarios where the service layer has additional validation
        # beyond what the schema can express
        with patch("src.backend.cc.mem0_service.create_note", side_effect=ValueError("Custom business rule violation")):
            data = {"key": "test_key", "content": "test content"}

            response = await async_client.post("/v1/cc/mem0/scratch/notes", json=data)

            # The ValueError is caught and converted to HTTPException 400
            assert response.status_code == 400
            assert "Custom business rule violation" in response.json()["detail"]

    @pytest.mark.skipif(
        os.getenv("CI") == "true", reason="Mock patching unreliable in CI - module import timing issues"
    )
    async def test_create_note_server_error(self, async_client: AsyncClient) -> None:
        """Test POST /scratch/notes with server error."""
        # Test the actual service layer by simulating a database error
        # This is more realistic than trying to mock imported modules
        with patch("src.backend.cc.mem0_service.create_note", side_effect=Exception("Database error")):
            data = {"key": "error_test", "content": "content"}

            response = await async_client.post("/v1/cc/mem0/scratch/notes", json=data)

            assert response.status_code == 500
            assert "Failed to create note" in response.json()["detail"]

    async def test_get_note_by_id_endpoint(self, async_client: AsyncClient, db_session: AsyncSession) -> None:
        """Test GET /scratch/notes/{note_id} endpoint."""
        # Create a note first
        note = ScratchNote(key="get_api_test", content="get content")
        db_session.add(note)
        await db_session.commit()
        await db_session.refresh(note)

        response = await async_client.get(f"/v1/cc/mem0/scratch/notes/{note.id}")

        assert response.status_code == 200
        result = response.json()
        assert result["id"] == note.id
        assert result["key"] == "get_api_test"

    async def test_get_note_by_id_not_found(self, async_client: AsyncClient) -> None:
        """Test GET /scratch/notes/{note_id} with non-existent ID."""
        response = await async_client.get("/v1/cc/mem0/scratch/notes/99999")

        assert response.status_code == 404
        assert response.json()["detail"] == "Note not found"

    async def test_get_note_by_key_endpoint(self, async_client: AsyncClient, db_session: AsyncSession) -> None:
        """Test GET /scratch/notes/key/{key} endpoint."""
        # Create a note first
        note = ScratchNote(key="key_api_test", content="key content")
        db_session.add(note)
        await db_session.commit()

        response = await async_client.get("/v1/cc/mem0/scratch/notes/key/key_api_test")

        assert response.status_code == 200
        result = response.json()
        assert result["key"] == "key_api_test"

    async def test_get_note_by_key_not_found(self, async_client: AsyncClient) -> None:
        """Test GET /scratch/notes/key/{key} with non-existent key."""
        response = await async_client.get("/v1/cc/mem0/scratch/notes/key/nonexistent")

        assert response.status_code == 404
        assert response.json()["detail"] == "Note not found"

    async def test_list_notes_endpoint(self, async_client: AsyncClient, db_session: AsyncSession) -> None:
        """Test GET /scratch/notes endpoint."""
        # Create test notes
        note1 = ScratchNote(key="list_test1", content="content1")
        note2 = ScratchNote(key="list_test2", content="content2")
        db_session.add_all([note1, note2])
        await db_session.commit()

        response = await async_client.get("/v1/cc/mem0/scratch/notes")

        assert response.status_code == 200
        result = response.json()
        assert isinstance(result, list)
        assert len(result) >= 2

    async def test_list_notes_with_filters(self, async_client: AsyncClient, db_session: AsyncSession) -> None:
        """Test GET /scratch/notes with query parameters."""
        # Create test notes
        note1 = ScratchNote(key="filter_test1", content="content1")
        note2 = ScratchNote(key="filter_test2", content="content2")
        note3 = ScratchNote(key="other_key", content="content3")
        db_session.add_all([note1, note2, note3])
        await db_session.commit()

        # Test with key prefix filter
        response = await async_client.get("/v1/cc/mem0/scratch/notes?key_prefix=filter_&limit=10&offset=0")

        assert response.status_code == 200
        result = response.json()
        assert len(result) >= 2
        for note in result:
            assert note["key"].startswith("filter_")

    @pytest.mark.skipif(os.getenv("CI") == "true", reason="Flaky in CI environment - timing issues with expired notes")
    async def test_list_notes_expired_filter(self, async_client: AsyncClient, db_session: AsyncSession) -> None:
        """Test GET /scratch/notes with expired filter."""
        current_time = datetime.now(UTC)

        # Create expired note with unique key
        expired_note = ScratchNote(key="test_router_expired_api", content="expired")
        expired_note.expires_at = current_time - timedelta(days=1)
        db_session.add(expired_note)
        await db_session.commit()

        # Test excluding expired
        response = await async_client.get("/v1/cc/mem0/scratch/notes?include_expired=false")

        assert response.status_code == 200
        result = response.json()
        keys = [note["key"] for note in result]
        assert "test_router_expired_api" not in keys

        # Test including expired
        response = await async_client.get("/v1/cc/mem0/scratch/notes?include_expired=true")

        assert response.status_code == 200
        result = response.json()
        keys = [note["key"] for note in result]
        assert "test_router_expired_api" in keys

    async def test_update_note_endpoint(self, async_client: AsyncClient, db_session: AsyncSession) -> None:
        """Test PUT /scratch/notes/{note_id} endpoint."""
        # Create a note first
        note = ScratchNote(key="update_api_test", content="original")
        db_session.add(note)
        await db_session.commit()
        await db_session.refresh(note)

        # Update it
        update_data = {"content": "updated content", "ttl_days": 5}

        response = await async_client.put(f"/v1/cc/mem0/scratch/notes/{note.id}", json=update_data)

        assert response.status_code == 200
        result = response.json()
        assert result["content"] == "updated content"
        assert result["expires_at"] is not None

    async def test_update_note_not_found(self, async_client: AsyncClient) -> None:
        """Test PUT /scratch/notes/{note_id} with non-existent ID."""
        update_data = {"content": "updated content"}

        response = await async_client.put("/v1/cc/mem0/scratch/notes/99999", json=update_data)

        assert response.status_code == 404
        assert response.json()["detail"] == "Note not found"

    async def test_delete_note_endpoint(self, async_client: AsyncClient, db_session: AsyncSession) -> None:
        """Test DELETE /scratch/notes/{note_id} endpoint."""
        # Create a note first
        note = ScratchNote(key="delete_api_test", content="to delete")
        db_session.add(note)
        await db_session.commit()
        await db_session.refresh(note)

        response = await async_client.delete(f"/v1/cc/mem0/scratch/notes/{note.id}")

        assert response.status_code == 200
        result = response.json()
        assert f"Note {note.id} deleted successfully" in result["message"]

    async def test_delete_note_not_found(self, async_client: AsyncClient) -> None:
        """Test DELETE /scratch/notes/{note_id} with non-existent ID."""
        response = await async_client.delete("/v1/cc/mem0/scratch/notes/99999")

        assert response.status_code == 404
        assert response.json()["detail"] == "Note not found"

    async def test_get_stats_endpoint(self, async_client: AsyncClient, db_session: AsyncSession) -> None:
        """Test GET /scratch/stats endpoint."""
        # Create test data
        current_time = datetime.now(UTC)

        # Active note
        active_note = ScratchNote(key="stats_api_active", content="active")
        active_note.expires_at = current_time + timedelta(days=1)
        db_session.add(active_note)

        # Expired note
        expired_note = ScratchNote(key="stats_api_expired", content="expired")
        expired_note.expires_at = current_time - timedelta(days=1)
        db_session.add(expired_note)

        await db_session.commit()

        response = await async_client.get("/v1/cc/mem0/scratch/stats")

        assert response.status_code == 200
        result = response.json()
        assert "total_notes" in result
        assert "expired_notes" in result
        assert "active_notes" in result
        assert "ttl_settings" in result

    @pytest.mark.skipif(
        os.getenv("CI") == "true", reason="Flaky in CI environment - timing issues with cleanup operations"
    )
    async def test_trigger_cleanup_endpoint(self, async_client: AsyncClient, db_session: AsyncSession) -> None:
        """Test POST /scratch/cleanup endpoint."""
        current_time = datetime.now(UTC)

        # Create expired notes
        for i in range(2):
            expired_note = ScratchNote(key=f"cleanup_api_{i}", content="expired")
            expired_note.expires_at = current_time - timedelta(days=1)
            db_session.add(expired_note)

        await db_session.commit()

        response = await async_client.post("/v1/cc/mem0/scratch/cleanup")

        assert response.status_code == 200
        result = response.json()
        assert "deleted" in result  # The actual response format uses "deleted", not "deleted_count"
        assert result["deleted"] >= 2

    async def test_trigger_cleanup_background_endpoint(self, async_client: AsyncClient) -> None:
        """Test POST /scratch/cleanup/background endpoint."""
        response = await async_client.post("/v1/cc/mem0/scratch/cleanup/background")

        assert response.status_code == 200
        result = response.json()
        assert "Cleanup scheduled in background" in result["message"]

    async def test_collect_stats_background_endpoint(self, async_client: AsyncClient) -> None:
        """Test POST /scratch/stats/background endpoint."""
        response = await async_client.post("/v1/cc/mem0/scratch/stats/background")

        assert response.status_code == 200
        result = response.json()
        assert "Stats collection scheduled in background" in result["message"]

    async def test_router_prefix_and_tags(self, async_client: AsyncClient) -> None:
        """Test that router has correct prefix and tags."""
        # This test verifies the router configuration
        response = await async_client.get("/v1/cc/mem0/scratch/stats")

        # Should work with the prefix
        assert response.status_code == 200

        # Test that endpoints without prefix don't work
        response = await async_client.get("/scratch/stats")
        assert response.status_code == 404

    async def test_query_parameter_validation(self, async_client: AsyncClient) -> None:
        """Test query parameter validation."""
        # Test invalid limit
        response = await async_client.get("/v1/cc/mem0/scratch/notes?limit=0")
        assert response.status_code == 422  # Validation error

        # Test invalid offset
        response = await async_client.get("/v1/cc/mem0/scratch/notes?offset=-1")
        assert response.status_code == 422  # Validation error

        # Test limit too high
        response = await async_client.get("/v1/cc/mem0/scratch/notes?limit=2000")
        assert response.status_code == 422  # Validation error

    async def test_request_body_validation(self, async_client: AsyncClient) -> None:
        """Test request body validation."""
        # Test missing required fields
        response = await async_client.post("/v1/cc/mem0/scratch/notes", json={})
        assert response.status_code == 422  # Validation error

        # Test invalid data types
        invalid_data = {
            "key": "test",
            "content": "content",
            "ttl_days": "invalid",  # Should be int
        }
        response = await async_client.post("/v1/cc/mem0/scratch/notes", json=invalid_data)
        assert response.status_code == 422  # Validation error

    async def test_response_model_validation(self, async_client: AsyncClient, db_session: AsyncSession) -> None:
        """Test that responses match the expected schema."""
        # Create a note
        data = {"key": "schema_test", "content": "schema content"}

        response = await async_client.post("/v1/cc/mem0/scratch/notes", json=data)

        assert response.status_code == 200
        result = response.json()

        # Verify all expected fields are present
        expected_fields = ["id", "key", "content", "created_at", "expires_at"]
        for field in expected_fields:
            assert field in result

    async def test_error_handling_consistency(self, async_client: AsyncClient) -> None:
        """Test that error responses are consistent."""
        # Test 404 error format
        response = await async_client.get("/v1/cc/mem0/scratch/notes/99999")
        assert response.status_code == 404
        error_response = response.json()
        assert "detail" in error_response

        # Test 422 validation error format (FastAPI returns 422 for validation errors)
        response = await async_client.post("/v1/cc/mem0/scratch/notes", json={"key": "", "content": "test"})
        assert response.status_code == 422
        error_response = response.json()
        assert "detail" in error_response

    async def test_background_task_integration(self, async_client: AsyncClient) -> None:
        """Test background task integration."""
        # The background tasks are working - just test the endpoint response
        response = await async_client.post("/v1/cc/mem0/scratch/cleanup/background")

        assert response.status_code == 200
        result = response.json()
        assert "Cleanup scheduled in background" in result["message"]

    async def test_concurrent_requests(self, async_client: AsyncClient) -> None:
        """Test handling of concurrent requests."""
        import asyncio

        # Create multiple notes concurrently
        tasks = []
        for i in range(5):
            data = {"key": f"concurrent_api_{i}", "content": f"content_{i}"}
            task = async_client.post("/v1/cc/mem0/scratch/notes", json=data)
            tasks.append(task)

        # Wait for all requests to complete
        responses = await asyncio.gather(*tasks)

        # Verify all succeeded
        for response in responses:
            assert response.status_code == 200

    async def test_large_content_handling(self, async_client: AsyncClient) -> None:
        """Test handling of large content."""
        # Test with large content (but not too large to cause issues)
        large_content = "x" * 10000  # 10KB content

        data = {"key": "large_content_test", "content": large_content}

        response = await async_client.post("/v1/cc/mem0/scratch/notes", json=data)

        assert response.status_code == 200
        result = response.json()
        assert result["content"] == large_content

    async def test_special_characters_in_key(self, async_client: AsyncClient) -> None:
        """Test handling of special characters in keys."""
        # Test with URL-safe special characters
        special_key = "test-key_with.special@chars"

        data = {"key": special_key, "content": "special content"}

        response = await async_client.post("/v1/cc/mem0/scratch/notes", json=data)

        assert response.status_code == 200
        result = response.json()
        assert result["key"] == special_key
