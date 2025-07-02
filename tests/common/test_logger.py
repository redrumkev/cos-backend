"""Tests for the logger module in common/logger.py.

These tests validate the functionality of the logger module,
which is used for structured logging to PostgreSQL L1 memory.
"""

# Import the functions directly
from src.common.logger import _demo, log_event


class TestLogger:
    """Tests for the logger module."""

    def test_log_event_with_all_parameters(self) -> None:
        """Test logging an event with all parameters specified."""
        # Act
        result = log_event(
            source="test-source",
            data={"test": "data"},
            tags=["tag1", "tag2"],
            key="custom-key",
            memo="Test memo",
        )

        # Assert
        assert "id" in result
        assert "status" in result
        assert result["id"] == "custom-key"
        # Should be success or fallback depending on database availability
        assert result["status"] in ["success", "fallback"]

    def test_log_event_with_minimal_parameters(self) -> None:
        """Test logging an event with only required parameters."""
        # Act
        result = log_event(
            source="test-source",
            data="string data",
        )

        # Assert
        assert "id" in result
        assert "status" in result
        assert result["id"].startswith("log-test-source-")
        # Should be mem0_stub since memo defaults to None
        assert result["status"] == "mem0_stub"

    def test_log_event_handles_dict_and_string_data(self) -> None:
        """Test that log_event handles both dict and string data."""
        # Test dict data
        result_dict = log_event(
            source="test-source",
            data={"key": "value", "number": 42},
        )
        assert "id" in result_dict
        assert "status" in result_dict

        # Test string data
        result_str = log_event(
            source="test-source",
            data="simple string data",
        )
        assert "id" in result_str
        assert "status" in result_str

    def test_demo_function(self) -> None:
        """Test the _demo function which is used when the module is run directly."""
        # Act - call the demo function
        result = _demo()

        # Assert - check the response format
        assert "id" in result
        assert "status" in result
        # Should be success or fallback depending on database availability
        assert result["status"] in ["success", "fallback"]
        assert result["id"].startswith("log-pem-")

        # Check that the data field contains the expected content
        assert "data" in result
        assert "prompt" in result["data"]
        assert "output" in result["data"]
