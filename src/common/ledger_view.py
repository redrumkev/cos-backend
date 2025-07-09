"""Memory ledger viewer service for COS system.

This module provides a service-based approach to viewing memory ledger data
with rich table formatting and filtering capabilities.

Pattern Reference: service.py v2.1.0 (Living Patterns System)
Applied: BaseService pattern for lifecycle management
Applied: ExecutionContext for resource management
Applied: Health checks and service initialization
"""

import argparse
import json
from pathlib import Path
from typing import Any, TypeAlias

from rich.console import Console
from rich.table import Table

from src.common.database import DatabaseExecutionContext, get_execution_context
from src.core_v2.patterns.service import BaseService

MemoryItem: TypeAlias = tuple[str, dict[str, Any]]  # noqa: UP040
MemoryList: TypeAlias = list[MemoryItem]  # noqa: UP040

MEMORY_PATH = Path("E:/mem0_data")
console = Console()


class LedgerViewService(BaseService):
    """Service for viewing memory ledger data with rich formatting.

    Implements the BaseService pattern with ExecutionContext integration
    for resource management and health monitoring.
    """

    def __init__(
        self, db_session: Any = None, cache: Any = None, execution_context: DatabaseExecutionContext | None = None
    ):
        """Initialize ledger view service.

        Args:
        ----
            db_session: Database session (not used for file-based operations)
            cache: Cache instance (not used for file-based operations)
            execution_context: Optional ExecutionContext for resource management

        """
        super().__init__(db_session, cache)
        self._execution_context = execution_context or get_execution_context()

    async def _setup(self) -> None:
        """Initialize service-specific resources."""
        # Verify memory path exists or log warning
        if not MEMORY_PATH.exists():
            console.print(f"[yellow]Warning: Memory path not found: {MEMORY_PATH}[/]")

    async def health_check(self) -> dict[str, Any]:
        """Return health check with memory path status."""
        base_health = await super().health_check()
        base_health.update(
            {
                "memory_path": str(MEMORY_PATH),
                "path_exists": MEMORY_PATH.exists(),
                "memory_files": len(list(MEMORY_PATH.glob("*.json"))) if MEMORY_PATH.exists() else 0,
            }
        )
        return base_health

    def load_memories(self) -> MemoryList:
        """Load memories from the configured path."""
        return load_memories()

    def filter_memories(self, memories: MemoryList, source: str | None = None, tag: str | None = None) -> MemoryList:
        """Filter memories by source and tag."""
        return filter_memories(memories, source, tag)

    def render_rich_table(self, memories: MemoryList) -> None:
        """Render memories as a rich table."""
        render_rich_table(memories)

    def render_plain(self, memories: MemoryList) -> None:
        """Render memories in plain text format."""
        render_plain(memories)

    def run_cli(self) -> None:
        """Run the CLI interface."""
        main()


def load_memories() -> MemoryList:
    memories: MemoryList = []
    if not MEMORY_PATH.exists():
        console.print(f"[bold red]Error: Memory path not found: {MEMORY_PATH}[/]")
        return memories

    for f in MEMORY_PATH.glob("*.json"):
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            memories.append((f.stem, data))
        except json.JSONDecodeError:
            console.print(f"[yellow]Warning: Skipping invalid JSON file: {f.name}[/]")
        except Exception as e:
            console.print(f"[yellow]Warning: Error loading file {f.name}: {e}[/]")
    return memories


def filter_memories(memories: MemoryList, source: str | None = None, tag: str | None = None) -> MemoryList:
    filtered: MemoryList = []
    for key, data in memories:
        if not isinstance(data, dict):
            continue
        if source and data.get("source") != source:
            continue
        if tag and tag not in data.get("tags", []):
            continue
        filtered.append((key, data))
    return filtered


def render_rich_table(memories: MemoryList) -> None:
    table = Table(title="📚 COS Memory Ledger", show_lines=False, expand=True)
    table.add_column("Key", style="cyan", overflow="fold", max_width=30)
    table.add_column("Source", style="magenta", width=10)
    table.add_column("Timestamp", style="green", width=19)
    table.add_column("Tags", style="yellow", overflow="fold", max_width=25)
    table.add_column("Memo", style="white", overflow="fold")

    for key, data in memories:
        if not isinstance(data, dict):
            continue
        ts = str(data.get("timestamp", ""))[:19].replace("T", " ")
        tags = ", ".join(data.get("tags", []))
        memo = str(data.get("memo", ""))
        table.add_row(key, str(data.get("source", "-")), ts, tags, memo)
    console.print(table)


def render_plain(memories: MemoryList) -> None:
    for key, data in memories:
        if not isinstance(data, dict):
            continue
        console.print(f"[cyan][{key}][/] {data.get('source')} @ {data.get('timestamp')}")
        console.print(f"[yellow]Tags:[/yellow] {data.get('tags', [])}")
        console.print(f"[white]Memo:[/white] {data.get('memo', '')}")
        console.print("---")


def main() -> None:
    """Run the CLI entry point using the service pattern."""
    parser = argparse.ArgumentParser(description="COS Memory Ledger Viewer")
    parser.add_argument("--plain", action="store_true", help="Plain text output")
    parser.add_argument("--limit", type=int, default=50, help="Number of recent entries to show")
    parser.add_argument("--source", type=str, help="Filter by source (e.g. pem, cursor, cc)")
    parser.add_argument("--tag", type=str, help="Filter by tag (e.g. prompt, log, summary)")
    args = parser.parse_args()

    # Create service instance
    service = LedgerViewService()

    # Load and process memories
    memories = service.load_memories()
    memories = sorted(
        memories,
        key=lambda x: x[1].get("timestamp", "") if isinstance(x[1], dict) else "",
        reverse=True,
    )
    memories = service.filter_memories(memories, source=args.source, tag=args.tag)
    memories = memories[: args.limit]

    # Render output
    if args.plain:
        service.render_plain(memories)
    else:
        service.render_rich_table(memories)


if __name__ == "__main__":
    main()
