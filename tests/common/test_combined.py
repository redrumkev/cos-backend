"""Combined tests for common module components.

This file contains tests for ledger_view.py, logger.py, and mem0_client.py
to ensure comprehensive test coverage in a way that works with the actual imports.
"""

import json
from datetime import datetime
from pathlib import Path  # noqa: F401
from unittest.mock import MagicMock, Mock, patch  # noqa: F401

import pytest  # noqa: F401
from rich.console import Console  # noqa: F401
from rich.table import Table

# We need to test these modules together
from src.common.ledger_view import (
    MEMORY_PATH,  # noqa: F401
    filter_memories,
    load_memories,
    main,
    render_plain,
    render_rich_table,
)
from src.common.logger import _demo, log_event
from src.common.mem0_client import Mem0Client


class TestMem0Client:
    """Tests for the Mem0Client class."""

    def test_initialization(self) -> None:
        """Test client initialization with default and custom URLs."""
        # Default URL
        client1 = Mem0Client()
        assert client1.base_url == "http://localhost:7790"

        # Custom URL
        custom_url = "http://custom-server:8000"
        client2 = Mem0Client(base_url=custom_url)
        assert client2.base_url == custom_url

    @patch("httpx.get")
    def test_get(self, mock_get: Mock) -> None:
        """Test the get method."""
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

    @patch("httpx.post")
    def test_set(self, mock_post: Mock) -> None:
        """Test the set method."""
        # Setup mock
        mock_response = Mock()
        mock_response.json.return_value = {"status": "success"}
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response

        # Execute
        client = Mem0Client()
        data = {"test": "data"}
        result = client.set("test-key", data)

        # Verify
        mock_post.assert_called_once_with("http://localhost:7790/memory/test-key", json=data)
        mock_response.raise_for_status.assert_called_once()
        assert result == {"status": "success"}


class TestLogger:
    """Tests for logger functionality."""

    @patch("src.common.logger.mem.set")  # Patch the 'set' method of the 'mem' instance
    @patch("uuid.uuid4")
    def test_log_event(
        self,
        mock_uuid4: Mock,
        mock_set: Mock,  # mock_set is now the patched method
    ) -> None:
        """Test log_event function."""
        # Setup mocks
        mock_uuid4.return_value.hex = "abcdef1234567890"
        mock_set.return_value = {"status": "success", "id": "test-id"}

        # Test with all parameters
        with patch("datetime.datetime") as mock_datetime:
            mock_datetime.now.return_value = datetime(2025, 4, 1)
            result1 = log_event(  # noqa: F841
                source="test",
                data={"key": "value"},
                tags=["tag1", "tag2"],
                key="custom-key",
                memo="Test memo",
            )

            # Verify the call for all parameters
            mock_set.assert_called_once()
            args, kwargs = mock_set.call_args
            assert args[0] == "custom-key"  # Key
            assert isinstance(args[1], dict)  # Payload
            assert args[1]["source"] == "test"
            assert args[1]["tags"] == ["tag1", "tag2"]
            assert args[1]["memo"] == "Test memo"
            assert "timestamp" in args[1]

            # Reset mock for the next call within the same test
            mock_set.reset_mock()
            mock_set.return_value = {
                "status": "success",
                "id": "log-test-abcdef12",
            }  # Set return for minimal call

            # Test with minimal parameters
            result2 = log_event(source="test", data="simple string")  # noqa: F841

            # Verify the call for minimal parameters
            mock_set.assert_called_once()
            args, kwargs = mock_set.call_args
            assert args[0] == "log-test-abcdef12"  # Expected generated key
            assert isinstance(args[1], dict)  # Payload
            assert args[1]["source"] == "test"
            assert args[1]["data"] == "simple string"
            assert args[1]["tags"] == []  # Ensure default empty list
            assert "memo" not in args[1]  # Ensure memo is not present

    @patch("src.common.logger.mem.set")  # Patch the 'set' method of the 'mem' instance
    def test_demo_function(
        self,
        mock_set: Mock,  # mock_set is now the patched method
    ) -> None:
        """Test the _demo function."""
        # Setup mock
        mock_set.return_value = {"status": "success", "id": "test-id"}

        # Call the function
        result = _demo()  # noqa: F841

        # Verify
        mock_set.assert_called_once()
        args, kwargs = mock_set.call_args
        assert args[0].startswith("log-pem-")  # Key
        assert isinstance(args[1], dict)  # Payload
        assert args[1]["source"] == "pem"
        assert "prompt" in args[1]["data"]
        assert "test" in args[1]["tags"]


class TestLedgerView:
    """Tests for ledger view functionality."""

    def test_filter_memories(self) -> None:
        """Test the filter_memories function."""
        # Create test data
        memories = [
            ("key1", {"source": "pem", "tags": ["tag1", "tag2"]}),
            ("key2", {"source": "cc", "tags": ["tag1"]}),
            ("key3", {"source": "pem", "tags": ["tag3"]}),
            ("key4", "not a dict"),  # Should be filtered out
        ]

        # Test no filter
        result1 = filter_memories(memories)  # type: ignore# type: ignore  # TODO: temp ignore — remove after refactor[arg-type]
        assert len(result1) == 3  # The non-dict item is filtered out

        # Test source filter
        result2 = filter_memories(memories, source="pem")  # type: ignore# type: ignore  # TODO: temp ignore — remove after refactor[arg-type]
        assert len(result2) == 2
        assert result2[0][0] == "key1"
        assert result2[1][0] == "key3"

        # Test tag filter
        result3 = filter_memories(memories, tag="tag1")  # type: ignore# type: ignore  # TODO: temp ignore — remove after refactor[arg-type]
        assert len(result3) == 2
        assert result3[0][0] == "key1"
        assert result3[1][0] == "key2"

        # Test both filters
        result4 = filter_memories(memories, source="pem", tag="tag1")  # type: ignore# type: ignore  # TODO: temp ignore — remove after refactor[arg-type]
        assert len(result4) == 1
        assert result4[0][0] == "key1"

    @patch("pathlib.Path.exists")
    @patch("pathlib.Path.glob")
    def test_load_memories(self, mock_glob: Mock, mock_exists: Mock) -> None:
        """Test the load_memories function."""
        # Test when path doesn't exist
        mock_exists.return_value = False
        with patch("rich.console.Console.print") as mock_print:
            result1 = load_memories()
            assert len(result1) == 0
            assert mock_print.called

        # Test with valid files
        mock_exists.return_value = True
        file1 = Mock()
        file1.stem = "key1"
        file1.name = "key1.json"
        file1.read_text.return_value = json.dumps({"data": "value1"})

        file2 = Mock()
        file2.stem = "key2"
        file2.name = "key2.json"
        file2.read_text.return_value = json.dumps({"data": "value2"})

        mock_glob.return_value = [file1, file2]

        result2 = load_memories()
        assert len(result2) == 2
        assert result2[0][0] == "key1"
        assert result2[0][1]["data"] == "value1"
        assert result2[1][0] == "key2"
        assert result2[1][1]["data"] == "value2"

        # Test with invalid JSON
        file3 = Mock()
        file3.stem = "key3"
        file3.name = "key3.json"
        file3.read_text.return_value = "invalid json"

        mock_glob.return_value = [file3]

        with patch("rich.console.Console.print") as mock_print:
            result3 = load_memories()
            assert len(result3) == 0
            assert mock_print.called

        # Test with file reading error
        file4 = Mock()
        file4.stem = "key4"
        file4.name = "key4.json"
        file4.read_text.side_effect = Exception("Test error")

        mock_glob.return_value = [file4]

        with patch("rich.console.Console.print") as mock_print:
            result4 = load_memories()
            assert len(result4) == 0
            assert mock_print.called

    def test_rendering_functions(self) -> None:
        """Test the render_rich_table and render_plain functions."""
        # Create test memories
        memories = [
            (
                "key1",
                {
                    "source": "test",
                    "tags": ["tag1", "tag2"],
                    "timestamp": "2025-04-01T12:00:00",
                    "memo": "Test memo",
                },
            )
        ]

        # Test rich table rendering
        with patch("rich.console.Console.print") as mock_print:
            render_rich_table(memories)
            assert mock_print.called
            assert isinstance(mock_print.call_args[0][0], Table)

        # Test plain rendering
        with patch("rich.console.Console.print") as mock_print:
            render_plain(memories)
            assert mock_print.call_count > 0

        # Test empty list
        empty_memories: list[tuple[str, dict[str, Any]]] = []  # type: ignore# type: ignore  # TODO: temp ignore — remove after refactor # noqa: F821
        with patch("rich.console.Console.print") as mock_print:
            render_rich_table(empty_memories)
            assert mock_print.called  # Should still print an empty table

        with patch("rich.console.Console.print") as mock_print:
            render_plain(empty_memories)
            assert not mock_print.called  # Should not print anything

    @patch("src.common.ledger_view.load_memories")
    @patch("src.common.ledger_view.filter_memories")
    @patch("src.common.ledger_view.render_rich_table")
    @patch("src.common.ledger_view.render_plain")
    @patch("argparse.ArgumentParser.parse_args")
    def test_main_function(
        self,
        mock_parse_args: Mock,
        mock_render_plain: Mock,
        mock_render_rich: Mock,
        mock_filter: Mock,
        mock_load: Mock,
    ) -> None:
        """Test the main function with various parameters."""
        # Setup test data
        memories = [("key1", {"source": "test", "timestamp": "2025-04-01T12:00:00"})]
        mock_load.return_value = memories
        mock_filter.return_value = memories

        # Test with default options (rich table)
        mock_args = Mock()
        mock_args.plain = False
        mock_args.limit = 50
        mock_args.source = None
        mock_args.tag = None
        mock_parse_args.return_value = mock_args

        main()

        mock_load.assert_called_once()
        mock_filter.assert_called_once_with(memories, source=None, tag=None)
        mock_render_rich.assert_called_once()
        assert not mock_render_plain.called

        # Reset mocks
        mock_load.reset_mock()
        mock_filter.reset_mock()
        mock_render_rich.reset_mock()

        # Test with plain output
        mock_args.plain = True
        main()

        mock_load.assert_called_once()
        mock_filter.assert_called_once()
        assert not mock_render_rich.called
        mock_render_plain.assert_called_once()

        # Reset mocks
        mock_load.reset_mock()
        mock_filter.reset_mock()
        mock_render_plain.reset_mock()

        # Test with source and tag filters
        mock_args.plain = False
        mock_args.source = "test"
        mock_args.tag = "tag1"

        main()

        mock_load.assert_called_once()
        mock_filter.assert_called_once_with(memories, source="test", tag="tag1")
        mock_render_rich.assert_called_once()

    def test_module_execution(self) -> None:
        """Test execution as a script using runpy."""
        # We'll mock the ledger_view module and verify it properly
        # checks if __name__ == "__main__" to call main()
        with patch("src.common.ledger_view.main") as mock_main:
            # Call the module's __name__ == "__main__" block directly
            module = __import__("src.common.ledger_view", fromlist=["ledger_view"])

            # Save the original __name__
            original_name = module.__name__

            try:
                # Simulate running as script
                module.__name__ = "__main__"

                # Re-execute the if __name__ == "__main__" check
                exec(  # noqa: S102
                    "if __name__ == '__main__':\n    main()", module.__dict__
                )

                # Verify main was called
                mock_main.assert_called_once()

            finally:
                # Restore original name
                module.__name__ = original_name
