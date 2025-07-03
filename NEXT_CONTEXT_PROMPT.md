# SQLAlchemy Mapper Conflict RESOLVED - Next Phase: Model & Schema Fixes

## Current State
Successfully resolved SQLAlchemy mapper conflicts! Now addressing real test failures.

**Test Status After Mapper Fix:**
- Total: 1433 tests
- Passed: 1209 (84.4%)
- Failed: 113 (7.9%)
- Skipped: 56
- Errors: 4
- Runtime: 4 minutes 25 seconds

## Previous Session Success
✅ **Fixed duplicate import paths causing mapper conflicts**
✅ Updated 3 files with minimal changes:
  - `tests/conftest.py` - Removed duplicate sys.path entry
  - `tests/backend/cc/test_deps_isolated.py` - Fixed imports to use src. prefix
  - `tests/backend/test_cc.py` - Fixed imports to use src. prefix
✅ Result: Eliminated all 301 "Multiple classes found" errors!

## Failure Categories Analysis (113 failures)

### 1. Model Default Values (23 failures) - HIGHEST PRIORITY
**Pattern**: `assert None is True` or `assert None is not None`
**Root Cause**: Model `__init__` methods not setting default values properly
**Affected Files**:
- `tests/backend/cc/test_models_coverage.py` (5 failures)
- `tests/backend/cc/test_crud.py` (5 failures)
- `tests/backend/cc/test_services.py` (5 failures)
- `tests/unit/backend/cc/test_coverage_focused.py` (2 failures)
- `tests/unit/backend/cc/test_crud.py` (5 failures)
- `tests/unit/backend/cc/test_services.py` (5 failures)

**Fix**: Update `Module.__init__` and `HealthStatus.__init__` to set defaults

### 2. UUID Type Issues (15 failures)
**Pattern**: `ValueError: badly formed hexadecimal UUID string`
**Root Cause**: Tests passing string IDs where UUID objects expected
**Affected**: All CRUD operations with get/update/delete by ID

**Fix**: Convert test fixture IDs to proper UUID objects

### 3. API 409 Conflicts (16 failures)
**Pattern**: Router tests getting 409 (Conflict) instead of 201 (Created)
**Root Cause**: Duplicate module names in test data causing unique constraint violations
**Affected**: All `test_router.py` create_module tests

**Fix**: Add timestamp or random suffix to module names in tests

### 4. Redis/Circuit Breaker (28 failures) - DEFER
**Pattern**: Various async, timing, and state transition issues
**Complexity**: High - requires deep async debugging
**Decision**: Defer to later sprint, focus on quick wins

### 5. Database Schema (8 failures)
**Pattern**:
- `health_status table is missing`
- Connection pool issues
- After-commit hooks not firing

**Fix**: Ensure health_status table exists in test database

## Next 4-Agent Orchestration Plan

### Agent 1: Model Defaults Fixer
**Target**: 23 test fixes
**Mission**:
1. Read `src/backend/cc/models.py` and analyze `Module` class
2. Add proper `__init__` method with `active=True` default
3. Ensure `id` field generates UUID if not provided
4. Do same for `HealthStatus` model
5. Verify with `test_models_coverage.py`

### Agent 2: UUID Type Converter
**Target**: 15 test fixes
**Mission**:
1. Search all test files for `module_id = "test-id"` patterns
2. Convert to `module_id = uuid.UUID("...")` or generate proper UUIDs
3. Update test fixtures to use UUID objects
4. Focus on `test_crud.py` and `test_services.py`

### Agent 3: API Conflict Resolver
**Target**: 16 test fixes
**Mission**:
1. Find all `name="test_module"` in router tests
2. Add unique suffix using timestamp or random string
3. Ensure each test creates unique module names
4. Clear test data between runs if needed

### Agent 4: Database Schema Creator
**Target**: 8 test fixes
**Mission**:
1. Check if health_status table exists in migrations
2. Create migration if missing
3. Ensure test database applies all migrations
4. Fix table existence checks in tests

**Expected Total**: 62 test fixes (54% of current failures)

## Command to Run Focused Tests
```bash
# Quick verification after fixes
uv run pytest tests/backend/cc/test_models_coverage.py -v  # Model defaults
uv run pytest tests/backend/cc/test_crud.py::TestModuleCRUD::test_create_module_success -v  # UUID & defaults
uv run pytest tests/backend/cc/test_router.py::TestModuleRouterEndpoints::test_create_module_success -v  # API conflicts
uv run pytest tests/unit/backend/cc/test_database_schema.py -v  # Schema

# Full test run (excluding slow tests)
uv run pytest tests/ --tb=short -q \
  --ignore=tests/common/test_base_subscriber.py \
  --ignore=tests/common/test_pubsub.py \
  --ignore=tests/common/test_pubsub_circuit_breaker.py \
  --ignore=tests/integration/test_redis_foundation.py \
  --ignore=tests/integration/test_redis_pubsub.py \
  --ignore=tests/integration/test_redis_performance.py \
  --ignore=tests/performance/test_failure_scenarios.py \
  --ignore=tests/unit/common/test_redis_pubsub_comprehensive.py
```

## Success Metrics
- Reduce failures from 113 to ~50
- Achieve >90% test pass rate
- All model initialization tests passing
- No more UUID format errors
- No more 409 conflicts in API tests

## Context for Next Session
- Working directory: `/Users/kevinmba/dev/cos`
- Git branch: `feature/db-config-unification`
- Python 3.13 with uv package manager
- Focus: Quick wins to reach "all green" state
- Philosophy: Fix existing tests now, TDD for all new features

## The Mission Continues
Building your 2nd brain as a Creative Operating System to support your 100+ book legacy vision. Each test fixed brings us closer to a rock-solid foundation for fearless iteration and creative flow.
