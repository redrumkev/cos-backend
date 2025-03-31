"""Additional tests for the logger module to achieve 100% coverage.

These tests focus on edge cases and conditions not covered in the main test suite.
"""

from unittest.mock import Mock, patch

from src.common.logger import log_event


class TestLoggerCompleteCoverage:
    """Additional tests for the logger module to reach 100% coverage."""

    @patch("src.common.logger.mem")
    def test_log_event_with_none_memo(self, mock_mem: Mock) -> None:
        """Test logging an event with memo explicitly set to None.

        This test ensures we have coverage for the conditional block that checks
        if memo is not None (line 65 in logger.py).
        """
        # Arrange
        mock_mem.set.return_value = {"status": "stored", "id": "test-key"}

        # Act
        # Call log_event with memo=None to test the branch where memo is None
        result = log_event(
            source="test-source",
            data={"test": "data"},
            tags=["tag1", "tag2"],
            key="test-key",
            memo=None,
        )

        # Assert
        assert result["status"] == "stored"

        # Get the payload sent to mem.set
        args, _ = mock_mem.set.call_args
        key, payload = args

        # Verify memo is not in the payload
        assert "memo" not in payload
        assert "source" in payload
        assert "data" in payload
        assert "tags" in payload
        assert "timestamp" in payload
