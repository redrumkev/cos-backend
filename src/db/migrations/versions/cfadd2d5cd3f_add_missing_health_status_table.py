"""Add missing health_status table.

Revision ID: cfadd2d5cd3f
Revises: 07f2af238b83
Create Date: 2025-06-29 16:52:14.496518

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "cfadd2d5cd3f"
down_revision: str | None = "07f2af238b83"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table(
        "health_status",
        sa.Column("id", postgresql.UUID(), nullable=False),
        sa.Column("module", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("last_updated", sa.DateTime(timezone=True), nullable=False),
        sa.Column("details", sa.String(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("module"),
    )
    op.create_index(op.f("ix_health_status_module"), "health_status", ["module"], unique=False)
    # ### end Alembic commands ###


def downgrade() -> None:
    """Downgrade schema."""
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_index(op.f("ix_health_status_module"), table_name="health_status")
    op.drop_table("health_status")
    # ### end Alembic commands ###
