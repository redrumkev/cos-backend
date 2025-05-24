import os

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.connection import get_async_engine


@pytest.mark.asyncio
async def test_cc_tables_exist(test_db_session: AsyncSession) -> None:
    """Test that CC tables exist in the database."""
    engine = get_async_engine()
    async with engine.connect() as conn:
        if os.getenv("ENABLE_DB_INTEGRATION", "0") == "1":
            # PostgreSQL with schemas
            for qualified in ("cc.health_status", "cc.modules"):
                result = await conn.execute(text("select to_regclass(:qn)"), {"qn": qualified})
                assert result.scalar(), f"{qualified} is missing"
        else:
            # SQLite without schemas
            for table_name in ("cc_health_status", "cc_modules"):
                result = await conn.execute(
                    text("SELECT name FROM sqlite_master WHERE type='table' AND name=:table_name"),
                    {"table_name": table_name},
                )
                assert result.scalar(), f"{table_name} is missing"
