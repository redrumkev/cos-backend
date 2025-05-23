# src/db/connection.py

import os
from collections.abc import AsyncGenerator
from functools import lru_cache

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    create_async_engine,
)
from sqlalchemy.orm import Session, sessionmaker

from src.common.config import get_settings

IN_TEST_MODE = "PYTEST_CURRENT_TEST" in os.environ


@lru_cache
def get_async_engine() -> AsyncEngine:
    s = get_settings()
    db_url = s.POSTGRES_TEST_URL if IN_TEST_MODE else s.POSTGRES_DEV_URL
    if db_url.startswith("postgresql://"):
        db_url = db_url.replace("postgresql://", "postgresql+asyncpg://", 1)
    return create_async_engine(
        db_url,
        pool_size=5,
        max_overflow=10,
        pool_timeout=30,
        echo=False,
    )


@lru_cache
def get_async_session_maker() -> sessionmaker[Session]:
    engine = get_async_engine()
    maker: sessionmaker[Session] = sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)  # type: ignore
    return maker


async def get_async_db() -> AsyncGenerator[AsyncSession, None]:
    async_session = get_async_session_maker()
    async with async_session() as session:  # type: ignore
        try:
            yield session
        finally:
            await session.rollback()
