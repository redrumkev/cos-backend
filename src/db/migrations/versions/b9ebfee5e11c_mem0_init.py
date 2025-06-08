"""mem0_init.

Revision ID: b9ebfee5e11c
Revises: afbf6e0c3845
Create Date: 2025-06-11 21:17:14.701685

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "b9ebfee5e11c"
down_revision: str | None = "afbf6e0c3845"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema - Create mem0_cc L1 memory layer tables."""
    # Create base_log table with PostgreSQL-native types
    op.create_table(
        "base_log",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
            comment="Primary key UUID",
        ),
        sa.Column(
            "timestamp",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
            comment="UTC timestamp of log entry",
        ),
        sa.Column(
            "level", sa.String(length=50), nullable=False, comment="Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)"
        ),
        sa.Column("message", sa.Text(), nullable=False, comment="Primary log message content"),
        sa.Column(
            "payload",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
            comment="Structured payload data as JSONB",
        ),
        sa.PrimaryKeyConstraint("id"),
        schema="mem0_cc",
    )

    # Create performance indexes for base_log
    op.create_index("ix_base_log_timestamp", "base_log", ["timestamp"], unique=False, schema="mem0_cc")
    op.create_index("ix_base_log_level", "base_log", ["level"], unique=False, schema="mem0_cc")
    op.create_index("ix_base_log_level_timestamp", "base_log", ["level", "timestamp"], unique=False, schema="mem0_cc")

    # Create prompt_trace table with foreign key to base_log
    op.create_table(
        "prompt_trace",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
            comment="Primary key UUID",
        ),
        sa.Column(
            "base_log_id", postgresql.UUID(as_uuid=True), nullable=False, comment="Foreign key to base_log table"
        ),
        sa.Column("prompt_text", sa.Text(), nullable=False, comment="Original prompt text sent to LLM"),
        sa.Column(
            "response_text", sa.Text(), nullable=True, comment="Response text from LLM (nullable for failed requests)"
        ),
        sa.Column("execution_time_ms", sa.Integer(), nullable=True, comment="Execution time in milliseconds"),
        sa.Column("token_count", sa.Integer(), nullable=True, comment="Total token count (input + output)"),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
            comment="UTC timestamp of prompt execution",
        ),
        sa.ForeignKeyConstraint(["base_log_id"], ["mem0_cc.base_log.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        schema="mem0_cc",
    )

    # Create performance indexes for prompt_trace
    op.create_index("ix_prompt_trace_base_log_id", "prompt_trace", ["base_log_id"], unique=False, schema="mem0_cc")
    op.create_index("ix_prompt_trace_created_at", "prompt_trace", ["created_at"], unique=False, schema="mem0_cc")
    op.create_index(
        "ix_prompt_trace_execution_time", "prompt_trace", ["execution_time_ms"], unique=False, schema="mem0_cc"
    )

    # Create event_log table with foreign key to base_log
    op.create_table(
        "event_log",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
            comment="Primary key UUID",
        ),
        sa.Column(
            "base_log_id", postgresql.UUID(as_uuid=True), nullable=False, comment="Foreign key to base_log table"
        ),
        sa.Column(
            "event_type", sa.String(length=100), nullable=False, comment="Event type for classification and filtering"
        ),
        sa.Column(
            "event_data",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
            comment="Structured event data as JSONB",
        ),
        sa.Column(
            "request_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
            comment="Request ID for correlation across services",
        ),
        sa.Column(
            "trace_id", sa.String(length=100), nullable=True, comment="Trace ID for distributed tracing correlation"
        ),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
            comment="UTC timestamp of event creation",
        ),
        sa.ForeignKeyConstraint(["base_log_id"], ["mem0_cc.base_log.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        schema="mem0_cc",
    )

    # Create performance indexes for event_log
    op.create_index("ix_event_log_base_log_id", "event_log", ["base_log_id"], unique=False, schema="mem0_cc")
    op.create_index("ix_event_log_event_type", "event_log", ["event_type"], unique=False, schema="mem0_cc")
    op.create_index("ix_event_log_request_id", "event_log", ["request_id"], unique=False, schema="mem0_cc")
    op.create_index("ix_event_log_trace_id", "event_log", ["trace_id"], unique=False, schema="mem0_cc")
    op.create_index("ix_event_log_created_at", "event_log", ["created_at"], unique=False, schema="mem0_cc")
    op.create_index(
        "ix_event_log_type_created", "event_log", ["event_type", "created_at"], unique=False, schema="mem0_cc"
    )


def downgrade() -> None:
    """Downgrade schema - Remove mem0_cc L1 memory layer tables."""
    # Drop event_log table and indexes
    op.drop_index("ix_event_log_type_created", table_name="event_log", schema="mem0_cc")
    op.drop_index("ix_event_log_created_at", table_name="event_log", schema="mem0_cc")
    op.drop_index("ix_event_log_trace_id", table_name="event_log", schema="mem0_cc")
    op.drop_index("ix_event_log_request_id", table_name="event_log", schema="mem0_cc")
    op.drop_index("ix_event_log_event_type", table_name="event_log", schema="mem0_cc")
    op.drop_index("ix_event_log_base_log_id", table_name="event_log", schema="mem0_cc")
    op.drop_table("event_log", schema="mem0_cc")

    # Drop prompt_trace table and indexes
    op.drop_index("ix_prompt_trace_execution_time", table_name="prompt_trace", schema="mem0_cc")
    op.drop_index("ix_prompt_trace_created_at", table_name="prompt_trace", schema="mem0_cc")
    op.drop_index("ix_prompt_trace_base_log_id", table_name="prompt_trace", schema="mem0_cc")
    op.drop_table("prompt_trace", schema="mem0_cc")

    # Drop base_log table and indexes
    op.drop_index("ix_base_log_level_timestamp", table_name="base_log", schema="mem0_cc")
    op.drop_index("ix_base_log_level", table_name="base_log", schema="mem0_cc")
    op.drop_index("ix_base_log_timestamp", table_name="base_log", schema="mem0_cc")
    op.drop_table("base_log", schema="mem0_cc")
