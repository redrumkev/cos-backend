"""Simple test for log_l1 function to debug database connection issues.

This diagnostic file is excluded from automated lint/type checks.
"""
# ruff: noqa
# mypy: ignore-errors

import os
from unittest.mock import patch
from uuid import uuid4

import pytest

from src.backend.cc.logging import log_l1
from src.backend.cc.mem0_models import BaseLog

# Skip if database integration is not enabled
ENABLE_DB_INTEGRATION = os.environ.get("ENABLE_DB_INTEGRATION", "").lower() == "true"


@pytest.mark.asyncio
@pytest.mark.skipif(not ENABLE_DB_INTEGRATION, reason="Database integration tests disabled")
async def test_simple_log_creation(monkeypatch):
    """Test basic log creation using the application's connection logic."""
    import os

    # Force use of dev database
    monkeypatch.setenv("TESTING", "false")
    monkeypatch.setenv(
        "DATABASE_URL_DEV", "postgresql+asyncpg://cos_user:Police9119!!Sql_dev@localhost:5433/cos_db_dev"
    )

    # Import models to ensure they're registered
    import src.backend.cc.mem0_models
    import src.backend.cc.models

    # Use the application's connection logic
    from src.db.connection import get_async_db

    # Mock the request ID function
    with patch("src.backend.cc.logging.get_request_id") as mock_get_request_id:
        mock_get_request_id.return_value = str(uuid4())

        # Get database session using the application's logic
        async for db_session in get_async_db():
            try:
                _ = await log_l1(db=db_session, event_type="test_event", payload={"test_key": "test_value"})

                assert "base_log_id" in _
                assert isinstance(_, dict) and "base_log_id" in _
                assert isinstance(_.get("base_log_id"), str) or hasattr(_.get("base_log_id"), "hex")

                # Verify record exists
                base_log = await db_session.get(BaseLog, _.get("base_log_id"))
                assert base_log is not None
                assert base_log.level == "INFO"
                print(f"✅ Test passed! Created BaseLog with ID: {base_log.id}")  # noqa: T201

                break  # Exit the async for loop after successful test

            except Exception as e:
                print(f"❌ Test failed: {e}")  # noqa: T201
                raise

    print("✅ mem0_cc schema exists")  # noqa: T201


if __name__ == "__main__":
    import asyncio

    asyncio.run(test_simple_log_creation())
