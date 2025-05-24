"""Test configuration for CC module tests.

This file provides fixtures and configuration specific to CC module testing,
including database session overrides and test client setup.
"""

from collections.abc import Generator

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.backend.cc.deps import get_cc_db


@pytest.fixture
def override_get_cc_db(test_db_session: AsyncSession) -> AsyncSession:
    """Override the get_cc_db dependency for testing."""
    return test_db_session


@pytest.fixture
def test_client(app: FastAPI, override_get_cc_db: AsyncSession) -> Generator[TestClient, None, None]:
    """Create a test client with overridden database dependency."""
    if app is None:
        pytest.skip("FastAPI app not available")

    app.dependency_overrides[get_cc_db] = lambda: override_get_cc_db

    with TestClient(app) as client:
        yield client

    # Clean up dependency overrides
    app.dependency_overrides.clear()
