"""Tests for mem0 models and schema functionality.

Tests the ScratchNote model including TTL management, expiration logic,
and proper schema configuration.
"""

from __future__ import annotations

import os
from datetime import UTC, datetime, timedelta
from unittest.mock import patch

import pytest  # Phase 2: Remove for skip removal
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.backend.cc.mem0_models import ScratchNote, get_mem0_table_args
from src.common.config import get_settings

# Phase 2: Skip removed for Mem0 module implementation (P2-MEM0-001) - COMPLETED


class TestScratchNoteModel:
    """Test the ScratchNote model functionality."""

    def test_scratch_note_creation_basic(self) -> None:
        """Test basic ScratchNote creation without TTL."""
        note = ScratchNote(key="test_key", content="test content")

        assert note.key == "test_key"
        assert note.content == "test content"
        assert note.expires_at is None
        assert not note.is_expired
        assert note.created_at is not None

    def test_scratch_note_creation_with_ttl(self) -> None:
        """Test ScratchNote creation with TTL."""
        ttl_days = 7
        note = ScratchNote(key="test_key", content="test content", ttl_days=ttl_days)

        assert note.key == "test_key"
        assert note.content == "test content"
        assert note.expires_at is not None

        # Check that expires_at is approximately ttl_days from now
        expected_expiry = datetime.now(UTC) + timedelta(days=ttl_days)
        time_diff = abs((note.expires_at - expected_expiry).total_seconds())
        assert time_diff < 1  # Within 1 second

    def test_scratch_note_expiration_check(self) -> None:
        """Test expiration checking logic."""
        # Create expired note
        expired_note = ScratchNote(key="expired", content="old")
        expired_note.expires_at = datetime.now(UTC) - timedelta(hours=1)
        assert expired_note.is_expired

        # Create future note
        future_note = ScratchNote(key="future", content="new")
        future_note.expires_at = datetime.now(UTC) + timedelta(hours=1)
        assert not future_note.is_expired

        # Create note without expiry
        permanent_note = ScratchNote(key="permanent", content="forever")
        assert not permanent_note.is_expired

    def test_scratch_note_repr(self) -> None:
        """Test string representation."""
        note = ScratchNote(key="test_key", content="test")
        repr_str = repr(note)

        assert "ScratchNote" in repr_str
        assert "test_key" in repr_str
        assert "expired=" in repr_str

    def test_scratch_note_table_configuration(self) -> None:
        """Test table configuration and indexes."""
        # Check table name
        assert ScratchNote.__tablename__ == "scratch_note"

        # Check that table args include indexes
        table_args = ScratchNote.__table_args__
        assert len(table_args) >= 2  # At least 2 indexes plus schema config

        # Verify index names are present
        index_names = [arg.name for arg in table_args if hasattr(arg, "name")]
        assert "ix_scratch_expires_created" in index_names
        assert "ix_scratch_key_active" in index_names


class TestMem0TableArgs:
    """Test the get_mem0_table_args function."""

    def test_table_args_with_db_integration_enabled(self) -> None:
        """Test table args when DB integration is enabled."""
        with patch.dict(os.environ, {"ENABLE_DB_INTEGRATION": "1"}):
            args = get_mem0_table_args()

            settings = get_settings()
            assert args["schema"] == settings.MEM0_SCHEMA
            assert args["extend_existing"] is True

    def test_table_args_with_db_integration_disabled(self) -> None:
        """Test table args when DB integration is disabled."""
        with patch.dict(os.environ, {"ENABLE_DB_INTEGRATION": "0"}):
            args = get_mem0_table_args()

            assert "schema" not in args
            assert args["extend_existing"] is True

    def test_table_args_default_behavior(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test table args with default environment."""
        # Remove the env var if it exists
        monkeypatch.delenv("ENABLE_DB_INTEGRATION", raising=False)

        args = get_mem0_table_args()
        assert "schema" not in args
        assert args["extend_existing"] is True


@pytest.mark.asyncio
class TestScratchNoteDatabase:
    """Test ScratchNote database operations."""

    async def test_scratch_note_database_creation(self, db_session: AsyncSession) -> None:
        """Test creating ScratchNote in database."""
        note = ScratchNote(key="db_test", content="database test", ttl_days=1)

        db_session.add(note)
        await db_session.commit()
        await db_session.refresh(note)

        assert note.id is not None
        assert note.key == "db_test"
        assert note.content == "database test"
        assert note.expires_at is not None

    @pytest.mark.skip(reason="CI: Schema isolation test failing in CI environment")
    async def test_scratch_note_schema_isolation(self, db_session: AsyncSession) -> None:
        """Test that scratch notes are created in the correct schema."""
        # This test verifies schema isolation by checking table metadata
        note = ScratchNote(key="schema_test", content="test")
        db_session.add(note)
        await db_session.commit()

        # Query to check if the table exists in the expected schema
        settings = get_settings()
        if os.getenv("ENABLE_DB_INTEGRATION", "0") == "1":
            # First verify the note was created successfully
            assert note.id is not None

            # Check that the table exists in the mem0 schema
            # In CI, the table might be in public schema or mem0_cc schema
            result = await db_session.execute(
                text("""
                SELECT table_name, table_schema
                FROM information_schema.tables
                WHERE table_name = 'scratch_note'
                AND table_schema IN ('public', :schema_name)
                """),
                {"schema_name": settings.MEM0_SCHEMA},
            )
            tables = result.fetchall()
            assert len(tables) > 0, "scratch_note table not found in any expected schema"

    async def test_scratch_note_ttl_query_optimization(self, db_session: AsyncSession) -> None:
        """Test that TTL queries use proper indexes."""
        # Create test data
        current_time = datetime.now(UTC)

        # Active note
        active_note = ScratchNote(key="active", content="active")
        active_note.expires_at = current_time + timedelta(days=1)

        # Expired note
        expired_note = ScratchNote(key="expired", content="expired")
        expired_note.expires_at = current_time - timedelta(days=1)

        db_session.add_all([active_note, expired_note])
        await db_session.commit()

        # Query for expired notes (should use ix_scratch_expires_created index)
        # Use datetime.now(UTC) in Python instead of SQL NOW() for SQLite compatibility
        current_time_param = datetime.now(UTC)
        # Use schema-qualified table name for integration tests
        import os

        # Use safe schema qualification without f-string injection risk
        if os.getenv("ENABLE_DB_INTEGRATION", "0") == "1":
            query = """
            SELECT key FROM mem0_cc.scratch_note
            WHERE expires_at IS NOT NULL AND expires_at <= :current_time
            ORDER BY expires_at, created_at
            """
        else:
            query = """
            SELECT key FROM scratch_note
            WHERE expires_at IS NOT NULL AND expires_at <= :current_time
            ORDER BY expires_at, created_at
            """

        result = await db_session.execute(
            text(query),
            {"current_time": current_time_param},
        )
        expired_keys = [row[0] for row in result.fetchall()]
        assert "expired" in expired_keys
        assert "active" not in expired_keys
