"""Tests for mem0 service layer.

Tests business logic, validation, configuration integration,
and error handling in the service layer.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import patch

import pytest  # Phase 2: Remove for skip removal
from sqlalchemy.ext.asyncio import AsyncSession

from src.backend.cc import mem0_service
from src.backend.cc.mem0_models import ScratchNote

# Phase 2: Remove this skip block for Mem0 module implementation (P2-MEM0-001)
pytestmark = pytest.mark.skip(reason="Phase 2: Mem0 module implementation needed. Trigger: P2-MEM0-001")


@pytest.mark.asyncio
class TestMem0Service:
    """Test mem0 service layer functionality."""

    async def test_create_note_basic(self, db_session: AsyncSession) -> None:
        """Test basic note creation through service."""
        note = await mem0_service.create_note(db_session, key="service_test", content="service content")

        assert note.key == "service_test"
        assert note.content == "service content"
        assert note.expires_at is None

    async def test_create_note_with_ttl(self, db_session: AsyncSession) -> None:
        """Test note creation with TTL through service."""
        ttl_days = 3
        note = await mem0_service.create_note(db_session, key="ttl_service", content="ttl content", ttl_days=ttl_days)

        assert note.expires_at is not None
        expected_expiry = datetime.now(UTC) + timedelta(days=ttl_days)
        # Handle timezone comparison
        if note.expires_at.tzinfo is None:
            expected_expiry = expected_expiry.replace(tzinfo=None)
        time_diff = abs((note.expires_at - expected_expiry).total_seconds())
        assert time_diff < 2

    async def test_create_note_key_validation(self, db_session: AsyncSession) -> None:
        """Test key validation in service layer."""
        # Test key too long (255 is the limit based on the model)
        long_key = "x" * 256
        with pytest.raises(ValueError, match="Key cannot exceed 255 characters"):
            await mem0_service.create_note(db_session, key=long_key, content="content")

    async def test_create_note_default_ttl(self, db_session: AsyncSession) -> None:
        """Test that service uses default TTL from configuration."""
        with patch("src.backend.cc.mem0_service.get_settings") as mock_settings:
            mock_settings.return_value.SCRATCH_DEFAULT_TTL_DAYS = 10

            # When use_default_ttl is True, it should use the default from config
            note = await mem0_service.create_note(
                db_session, key="default_ttl", content="content", ttl_days=None, use_default_ttl=True
            )

            assert note.expires_at is not None
            expected_expiry = datetime.now(UTC) + timedelta(days=10)
            # Handle timezone comparison
            if note.expires_at.tzinfo is None:
                expected_expiry = expected_expiry.replace(tzinfo=None)
            time_diff = abs((note.expires_at - expected_expiry).total_seconds())
            assert time_diff < 2

    async def test_get_note(self, db_session: AsyncSession) -> None:
        """Test getting note through service."""
        # Create note first
        created_note = await mem0_service.create_note(db_session, key="get_service", content="get content")

        # Get it back
        retrieved_note = await mem0_service.get_note(db_session, created_note.id)

        assert retrieved_note is not None
        assert retrieved_note.id == created_note.id
        assert retrieved_note.key == "get_service"

    async def test_get_note_by_key(self, db_session: AsyncSession) -> None:
        """Test getting note by key through service."""
        # Create note first
        await mem0_service.create_note(db_session, key="key_service", content="key content")

        # Get it back by key
        retrieved_note = await mem0_service.get_note_by_key(db_session, "key_service")

        assert retrieved_note is not None
        assert retrieved_note.key == "key_service"

    async def test_update_note(self, db_session: AsyncSession) -> None:
        """Test updating note through service."""
        # Create note first
        note = await mem0_service.create_note(db_session, key="update_service", content="original")

        # Update it
        updated_note = await mem0_service.update_note(db_session, note.id, content="updated", ttl_days=5)

        assert updated_note is not None
        assert updated_note.content == "updated"
        assert updated_note.expires_at is not None

    async def test_delete_note(self, db_session: AsyncSession) -> None:
        """Test deleting note through service."""
        # Create note first
        note = await mem0_service.create_note(db_session, key="delete_service", content="to delete")

        # Delete it
        deleted = await mem0_service.delete_note(db_session, note.id)
        assert deleted is True

        # Verify it's gone
        retrieved = await mem0_service.get_note(db_session, note.id)
        assert retrieved is None

    async def test_list_notes_validation(self, db_session: AsyncSession) -> None:
        """Test validation in list_notes service function."""
        # Test limits - service automatically caps these, doesn't raise errors
        # Test with large limit (should be capped to 1000)
        notes = await mem0_service.list_notes(db_session, limit=2000)
        assert isinstance(notes, list)  # Should work, just capped

        # Test with negative offset (should be set to 0)
        notes = await mem0_service.list_notes(db_session, offset=-1)
        assert isinstance(notes, list)  # Should work, offset set to 0

    async def test_list_notes_with_filters(self, db_session: AsyncSession) -> None:
        """Test listing notes with various filters."""
        # Create test data
        await mem0_service.create_note(db_session, key="filter_test1", content="content1")
        await mem0_service.create_note(db_session, key="filter_test2", content="content2")
        await mem0_service.create_note(db_session, key="other_key", content="content3")

        # Test prefix filter
        notes = await mem0_service.list_notes(db_session, key_prefix="filter_")
        assert len(notes) >= 2
        for note in notes:
            assert note.key.startswith("filter_")

    async def test_run_cleanup(self, db_session: AsyncSession) -> None:
        """Test cleanup operation through service."""
        current_time = datetime.now(UTC)

        # Create expired notes
        for i in range(3):
            expired_note = ScratchNote(key=f"cleanup_service_{i}", content="expired")
            expired_note.expires_at = current_time - timedelta(days=1)
            db_session.add(expired_note)

        await db_session.commit()

        # Run cleanup
        result = await mem0_service.run_cleanup(db_session)

        assert "deleted" in result
        assert result["deleted"] >= 3
        assert "timestamp" in result

    async def test_run_cleanup_with_config(self, db_session: AsyncSession) -> None:
        """Test cleanup uses configuration settings."""
        with patch("src.backend.cc.mem0_service.get_settings") as mock_settings:
            mock_settings.return_value.SCRATCH_CLEANUP_BATCH_SIZE = 5
            mock_settings.return_value.SCRATCH_ENABLE_AUTO_CLEANUP = True

            current_time = datetime.now(UTC)

            # Create expired notes
            for i in range(3):
                expired_note = ScratchNote(key=f"config_cleanup_{i}", content="expired")
                expired_note.expires_at = current_time - timedelta(days=1)
                db_session.add(expired_note)

            await db_session.commit()

            # Run cleanup
            result = await mem0_service.run_cleanup(db_session)

            assert result["deleted"] >= 3

    async def test_get_stats(self, db_session: AsyncSession) -> None:
        """Test statistics collection through service."""
        # Create test data
        current_time = datetime.now(UTC)

        # Active note
        active_note = ScratchNote(key="stats_active", content="active")
        active_note.expires_at = current_time + timedelta(days=1)
        db_session.add(active_note)

        # Expired note
        expired_note = ScratchNote(key="stats_expired", content="expired")
        expired_note.expires_at = current_time - timedelta(days=1)
        db_session.add(expired_note)

        # Permanent note
        permanent_note = ScratchNote(key="stats_permanent", content="permanent")
        db_session.add(permanent_note)

        await db_session.commit()

        # Get stats
        stats = await mem0_service.get_stats(db_session)

        assert "total_notes" in stats
        assert "expired_notes" in stats
        assert "active_notes" in stats
        assert "ttl_settings" in stats
        assert stats["total_notes"] >= 3
        assert stats["expired_notes"] >= 1
        assert stats["active_notes"] >= 2  # Active note + permanent note

    async def test_get_stats_ttl_settings(self, db_session: AsyncSession) -> None:
        """Test that stats include TTL configuration."""
        with patch("src.backend.cc.mem0_service.get_settings") as mock_settings:
            mock_settings.return_value.SCRATCH_DEFAULT_TTL_DAYS = 7
            mock_settings.return_value.SCRATCH_CLEANUP_BATCH_SIZE = 1000
            mock_settings.return_value.SCRATCH_ENABLE_AUTO_CLEANUP = True

            stats = await mem0_service.get_stats(db_session)

            ttl_settings = stats["ttl_settings"]
            assert ttl_settings["default_ttl_days"] == 7
            assert ttl_settings["cleanup_batch_size"] == 1000
            assert ttl_settings["auto_cleanup_enabled"] is True

    async def test_logging_integration(self, db_session: AsyncSession) -> None:
        """Test that service operations are properly logged."""
        with patch("src.backend.cc.mem0_service.log_event") as mock_log:
            # Create a note
            await mem0_service.create_note(db_session, key="log_test", content="log content")

            # Verify logging was called
            mock_log.assert_called()
            call_args = mock_log.call_args
            assert call_args[1]["source"] == "cc_scratch"
            assert "create" in call_args[1]["tags"]

    async def test_error_handling_crud_failure(self, db_session: AsyncSession) -> None:
        """Test error handling when CRUD operations fail."""
        with (
            patch("src.backend.cc.mem0_crud.create_scratch_note", side_effect=Exception("CRUD error")),
            pytest.raises(Exception, match="CRUD error"),
        ):
            await mem0_service.create_note(db_session, key="error_test", content="test")

    async def test_performance_timing(self, db_session: AsyncSession) -> None:
        """Test that service operations include timing information."""
        # Test cleanup timing
        result = await mem0_service.run_cleanup(db_session)
        assert "execution_time_ms" in result
        assert isinstance(result["execution_time_ms"], int | float)
        assert result["execution_time_ms"] >= 0

    async def test_concurrent_operations(self, db_session: AsyncSession) -> None:
        """Test that service handles sequential operations properly."""
        # Note: SQLAlchemy sessions don't support true concurrency
        # This test verifies sequential operations work correctly

        notes = []
        for i in range(5):
            note = await mem0_service.create_note(db_session, key=f"concurrent_{i}", content=f"content_{i}")
            notes.append(note)

        # Verify all were created
        assert len(notes) == 5
        for i, note in enumerate(notes):
            assert note.key == f"concurrent_{i}"

    async def test_edge_case_empty_content(self, db_session: AsyncSession) -> None:
        """Test handling of edge cases like empty content."""
        # Empty content should be allowed
        note = await mem0_service.create_note(db_session, key="empty_content", content="")
        assert note.content == ""

        # None content should be allowed
        note2 = await mem0_service.create_note(db_session, key="none_content", content=None)
        assert note2.content is None

    async def test_ttl_boundary_conditions(self, db_session: AsyncSession) -> None:
        """Test TTL boundary conditions."""
        # Test minimum TTL
        note1 = await mem0_service.create_note(db_session, key="min_ttl", content="test", ttl_days=1)
        assert note1.expires_at is not None

        # Test large TTL
        note2 = await mem0_service.create_note(db_session, key="max_ttl", content="test", ttl_days=365)
        assert note2.expires_at is not None

        # Verify the time difference
        time_diff = note2.expires_at - note1.expires_at
        assert abs(time_diff.days - 364) <= 1  # Account for timing differences
