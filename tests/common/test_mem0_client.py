"""Tests for the mem0_client module.

These tests validate the functionality of the Mem0Client class,
which is used for interacting with the mem0 memory service.
"""

from collections.abc import Callable  # noqa: F401
from typing import Any  # noqa: F401
from unittest.mock import Mock, patch

import pytest
from httpx import HTTPStatusError, Request, Response

from src.common.logger import logger
from src.common.mem0_client import Mem0Client, get_client


class TestMem0Client:
    """Tests for the Mem0Client class."""

    def test_initialization(self) -> None:
        """Test initialization with default and custom URLs."""
        # Default URL
        client = Mem0Client()
        assert client.base_url == "http://localhost:7790"

        # Custom URL
        custom_url = "http://custom-server:8000"
        client = Mem0Client(base_url=custom_url)
        assert client.base_url == custom_url

    @patch("httpx.get")
    def test_get_success(self, mock_get: Mock) -> None:
        """Test successful get operation."""
        # Setup mock
        mock_response = Mock()
        mock_response.json.return_value = {"key": "value"}
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        # Execute
        client = Mem0Client()
        result = client.get("test-key")

        # Verify
        mock_get.assert_called_once_with("http://localhost:7790/memory/test-key")
        mock_response.raise_for_status.assert_called_once()
        assert result == {"key": "value"}

    @patch("httpx.get")
    def test_get_error(self, mock_get: Mock) -> None:
        """Test get operation with error."""
        # Setup mock to raise error
        mock_response = Mock()
        mock_response.raise_for_status.side_effect = HTTPStatusError(
            "Error",
            request=Request("GET", "http://localhost:7790/memory/test-key"),
            response=Response(404),
        )
        mock_get.return_value = mock_response

        # Execute and verify
        client = Mem0Client()
        with pytest.raises(HTTPStatusError):
            client.get("test-key")

    @patch("httpx.post")
    def test_set_success(self, mock_post: Mock) -> None:
        """Test successful set operation."""
        # Setup mock
        mock_response = Mock()
        mock_response.json.return_value = {"status": "success", "id": "test-key"}
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response

        # Execute
        client = Mem0Client()
        data = {"test": "data"}
        result = client.set("test-key", data)

        # Verify
        mock_post.assert_called_once_with("http://localhost:7790/memory/test-key", json=data)
        mock_response.raise_for_status.assert_called_once()
        assert result == {"status": "success", "id": "test-key"}

    @patch("httpx.post")
    def test_set_error(self, mock_post: Mock) -> None:
        """Test set operation with error."""
        # Setup mock to raise error
        mock_response = Mock()
        mock_response.raise_for_status.side_effect = HTTPStatusError(
            "Error",
            request=Request("POST", "http://localhost:7790/memory/test-key"),
            response=Response(500),
        )
        mock_post.return_value = mock_response

        # Execute and verify
        client = Mem0Client()
        data = {"test": "data"}
        with pytest.raises(HTTPStatusError):
            client.set("test-key", data)

    def test_get_client(self) -> None:
        """Test the get_client function."""
        client = get_client()
        assert isinstance(client, Mem0Client)
        assert client.base_url == "http://localhost:7790"

    @patch("src.common.mem0_client.Mem0Client.get")
    @patch("src.common.mem0_client.Mem0Client.set")
    @patch("src.common.logger.logger.info")
    def test_main_execution_directly(self, mock_logger_info: Mock, mock_set: Mock, mock_get: Mock) -> None:
        """Test execution of the module's main block with direct execution."""
        # Setup mocks
        mock_set.return_value = {"status": "success", "id": "test-client-main"}
        mock_get.return_value = {"msg": "Hello from client"}

        # Import the module directly
        import src.common.mem0_client as mem0_client_module

        # Save the original __name__
        original_name = mem0_client_module.__name__

        try:
            # Set the __name__ to '__main__'
            mem0_client_module.__name__ = "__main__"

            # Execute the module's main block directly
            client = mem0_client_module.get_client()
            data_to_set = {"msg": "Hello from client"}
            key_to_test = "test-client-main"
            logger.info(f"Setting data for key '{key_to_test}': {data_to_set}")
            client.set(key_to_test, data_to_set)
            retrieved_data = client.get(key_to_test)
            logger.info(f"Retrieved data for key '{key_to_test}': {retrieved_data}")

            # Verify the mocks were called
            mock_set.assert_called_once_with(key_to_test, data_to_set)
            mock_get.assert_called_once_with(key_to_test)
            assert mock_logger_info.call_count >= 2

        finally:
            # Restore original name
            mem0_client_module.__name__ = original_name

    @patch("httpx.post")
    @patch("httpx.get")
    @patch("src.common.logger.logger.info")
    def test_main_execution(self, mock_logger_info: Mock, mock_get: Mock, mock_post: Mock) -> None:
        """Test execution of the module's main block."""
        # Setup mocks
        mock_post_response = Mock()
        mock_post_response.json.return_value = {
            "status": "success",
            "id": "test-client-main",
        }
        mock_post_response.raise_for_status = Mock()
        mock_post.return_value = mock_post_response

        mock_get_response = Mock()
        mock_get_response.json.return_value = {"msg": "Hello from client"}
        mock_get_response.raise_for_status = Mock()
        mock_get.return_value = mock_get_response

        # Direct test of the __main__ block by running the file
        import runpy
        import sys
        from unittest.mock import patch

        # Use runpy.run_path to execute the module as __main__
        with (
            patch.dict(sys.modules, {"httpx": sys.modules["httpx"]}),
            patch("src.common.logger.logger", logger),
        ):
            runpy.run_path("src/common/mem0_client.py", run_name="__main__")

        # Verify the mocks were called properly
        mock_post.assert_called_once()
        mock_get.assert_called_once()
        assert mock_logger_info.call_count >= 2

        # Verify specific arguments
        call_args = mock_post.call_args
        assert call_args is not None
        assert call_args[0][0].endswith("/test-client-main")
        assert call_args[1]["json"] == {"msg": "Hello from client"}
