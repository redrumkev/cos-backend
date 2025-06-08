#!/usr/bin/env python3
# ruff: noqa
# mypy: ignore-errors
"""Developer utility script to test local Postgres connectivity.

This file is *not* part of the automated test suite.  It remains in the
repository as a handy manual check during local development, and therefore we
disable lint/type-checking for this file via the directives above.
"""

import asyncio

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker


async def test_conn():
    # Connect directly to dev database
    dev_url = "postgresql+asyncpg://postgres:dev_password@localhost:5433/cos_dev"

    try:
        # Create engine directly for dev database
        engine = create_async_engine(dev_url)
        async_session = sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

        async with async_session() as session:
            await session.execute(text("SELECT 1"))

            _ = await session.execute(
                text("SELECT schema_name FROM information_schema.schemata WHERE schema_name = 'mem0_cc'")
            )

            _ = await session.execute(
                text("SELECT table_name FROM information_schema.tables WHERE table_schema = 'mem0_cc'")
            )

            return True
    except Exception:
        return False


if __name__ == "__main__":
    asyncio.run(test_conn())
