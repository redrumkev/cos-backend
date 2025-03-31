"""Tests for the logger module in common/logger.py.

These tests validate the functionality of the logger module,
which is used for structured logging to mem0.
"""

from datetime import UTC, datetime
from unittest.mock import Mock, patch

# Import the functions directly
from src.common.logger import _demo, log_event


class TestLogger:
    """Tests for the logger module."""

    @patch("src.common.logger.mem")  # Directly patch the module-level instance
    def test_log_event_with_all_parameters(
        self,
        mock_mem: Mock,
    ) -> None:
        """Test logging an event with all parameters specified."""
        # Arrange
        mock_mem.set.return_value = {"status": "stored", "id": "custom-key"}
        test_timestamp = datetime(2025, 4, 3, 12, 0, 0, tzinfo=UTC)
        test_uuid = "abcdef1234567890"

        # Act
        # Combine nested `with` statements into a single `with` statement
        with (
            patch("datetime.datetime") as mock_datetime,
            patch("uuid.uuid4") as mock_uuid4,
        ):
            # Setup mocks
            mock_datetime.now.return_value = test_timestamp
            mock_uuid4.return_value.hex = test_uuid

            # Call the function
            result = log_event(
                source="test-source",
                data={"test": "data"},
                tags=["tag1", "tag2"],
                key="custom-key",
                memo="Test memo",
            )

        # Assert - verify the set was called with expected parameters
        # The actual return value contains both 'id' and 'status'
        assert "id" in result
        assert "status" in result
        assert result["id"] == "custom-key"
        # Verify the mock instance's method was called
        mock_mem.set.assert_called_once()

    @patch("src.common.logger.mem")  # Directly patch the module-level instance
    def test_log_event_with_minimal_parameters(
        self,
        mock_mem: Mock,
    ) -> None:
        """Test logging an event with only required parameters."""
        # Arrange
        test_uuid = "abcdef1234567890"
        expected_key = f"log-test-source-{test_uuid[:8]}"
        mock_mem.set.return_value = {"status": "stored", "id": expected_key}

        # Act
        with patch("uuid.uuid4") as mock_uuid4:
            # Setup mocks
            mock_uuid4.return_value.hex = test_uuid

            # Call the function with minimal parameters
            result = log_event(
                source="test-source",
                data="string data",
            )

        # Assert - verify the set was called with expected parameters
        expected_key = f"log-test-source-{test_uuid[:8]}"
        assert "id" in result
        assert "status" in result
        assert result["id"] == expected_key
        # Verify the mock instance's method was called
        mock_mem.set.assert_called_once()

    @patch("src.common.logger.mem")  # Directly patch the module-level instance
    def test_demo_function(self, mock_mem: Mock) -> None:
        """Test the _demo function which is used when the module is run directly."""
        # Arrange
        # Simulate a return value that includes an ID starting with "log-pem-"
        mock_mem.set.return_value = {
            "status": "stored",
            "id": "log-pem-generatedid",
        }

        # Act - call the demo function
        result = _demo()

        # Assert
        assert "id" in result
        assert "status" in result
        assert result["id"].startswith("log-pem-")
        # Verify the mock's method was called
        mock_mem.set.assert_called_once()

        # Get the last call arguments from the correct mock
        args, kwargs = mock_mem.set.call_args

        # Check payload fields
        assert "source" in args[1]
        assert "data" in args[1]
        assert "tags" in args[1]
        assert "memo" in args[1]
        assert args[1]["source"] == "pem"
        assert "prompt" in args[1]["data"]
        assert "quantum authorship" in args[1]["data"]["prompt"]
        assert "test" in args[1]["tags"]
