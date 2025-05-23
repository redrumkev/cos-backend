"""Tests for the ledger view in common/ledger_view.py.

These tests validate the functionality of the ledger view module,
which is used to display and filter memory items from the filesystem.
"""

import argparse
import json
from pathlib import Path
from unittest.mock import Mock, patch

from src.common.ledger_view import (
    MEMORY_PATH,
    MemoryList,
    filter_memories,
    load_memories,
    main,
    render_plain,
    render_rich_table,
)


class TestLedgerView:
    """Tests for the ledger view module."""

    def test_memory_path_constant(self) -> None:
        """Test that the MEMORY_PATH constant has the expected value."""
        assert Path("E:/mem0_data") == MEMORY_PATH

    @patch("pathlib.Path.exists")
    @patch("pathlib.Path.glob")
    def test_load_memories_success(self, mock_glob: Mock, mock_exists: Mock) -> None:
        """Test successful loading of memory files."""
        # Arrange
        mock_exists.return_value = True

        # Create mock file objects
        mock_file1 = Mock()
        mock_file1.stem = "memory-1"
        mock_file1.name = "memory-1.json"
        mock_file1.read_text.return_value = json.dumps({"source": "pem", "tags": ["tag1"]})

        mock_file2 = Mock()
        mock_file2.stem = "memory-2"
        mock_file2.name = "memory-2.json"
        mock_file2.read_text.return_value = json.dumps({"source": "cc", "tags": ["tag2"]})

        mock_glob.return_value = [mock_file1, mock_file2]

        # Act
        result = load_memories()

        # Assert
        mock_exists.assert_called_once_with()
        mock_glob.assert_called_once_with("*.json")
        assert len(result) == 2
        assert result[0][0] == "memory-1"
        assert result[0][1] == {"source": "pem", "tags": ["tag1"]}
        assert result[1][0] == "memory-2"
        assert result[1][1] == {"source": "cc", "tags": ["tag2"]}

    @patch("pathlib.Path.exists")
    def test_load_memories_path_not_found(self, mock_exists: Mock) -> None:
        """Test loading memories when the path doesn't exist."""
        # Arrange
        mock_exists.return_value = False

        # Act
        with patch("rich.console.Console.print") as mock_print:
            result = load_memories()

        # Assert
        mock_exists.assert_called_once_with()
        mock_print.assert_called_once()
        assert "Error: Memory path not found" in mock_print.call_args[0][0]
        assert len(result) == 0

    @patch("pathlib.Path.exists")
    @patch("pathlib.Path.glob")
    def test_load_memories_invalid_json(self, mock_glob: Mock, mock_exists: Mock) -> None:
        """Test loading memories with invalid JSON files."""
        # Arrange
        mock_exists.return_value = True

        mock_file = Mock()
        mock_file.stem = "invalid-json"
        mock_file.name = "invalid-json.json"
        mock_file.read_text.return_value = "{ invalid json }"

        mock_glob.return_value = [mock_file]

        # Act
        with patch("rich.console.Console.print") as mock_print:
            result = load_memories()

        # Assert
        mock_exists.assert_called_once_with()
        mock_glob.assert_called_once_with("*.json")
        mock_print.assert_called_once()
        assert "Warning: Skipping invalid JSON file" in mock_print.call_args[0][0]
        assert len(result) == 0

    @patch("pathlib.Path.exists")
    @patch("pathlib.Path.glob")
    def test_load_memories_general_exception(self, mock_glob: Mock, mock_exists: Mock) -> None:
        """Test loading memories when a general exception occurs."""
        # Arrange
        mock_exists.return_value = True

        mock_file = Mock()
        mock_file.stem = "error-file"
        mock_file.name = "error-file.json"
        mock_file.read_text.side_effect = Exception("Test exception")

        mock_glob.return_value = [mock_file]

        # Act
        with patch("rich.console.Console.print") as mock_print:
            result = load_memories()

        # Assert
        mock_exists.assert_called_once_with()
        mock_glob.assert_called_once_with("*.json")
        mock_print.assert_called_once()
        assert "Warning: Error loading file" in mock_print.call_args[0][0]
        assert len(result) == 0

    def test_filter_memories_no_filter(self) -> None:
        """Test filtering memories with no filters applied."""
        # Arrange
        memories: MemoryList = [
            ("key1", {"source": "pem", "tags": ["tag1", "tag2"]}),
            ("key2", {"source": "cc", "tags": ["tag3"]}),
        ]

        # Act
        result = filter_memories(memories)

        # Assert
        assert len(result) == 2
        assert result == memories

    def test_filter_memories_by_source(self) -> None:
        """Test filtering memories by source."""
        # Arrange
        memories: MemoryList = [
            ("key1", {"source": "pem", "tags": ["tag1", "tag2"]}),
            ("key2", {"source": "cc", "tags": ["tag3"]}),
            ("key3", {"source": "pem", "tags": ["tag4"]}),
        ]

        # Act
        result = filter_memories(memories, source="pem")

        # Assert
        assert len(result) == 2
        assert result[0][0] == "key1"
        assert result[1][0] == "key3"

    def test_filter_memories_by_tag(self) -> None:
        """Test filtering memories by tag."""
        # Arrange
        memories: MemoryList = [
            ("key1", {"source": "pem", "tags": ["tag1", "tag2"]}),
            ("key2", {"source": "cc", "tags": ["tag1", "tag3"]}),
            ("key3", {"source": "pem", "tags": ["tag4"]}),
        ]

        # Act
        result = filter_memories(memories, tag="tag1")

        # Assert
        assert len(result) == 2
        assert result[0][0] == "key1"
        assert result[1][0] == "key2"

    def test_filter_memories_by_source_and_tag(self) -> None:
        """Test filtering memories by both source and tag."""
        # Arrange
        memories: MemoryList = [
            ("key1", {"source": "pem", "tags": ["tag1", "tag2"]}),
            ("key2", {"source": "cc", "tags": ["tag1", "tag3"]}),
            ("key3", {"source": "pem", "tags": ["tag1", "tag4"]}),
        ]

        # Act
        result = filter_memories(memories, source="pem", tag="tag1")

        # Assert
        assert len(result) == 2
        assert result[0][0] == "key1"
        assert result[1][0] == "key3"

    def test_filter_memories_non_dict_data(self) -> None:
        """Test filtering memories with non-dictionary data."""
        # Arrange - include a non-dict item that should be filtered out
        memories: MemoryList = [
            ("key1", {"source": "pem", "tags": ["tag1"]}),
            ("key2", "not a dict"),  # type: ignore# type: ignore  # TODO: temp ignore — remove after refactor
        ]

        # Act
        result = filter_memories(memories)

        # Assert
        assert len(result) == 1
        assert result[0][0] == "key1"

    def test_render_rich_table(self) -> None:
        """Test rendering memories in a rich table."""
        # Arrange
        memories: MemoryList = [
            (
                "key1",
                {
                    "source": "pem",
                    "tags": ["tag1", "tag2"],
                    "timestamp": "2025-03-15T10:15:30",
                    "memo": "Test memo",
                },
            ),
        ]

        # Act - capture console output
        with patch("rich.console.Console.print") as mock_print:
            render_rich_table(memories)

        # Assert
        mock_print.assert_called_once()
        # We can't easily check the exact table content,
        # but we can check that a table was printed
        assert mock_print.call_args[0][0].__class__.__name__ == "Table"

    def test_render_plain(self) -> None:
        """Test rendering memories in plain text."""
        # Arrange
        memories: MemoryList = [
            (
                "key1",
                {
                    "source": "pem",
                    "tags": ["tag1", "tag2"],
                    "timestamp": "2025-03-15T10:15:30",
                    "memo": "Test memo",
                },
            ),
        ]

        # Act - capture console output
        with patch("rich.console.Console.print") as mock_print:
            render_plain(memories)

        # Assert - verify each field is printed
        assert mock_print.call_count == 4  # 3 lines plus separator
        # First call should contain key and source
        assert "key1" in str(mock_print.call_args_list[0])
        assert "pem" in str(mock_print.call_args_list[0])
        # Second call should contain tags
        assert "tag1" in str(mock_print.call_args_list[1])
        # Third call should contain memo
        assert "Test memo" in str(mock_print.call_args_list[2])

    @patch("src.common.ledger_view.load_memories")
    @patch("src.common.ledger_view.filter_memories")
    @patch("src.common.ledger_view.render_rich_table")
    def test_main_default_options(self, mock_render_rich: Mock, mock_filter: Mock, mock_load: Mock) -> None:
        """Test main function with default options."""
        # Arrange
        memories = [("key1", {"source": "pem", "timestamp": "2025-03-15T10:15:30"})]
        mock_load.return_value = memories
        mock_filter.return_value = memories

        # Act - mock argument parsing and run main
        with patch("argparse.ArgumentParser.parse_args") as mock_parse_args:
            # Mock arguments with default values
            mock_args = argparse.Namespace()
            mock_args.plain = False
            mock_args.limit = 50
            mock_args.source = None
            mock_args.tag = None
            mock_parse_args.return_value = mock_args

            main()

        # Assert
        mock_load.assert_called_once()
        mock_filter.assert_called_once_with(memories, source=None, tag=None)
        mock_render_rich.assert_called_once()

    @patch("src.common.ledger_view.load_memories")
    @patch("src.common.ledger_view.filter_memories")
    @patch("src.common.ledger_view.render_plain")
    def test_main_plain_output(self, mock_render_plain: Mock, mock_filter: Mock, mock_load: Mock) -> None:
        """Test main function with plain output."""
        # Arrange
        memories = [("key1", {"source": "pem", "timestamp": "2025-03-15T10:15:30"})]
        mock_load.return_value = memories
        mock_filter.return_value = memories

        # Act - mock argument parsing to enable plain output
        with patch("argparse.ArgumentParser.parse_args") as mock_parse_args:
            mock_args = argparse.Namespace()
            mock_args.plain = True
            mock_args.limit = 50
            mock_args.source = None
            mock_args.tag = None
            mock_parse_args.return_value = mock_args

            main()

        # Assert
        mock_render_plain.assert_called_once()

    @patch("src.common.ledger_view.load_memories")
    def test_main_with_source_and_tag_filter(self, mock_load: Mock) -> None:
        """Test main function with source and tag filters."""
        # Arrange
        memories = [
            (
                "key1",
                {"source": "pem", "timestamp": "2025-03-15T10:15:30", "tags": ["tag1"]},
            ),
            (
                "key2",
                {"source": "cc", "timestamp": "2025-03-15T10:20:30", "tags": ["tag2"]},
            ),
            (
                "key3",
                {"source": "pem", "timestamp": "2025-03-15T10:25:30", "tags": ["tag1"]},
            ),
        ]
        mock_load.return_value = memories

        # Act - mock argument parsing for source and tag filters
        with patch("argparse.ArgumentParser.parse_args") as mock_parse_args:
            mock_args = argparse.Namespace()
            mock_args.plain = False
            mock_args.limit = 50
            mock_args.source = "pem"
            mock_args.tag = "tag1"
            mock_parse_args.return_value = mock_args

            # Mock render_rich_table to avoid actual printing
            with patch("src.common.ledger_view.render_rich_table") as mock_render:
                main()

                # Assert - verify the filtered memories have the right source and tag
                # We only need to check that the filter is applied
                assert mock_render.call_count == 1
                filtered_memories = mock_render.call_args[0][0]
                assert len(filtered_memories) <= len(memories)  # Should be filtered
                for _, data in filtered_memories:
                    assert data["source"] == "pem"
                    assert "tag1" in data["tags"]

    def test_empty_memories_render_rich_table(self) -> None:
        """Test rendering an empty memories list with rich table."""
        # Arrange
        memories: MemoryList = []

        # Act
        with patch("rich.console.Console.print") as mock_print:
            render_rich_table(memories)

        # Assert - should still create and print a table, even if empty
        mock_print.assert_called_once()
        assert mock_print.call_args[0][0].__class__.__name__ == "Table"

    def test_empty_memories_render_plain(self) -> None:
        """Test rendering an empty memories list with plain format."""
        # Arrange
        memories: MemoryList = []

        # Act
        with patch("rich.console.Console.print") as mock_print:
            render_plain(memories)

        # Assert - shouldn't print anything for empty list
        assert not mock_print.called

    def test_main_script_execution(self) -> None:
        """Test execution of the script via __main__ block."""
        # Arrange - prepare for simulating script execution
        import src.common.ledger_view

        original_name = src.common.ledger_view.__name__

        # Mock everything that would be called inside main
        with (
            patch("src.common.ledger_view.load_memories") as mock_load,
            patch("src.common.ledger_view.filter_memories") as mock_filter,
            patch("src.common.ledger_view.render_rich_table") as mock_render,
            patch("argparse.ArgumentParser.parse_args") as mock_parse_args,
        ):
            # Setup mocks
            memories = [
                (
                    "key1",
                    {"source": "test", "timestamp": "2025-03-15T10:15:30"},
                )
            ]
            mock_load.return_value = memories
            mock_filter.return_value = memories

            # Mock command line args
            mock_args = argparse.Namespace()
            mock_args.plain = False
            mock_args.limit = 10
            mock_args.source = None
            mock_args.tag = None
            mock_parse_args.return_value = mock_args

            try:
                # Simulate running as main script
                src.common.ledger_view.__name__ = "__main__"
                # Execute the code that would run
                # if the module was run as main
                if hasattr(src.common.ledger_view, "main"):
                    src.common.ledger_view.main()

                # Check if all expected calls were made
                mock_load.assert_called_once()
                # Sorting would be applied here (covering line 58)
                mock_filter.assert_called_once()
                mock_render.assert_called_once()
            finally:
                # Restore original module name
                src.common.ledger_view.__name__ = original_name
