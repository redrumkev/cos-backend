import pytest
from sqlalchemy import text

from src.db.connection import get_async_engine


@pytest.mark.asyncio
async def test_cc_tables_exist() -> None:
    engine = get_async_engine()
    async with engine.connect() as conn:
        for qualified in ("cc.health_status", "cc.modules"):
            result = await conn.execute(
                text("select to_regclass(:qn)"), {"qn": qualified}
            )
            assert result.scalar(), f"{qualified} is missing"
