from __future__ import annotations

import sys

import pytest  # Phase 2: Remove for skip removal

sys.path.append("scripts")
from generate_module import generate_module

# Phase 2: Remove this skip block for script testing (P2-SCRIPTS-001)
pytestmark = pytest.mark.skip(reason="Phase 2: Script testing needed. Trigger: P2-SCRIPTS-001")

generate_module("tech", "test_mod", dry_run=True)
