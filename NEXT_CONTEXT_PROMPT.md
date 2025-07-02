# Continue COS Test Suite Fixes - Phase 2 Sprint 2

## Current State
Working on COS (Creative Operating System) Phase 2 Sprint 2 Redis implementation. Goal is to achieve "all green" test suite for true TDD workflow.

## Test Suite Status (as of last run)
- **Total:** 1252 tests (excluding slow tests)
- **Passed:** 846 (67.6%)
- **Failed:** 298 (23.8%)
- **Runtime:** 92 seconds

## Progress Made in Previous Session
1. ✅ Fixed Redis event loop bindings in test_redis_performance_simplified.py
2. ✅ Fixed circuit breaker timing issues (8 failures)
3. ✅ Fixed L1 event publishing mocks (8 failures)
4. ✅ Fixed database connection issues (15 failures)
5. ✅ Fixed API endpoint 404 errors (10 failures) - Key fixes:
   - Fixed SQLAlchemy model duplicate registration (changed imports to use `src.` prefix consistently)
   - Fixed event loop issues by setting `RUN_INTEGRATION=0` early in conftest.py
   - Fixed pytest-asyncio configuration by adding class-level decorators

## Key Files Modified
1. `/src/cos_main.py` - Fixed import order and made imports consistent with `src.` prefix
2. `/src/backend/cc/mem0_models.py` - Updated relationship definitions to use fully qualified paths
3. `/tests/conftest.py` - Added `os.environ["RUN_INTEGRATION"] = RUN_INTEGRATION_MODE` early
4. `/tests/backend/cc/test_router.py` - Added `@pytest.mark.asyncio` at class level

## Slow Tests to Exclude
```bash
# Add these to pytest command with --ignore flag:
tests/common/test_base_subscriber.py
tests/common/test_pubsub.py  # excruciatingly slow
tests/common/test_pubsub_circuit_breaker.py  # slow
tests/integration/test_redis_foundation.py  # slow
tests/integration/test_redis_pubsub.py  # slow
tests/integration/test_redis_performance.py  # slow with many failures
tests/performance/test_failure_scenarios.py  # slow with many failures
tests/unit/common/test_redis_pubsub_comprehensive.py  # slow and long
```

## Critical Issue: Redis Pausing
**IMPORTANT**: Redis pauses during some tests and doesn't resume automatically. User has to manually hit play button in Docker Desktop. This happens multiple times during test runs. This might be a HIGH PRIORITY to fix before other test failures. However this seems to occur during the tests we are skipping, perhaps run these skipped tests only to figure out if its within those these or else where?

## Command to Run Tests (excluding slow ones)
```bash
uv run pytest --tb=short -q \
  --ignore=tests/common/test_base_subscriber.py \
  --ignore=tests/common/test_pubsub.py \
  --ignore=tests/common/test_pubsub_circuit_breaker.py \
  --ignore=tests/integration/test_redis_foundation.py \
  --ignore=tests/integration/test_redis_pubsub.py \
  --ignore=tests/integration/test_redis_performance.py \
  --ignore=tests/performance/test_failure_scenarios.py \
  --ignore=tests/unit/common/test_redis_pubsub_comprehensive.py
```

## Main Areas Still Needing Fixes
1. **test_crud.py** - 15 failures (database CRUD operations)
2. **test_log_l1.py** - 23 failures (L1 logging functionality)
3. **test_mem0_crud.py** - 21 failures (mem0 CRUD operations)
4. **test_mem0_router.py** - many failures (mem0 API endpoints)
5. **test_mem0_service.py** - many failures (mem0 service layer)
6. **test_services.py** - 16 failures (CC service layer)
7. **test_models_coverage.py** - many failures (model test coverage)

## Next Steps
1. Consider investigating Redis pausing issue first (might be causing cascading failures)
2. Fix remaining database operation failures (likely similar issues to what was already fixed)
3. Continue toward "all green" state for true TDD workflow

## Context
- Working directory: `/Users/kevinmba/dev/cos`
- Python 3.13 with uv package manager
- Using mock mode for tests (`RUN_INTEGRATION=0`)
- Goal: Achieve 100% green tests to enable fearless refactoring

## Instructions for Next Session
Please continue fixing the test failures without asking questions. Start by running the test suite with the slow tests excluded to see current state, then prioritize either:
1. The Redis pausing issue (if it seems to be causing other failures)
2. The database operation failures in the order listed above

Remember: The goal is "all green" to enable true TDD workflow where we can refactor without fear.
