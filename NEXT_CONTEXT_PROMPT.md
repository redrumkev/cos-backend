# Continue COS Test Suite Fixes - Phase 2 Sprint 2

## Current State
Working on COS (Creative Operating System) Phase 2 Sprint 2 Redis implementation. Goal is to achieve "all green" test suite for true TDD workflow.

**Last Commit:** 26ee4947 - 🔧 Fix API endpoint 404 errors: 16 router tests now passing

## Test Suite Status (as of current run)
- **Total:** 1252 tests (excluding slow tests)
- **Passed:** 849 (67.8%)
- **Failed:** 295 (23.6%)
- **Runtime:** 92 seconds
- **Note:** Many tests pass individually but fail when run as collection due to test isolation issues

## Progress Made in Previous Session
1. ✅ Fixed Redis event loop bindings in test_redis_performance_simplified.py
2. ✅ Fixed circuit breaker timing issues (8 failures)
3. ✅ Fixed L1 event publishing mocks (8 failures)
4. ✅ Fixed database connection issues (15 failures)
5. ✅ Fixed API endpoint 404 errors (10 failures) - Key fixes:
   - Fixed SQLAlchemy model duplicate registration (changed imports to use `src.` prefix consistently)
   - Fixed event loop issues by setting `RUN_INTEGRATION=0` early in conftest.py
   - Fixed pytest-asyncio configuration by adding class-level decorators

## Progress Made in Current Session
1. ✅ Fixed test_cos_main_coverage.py startup log event test (1 failure)
2. ✅ Fixed test_circuit_breaker.py state reset test (1 failure)
3. ✅ Fixed test_circuit_breaker_edge.py success threshold test (1 failure)
4. ✅ Discovered that many reported failures in NEXT_CONTEXT_PROMPT were already fixed
5. ✅ Reduced failures from 298 to 294
6. ✅ Created comprehensive 5-phase plan to fix test isolation issues
7. ✅ Phase 1 Complete: Removed session-scoped event loops, standardized to function scope
8. ✅ Phase 2 Complete: Converted global variables to fixtures, fixed environment variable isolation with monkeypatch
9. 🔄 Phase 3 In Progress: Working on Redis and database state isolation

## Key Files Modified in Current Session
1. `/tests/unit/test_cos_main_coverage.py` - Fixed log_event test to use monkeypatch
2. `/tests/unit/common/test_circuit_breaker.py` - Fixed state reset test to ensure state transition
3. `/tests/unit/common/test_circuit_breaker_edge.py` - Fixed success threshold test for threshold=1 case
4. `/tests/conftest.py` - Added fixtures for test isolation, removed session-scoped fixtures
5. `/tests/conftest_db.py` - Changed postgres_engine to function scope
6. `/tests/unit/common/conftest.py` - Removed session-scoped event loop, updated fake_redis
7. `/tests/common/test_config.py` - Fixed to use monkeypatch for env variables
8. `/tests/backend/cc/test_log_l1_simple.py` - Fixed to use monkeypatch
9. `/tests/common/test_database.py` - Fixed to use monkeypatch
10. `/tests/backend/cc/test_mem0_models.py` - Fixed to use monkeypatch
11. `/tests/backend/cc/test_logfire_instrumentation.py` - Fixed fixtures to use monkeypatch

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

## Critical Issue: Test Isolation
**ROOT CAUSE IDENTIFIED**: Tests pass individually but fail when run as a collection due to:
- Event loop scope conflicts (✅ Fixed)
- Global state variables (✅ Fixed)
- Environment variable pollution (✅ Fixed)
- Redis state leakage between tests (🔄 In Progress)
- Database session isolation (🔄 In Progress)
- SQLAlchemy mapper registration conflicts

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

## Main Areas Still Needing Fixes (Updated)
1. **Circuit breaker and pubsub tests** - Various timing and race condition issues
2. **Base subscriber tests** - Timeout and batch handling issues
3. **Enhanced error handling tests** - Serialization and recovery tests
4. **Performance benchmarks** - Database connection pool tests (3 errors)
5. **Unit test database schema** - Missing health_status table
6. **Logging Redis publish tests** - After-commit hooks not firing

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
Continue with the test isolation fixes:

1. **SQLAlchemy Mapper Conflicts**: The main remaining issue is SQLAlchemy mapper registration conflicts. Tests pass individually but fail when run together due to models being registered multiple times or relationships not being properly resolved.

2. **Recommended Approach**:
   - Clear SQLAlchemy registries between tests
   - Ensure models are imported only once per test session
   - Fix the relationship back_populates issues in mem0_models.py
   - Consider using a fresh MetaData instance per test

3. **After Fixing Mapper Issues**:
   - Continue with Phase 4: Dynamic port allocation
   - Phase 5: Cleanup hooks
   - Run tests with --randomly-seed to verify no order dependencies

Remember: The goal is "all green" to enable true TDD workflow where we can refactor without fear.
