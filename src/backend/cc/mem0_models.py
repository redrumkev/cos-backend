"""SQLAlchemy models for mem0 scratch data storage.

This file demonstrates modern SQLAlchemy 2.0 patterns for temporary data storage,
including TTL management, efficient indexing, and async compatibility.

Reference implementation for future module scratch storage patterns.
"""

from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import Index, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column

from src.common.config import get_settings
from src.db.base import Base

settings = get_settings()


def get_mem0_table_args() -> dict[str, Any]:
    """Get table args for mem0 schema with proper overrides."""
    import os

    # Override for mem0 schema
    if os.getenv("ENABLE_DB_INTEGRATION", "0") == "1":
        return {"schema": settings.MEM0_SCHEMA, "extend_existing": True}
    else:
        return {"extend_existing": True}


class ScratchNote(Base):
    """Reference implementation for temporary data storage.

    Demonstrates:
    - Modern SQLAlchemy 2.0 patterns (Mapped, mapped_column)
    - Efficient TTL management with proper indexing
    - Clean async patterns compatible with Sprint 2 integrations
    """

    __tablename__ = "scratch_note"
    __table_args__ = (
        # Optimized for TTL cleanup queries
        Index("ix_scratch_expires_created", "expires_at", "created_at"),
        # Optimized for active data queries
        Index("ix_scratch_key_active", "key", postgresql_where=text("expires_at IS NULL OR expires_at > NOW()")),
        get_mem0_table_args(),
    )

    # Modern SQLAlchemy 2.0 patterns with full type safety
    id: Mapped[int] = mapped_column(primary_key=True, sort_order=-100)
    key: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    content: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(UTC), nullable=False, comment="UTC timestamp of creation"
    )
    expires_at: Mapped[datetime | None] = mapped_column(
        nullable=True, comment="UTC timestamp when record expires (NULL = never)"
    )

    def __init__(self, key: str, content: str | None = None, ttl_days: int | None = None, **kwargs: Any) -> None:
        """Initialize with automatic TTL calculation."""
        # Ensure created_at is set if not provided
        if "created_at" not in kwargs:
            kwargs["created_at"] = datetime.now(UTC)

        super().__init__(key=key, content=content, **kwargs)
        if ttl_days is not None:
            self.expires_at = datetime.now(UTC) + timedelta(days=ttl_days)

    @property
    def is_expired(self) -> bool:
        """Check if this note has expired."""
        return self.expires_at is not None and self.expires_at <= datetime.now(UTC)

    def __repr__(self) -> str:
        """Return string representation of ScratchNote."""
        return f"<ScratchNote(key='{self.key}', expired={self.is_expired})>"
