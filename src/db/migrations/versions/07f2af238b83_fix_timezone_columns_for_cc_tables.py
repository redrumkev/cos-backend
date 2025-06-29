"""Fix timezone columns for cc tables."""
# Migration files don't need __init__.py

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "07f2af238b83"
down_revision: str | None = "b9ebfee5e11c"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Fix timezone columns to use TIMESTAMP WITH TIME ZONE. Ensure tables exist first."""
    # Ensure schemas exist
    op.execute("CREATE SCHEMA IF NOT EXISTS cc")
    op.execute("CREATE SCHEMA IF NOT EXISTS mem0_cc")

    # Ensure cc.health_status table exists before altering
    op.execute("""
        CREATE TABLE IF NOT EXISTS cc.health_status (
            id UUID PRIMARY KEY,
            "module" TEXT NOT NULL,
            status TEXT NOT NULL,
            last_updated TIMESTAMP NOT NULL,
            details TEXT
        )
    """)
    op.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS ix_cc_health_status_module
        ON cc.health_status (module)
    """)

    # Ensure cc.modules table exists before altering
    op.execute("""
        CREATE TABLE IF NOT EXISTS cc.modules (
            id UUID PRIMARY KEY,
            "name" TEXT NOT NULL,
            "version" TEXT NOT NULL,
            active BOOLEAN NOT NULL,
            last_active TIMESTAMP NOT NULL,
            config TEXT
        )
    """)
    op.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS ix_cc_modules_name
        ON cc.modules (name)
    """)

    # Now fix timezone columns
    op.execute("""
        ALTER TABLE cc.health_status
        ALTER COLUMN last_updated TYPE TIMESTAMP WITH TIME ZONE
    """)

    op.execute("""
        ALTER TABLE cc.modules
        ALTER COLUMN last_active TYPE TIMESTAMP WITH TIME ZONE
    """)


def downgrade() -> None:
    """Revert timezone columns to TIMESTAMP WITHOUT TIME ZONE."""
    # Revert last_updated column in health_status (only if table exists)
    op.execute("""
        DO $$
        BEGIN
            IF EXISTS (SELECT FROM pg_tables WHERE schemaname = 'cc' AND tablename = 'health_status') THEN
                ALTER TABLE cc.health_status
                ALTER COLUMN last_updated TYPE TIMESTAMP WITHOUT TIME ZONE;
            END IF;
        END $$;
    """)

    # Revert last_active column in modules (only if table exists)
    op.execute("""
        DO $$
        BEGIN
            IF EXISTS (SELECT FROM pg_tables WHERE schemaname = 'cc' AND tablename = 'modules') THEN
                ALTER TABLE cc.modules
                ALTER COLUMN last_active TYPE TIMESTAMP WITHOUT TIME ZONE;
            END IF;
        END $$;
    """)
