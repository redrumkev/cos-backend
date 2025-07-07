#!/usr/bin/env python3
"""MCP filename-drift checker ( **placeholder** ).

This utility will, in a later sprint, validate that filenames within
`:mcp:` tool and resource directories follow the agreed-upon
naming conventions.  For now it simply exits successfully so that CI
jobs can reference the command.

NOTE: Output is intentionally minimal - a single line - because the
script may be executed inside automated pipelines.
"""

from __future__ import annotations

import sys

from rich.console import Console

# Use Rich for consistent CLI styling; fall back silently if disabled by CI.
console: Console = Console(highlight=False, markup=False)


def main() -> int:
    """Run the checker and return an exit status.

    Returns
    -------
    int
        ``0`` to indicate success. In future versions a non-zero value
        will signal drift detection.

    """
    console.print("MCP filename drift checker: placeholder (no-op)")
    return 0


if __name__ == "__main__":  # pragma: no cover - trivial wrapper
    sys.exit(main())
