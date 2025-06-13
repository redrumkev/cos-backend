"""SQLAlchemy models for mem0 scratch data storage.

This file demonstrates modern SQLAlchemy 2.0 patterns for temporary data storage,
including TTL management, efficient indexing, and async compatibility.

Reference implementation for future module scratch storage patterns.
"""

from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import TIMESTAMP, ForeignKey, Index, Integer, String, Text, text
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import Mapped, mapped_column, relationship

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
        TIMESTAMP(timezone=True), default=lambda: datetime.now(UTC), nullable=False, comment="UTC timestamp of creation"
    )
    expires_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True, comment="UTC timestamp when record expires (NULL = never)"
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


class BaseLog(Base):
    """Core logging table for L1 memory layer.

    Stores primary logging events with structured payload support.
    All other logging tables reference this as the source of truth.
    """

    __tablename__ = "base_log"
    __table_args__ = (
        # Performance indexes for common query patterns
        Index("ix_base_log_timestamp", "timestamp"),
        Index("ix_base_log_level", "level"),
        Index("ix_base_log_level_timestamp", "level", "timestamp"),
        get_mem0_table_args(),
    )

    # PostgreSQL-native UUID primary key
    id: Mapped[UUID] = mapped_column(
        postgresql.UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        server_default=text("gen_random_uuid()"),
        comment="Primary key UUID",
    )

    # Timezone-aware timestamp with server default
    timestamp: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        default=lambda: datetime.now(UTC),
        server_default=text("NOW()"),
        nullable=False,
        comment="UTC timestamp of log entry",
    )

    # Log level for filtering
    level: Mapped[str] = mapped_column(
        String(50), nullable=False, index=True, comment="Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)"
    )

    # Primary log message
    message: Mapped[str] = mapped_column(Text, nullable=False, comment="Primary log message content")

    # PostgreSQL JSONB for structured data (fix for asyncpg encoding issue)
    payload: Mapped[dict[str, Any] | None] = mapped_column(
        postgresql.JSONB, nullable=True, comment="Structured payload data as JSONB"
    )

    # Relationships to child tables
    prompt_traces: Mapped[list["PromptTrace"]] = relationship(
        "PromptTrace", back_populates="base_log", cascade="all, delete-orphan"
    )
    event_logs: Mapped[list["EventLog"]] = relationship(
        "EventLog", back_populates="base_log", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        """Return string representation of BaseLog."""
        return f"<BaseLog(id={self.id}, level='{self.level}', timestamp={self.timestamp})>"


class PromptTrace(Base):
    """Prompt execution tracking for L1 memory layer.

    Tracks LLM prompt/response pairs with execution metrics.
    References BaseLog for complete audit trail.
    """

    __tablename__ = "prompt_trace"
    __table_args__ = (
        # Performance indexes for common query patterns
        Index("ix_prompt_trace_base_log_id", "base_log_id"),
        Index("ix_prompt_trace_created_at", "created_at"),
        Index("ix_prompt_trace_execution_time", "execution_time_ms"),
        get_mem0_table_args(),
    )

    # PostgreSQL-native UUID primary key
    id: Mapped[UUID] = mapped_column(
        postgresql.UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        server_default=text("gen_random_uuid()"),
        comment="Primary key UUID",
    )

    # Foreign key to BaseLog
    base_log_id: Mapped[UUID] = mapped_column(
        postgresql.UUID(as_uuid=True),
        ForeignKey(f"{settings.MEM0_SCHEMA}.base_log.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Foreign key to base_log table",
    )

    # Prompt and response content
    prompt_text: Mapped[str] = mapped_column(Text, nullable=False, comment="Original prompt text sent to LLM")

    response_text: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="Response text from LLM (nullable for failed requests)"
    )

    # Execution metrics
    execution_time_ms: Mapped[int | None] = mapped_column(
        Integer, nullable=True, comment="Execution time in milliseconds"
    )

    token_count: Mapped[int | None] = mapped_column(
        Integer, nullable=True, comment="Total token count (input + output)"
    )

    # Timestamp for this specific trace
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        default=lambda: datetime.now(UTC),
        server_default=text("NOW()"),
        nullable=False,
        comment="UTC timestamp of prompt execution",
    )

    # Relationship to parent BaseLog
    base_log: Mapped["BaseLog"] = relationship("BaseLog", back_populates="prompt_traces")

    def __repr__(self) -> str:
        """Return string representation of PromptTrace."""
        return (
            f"<PromptTrace(id={self.id}, base_log_id={self.base_log_id}, execution_time_ms={self.execution_time_ms})>"
        )


class EventLog(Base):
    """Event-specific logging for L1 memory layer.

    Stores structured event data with request/trace correlation.
    References BaseLog for complete audit trail.
    """

    __tablename__ = "event_log"
    __table_args__ = (
        # Performance indexes for common query patterns
        Index("ix_event_log_base_log_id", "base_log_id"),
        Index("ix_event_log_event_type", "event_type"),
        Index("ix_event_log_request_id", "request_id"),
        Index("ix_event_log_trace_id", "trace_id"),
        Index("ix_event_log_created_at", "created_at"),
        Index("ix_event_log_type_created", "event_type", "created_at"),
        get_mem0_table_args(),
    )

    # PostgreSQL-native UUID primary key
    id: Mapped[UUID] = mapped_column(
        postgresql.UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        server_default=text("gen_random_uuid()"),
        comment="Primary key UUID",
    )

    # Foreign key to BaseLog
    base_log_id: Mapped[UUID] = mapped_column(
        postgresql.UUID(as_uuid=True),
        ForeignKey(f"{settings.MEM0_SCHEMA}.base_log.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Foreign key to base_log table",
    )

    # Event classification
    event_type: Mapped[str] = mapped_column(
        String(100), nullable=False, index=True, comment="Event type for classification and filtering"
    )

    # Structured event data (fix for asyncpg encoding issue)
    event_data: Mapped[dict[str, Any] | None] = mapped_column(
        postgresql.JSONB, nullable=True, comment="Structured event data as JSONB"
    )

    # Request correlation
    request_id: Mapped[UUID | None] = mapped_column(
        postgresql.UUID(as_uuid=True), nullable=True, index=True, comment="Request ID for correlation across services"
    )

    # Trace correlation
    trace_id: Mapped[str | None] = mapped_column(
        String(100), nullable=True, index=True, comment="Trace ID for distributed tracing correlation"
    )

    # Event timestamp
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        default=lambda: datetime.now(UTC),
        server_default=text("NOW()"),
        nullable=False,
        comment="UTC timestamp of event creation",
    )

    # Relationship to parent BaseLog
    base_log: Mapped["BaseLog"] = relationship("BaseLog", back_populates="event_logs")

    def __repr__(self) -> str:
        """Return string representation of EventLog."""
        return f"<EventLog(id={self.id}, event_type='{self.event_type}', request_id={self.request_id})>"
