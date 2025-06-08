import argparse
import json
from pathlib import Path
from typing import Any, TypeAlias

from rich.console import Console
from rich.table import Table

MemoryItem: TypeAlias = tuple[str, dict[str, Any]]  # noqa: UP040
MemoryList: TypeAlias = list[MemoryItem]  # noqa: UP040

MEMORY_PATH = Path("E:/mem0_data")
console = Console()


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
    parser = argparse.ArgumentParser(description="COS Memory Ledger Viewer")
    parser.add_argument("--plain", action="store_true", help="Plain text output")
    parser.add_argument("--limit", type=int, default=50, help="Number of recent entries to show")
    parser.add_argument("--source", type=str, help="Filter by source (e.g. pem, cursor, cc)")
    parser.add_argument("--tag", type=str, help="Filter by tag (e.g. prompt, log, summary)")
    args = parser.parse_args()

    memories = load_memories()
    memories = sorted(
        memories,
        key=lambda x: x[1].get("timestamp", "") if isinstance(x[1], dict) else "",
        reverse=True,
    )
    memories = filter_memories(memories, source=args.source, tag=args.tag)
    memories = memories[: args.limit]

    if args.plain:
        render_plain(memories)
    else:
        render_rich_table(memories)


if __name__ == "__main__":
    main()
