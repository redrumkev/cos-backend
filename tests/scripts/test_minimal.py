from __future__ import annotations

import sys

sys.path.append("scripts")
from generate_module import generate_module

generate_module("tech", "test_mod", dry_run=True)
