"""Additional tests for the logger module to achieve 100% coverage.

These tests focus on edge cases and conditions not covered in the main test suite.
"""

from src.common.logger import log_event


class TestLoggerCompleteCoverage:
    """Additional tests for the logger module to reach 100% coverage."""

    def test_log_event_with_none_memo(self) -> None:
        """Test logging an event with memo explicitly set to None.

        This test ensures we have coverage for the conditional block that checks
        if memo is not None (line 65 in logger.py).
        """
        # Act
        # Call log_event with memo=None to test the branch where memo is None
        result = log_event(
            source="test-source",
            data={"test": "data"},
            tags=["tag1", "tag2"],
            key="test-key",
            memo=None,
        )

        # Assert - check the stub response format
        assert result["status"] == "mem0_stub"
        assert result["id"] == "test-key"
        assert result["memo"] is None  # memo should be None in result
        assert "data" in result
