# Cursor Context: Scripts Directory Cleanup (Chat F)

## Sprint Context
**Phase**: 2 Sprint 2 CI Cleanup
**Goal**: Remove quality tool bypasses from scripts/ directory
**Branch**: `feat/cc-goldPh2S2` (development scratch pad)
**Status**: INDEPENDENT - can execute immediately

## Project Overview
COS (Creative Operating System) - FastAPI backend with PostgreSQL, Redis, Neo4j
- **Gold Standard**: cc module in src/backend/cc/
- **Database**: PostgreSQL-only policy (cos_postgres_dev port 5433)
- **Quality Target**: 97% coverage, 0 ruff violations, 0 mypy errors

## Three-Tier Workflow
```
feat/cc-goldPh2S2 → release/phase2-sprint2 → main
(scratch pad)      (CI validation)        (production)
```

## Scripts Directory Targets
**Files to Clean** (estimated 15-20 bypasses total):
- `scripts/generate_module.py` (5+ bypasses)
- `scripts/run_performance_tests.py` (3+ bypasses)
- `scripts/check_mcp_filename_drift.py` (2+ bypasses)
- `scripts/test_*.py` files (remaining bypasses)

## Quality Standards
```bash
# Pre-commit validation (REQUIRED)
uv run pre-commit run --files scripts/[modified_files]

# Type checking
mypy scripts/ --strict

# Linting
ruff check scripts/

# Test script functionality
python scripts/[script_name].py --help  # if applicable
```

## Development Environment
```bash
# Setup commands
cd /path/to/cos
git checkout feat/cc-goldPh2S2
uv sync  # if dependencies needed

# Environment variables (if needed)
export DATABASE_URL_DEV="postgresql+asyncpg://postgres:dev_password@localhost:5433/cos_dev"
export REDIS_URL="redis://localhost:6379"
```

## Bypass Cleanup Strategy
1. **Type annotations**: Add proper typing for function parameters/returns
2. **Import organization**: Fix unused imports, improve import structure
3. **Error handling**: Replace bare excepts, improve exception typing
4. **Code organization**: Remove dead code, improve function structure

## Success Criteria
- ✅ Zero `# noqa` bypasses in scripts/
- ✅ Zero `# type: ignore` bypasses in scripts/
- ✅ All scripts execute without errors
- ✅ Pre-commit hooks pass on all modified files
- ✅ Strict mypy compliance

## Commit Strategy
```bash
# Multiple focused commits
git add scripts/[specific_file]
git commit -m "fix: clean quality bypasses in scripts/[file]

- Remove [X] ruff bypasses
- Add proper type annotations
- Improve error handling"

git push origin feat/cc-goldPh2S2
```

## Context References
- Main coordination: `/PHASE_2_SPRINT_2_COORDINATION.md`
- Project standards: `/CLAUDE.md`
- Architecture: cc module in `src/backend/cc/`

---
**Independence**: Scripts cleanup doesn't depend on test infrastructure fixes
**Duration**: 20-30 minutes estimated
**Platform**: Cursor with Claude Sonnet 4
