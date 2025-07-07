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

# Tests will use mock when RUN_INTEGRATION=0
# ENABLE_DB_INTEGRATION = os.environ.get("ENABLE_DB_INTEGRATION", "").lower() == "true"


@pytest.mark.asyncio
# Removed skipif - test will use mock or real DB based on RUN_INTEGRATION
async def test_simple_log_creation(test_db_session, monkeypatch):
    """Test basic log creation using the test database session."""
    # Mock the request ID function
    with patch("src.backend.cc.logging.get_request_id") as mock_get_request_id:
        mock_get_request_id.return_value = str(uuid4())

        # Use the test database session (will be mock or real based on RUN_INTEGRATION)
        _ = await log_l1(db=test_db_session, event_type="test_event", payload={"test_key": "test_value"})

        assert "base_log_id" in _
        assert isinstance(_, dict) and "base_log_id" in _
        assert isinstance(_.get("base_log_id"), str) or hasattr(_.get("base_log_id"), "hex")

        # Verify record exists
        base_log = await test_db_session.get(BaseLog, _.get("base_log_id"))
        assert base_log is not None
        assert base_log.level == "INFO"
        print(f"✅ Test passed! Created BaseLog with ID: {base_log.id}")  # noqa: T201
