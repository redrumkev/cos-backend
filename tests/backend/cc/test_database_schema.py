from __future__ import annotations

import pytest  # Phase 2: Remove for skip removal
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

# ✅ Phase 2: P2-SCHEMA-001 RESOLVED - Database schema creation completed
# Resolved by: PostgreSQL schema creation via Alembic migrations


@pytest.mark.asyncio
async def test_cc_tables_exist(test_db_session: AsyncSession) -> None:
    """Test that CC tables exist in the database."""
    # Phase 2: PostgreSQL-only approach with schemas
    for qualified in ("cc.health_status", "cc.modules"):
        result = await test_db_session.execute(text("select to_regclass(:qn)"), {"qn": qualified})
        assert result.scalar(), f"{qualified} is missing"


@pytest.mark.asyncio
async def test_mem0_cc_tables_exist(test_db_session: AsyncSession) -> None:
    """Test that mem0_cc schema tables exist in the database."""
    # Phase 2: Check for mem0_cc schema tables (actual table names from migrations)
    for qualified in ("mem0_cc.scratch_note", "mem0_cc.event_log", "mem0_cc.base_log", "mem0_cc.prompt_trace"):
        result = await test_db_session.execute(text("select to_regclass(:qn)"), {"qn": qualified})
        assert result.scalar(), f"{qualified} is missing"
