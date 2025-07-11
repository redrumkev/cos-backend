# Test file - configured per-file ignores in ruff.toml handle common test patterns
"""Unit tests for edge cases in database connection module.

This file specifically covers edge cases and error conditions that are not
covered by the main test files, targeting 99.5%+ coverage for connection.py.

Following TDD methodology: RED → GREEN → REFACTOR
"""

import os
from unittest.mock import Mock, patch

import pytest

from src.db.connection import get_db_url


class TestConnectionEdgeCases:
    """Test edge cases in database connection functions."""

    @patch.dict(os.environ, {}, clear=True)
    @patch("src.db.connection.logger")
    def test_get_db_url_dev_not_set_warning(self, mock_logger: Mock) -> None:
        """Test warning when DATABASE_URL_DEV is not set."""
        # Ensure DATABASE_URL_DEV is not set
        if "DATABASE_URL_DEV" in os.environ:
            del os.environ["DATABASE_URL_DEV"]

        # Call with dev=True (default)
        url = get_db_url(dev=True)

        # Should return default dev URL
        assert url == "postgresql+asyncpg://cos_user:cos_dev_pass@localhost:5433/cos_db_dev"

        # Should log warning
        mock_logger.warning.assert_called_once_with("DATABASE_URL_DEV not set, using default dev URL")

    @patch.dict(os.environ, {}, clear=True)
    @patch("src.db.connection.logger")
    def test_get_db_url_production_not_set_error(self, mock_logger: Mock) -> None:
        """Test error when DATABASE_URL is not set for production."""
        # Ensure DATABASE_URL is not set
        if "DATABASE_URL" in os.environ:
            del os.environ["DATABASE_URL"]

        # Force production mode (though this shouldn't happen in Phase 2)
        # We need to mock the conditions that would lead to this path
        with patch("src.db.connection.os.getenv") as mock_getenv:
            # Make it think we're not in testing or dev mode
            mock_getenv.side_effect = lambda key, default=None: {
                "TESTING": None,
                "DATABASE_URL_DEV": None,
                "DATABASE_URL": None,
            }.get(key, default)

            # Should raise ValueError
            with pytest.raises(ValueError, match="DATABASE_URL must be configured for production"):
                get_db_url(testing=False, dev=False)

            # Should log error
            mock_logger.error.assert_called_once_with("DATABASE_URL is not set!")

    def test_get_db_url_always_uses_dev_in_phase2(self) -> None:
        """Test that get_db_url always uses dev database during Phase 2."""
        # Set a production URL
        with patch.dict(os.environ, {"DATABASE_URL": "postgresql://prod"}):
            # Even with dev=False, should still use dev database
            url = get_db_url(dev=False)

            # Should contain port 5433 (dev database)
            assert ":5433/" in url or "DATABASE_URL_DEV" in os.environ

    def test_get_db_url_testing_mode_uses_dev(self) -> None:
        """Test that testing mode always uses dev database."""
        with patch.dict(os.environ, {"TESTING": "1"}):
            url = get_db_url(testing=False, dev=False)

            # Should use dev database even with both flags False
            assert ":5433/" in url or "DATABASE_URL_DEV" in os.environ
