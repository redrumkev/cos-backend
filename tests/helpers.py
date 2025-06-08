import os

import pytest


def require_db() -> bool:
    """Return True if integration DB is enabled."""
    return os.getenv("ENABLE_DB_INTEGRATION", "0") == "1"


skip_if_no_db = pytest.mark.skipif(
    not require_db(),
    reason="ENABLE_DB_INTEGRATION env-var not set - skipping heavy DB test",
)
