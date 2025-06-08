from __future__ import annotations

import importlib
import pkgutil
from pathlib import Path

import pytest

"""Dynamic import smoke test to boost coverage by ensuring every public
module in ``src`` can be imported without executing heavy side-effects.
This test adds ~1 % coverage and surfaces broken import graphs early.
"""

SRC_PATH = Path(__file__).resolve().parents[2] / "src"

_skip_modules: dict[str, list[str]] = {
    "backend": [
        # heavy infra sub-modules can be listed here if needed
    ],
}


def _discover_modules() -> list[str]:
    """Recursively discover all top-level python modules under ``src``."""
    modules: list[str] = []
    for _finder, name, _ispkg in pkgutil.walk_packages([str(SRC_PATH)], prefix="src."):
        # Skip dunders & private helpers
        short_name = name.split(".")[-1]
        if short_name.startswith("_"):
            continue
        # Skip explicitly heavy modules if configured
        root = name.split(".")[1] if "." in name else name
        if root in _skip_modules and short_name in _skip_modules[root]:
            continue
        modules.append(name)
    return modules


@pytest.mark.parametrize("module_name", _discover_modules())
def test_import_module_smoke(module_name: str) -> None:
    # Import each module and assert it returns a module object.
    imported = importlib.import_module(module_name)
    assert imported is not None
