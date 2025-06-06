"""Add mem0 scratch_note table.

Revision ID: afbf6e0c3845
Revises: ef3c881c1d43
Create Date: 2025-06-03 19:55:17.930478

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "afbf6e0c3845"
down_revision: str | None = "ef3c881c1d43"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    # Create scratch_note table in mem0_cc schema
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS mem0_cc.scratch_note (
            id SERIAL PRIMARY KEY,
            key VARCHAR(255) NOT NULL,
            content TEXT,
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
            expires_at TIMESTAMP WITH TIME ZONE
        )
        """
    )

    # Create indexes for efficient queries
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_scratch_note_key
        ON mem0_cc.scratch_note (key)
        """
    )

    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_scratch_expires_created
        ON mem0_cc.scratch_note (expires_at, created_at)
        """
    )

    # Create composite index for efficient active data queries
    # Note: Avoiding time-based functions in index predicates due to immutability requirements
    # This composite index supports queries on both key and expires_at efficiently
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_scratch_key_expires
        ON mem0_cc.scratch_note (key, expires_at)
        """
    )


def downgrade() -> None:
    """Downgrade schema."""
    # Drop indexes first
    op.execute("DROP INDEX IF EXISTS mem0_cc.ix_scratch_key_expires")
    op.execute("DROP INDEX IF EXISTS mem0_cc.ix_scratch_expires_created")
    op.execute("DROP INDEX IF EXISTS mem0_cc.ix_scratch_note_key")

    # Drop table
    op.execute("DROP TABLE IF EXISTS mem0_cc.scratch_note")
