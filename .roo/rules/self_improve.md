---
description: Guidelines for continuously improving Roo Code rules based on emerging code patterns and best practices.
globs: **/*
alwaysApply: true
---
# ---
# name: self_improve
# version: 2.0
# applies_to: ["**/*.py", "**/*.tsx", "**/*.md"]
# trigger: always
# summary: COS-wide continuous rule improvement and pattern elevation protocol
# ---

definition:
  purpose: >
    Ensure that every change, fix, or new feature improves the intelligence,
    structure, or soul of the system. Self-improvement rules act as a living
    meta-layer, detecting emergent patterns, upgrading code wisdom, and
    creating harmony across backend and frontend modules.

pattern:
  - 🔍 Trigger new rules when:
      - A pattern repeats in 3+ files (FastAPI routes, Redis ops, React hooks)
      - Code reviews reveal repeated advice
      - Tests repeatedly fail due to the same missed edge case
      - A new tool or library gains usage across modules (e.g. `rich`, `tqdm`, `framer-motion`)
  - ✨ Update existing rules when:
      - A cleaner implementation emerges
      - A better metaphor or docstring clarifies the concept
      - Edge cases evolve or performance shifts
  - 🚫 Deprecate rules when:
      - Tools or patterns become outdated (e.g. removing Prisma if present)
      - The system evolves past them (e.g. hardcoded schemas → dynamic settings)
      - Agent behavior shifts to smarter alternatives

examples:
  - Refactor repeated query logic in FastAPI routes into shared `service` methods
  - Add `rich.print("✅ Cache hit")` or `console.log("%c⚡ Optimized Render", "color:orange")`
  - Detect that multiple `.tsx` files use the same hook logic and extract a shared `useXYZ.ts`
  - Replace `prisma.*` patterns (if copied from elsewhere) with SQLAlchemy-based equivalents
  - Upgrade repetitive `response_model=` declarations with dynamic schema handlers

enforcement:
  - Rules should be actionable, agent-readable, and codable.
  - Examples must be pulled from real COS or Pipeline usage.
  - Test patterns should suggest refactor paths and rule creation.
  - Review `task-master expand --id=X` output for emergent sub-patterns.

continuous_improvement:
  - Monitor `task-master next` and phase feedback for meta-patterns
  - Annotate PRs where manual insights could feed agent rule evolution
  - Record insights in `rules/_drafts/` before promotion to `.md.yaml`
  - Update changelog when a rule is created, modified, or deprecated
  - Include “origin” and “impact” metadata when documenting a new rule

note:
  This file governs the *evolution* of the COS mind. It is not static.
  Its job is to recognize patterns, improve them, and teach the system how to self-upgrade.
  If something feels friction-heavy, it's likely a missing rule. If something feels elegant, it's likely a seed for one.
.
