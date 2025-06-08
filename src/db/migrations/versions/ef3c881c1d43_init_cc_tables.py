"""init cc tables.

Revision ID: ef3c881c1d43
Revises:
Create Date: 2025-05-17 20:25:12.058707

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "ef3c881c1d43"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Idempotent upgrade — creates schemas and tables if they do not exist."""
    # create schemas first (safe if already present)
    op.execute("CREATE SCHEMA IF NOT EXISTS cc")
    op.execute("CREATE SCHEMA IF NOT EXISTS mem0_cc")

    # NB: op.create_table will raise if table exists.
    # We guard with 'IF NOT EXISTS' raw SQL instead for bullet-proof run-again.
    # HealthStatus
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS cc.health_status (
            id UUID PRIMARY KEY,
            "module" TEXT NOT NULL,
            status TEXT NOT NULL,
            last_updated TIMESTAMP NOT NULL,
            details TEXT
        )
        """
    )
    # Create unique index for health_status.module
    op.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS ix_cc_health_status_module
        ON cc.health_status (module)
        """
    )

    # Modules
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS cc.modules (
            id UUID PRIMARY KEY,
            "name" TEXT NOT NULL,
            "version" TEXT NOT NULL,
            active BOOLEAN NOT NULL,
            last_active TIMESTAMP NOT NULL,
            config TEXT
        )
        """
    )
    # Create unique index for modules.name
    op.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS ix_cc_modules_name
        ON cc.modules (name)
        """
    )


def downgrade() -> None:
    """Safe downgrade - drops tables we created but leaves schemas."""
    op.execute("DROP INDEX IF EXISTS cc.ix_cc_modules_name")
    op.execute("DROP TABLE IF EXISTS cc.modules")
    op.execute("DROP INDEX IF EXISTS cc.ix_cc_health_status_module")
    op.execute("DROP TABLE IF EXISTS cc.health_status")
