# COS Patterns Library

This folder contains the canonical code patterns used across the COS project.

## Purpose
- Each pattern is the current "gold standard" for a class, function, or workflow
- All agents, LLMs, and contributors should reference these files *before* generating or updating code
- Major changes are documented in ADRs (see `.cursor/adr/`)
- When Python or COS upgrades allow new best practices, update the relevant pattern and propagate

## How to Use
1. **Before writing code**: Check here for the relevant pattern
2. **When reviewing code**: Verify it matches our patterns
3. **When improving**: Research, validate, document, then update

## Pattern Files

| Pattern | Purpose | Status | Last Updated |
| `service.py` | Business logic service classes | **In Use** | 2025-07-08 |
| `async_handler.py` | Async FastAPI route handlers | **Pending Research** | 2025-07-08 |
| `error_handling.py` | Exception handling patterns | **In Use** | 2025-07-08 v2.1.0 |
| `dependency_injection.py` | DI and component wiring | **Not Created** | - |
| `model.py` | Pydantic model structure | **Not Created** | - |
| `router.py` | FastAPI router organization | **Not Created** | - |
| `database_operations.py` | Async database patterns | **Not Created** | - |

## Quick Links
- [Pattern Philosophy](./COS_PATTERNS_PHILOSOPHY.md) - Why we use patterns
- [Contributing Patterns](../../../.cursor/adr/) - How to propose changes
- [Migration Guide](../../../.cursor/adr/ADR-001-strangler-refactor-strategy.md) - How we evolve code

## The Pattern Promise
Every pattern here has been:
- ✅ Researched against best practices
- ✅ Tested in real code
- ✅ Documented with examples
- ✅ Approved through ADR process

## Remember
**Always Pattern-First**: Check here before writing any code. If a pattern doesn't exist or seems outdated, that's your cue to research and propose an improvement!
