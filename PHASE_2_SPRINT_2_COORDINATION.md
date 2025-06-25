# Phase 2 Sprint 2: CI Cleanup Coordination Center

## Current Status: Chat A NEEDS RE-EXECUTION
**Date**: 2025-06-25
**Active Branch**: `feat/cc-goldPh2S2`
**Working Directory**: `/Users/kevinmba/dev/cos`

⚠️ **IMPORTANT**: Chat A completion report was incorrect - tests/conftest.py still has 42 bypasses, not 8 as reported.

## Three-Tier Workflow Established ✅
```
feat/cc-goldPh2S2 (development) → release/phase2-sprint2 (CI validation) → main (production)
```

### Branch Protection Status ✅
- **Main**: Classic protection with lock branch, PR required, status checks, conversation resolution
- **Release/***: Ruleset with automatic pattern protection
- **CI Workflow**: Triggers only on main, release/*, develop (NOT on feat/, fix/, chore/, bug/)

## Multi-Agent Execution Strategy

### Phase 1: Sequential Infrastructure (Claude Code)
**Critical Dependencies - Must be sequential to avoid conflicts**

#### Chat A: Test Infrastructure Foundation ❌ **NEEDS RE-EXECUTION**
- **File**: `tests/conftest.py` (42 bypasses - NO PROGRESS)
- **Impact**: Affects ALL test infrastructure
- **Status**: FAILED - reported completion but no actual changes made
- **Action**: RE-RUN Chat A surgical prompt with proper execution

#### Chat B: Database Migration Layer 🎯 **READY AFTER A**
- **File**: `src/db/migrations/env.py` (13 bypasses)
- **Impact**: Database layer foundation
- **Status**: BLOCKED - waiting for Chat A completion
- **Prompt**: Created and ready

#### Chat C: Core Service Infrastructure
- **Files**: `src/common/redis_config.py` + `src/common/pubsub.py`
- **Impact**: Redis/PubSub core services
- **Status**: BLOCKED - waiting for Chat A+B completion

### Phase 2: Parallel Independent (Cursor + Claude Sonnet 4)
**Can run concurrently after Phase 1 complete**

#### Chat F: Scripts Cleanup 🚀 **IN PROGRESS (Cursor)**
- **Directory**: `scripts/` (3-4 files)
- **Status**: ACTIVE - Cursor working independently
- **Platform**: Cursor + Claude Sonnet 4

#### Chat D: Performance Test Suite
- **Directory**: `tests/performance/` (4-5 files)
- **Status**: BLOCKED - depends on conftest.py (Chat A)

#### Chat E: Unit Test Common
- **Directory**: `tests/unit/common/` (6-8 files)
- **Status**: BLOCKED - depends on conftest.py (Chat A)

#### Chat G: Integration Tests
- **Directory**: `tests/integration/` (remaining files)
- **Status**: BLOCKED - depends on A+B+C completion

## Quality Standards & Context

### Bypass Cleanup Targets
- **Total Identified**: 350+ bypasses across codebase
- **Ruff/noqa**: 150+ instances across 23 files
- **MyPy type ignores**: 100+ instances across 23 files
- **Pytest skips**: 17 instances across 8 files

### Success Criteria
- **Coverage**: Target 97%+ (current: ~40% during infrastructure build)
- **Quality Gates**: 0 ruff violations, 0 mypy errors
- **Test Status**: All tests passing
- **CI Status**: ALL GREEN on release/ branches

## Critical Issue Resolution

### Chat A Failure Analysis
**Problem**: Chat A reported success but made no actual changes
**Evidence**: tests/conftest.py still has 42 bypasses including:
- `# ruff: noqa` (line 1)
- `# mypy: ignore-errors` (line 2)
- Multiple `# type: ignore` throughout

**Solution**: Re-execute Chat A with verified bypass reduction

## Progress Tracking

### Completed ✅
- Branch protection setup (main + release/*)
- CI workflow restructure (three-tier)
- Roadmap documentation
- Multi-agent strategy design

### In Progress 🎯
- Chat F: Scripts cleanup (Cursor independent)

### Failed - Needs Re-execution ❌
- Chat A: tests/conftest.py surgical cleanup

### Blocked ⏳
- Chat B: Database migration cleanup (waiting for Chat A)
- Chat C: Redis/PubSub infrastructure cleanup (waiting for A+B)
- Phase 2: Parallel cleanup (D,E,G) (waiting for Phase 1)

## Recovery Protocol
**If context window restart needed:**
1. Read this coordination file
2. Check git status on feat/cc-goldPh2S2
3. Review recent commits for progress
4. Continue from last pending item
5. Update this file with new progress

## Communication Protocol
**Between Agents:**
- Update this file after each completion
- Commit changes to feat/cc-goldPh2S2
- Report completion status and any blockers discovered
- **VERIFY ACTUAL CHANGES** before marking complete

**Quality Gates:**
- Each agent runs full test suite after changes
- Validates pre-commit hooks pass
- Reports coverage impact
- **COUNT ACTUAL BYPASSES** before/after

---
**Next Action**: RE-EXECUTE Chat A with proper verification
**Context Window**: Phase 1 stays in Claude Code, Phase 2 moves to Cursor
