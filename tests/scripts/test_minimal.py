from __future__ import annotations

import sys

sys.path.append("scripts")
from generate_module import generate_module


def test_generate_module_dry_run() -> None:
    """Test that generate_module executes without error in dry_run mode."""
    # Should not raise any exception
    result = generate_module("tech", "test_mod", dry_run=True)

    # Function returns None on successful dry run
    assert result is None
