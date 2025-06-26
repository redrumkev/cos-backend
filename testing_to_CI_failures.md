# COS Testing Infrastructure Failures Analysis

**Context**: Post-infinite loop fix validation from PR to 'release/phase2-sprint2' from 'feat/cc-goldPh2S2'
**Date**: January 26, 2025
**Branch State**: feat/cc-goldPh2S2 with recent base subscriber timeout fixes
**Test Environment**: GitHub Actions CI with full service stack (PostgreSQL, Redis, Neo4j)

## Executive Summary

### 🚨 Critical Issues Identified

**Primary Failure**: Coverage at 62% vs required 90% threshold (-28% gap)
**Test Results**: 134 failed, 622 passed, 391 skipped, 241 errors
**Root Causes**: Infrastructure misalignment, SQLAlchemy conflicts, mock pattern inconsistencies

### 🔍 Failure Pattern Analysis

#### **1. SQLAlchemy Registry Conflicts (High Impact)**
- **Pattern**: `Multiple classes found for path "PromptTrace"` - 13 failures
- **Root Cause**: Declarative base registry pollution across test modules
- **Impact**: Blocks all L1 logging and mem0 functionality tests
- **Priority**: CRITICAL - Foundation infrastructure

#### **2. Mock Infrastructure Inconsistencies (High Impact)**
- **Pattern**: `correlation_id` parameter mismatches - 6 failures
- **Root Cause**: Updated function signatures not reflected in test expectations
- **Impact**: Redis publishing and L1 event integration broken
- **Priority**: CRITICAL - Core pipeline functionality

#### **3. Database Connection Architecture (Medium Impact)**
- **Pattern**: `'_DummyConn' object has no attribute 'prepare'` - Multiple failures
- **Root Cause**: Test database mock vs real database connection mismatch
- **Impact**: All database-dependent tests failing in CI environment
- **Priority**: HIGH - Test infrastructure foundation

#### **4. Logfire Integration Misalignment (Medium Impact)**
- **Pattern**: FastAPI instrumentation and request attribute mapping failures
- **Root Cause**: Test environment vs production Logfire configuration drift
- **Impact**: Observability and tracing tests unreliable
- **Priority**: MEDIUM - Monitoring infrastructure

#### **5. Base Subscriber Timeout Integration (Low Impact)**
- **Pattern**: Recent timeout fixes creating new test failures
- **Root Cause**: Test expectations not updated for new timeout behavior
- **Impact**: Limited to subscriber functionality tests
- **Priority**: LOW - Already partially addressed

### 📊 Coverage Gap Contributors

**Major Coverage Gaps (scripts/ and graph/ modules):**
- `scripts/check_mcp_filename_drift.py`: 0% coverage
- `scripts/run_performance_tests.py`: 0% coverage
- `src/graph/background.py`: 10% coverage
- `src/graph/service.py`: 14% coverage

**Module Performance vs Targets:**
- **Strong Performers**: `common/` modules (85-100% coverage)
- **Moderate Performers**: `backend/cc/` modules (24-98% mixed)
- **Critical Gaps**: `graph/` and performance infrastructure

### 🎯 Strategic Recommendations (AI Coder Optimized Timeline)

#### **Phase 1: Foundation Stabilization (1-2 Days)**
1. **SQLAlchemy Registry Cleanup**: Implement proper test isolation
2. **Mock Infrastructure Alignment**: Update all test signatures
3. **Database Connection Standardization**: Resolve `_DummyConn` vs real DB

#### **Phase 2: Coverage Recovery (2-3 Days)**
1. **P2-* Skip Removal**: Apply proven systematic method (47 tests in <1 day precedent)
2. **Scripts Module Testing**: Enable 0% coverage modules (already proven method)
3. **Graph Module Implementation**: Address 10-31% coverage gaps

#### **Phase 3: Pipeline Validation (1 Day)**
1. **Integration Test Restoration**: Fix performance and infrastructure tests
2. **L1→L2 Memory Pipeline**: End-to-end validation
3. **Performance Benchmarking**: Restore production-readiness validation

**Total Timeline: 3-5 days to 90%+ coverage** (based on proven P2-* methodology completing 47 tests in <1 working day)

### 🔥 Immediate Next Actions

**Priority 1**: Fix SQLAlchemy declarative base registry conflicts
**Priority 2**: Update mock signatures for correlation_id parameters
**Priority 3**: Resolve database connection architecture in CI environment
**Priority 4**: Restore scripts/ module test coverage from 0% baseline

**Success Criteria**: Achieve 90%+ coverage with <10 test failures for next iteration.

---

## 🧠 AI Coder Context: Critical Insights Beyond Training Data

**For Future AI Coders**: This context contains proven systematic solutions specific to this codebase that go beyond general debugging training data.

### **Proven P2-* Methodology (Validated <1 Day Success)**
- **Sprint 1 DELTA**: P2-SCRIPTS-001 eliminated (23 tests, 99% scripts coverage)
- **Sprint 1 EPSILON**: P2-UTILS-001 eliminated (21 tests, config reload fixes)
- **Sprint 1 ZETA**: P2-DB-001 eliminated (3 tests, IN_TEST_MODE timing fixes)
- **Result**: 41% → 53% coverage (+12%) in <1 working day
- **Method**: Remove skip decorators first, then fix infrastructure systematically

### **Environment-Specific Context (Critical for Success)**
- **Platform**: Windows with PowerShell, UV package manager (not pip)
- **Database**: PostgreSQL port 5433 (not default 5432), credentials: cos_user:Police9119!!Sql_dev
- **Git Flow**: feat/cc-goldPh2S2 → release/phase2-sprint2 → main
- **Redis**: localhost:6379 for pub/sub with channel naming `mem0.recorded.cc`
- **Test Commands**: Always `uv run pytest`, never bare `pytest`

### **Specific Failure Patterns with Exact Solutions**

#### **Pattern 1: SQLAlchemy Registry Conflicts (13 failures)**
```
Error: "Multiple classes found for path 'PromptTrace' in the registry of this declarative base"
Root Cause: Declarative base pollution across test modules
Location: L1 logging and mem0 functionality tests
Solution: Implement proper test isolation in conftest.py
```

#### **Pattern 2: Mock Infrastructure Inconsistencies (6 failures)**
```
Error: correlation_id parameter mismatches
Example: Expected: publish('mem0.recorded.cc', {...})
         Actual: publish('mem0.recorded.cc', {...}, correlation_id='...')
Root Cause: Function signatures updated, test expectations not updated
Solution: Systematic mock signature updates in test files
```

#### **Pattern 3: Database Connection Architecture (Multiple failures)**
```
Error: "'_DummyConn' object has no attribute 'prepare'"
Root Cause: Test database mock vs real database connection mismatch
Environment: CI vs local development setup differences
Solution: Standardize connection architecture for test environment
```

### **Codebase-Specific Technical Context**
- **Coverage Calculation**: 391 skipped tests = 0% coverage contribution (removing skips = immediate coverage boost)
- **Test Structure**: 1147 total tests (134 failed + 622 passed + 391 skipped)
- **Success Pattern**: Systematic fixes resolve multiple tests simultaneously (not 1:1 debugging)
- **Infinite Loop Fix**: Base subscriber timeout mechanism already implemented (recent fix)

**Key Insight**: This codebase responds exceptionally well to systematic pattern-based fixes rather than individual test debugging. The P2-* methodology is proven and should be applied to remaining patterns.

---

## Detailed Failure Analysis

The following was from a PR to 'release/phase2-sprint2' from 'feat/cc-goldPh2S2' with a batch of our in process tests that were removed of "skips"

ERROR: Coverage failure: total of 62 is less than fail-under=90
================================ tests coverage ================================
_______________ coverage: platform linux, python 3.13.5-final-0 ________________
Name                                  Stmts   Miss  Cover   Missing
-------------------------------------------------------------------
scripts/check_mcp_filename_drift.py       7      7     0%   13-34
scripts/generate_module.py              146     12    92%   89-90, 129-130, 180-181, 222-227, 301-302
scripts/run_performance_tests.py        201    201     0%   10-411
src/__init__.py                           0      0   100%
src/backend/__init__.py                   0      0   100%
src/backend/cc/__init__.py                0      0   100%
src/backend/cc/background.py             64     53    17%   21-88, 100-161, 174, 179, 185-212
src/backend/cc/cc_main.py                68      5    93%   35-37, 80, 147
src/backend/cc/crud.py                   59     40    32%   69-88, 113-122, 147-158, 180-189, 211-220, 243-252, 275-291, 313-328
src/backend/cc/deps.py                   11      0   100%
src/backend/cc/logging.py               109     46    58%   192-201, 214-219, 223-290
src/backend/cc/mem0_crud.py              77     64    17%   21-25, 30-32, 37-39, 46-57, 64-78, 83-89, 94-125, 130-140, 145-150
src/backend/cc/mem0_models.py            76     11    86%   41, 76-81, 86, 90, 150, 217, 293
src/backend/cc/mem0_router.py            61     35    43%   23-29, 35-38, 44-47, 59-60, 66-69, 75-78, 84-85, 92-93, 99-102, 108-111
src/backend/cc/mem0_service.py           63     48    24%   26-40, 45-54, 59-68, 76-98, 105-119, 124-133, 138-183, 188-206
src/backend/cc/models.py                 63     24    62%   31-34, 37-40, 43-46, 55, 76-80, 84, 106-112, 116
src/backend/cc/router.py                184     95    48%   133-179, 198-255, 315-385, 397-443, 469-576
src/backend/cc/schemas.py               159      3    98%   182, 236, 241
src/backend/cc/services.py               62     35    44%   35-41, 83-105, 131-142, 216-229, 251-258, 280-287, 310-317, 344-357, 379-386
src/common/__init__.py                    0      0   100%
src/common/base_subscriber.py           259     23    91%   31-40, 136, 224, 251-252, 273, 278, 305, 312, 485, 498-500, 506-509, 517-518
src/common/config.py                     37      0   100%
src/common/database.py                   76     34    55%   49-50, 64, 75-98, 111, 118-125, 130-135, 140-142
src/common/ledger_view.py                72      0   100%
src/common/logger.py                     26      0   100%
src/common/logger_logfire.py             38      4    89%   14, 23-26
src/common/message_format.py             48      5    90%   28-29, 113, 166, 168
src/common/pubsub.py                    516     54    90%   30, 39-41, 89-91, 227, 359-361, 415, 418, 493, 704-712, 717, 728-737, 769-770, 794-805, 884, 958-968, 1077-1079
src/common/redis_config.py               92     19    79%   29-31, 72, 80, 88, 96, 104, 150-162
src/common/request_id_middleware.py      37      2    95%   34-35
src/cos_main.py                          14      0   100%
src/db/__init__.py                        0      0   100%
src/db/base.py                            9      0   100%
src/db/connection.py                     45      9    80%   30-31, 35-39, 53-54
src/db/migrations/env.py                 76     29    62%   34-35, 46-48, 52-53, 66-69, 80-86, 89, 110-115, 120-127, 137-143, 147
src/graph/__init__.py                     0      0   100%
src/graph/background.py                 125    112    10%   17-97, 102-243, 248-320, 326, 331, 336, 342-369, 374-401
src/graph/base.py                       113     78    31%   31-32, 55-56, 67-72, 76-107, 111-115, 124-139, 144-160, 164-192, 197, 203-211, 218-227, 232-244, 252-254, 262-263
src/graph/registry.py                    72     30    58%   66, 82-83, 103-107, 127-130, 161-171, 181, 186, 191, 208-240, 251
src/graph/router.py                     136     68    50%   99, 106-117, 125-129, 136-144, 155-164, 176-185, 197-206, 219-225, 237-243, 252-267, 280-284, 291-293
src/graph/service.py                    115     99    14%   19, 43-69, 85-93, 113-119, 138-168, 187-219, 250-281, 306-327, 353-385, 389-390, 405-420
-------------------------------------------------------------------
TOTAL                                  3316   1245    62%
Coverage HTML written to dir htmlcov
Coverage XML written to file coverage.xml
Coverage JSON written to file coverage.json
FAIL Required test coverage of 90% not reached. Total coverage: 62.45%
--------------------------------------------------- benchmark 'latency': 1 tests ---------------------------------------------------
Name (time in us)                     Min          Max     Mean   StdDev  Median     IQR  Outliers  OPS (Kops/s)  Rounds  Iterations
------------------------------------------------------------------------------------------------------------------------------------
test_publish_latency_benchmark     8.0650  13,445.3310  10.3299  51.0036  9.3070  1.4930   15;5745       96.8064   95552           1
------------------------------------------------------------------------------------------------------------------------------------
------------------------------------------- benchmark 'log_l1_baseline': 1 tests ------------------------------------------
Name (time in us)                   Min     Max    Mean  StdDev  Median     IQR  Outliers  OPS (Kops/s)  Rounds  Iterations
---------------------------------------------------------------------------------------------------------------------------
test_log_l1_baseline_minimal     1.6105  3.8879  2.5042  0.8959  2.4198  1.5860       1;0      399.3344      10         100
---------------------------------------------------------------------------------------------------------------------------
---------------------------------------------------------------------------------- benchmark 'log_l1_latency': 3 tests -----------------------------------------------------------------------------------
Name (time in us)                            Min               Max              Mean            StdDev            Median               IQR            Outliers  OPS (Kops/s)            Rounds  Iterations
----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
test_log_l1_latency_prompt_only           1.6097 (1.0)      1.8219 (1.04)     1.6455 (1.0)      0.0641 (1.56)     1.6255 (1.0)      0.0205 (1.0)           1;2      607.7084 (1.0)          10         100
test_log_l1_latency_event_only            1.6198 (1.01)     1.7571 (1.01)     1.6484 (1.00)     0.0411 (1.0)      1.6371 (1.01)     0.0295 (1.43)          1;1      606.6448 (1.00)         10         100
test_log_l1_latency_combined_scenario     1.6303 (1.01)     1.7466 (1.0)      1.6601 (1.01)     0.0423 (1.03)     1.6400 (1.01)     0.0261 (1.27)          2;2      602.3599 (0.99)         10         100
----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
----------------------------------------------- benchmark 'log_l1_stress': 1 tests -----------------------------------------------
Name (time in us)                          Min     Max    Mean  StdDev  Median     IQR  Outliers  OPS (Kops/s)  Rounds  Iterations
----------------------------------------------------------------------------------------------------------------------------------
test_log_l1_performance_consistency     1.5955  2.1688  1.7986  0.2363  1.6859  0.3718       2;0      555.9902      10         100
----------------------------------------------------------------------------------------------------------------------------------
Legend:
  Outliers: 1 Standard Deviation from Mean; 1.5 IQR (InterQuartile Range) from 1st Quartile and 3rd Quartile.
  OPS: Operations Per Second, computed as 1 / Mean
=========================== short test summary info ============================
FAILED tests/backend/cc/test_log_l1.py::TestLogL1Performance::test_log_l1_latency_event_only - sqlalchemy.exc.InvalidRequestError: Multiple classes found for path "PromptTrace" in the registry of this declarative base. Please use a fully module-qualified path.
FAILED tests/backend/cc/test_log_l1.py::TestLogL1Performance::test_log_l1_latency_prompt_only - sqlalchemy.exc.InvalidRequestError: One or more mappers failed to initialize - can't proceed with initialization of other mappers. Triggering mapper: 'Mapper[BaseLog(base_log)]'. Original exception was: Multiple classes found for path "PromptTrace" in the registry of this declarative base. Please use a fully module-qualified path.
FAILED tests/backend/cc/test_log_l1.py::TestLogL1Performance::test_log_l1_latency_combined_scenario - sqlalchemy.exc.InvalidRequestError: One or more mappers failed to initialize - can't proceed with initialization of other mappers. Triggering mapper: 'Mapper[BaseLog(base_log)]'. Original exception was: Multiple classes found for path "PromptTrace" in the registry of this declarative base. Please use a fully module-qualified path.
FAILED tests/backend/cc/test_log_l1.py::TestLogL1Performance::test_log_l1_baseline_minimal - sqlalchemy.exc.InvalidRequestError: One or more mappers failed to initialize - can't proceed with initialization of other mappers. Triggering mapper: 'Mapper[BaseLog(base_log)]'. Original exception was: Multiple classes found for path "PromptTrace" in the registry of this declarative base. Please use a fully module-qualified path.
FAILED tests/backend/cc/test_log_l1.py::TestLogL1Performance::test_log_l1_performance_consistency - sqlalchemy.exc.InvalidRequestError: One or more mappers failed to initialize - can't proceed with initialization of other mappers. Triggering mapper: 'Mapper[BaseLog(base_log)]'. Original exception was: Multiple classes found for path "PromptTrace" in the registry of this declarative base. Please use a fully module-qualified path.
FAILED tests/backend/cc/test_log_l1_simple.py::test_simple_log_creation - sqlalchemy.exc.InvalidRequestError: One or more mappers failed to initialize - can't proceed with initialization of other mappers. Triggering mapper: 'Mapper[BaseLog(base_log)]'. Original exception was: Multiple classes found for path "PromptTrace" in the registry of this declarative base. Please use a fully module-qualified path.
FAILED tests/backend/cc/test_logfire_instrumentation.py::TestFastAPIInstrumentation::test_instrument_fastapi_app_error - AssertionError: assert 'Failed to apply FastAPI auto-instrumentation' in 'ERROR    src.backend.cc.cc_main:cc_main.py:118 Failed to instrument FastAPI application: Instrumentation failed\n'
 +  where 'ERROR    src.backend.cc.cc_main:cc_main.py:118 Failed to instrument FastAPI application: Instrumentation failed\n' = <_pytest.logging.LogCaptureFixture object at 0x7f17d4827bd0>.text
FAILED tests/backend/cc/test_logfire_instrumentation.py::TestFastAPIInstrumentation::test_request_attributes_mapper_functionality - AssertionError: assert 'client_host' in {'user_agent': 'test-agent', 'client_ip': '127.0.0.1'}
FAILED tests/backend/cc/test_logfire_instrumentation.py::TestFastAPIInstrumentation::test_request_attributes_mapper_missing_headers - AssertionError: assert None == 'unknown'
 +  where None = <built-in method get of dict object at 0x7f17d61fea80>('client_host')
 +    where <built-in method get of dict object at 0x7f17d61fea80> = {'user_agent': 'unknown', 'client_ip': 'unknown'}.get
FAILED tests/backend/cc/test_logfire_instrumentation.py::TestLifespanIntegration::test_lifespan_startup_partial_failure - AssertionError: assert 'Failed to apply FastAPI auto-instrumentation' in 'INFO     src.backend.cc.cc_main:cc_main.py:59 Logfire initialized successfully for FastAPI auto-instrumentation\nERROR    src.backend.cc.cc_main:cc_main.py:118 Failed to instrument FastAPI application: Instrumentation error\n'
 +  where 'INFO     src.backend.cc.cc_main:cc_main.py:59 Logfire initialized successfully for FastAPI auto-instrumentation\nERROR    src.backend.cc.cc_main:cc_main.py:118 Failed to instrument FastAPI application: Instrumentation error\n' = <_pytest.logging.LogCaptureFixture object at 0x7f17d5b37b50>.text
FAILED tests/backend/cc/test_logfire_instrumentation.py::TestIntegrationScenarios::test_cc_app_health_endpoint_functionality - AttributeError: '_DummyConn' object has no attribute 'prepare'
FAILED tests/backend/cc/test_logfire_instrumentation.py::TestIntegrationScenarios::test_error_handling_preserves_app_functionality - AttributeError: '_DummyConn' object has no attribute 'prepare'
FAILED tests/backend/cc/test_mem0_models.py::TestScratchNoteModel::test_scratch_note_creation_basic - sqlalchemy.exc.InvalidRequestError: One or more mappers failed to initialize - can't proceed with initialization of other mappers. Triggering mapper: 'Mapper[BaseLog(base_log)]'. Original exception was: Multiple classes found for path "PromptTrace" in the registry of this declarative base. Please use a fully module-qualified path.
FAILED tests/backend/cc/test_mem0_models.py::TestScratchNoteModel::test_scratch_note_creation_with_ttl - sqlalchemy.exc.InvalidRequestError: One or more mappers failed to initialize - can't proceed with initialization of other mappers. Triggering mapper: 'Mapper[BaseLog(base_log)]'. Original exception was: Multiple classes found for path "PromptTrace" in the registry of this declarative base. Please use a fully module-qualified path.
FAILED tests/backend/cc/test_mem0_models.py::TestScratchNoteModel::test_scratch_note_expiration_check - sqlalchemy.exc.InvalidRequestError: One or more mappers failed to initialize - can't proceed with initialization of other mappers. Triggering mapper: 'Mapper[BaseLog(base_log)]'. Original exception was: Multiple classes found for path "PromptTrace" in the registry of this declarative base. Please use a fully module-qualified path.
FAILED tests/backend/cc/test_mem0_models.py::TestScratchNoteModel::test_scratch_note_repr - sqlalchemy.exc.InvalidRequestError: One or more mappers failed to initialize - can't proceed with initialization of other mappers. Triggering mapper: 'Mapper[BaseLog(base_log)]'. Original exception was: Multiple classes found for path "PromptTrace" in the registry of this declarative base. Please use a fully module-qualified path.
FAILED tests/backend/cc/test_models.py::TestHealthStatusModel::test_instance_creation - sqlalchemy.exc.InvalidRequestError: One or more mappers failed to initialize - can't proceed with initialization of other mappers. Triggering mapper: 'Mapper[BaseLog(base_log)]'. Original exception was: Multiple classes found for path "PromptTrace" in the registry of this declarative base. Please use a fully module-qualified path.
FAILED tests/backend/cc/test_models.py::TestHealthStatusModel::test_repr - sqlalchemy.exc.InvalidRequestError: One or more mappers failed to initialize - can't proceed with initialization of other mappers. Triggering mapper: 'Mapper[BaseLog(base_log)]'. Original exception was: Multiple classes found for path "PromptTrace" in the registry of this declarative base. Please use a fully module-qualified path.
FAILED tests/backend/cc/test_models.py::TestModuleModel::test_instance_creation - sqlalchemy.exc.InvalidRequestError: One or more mappers failed to initialize - can't proceed with initialization of other mappers. Triggering mapper: 'Mapper[BaseLog(base_log)]'. Original exception was: Multiple classes found for path "PromptTrace" in the registry of this declarative base. Please use a fully module-qualified path.
FAILED tests/backend/cc/test_models.py::TestModuleModel::test_repr - sqlalchemy.exc.InvalidRequestError: One or more mappers failed to initialize - can't proceed with initialization of other mappers. Triggering mapper: 'Mapper[BaseLog(base_log)]'. Original exception was: Multiple classes found for path "PromptTrace" in the registry of this declarative base. Please use a fully module-qualified path.
FAILED tests/common/test_base_subscriber.py::TestMessageProcessing::test_message_processing_failure - KeyError: "Attempt to overwrite 'message' in LogRecord"
FAILED tests/common/test_base_subscriber.py::TestCircuitBreakerIntegration::test_circuit_breaker_protection - ValueError: Simulated processing failure
FAILED tests/common/test_base_subscriber.py::TestDeadLetterQueue::test_dlq_error_handling - KeyError: "Attempt to overwrite 'message' in LogRecord"
FAILED tests/common/test_base_subscriber.py::TestConcurrencyControl::test_timeout_handling - KeyError: "Attempt to overwrite 'message' in LogRecord"
FAILED tests/common/test_base_subscriber.py::TestSubscribeToChannelIterator::test_subscribe_to_channel_basic - StopAsyncIteration
FAILED tests/common/test_base_subscriber.py::TestAsyncTimeoutIntegration::test_asyncio_wait_for_fallback - KeyError: "Attempt to overwrite 'message' in LogRecord"
FAILED tests/common/test_database.py::test_async_engine_connection_failure_logs_rich_error - AssertionError: No rich error log with emoji/color found.
assert False
FAILED tests/common/test_pubsub.py::TestRedisPubSub::test_connect_success - AttributeError: module 'src.common.pubsub' has no attribute 'aioredis'
FAILED tests/common/test_pubsub.py::TestRedisPubSub::test_publish_not_connected - AssertionError: Expected 'connect' to have been called once. Called 0 times.
FAILED tests/common/test_pubsub.py::TestRedisPubSub::test_subscribe_not_connected - AttributeError: 'coroutine' object has no attribute 'subscribe'
FAILED tests/common/test_pubsub.py::TestRedisPubSub::test_get_subscribers_count_not_connected - AssertionError: Expected 'connect' to have been called once. Called 0 times.
FAILED tests/common/test_pubsub.py::TestGlobalFunctions::test_get_pubsub_singleton - AttributeError: module 'src.common.pubsub' has no attribute 'aioredis'
FAILED tests/common/test_pubsub.py::TestGlobalFunctions::test_cleanup_pubsub - AttributeError: module 'src.common.pubsub' has no attribute 'aioredis'
FAILED tests/common/test_pubsub_circuit_breaker.py::TestRedisPubSubCircuitBreaker::test_connect_failure_triggers_circuit_breaker - AssertionError: assert <CircuitBreakerState.CLOSED: 'closed'> == <CircuitBreakerState.OPEN: 'open'>
 +  where <CircuitBreakerState.CLOSED: 'closed'> = <src.common.pubsub.CircuitBreaker object at 0x7f17d4b57e10>.state
 +    where <src.common.pubsub.CircuitBreaker object at 0x7f17d4b57e10> = <src.common.pubsub.RedisPubSub object at 0x7f17d4b3f890>._circuit_breaker
 +  and   <CircuitBreakerState.OPEN: 'open'> = CircuitBreakerState.OPEN
FAILED tests/common/test_pubsub_circuit_breaker.py::TestRedisPubSubCircuitBreaker::test_publish_failure_opens_circuit_breaker - AssertionError: assert <CircuitBreakerState.CLOSED: 'closed'> == <CircuitBreakerState.OPEN: 'open'>
 +  where <CircuitBreakerState.CLOSED: 'closed'> = <src.common.pubsub.CircuitBreaker object at 0x7f17d4b56a90>.state
 +    where <src.common.pubsub.CircuitBreaker object at 0x7f17d4b56a90> = <src.common.pubsub.RedisPubSub object at 0x7f17d4b3f7f0>._circuit_breaker
 +  and   <CircuitBreakerState.OPEN: 'open'> = CircuitBreakerState.OPEN
FAILED tests/common/test_pubsub_circuit_breaker.py::TestRedisPubSubCircuitBreaker::test_circuit_breaker_recovery - AssertionError: assert <CircuitBreakerState.CLOSED: 'closed'> == <CircuitBreakerState.OPEN: 'open'>
 +  where <CircuitBreakerState.CLOSED: 'closed'> = <src.common.pubsub.CircuitBreaker object at 0x7f17d4b964e0>.state
 +    where <src.common.pubsub.CircuitBreaker object at 0x7f17d4b964e0> = <src.common.pubsub.RedisPubSub object at 0x7f17d4a11e50>._circuit_breaker
 +  and   <CircuitBreakerState.OPEN: 'open'> = CircuitBreakerState.OPEN
FAILED tests/common/test_pubsub_simple.py::TestRedisPubSubCore::test_connect_success - AttributeError: module 'src.common.pubsub' has no attribute 'aioredis'
FAILED tests/common/test_pubsub_simple.py::TestRedisPubSubCore::test_publish_json_error - AssertionError: Regex pattern did not match.
 Regex: 'Failed to publish message'
 Input: 'Unexpected publish error: Failed to serialize message: Object of type NonSerializable is not JSON serializable'
FAILED tests/common/test_pubsub_simple.py::TestGlobalFunctions::test_get_pubsub_singleton - AttributeError: module 'src.common.pubsub' has no attribute 'aioredis'
FAILED tests/db/test_alembic_migrations.py::test_upgrade_idempotent - sqlalchemy.exc.OperationalError: (psycopg.OperationalError) connection failed: connection to server at "127.0.0.1", port 5433 failed: FATAL:  password authentication failed for user "cos_user"
Multiple connection attempts failed. All failures were:
- host: 'localhost', port: 5433, hostaddr: '::1': connection failed: connection to server at "::1", port 5433 failed: FATAL:  password authentication failed for user "cos_user"
- host: 'localhost', port: 5433, hostaddr: '127.0.0.1': connection failed: connection to server at "127.0.0.1", port 5433 failed: FATAL:  password authentication failed for user "cos_user"
(Background on this error at: https://sqlalche.me/e/20/e3q8)
FAILED tests/db/test_alembic_migrations.py::test_recreate_after_drop - AttributeError: '_DummyConn' object has no attribute 'prepare'
FAILED tests/db/test_alembic_migrations.py::test_downgrade_then_upgrade - sqlalchemy.exc.OperationalError: (psycopg.OperationalError) connection failed: connection to server at "127.0.0.1", port 5433 failed: FATAL:  password authentication failed for user "cos_user"
Multiple connection attempts failed. All failures were:
- host: 'localhost', port: 5433, hostaddr: '::1': connection failed: connection to server at "::1", port 5433 failed: FATAL:  password authentication failed for user "cos_user"
- host: 'localhost', port: 5433, hostaddr: '127.0.0.1': connection failed: connection to server at "127.0.0.1", port 5433 failed: FATAL:  password authentication failed for user "cos_user"
(Background on this error at: https://sqlalche.me/e/20/e3q8)
FAILED tests/db/test_alembic_migrations.py::test_schemas_created - sqlalchemy.exc.OperationalError: (psycopg.OperationalError) connection failed: connection to server at "127.0.0.1", port 5433 failed: FATAL:  password authentication failed for user "cos_user"
Multiple connection attempts failed. All failures were:
- host: 'localhost', port: 5433, hostaddr: '::1': connection failed: connection to server at "::1", port 5433 failed: FATAL:  password authentication failed for user "cos_user"
- host: 'localhost', port: 5433, hostaddr: '127.0.0.1': connection failed: connection to server at "127.0.0.1", port 5433 failed: FATAL:  password authentication failed for user "cos_user"
(Background on this error at: https://sqlalche.me/e/20/e3q8)
FAILED tests/db/test_alembic_migrations.py::test_tables_in_correct_schema - sqlalchemy.exc.OperationalError: (psycopg.OperationalError) connection failed: connection to server at "127.0.0.1", port 5433 failed: FATAL:  password authentication failed for user "cos_user"
Multiple connection attempts failed. All failures were:
- host: 'localhost', port: 5433, hostaddr: '::1': connection failed: connection to server at "::1", port 5433 failed: FATAL:  password authentication failed for user "cos_user"
- host: 'localhost', port: 5433, hostaddr: '127.0.0.1': connection failed: connection to server at "127.0.0.1", port 5433 failed: FATAL:  password authentication failed for user "cos_user"
(Background on this error at: https://sqlalche.me/e/20/e3q8)
FAILED tests/db/test_alembic_migrations.py::test_indexes_created - sqlalchemy.exc.OperationalError: (psycopg.OperationalError) connection failed: connection to server at "127.0.0.1", port 5433 failed: FATAL:  password authentication failed for user "cos_user"
Multiple connection attempts failed. All failures were:
- host: 'localhost', port: 5433, hostaddr: '::1': connection failed: connection to server at "::1", port 5433 failed: FATAL:  password authentication failed for user "cos_user"
- host: 'localhost', port: 5433, hostaddr: '127.0.0.1': connection failed: connection to server at "127.0.0.1", port 5433 failed: FATAL:  password authentication failed for user "cos_user"
(Background on this error at: https://sqlalche.me/e/20/e3q8)
FAILED tests/db/test_connection.py::test_basic_connection - AttributeError: '_DummyConn' object has no attribute 'prepare'
FAILED tests/db/test_connection.py::test_postgres_specific_features - AttributeError: '_DummyConn' object has no attribute 'prepare'
FAILED tests/integration/test_redis_performance.py::TestMemoryLeakDetection::test_connection_cleanup_memory - AttributeError: module 'fakeredis.aioredis' has no attribute 'Redis'
FAILED tests/integration/test_redis_performance.py::TestCircuitBreakerPerformance::test_circuit_breaker_blocked_request_performance - src.common.pubsub.CircuitBreakerError: Circuit breaker is open. Next attempt at 1750970426.7774487
FAILED tests/integration/test_redis_performance_simplified.py::TestDirectRedisBenchmarks::test_redis_set_latency - RuntimeError: <Queue at 0x7f17d44166d0 maxsize=0 tasks=3> is bound to a different event loop
FAILED tests/integration/test_redis_performance_simplified.py::TestDirectRedisBenchmarks::test_redis_get_latency - RuntimeError: <Queue at 0x7f17d45a44d0 maxsize=0 tasks=3> is bound to a different event loop
FAILED tests/integration/test_redis_performance_simplified.py::TestDirectRedisBenchmarks::test_json_serialization_latency - RuntimeError: <Queue at 0x7f17d4385e50 maxsize=0 tasks=3> is bound to a different event loop
FAILED tests/performance/test_comprehensive_benchmarks.py::TestFailureScenarioTesting::test_redis_service_interruption - redis.exceptions.AuthenticationError: AUTH <password> called without any password configured for the default user. Are you sure your configuration is correct?
FAILED tests/performance/test_comprehensive_benchmarks.py::TestFailureScenarioTesting::test_memory_exhaustion_simulation - redis.exceptions.AuthenticationError: AUTH <password> called without any password configured for the default user. Are you sure your configuration is correct?
FAILED tests/performance/test_comprehensive_benchmarks.py::TestResourceMonitoring::test_memory_usage_monitoring - redis.exceptions.AuthenticationError: AUTH <password> called without any password configured for the default user. Are you sure your configuration is correct?
FAILED tests/performance/test_comprehensive_benchmarks.py::TestResourceMonitoring::test_connection_pool_utilization - redis.exceptions.AuthenticationError: AUTH <password> called without any password configured for the default user. Are you sure your configuration is correct?
FAILED tests/performance/test_comprehensive_benchmarks.py::TestResourceMonitoring::test_cpu_utilization_monitoring - redis.exceptions.AuthenticationError: AUTH <password> called without any password configured for the default user. Are you sure your configuration is correct?
FAILED tests/performance/test_comprehensive_benchmarks.py::TestRecoveryValidation::test_redis_service_recovery_validation - redis.exceptions.AuthenticationError: AUTH <password> called without any password configured for the default user. Are you sure your configuration is correct?
FAILED tests/performance/test_production_readiness.py::TestRedisPerformance::test_redis_latency_performance - redis.exceptions.AuthenticationError: AUTH <password> called without any password configured for the default user. Are you sure your configuration is correct?
FAILED tests/performance/test_production_readiness.py::TestRedisPerformance::test_redis_throughput_performance - redis.exceptions.AuthenticationError: AUTH <password> called without any password configured for the default user. Are you sure your configuration is correct?
FAILED tests/performance/test_production_readiness.py::TestRedisPerformance::test_redis_pubsub_latency - redis.exceptions.AuthenticationError: AUTH <password> called without any password configured for the default user. Are you sure your configuration is correct?
FAILED tests/performance/test_production_readiness.py::TestAPIPerformance::test_api_endpoint_performance - httpx.ConnectError: All connection attempts failed
FAILED tests/performance/test_production_readiness.py::TestAPIPerformance::test_api_concurrent_load - AssertionError: API error rate 100.00% > 5%
assert 1.0 < 0.05
FAILED tests/performance/test_production_readiness.py::TestMemoryAndResourceUsage::test_memory_stability_under_load - redis.exceptions.AuthenticationError: AUTH <password> called without any password configured for the default user. Are you sure your configuration is correct?
FAILED tests/performance/test_production_readiness.py::TestMemoryAndResourceUsage::test_cpu_usage_under_load - redis.exceptions.AuthenticationError: AUTH <password> called without any password configured for the default user. Are you sure your configuration is correct?
FAILED tests/performance/test_production_readiness.py::TestFailureScenarios::test_redis_service_interruption_recovery - redis.exceptions.AuthenticationError: AUTH <password> called without any password configured for the default user. Are you sure your configuration is correct?
FAILED tests/performance/test_production_readiness.py::TestFailureScenarios::test_high_error_rate_handling - AssertionError: Some operations should succeed
assert 0 > 0
FAILED tests/performance/test_redis_benchmarks.py::TestRedisLatencyBenchmarks::test_publish_latency_benchmark - redis.exceptions.AuthenticationError: AUTH <password> called without any password configured for the default user. Are you sure your configuration is correct?
FAILED tests/performance/test_redis_benchmarks.py::TestRedisLatencyBenchmarks::test_latency_percentiles_validation - redis.exceptions.AuthenticationError: AUTH <password> called without any password configured for the default user. Are you sure your configuration is correct?
FAILED tests/performance/test_redis_benchmarks.py::TestRedisThroughputBenchmarks::test_throughput_stress_benchmark - RuntimeError: asyncio.run() cannot be called from a running event loop
FAILED tests/performance/test_redis_benchmarks.py::TestRedisThroughputBenchmarks::test_sustained_load_validation - redis.exceptions.AuthenticationError: AUTH <password> called without any password configured for the default user. Are you sure your configuration is correct?
FAILED tests/performance/test_redis_benchmarks.py::TestRedisThroughputBenchmarks::test_concurrent_throughput_benchmark - RuntimeError: asyncio.run() cannot be called from a running event loop
FAILED tests/performance/test_redis_benchmarks.py::TestConnectionPoolBenchmarks::test_pool_vs_individual_connections - redis.exceptions.AuthenticationError: AUTH <password> called without any password configured for the default user. Are you sure your configuration is correct?
FAILED tests/performance/test_redis_benchmarks.py::TestConnectionPoolBenchmarks::test_pool_connection_reuse - redis.exceptions.AuthenticationError: AUTH <password> called without any password configured for the default user. Are you sure your configuration is correct?
FAILED tests/performance/test_redis_benchmarks.py::TestMemoryLeakDetection::test_memory_leak_detection - redis.exceptions.AuthenticationError: AUTH <password> called without any password configured for the default user. Are you sure your configuration is correct?
FAILED tests/performance/test_redis_benchmarks.py::TestMemoryLeakDetection::test_tracemalloc_leak_detection - redis.exceptions.AuthenticationError: AUTH <password> called without any password configured for the default user. Are you sure your configuration is correct?
FAILED tests/performance/test_redis_benchmarks.py::TestMemoryLeakDetection::test_connection_pool_memory_hygiene - redis.exceptions.AuthenticationError: AUTH <password> called without any password configured for the default user. Are you sure your configuration is correct?
FAILED tests/performance/test_redis_benchmarks.py::TestRegressionDetection::test_throughput_baseline_benchmark - RuntimeError: asyncio.run() cannot be called from a running event loop
FAILED tests/performance/test_redis_benchmarks.py::TestRegressionDetection::test_performance_targets_validation - redis.exceptions.AuthenticationError: AUTH <password> called without any password configured for the default user. Are you sure your configuration is correct?
FAILED tests/unit/backend/cc/test_logging_redis_publish.py::TestPublishL1EventFunction::test_publish_l1_event_success - AssertionError: expected call not found.
Expected: publish('mem0.recorded.cc', {'event_type': 'test_event', 'event_data': {'action': 'test'}, 'created_at': '2024-01-01T00:00:00Z', 'log_id': '12345678-1234-5678-9012-123456789abc'})
  Actual: publish('mem0.recorded.cc', {'event_type': 'test_event', 'event_data': {'action': 'test'}, 'created_at': '2024-01-01T00:00:00Z', 'log_id': '12345678-1234-5678-9012-123456789abc'}, correlation_id='914caf23-7b62-4970-8552-d3aed5df1cbf')
pytest introspection follows:
Kwargs:
assert {'correlation_id': '914caf23-7b62-4970-8552-d3aed5df1cbf'} == {}

  Left contains 1 more item:
  {'correlation_id': '914caf23-7b62-4970-8552-d3aed5df1cbf'}

  Full diff:
  - {}
  + {
  +     'correlation_id': '914caf23-7b62-4970-8552-d3aed5df1cbf',
  + }
FAILED tests/unit/backend/cc/test_logging_redis_publish.py::TestPublishL1EventFunction::test_publish_l1_event_logfire_span - AssertionError: expected call not found.
Expected: span('publish_l1_event', kind='producer')
  Actual: span('publish_l1_event', kind='producer', log_id='12345678-1234-5678-9012-123456789abc', correlation_id='5473d83b-053f-44a5-9de8-99dcf65a43fe')
pytest introspection follows:
Kwargs:
assert {'kind': 'producer', 'log_id': '12345678-1234-5678-9012-123456789abc', 'correlation_id': '5473d83b-053f-44a5-9de8-99dcf65a43fe'} == {'kind': 'producer'}

  Common items:
  {'kind': 'producer'}
  Left contains 2 more items:
  {'correlation_id': '5473d83b-053f-44a5-9de8-99dcf65a43fe',
   'log_id': '12345678-1234-5678-9012-123456789abc'}

  Full diff:
    {
  +     'correlation_id': '5473d83b-053f-44a5-9de8-99dcf65a43fe',
        'kind': 'producer',
  +     'log_id': '12345678-1234-5678-9012-123456789abc',
    }
FAILED tests/unit/backend/cc/test_logging_redis_simple.py::TestPublishL1EventFunction::test_publish_l1_event_success - AssertionError: expected call not found.
Expected: publish('mem0.recorded.cc', {'log_id': '12345678-1234-5678-9012-123456789abc', 'created_at': '2024-01-01T00:00:00Z', 'event': {'event_type': 'test_event', 'event_data': {'action': 'test'}, 'request_id': 'test-request-id', 'trace_id': 'test-trace-id'}})
  Actual: publish('mem0.recorded.cc', {'log_id': '12345678-1234-5678-9012-123456789abc', 'created_at': '2024-01-01T00:00:00Z', 'event': {'event_type': 'test_event', 'event_data': {'action': 'test'}, 'request_id': 'test-request-id', 'trace_id': 'test-trace-id'}}, correlation_id='test-request-id')
pytest introspection follows:
Kwargs:
assert {'correlation_id': 'test-request-id'} == {}

  Left contains 1 more item:
  {'correlation_id': 'test-request-id'}

  Full diff:
  - {}
  + {
  +     'correlation_id': 'test-request-id',
  + }
FAILED tests/unit/backend/cc/test_logging_redis_simple.py::TestPublishL1EventFunction::test_publish_l1_event_redis_error_isolation - AssertionError: Expected 'warn' to have been called once. Called 0 times.
FAILED tests/unit/backend/cc/test_logging_redis_simple.py::TestPublishL1EventFunction::test_publish_l1_event_logfire_span_error_isolation - AssertionError: Expected 'warn' to have been called once. Called 0 times.
FAILED tests/unit/backend/cc/test_logging_redis_simple.py::TestRedisChannelAndMessageFormat::test_correct_channel_name - AssertionError: expected call not found.
Expected: publish('mem0.recorded.cc', {'event': {'event_type': 'channel_test'}})
  Actual: publish('mem0.recorded.cc', {'event': {'event_type': 'channel_test'}}, correlation_id='db6516ac-d461-4b4d-8537-4c39479a7c58')
pytest introspection follows:
Kwargs:
assert {'correlation_id': 'db6516ac-d461-4b4d-8537-4c39479a7c58'} == {}

  Left contains 1 more item:
  {'correlation_id': 'db6516ac-d461-4b4d-8537-4c39479a7c58'}

  Full diff:
  - {}
  + {
  +     'correlation_id': 'db6516ac-d461-4b4d-8537-4c39479a7c58',
  + }
FAILED tests/unit/backend/cc/test_logging_redis_simple.py::TestRedisChannelAndMessageFormat::test_message_data_passed_correctly - AssertionError: expected call not found.
Expected: publish('mem0.recorded.cc', {'log_id': '12345678-1234-5678-9012-123456789abc', 'created_at': '2024-01-01T00:00:00Z', 'event': {'event_type': 'complex_test', 'event_data': {'nested': {'value': 123}, 'array': [1, 2, 3]}, 'request_id': 'req-123', 'trace_id': 'trace-456'}})
  Actual: publish('mem0.recorded.cc', {'log_id': '12345678-1234-5678-9012-123456789abc', 'created_at': '2024-01-01T00:00:00Z', 'event': {'event_type': 'complex_test', 'event_data': {'nested': {'value': 123}, 'array': [1, 2, 3]}, 'request_id': 'req-123', 'trace_id': 'trace-456'}}, correlation_id='req-123')
pytest introspection follows:
Kwargs:
assert {'correlation_id': 'req-123'} == {}

  Left contains 1 more item:
  {'correlation_id': 'req-123'}

  Full diff:
  - {}
  + {
  +     'correlation_id': 'req-123',
  + }
FAILED tests/unit/common/test_base_subscriber_comprehensive.py::TestBaseSubscriber::test_start_consuming_single_message_mode - assert False
 +  where False = <test_base_subscriber_comprehensive.ConcreteSubscriber object at 0x7f17cd358830>.is_consuming
FAILED tests/unit/common/test_base_subscriber_comprehensive.py::TestBaseSubscriber::test_start_consuming_batch_mode - assert False
 +  where False = <test_base_subscriber_comprehensive.ConcreteSubscriber object at 0x7f17cf6f6ad0>.is_consuming
FAILED tests/unit/common/test_base_subscriber_comprehensive.py::TestBaseSubscriber::test_start_consuming_already_consuming - AssertionError: assert 'Already consuming' in ''
 +  where '' = <_pytest.logging.LogCaptureFixture object at 0x7f17d425a6d0>.text
FAILED tests/unit/common/test_base_subscriber_comprehensive.py::TestBaseSubscriber::test_stop_consuming_cleanup - TypeError: An asyncio.Future, a coroutine or an awaitable is required
FAILED tests/unit/common/test_base_subscriber_comprehensive.py::TestBaseSubscriber::test_handle_single_message_failure - assert 0 == 1
FAILED tests/unit/common/test_base_subscriber_comprehensive.py::TestBaseSubscriber::test_handle_message_batch_mixed_results - assert 2 == 1
FAILED tests/unit/common/test_base_subscriber_comprehensive.py::TestBaseSubscriber::test_processing_state_management_errors - AssertionError: assert 'Failed to set processing state' in ''
 +  where '' = <_pytest.logging.LogCaptureFixture object at 0x7f17cd3c5e60>.text
FAILED tests/unit/common/test_base_subscriber_comprehensive.py::TestBaseSubscriber::test_send_to_dlq_error - AssertionError: assert 'Failed to send message to DLQ' in ''
 +  where '' = <_pytest.logging.LogCaptureFixture object at 0x7f17cff51610>.text
FAILED tests/unit/common/test_base_subscriber_comprehensive.py::TestBaseSubscriber::test_consume_loop_error_handling - AssertionError: assert 'Error in consumer loop' in ''
 +  where '' = <_pytest.logging.LogCaptureFixture object at 0x7f17cff52690>.text
FAILED tests/unit/common/test_circuit_breaker.py::TestCircuitBreaker::test_state_reset_on_close - assert 5 == 0
 +  where 5 = <src.common.pubsub.CircuitBreaker object at 0x7f17cf1375f0>.failure_count
FAILED tests/unit/common/test_circuit_breaker_edge.py::TestCircuitBreakerConfiguration::test_success_threshold_variations[1] - AssertionError: assert <CircuitBreakerState.CLOSED: 'closed'> == <CircuitBreakerState.HALF_OPEN: 'half_open'>
 +  where <CircuitBreakerState.CLOSED: 'closed'> = <src.common.pubsub.CircuitBreaker object at 0x7f17cd3c5e60>.state
 +  and   <CircuitBreakerState.HALF_OPEN: 'half_open'> = CircuitBreakerState.HALF_OPEN
FAILED tests/unit/common/test_circuit_breaker_edge.py::TestCircuitBreakerTimingAndRecovery::test_recovery_under_load - src.common.pubsub.CircuitBreakerError: Circuit breaker is open. Next attempt at 1750970764.1164496
FAILED tests/unit/common/test_circuit_breaker_edge.py::TestCircuitBreakerEdgeCases::test_concurrent_state_transitions - AssertionError: No successes during recovery
assert 0 > 0
 +  where 0 = len([])
FAILED tests/unit/common/test_coverage_check.py::TestCoverageCheck::test_redis_config_properties - AssertionError: assert 'redis://localhost:6379' == 'redis://localhost:6379/0'

  - redis://localhost:6379/0
  ?                       --
  + redis://localhost:6379
FAILED tests/unit/common/test_enhanced_error_handling.py::TestEnhancedPublishMethod::test_publish_serialization_error - AssertionError: assert 'Message serialization failed' in 'Unexpected publish error'
FAILED tests/unit/common/test_enhanced_error_handling.py::TestErrorIsolation::test_error_recovery_after_redis_restoration - src.common.pubsub.PublishError: Failed to publish message: Temporary failure
FAILED tests/unit/common/test_enhanced_redis_pubsub_suite.py::TestEnhancedRedisPubSubSuite::test_failure_injection_patterns - AssertionError: Expected some successes after failures
assert 0 > 0
FAILED tests/unit/common/test_pubsub_failures.py::TestNetworkFailureScenarios::test_redis_server_restart_simulation - src.common.pubsub.PublishError: Publish blocked by circuit breaker: Circuit breaker is open. Next attempt at 1750970797.5484233
FAILED tests/unit/common/test_pubsub_failures.py::TestMalformedDataHandling::test_invalid_json_serialization - AssertionError: Regex pattern did not match.
 Regex: 'Failed to serialize'
 Input: 'Unexpected publish error: Circular reference detected'
FAILED tests/unit/common/test_pubsub_failures.py::TestConcurrencyFailures::test_circuit_breaker_race_conditions - assert 3 == 50
 +  where 50 = len([<function TestConcurrencyFailures.test_circuit_breaker_race_conditions.<locals>.failing_operation at 0x7f17cf10dee0>, <function TestConcurrencyFailures.test_circuit_breaker_race_conditions.<locals>.failing_operation at 0x7f17cf10dee0>, <function TestConcurrencyFailures.test_circuit_breaker_race_conditions.<locals>.failing_operation at 0x7f17cf10dee0>, <function TestConcurrencyFailures.test_circuit_breaker_race_conditions.<locals>.failing_operation at 0x7f17cf10dee0>, <function TestConcurrencyFailures.test_circuit_breaker_race_conditions.<locals>.failing_operation at 0x7f17cf10dee0>, <function TestConcurrencyFailures.test_circuit_breaker_race_conditions.<locals>.failing_operation at 0x7f17cf10dee0>, <function TestConcurrencyFailures.test_circuit_breaker_race_conditions.<locals>.failing_operation at 0x7f17cf10dee0>, <function TestConcurrencyFailures.test_circuit_breaker_race_conditions.<locals>.failing_operation at 0x7f17cf10dee0>, <function TestConcurrencyFailures.test_circuit_breaker_race_
FAILED tests/unit/common/test_pubsub_performance.py::TestRedisPubSubPerformance::test_concurrent_publish_throughput - AssertionError: Mean concurrent latency 66.78ms exceeds 2x threshold under load
assert 66.7784286999995 < (5.0 * 2)
FAILED tests/unit/common/test_pubsub_performance.py::TestRedisPubSubStressTests::test_sustained_high_throughput - AssertionError: Actual throughput 374.4 ops/sec below minimum 800.0 ops/sec
assert 374.4405005852174 >= 800.0
FAILED tests/unit/common/test_pubsub_performance.py::TestRedisPubSubStressTests::test_many_concurrent_subscribers - AssertionError: Expected 500 messages, received 11
assert 11 == 500
FAILED tests/unit/common/test_redis_config_comprehensive.py::TestRedisConfigComprehensive::test_env_file_loading_simulation - AssertionError: Expected 'load_dotenv' to have been called.
FAILED tests/unit/common/test_redis_config_comprehensive.py::TestRedisConfigIntegrationScenarios::test_development_environment_complete - AssertionError: assert 'redis://localhost:6379' == 'redis://localhost:6379/0'

  - redis://localhost:6379/0
  ?                       --
  + redis://localhost:6379
FAILED tests/unit/common/test_redis_config_comprehensive.py::TestRedisConfigIntegrationScenarios::test_production_environment_complete - AssertionError: assert 'redis://localhost:6379' == 'redis://:prod-super-secret-password-v2@redis-cluster-prod.company.com:6380/1'

  - redis://:prod-super-secret-password-v2@redis-cluster-prod.company.com:6380/1
  + redis://localhost:6379
FAILED tests/unit/common/test_redis_config_comprehensive.py::TestRedisConfigIntegrationScenarios::test_redis_sentinel_configuration - AssertionError: assert 'sentinel-password' in 'redis://localhost:6379'
 +  where 'redis://localhost:6379' = RedisConfig(redis_host='redis-sentinel.service.consul', redis_port=26379, redis_password='sentinel-password', redis_db=0, redis_url_override='redis://localhost:6379', redis_max_connections=20, redis_socket_connect_timeout=5, redis_socket_keepalive=True, redis_retry_on_timeout=True, redis_health_check_interval=10).redis_url
FAILED tests/unit/common/test_redis_config_comprehensive.py::TestRedisConfigIntegrationScenarios::test_docker_container_configuration - AssertionError: assert 'redis://localhost:6379' == 'redis://:k8s-redis-secret@redis-service:6379/0'

  - redis://:k8s-redis-secret@redis-service:6379/0
  + redis://localhost:6379
FAILED tests/unit/common/test_redis_config_matrix.py::TestRedisConfigurationMatrix::test_environment_specific_defaults[development-expected_defaults0] - AssertionError: assert 20 == 10
 +  where 20 = RedisConfig(redis_host='localhost', redis_port=6379, redis_password=None, redis_db=0, redis_url_override=None, redis_max_connections=20, redis_socket_connect_timeout=5, redis_socket_keepalive=True, redis_retry_on_timeout=True, redis_health_check_interval=30).redis_max_connections
FAILED tests/unit/common/test_redis_config_matrix.py::TestRedisConfigurationMatrix::test_environment_specific_defaults[testing-expected_defaults1] - AssertionError: assert 20 == 5
 +  where 20 = RedisConfig(redis_host='localhost', redis_port=6379, redis_password=None, redis_db=0, redis_url_override=None, redis_max_connections=20, redis_socket_connect_timeout=5, redis_socket_keepalive=True, redis_retry_on_timeout=True, redis_health_check_interval=30).redis_max_connections
FAILED tests/unit/common/test_redis_config_matrix.py::TestRedisConfigurationMatrix::test_environment_specific_defaults[production-expected_defaults2] - AssertionError: assert 5 == 10
 +  where 5 = RedisConfig(redis_host='localhost', redis_port=6379, redis_password=None, redis_db=0, redis_url_override=None, redis_max_connections=20, redis_socket_connect_timeout=5, redis_socket_keepalive=True, redis_retry_on_timeout=True, redis_health_check_interval=30).redis_socket_connect_timeout
FAILED tests/unit/common/test_redis_config_matrix.py::TestRedisConfigurationMatrix::test_invalid_configuration_handling - AssertionError: Regex pattern did not match.
 Regex: 'invalid literal for int()'
 Input: "1 validation error for RedisConfig\nredis_port\n  Input should be a valid integer, unable to parse string as an integer [type=int_parsing, input_value='invalid', input_type=str]\n    For further information visit https://errors.pydantic.dev/2.11/v/int_parsing"
FAILED tests/unit/common/test_redis_config_matrix.py::TestRedisConfigurationMatrix::test_fallback_behavior[missing_vars0-expected_fallbacks0] - AssertionError: assert ('@' not in 'redis://:test-pass@localhost:6379/1'

  '@' is contained here:
    redis://:test-pass@localhost:6379/1
  ?                   + or ':@' in 'redis://:test-pass@localhost:6379/1')
FAILED tests/unit/common/test_redis_config_matrix.py::TestRedisConfigurationMatrix::test_fallback_behavior[missing_vars1-expected_fallbacks1] - AssertionError: assert ('@' not in 'redis://:test-pass@test-host:6379/1'

  '@' is contained here:
    redis://:test-pass@test-host:6379/1
  ?                   + or ':@' in 'redis://:test-pass@test-host:6379/1')
FAILED tests/unit/common/test_redis_config_matrix.py::TestRedisConfigurationMatrix::test_fallback_behavior[missing_vars2-expected_fallbacks2] - AssertionError: assert ('@' not in 'redis://:test-pass@localhost:6379/1'

  '@' is contained here:
    redis://:test-pass@localhost:6379/1
  ?                   + or ':@' in 'redis://:test-pass@localhost:6379/1')
FAILED tests/unit/common/test_redis_config_matrix.py::TestRedisConfigurationMatrix::test_fallback_behavior[missing_vars4-expected_fallbacks4] - AssertionError: assert ('@' not in 'redis://:test-pass@test-host:6379/0'

  '@' is contained here:
    redis://:test-pass@test-host:6379/0
  ?                   + or ':@' in 'redis://:test-pass@test-host:6379/0')
FAILED tests/unit/common/test_redis_pubsub_comprehensive.py::TestRedisPubSubComprehensive::test_connect_circuit_breaker_protection - Exception: Connection failed
FAILED tests/unit/common/test_redis_pubsub_comprehensive.py::TestRedisPubSubComprehensive::test_publish_performance_logging - AssertionError: assert 'exceeded 1ms target' in ''
 +  where '' = <_pytest.logging.LogCaptureFixture object at 0x7f17bc6a2fc0>.text
FAILED tests/unit/common/test_redis_pubsub_comprehensive.py::TestRedisPubSubComprehensive::test_subscribe_with_circuit_breaker_failure - AttributeError: 'method' object has no attribute 'return_value' and no __dict__ for setting new attributes
FAILED tests/unit/common/test_redis_pubsub_comprehensive.py::TestRedisPubSubComprehensive::test_message_handling_malformed_data - AssertionError: assert 'Failed to decode message' in ''
 +  where '' = <_pytest.logging.LogCaptureFixture object at 0x7f17bc6a0ec0>.text
FAILED tests/unit/common/test_redis_pubsub_comprehensive.py::TestRedisPubSubComprehensive::test_message_handling_handler_exceptions - AssertionError: assert 'Error handling message' in ''
 +  where '' = <_pytest.logging.LogCaptureFixture object at 0x7f17cf729f90>.text
FAILED tests/unit/common/test_redis_pubsub_comprehensive.py::TestRedisPubSubComprehensive::test_listen_loop_cancellation_scenarios - TypeError: 'async for' requires an object with __aiter__ method, got coroutine
FAILED tests/unit/common/test_redis_pubsub_comprehensive.py::TestRedisPubSubComprehensive::test_listen_loop_reconnection_scenarios - TypeError: 'async for' requires an object with __aiter__ method, got coroutine
FAILED tests/unit/common/test_redis_pubsub_comprehensive.py::TestRedisPubSubComprehensive::test_channel_subscription_context_manager_error_handling - AttributeError: 'method' object has no attribute 'return_value' and no __dict__ for setting new attributes
FAILED tests/unit/common/test_redis_pubsub_comprehensive.py::TestRedisPubSubComprehensive::test_disconnect_partial_cleanup_scenarios - Exception: Cleanup error
FAILED tests/unit/common/test_redis_pubsub_comprehensive.py::TestRedisPubSubComprehensive::test_publish_performance_benchmark - AssertionError: Average publish time 1.613ms exceeds 1ms target
assert 1.6127236300189907 < 1.0
FAILED tests/unit/common/test_redis_pubsub_comprehensive.py::TestGlobalPubSubFunctions::test_cleanup_pubsub_with_disconnect_error - Exception: Disconnect failed
FAILED tests/unit/test_cos_main_coverage.py::TestCosMainLogEvent::test_startup_log_event_called - AssertionError: expected call not found.
Expected: log_event(source='cos_main', data={'event': 'startup'}, memo='COS FastAPI initialized.')
  Actual: not called.
ERROR tests/performance/test_failure_scenarios.py - Failed: 'failure_scenarios' not found in `markers` configuration option
ERROR tests/performance/test_performance_metrics.py - Failed: 'metrics' not found in `markers` configuration option
ERROR tests/backend/cc/test_crud.py::TestGetSystemHealth::test_get_system_health_empty - AttributeError: '_DummyConn' object has no attribute 'prepare'
ERROR tests/backend/cc/test_crud.py::TestGetSystemHealth::test_get_system_health_single_record - AttributeError: '_DummyConn' object has no attribute 'prepare'
ERROR tests/backend/cc/test_crud.py::TestGetSystemHealth::test_get_system_health_returns_latest - AttributeError: '_DummyConn' object has no attribute 'prepare'
ERROR tests/backend/cc/test_crud.py::TestGetSystemHealth::test_get_system_health_multiple_records_order - AttributeError: '_DummyConn' object has no attribute 'prepare'
ERROR tests/backend/cc/test_crud.py::TestModuleCRUD::test_create_module_success - AttributeError: '_DummyConn' object has no attribute 'prepare'
ERROR tests/backend/cc/test_crud.py::TestModuleCRUD::test_create_module_with_config - AttributeError: '_DummyConn' object has no attribute 'prepare'
ERROR tests/backend/cc/test_crud.py::TestModuleCRUD::test_get_module_by_id_exists - AttributeError: '_DummyConn' object has no attribute 'prepare'
ERROR tests/backend/cc/test_crud.py::TestModuleCRUD::test_get_module_by_id_not_exists - AttributeError: '_DummyConn' object has no attribute 'prepare'
ERROR tests/backend/cc/test_crud.py::TestModuleCRUD::test_get_module_by_name_exists - AttributeError: '_DummyConn' object has no attribute 'prepare'
ERROR tests/backend/cc/test_crud.py::TestModuleCRUD::test_get_module_by_name_not_exists - AttributeError: '_DummyConn' object has no attribute 'prepare'
ERROR tests/backend/cc/test_crud.py::TestModuleCRUD::test_get_modules_empty - AttributeError: '_DummyConn' object has no attribute 'prepare'
ERROR tests/backend/cc/test_crud.py::TestModuleCRUD::test_get_modules_with_data - AttributeError: '_DummyConn' object has no attribute 'prepare'
ERROR tests/backend/cc/test_crud.py::TestModuleCRUD::test_get_modules_pagination - AttributeError: '_DummyConn' object has no attribute 'prepare'
ERROR tests/backend/cc/test_crud.py::TestModuleCRUD::test_update_module_success - AttributeError: '_DummyConn' object has no attribute 'prepare'
ERROR tests/backend/cc/test_crud.py::TestModuleCRUD::test_update_module_not_exists - AttributeError: '_DummyConn' object has no attribute 'prepare'
ERROR tests/backend/cc/test_crud.py::TestModuleCRUD::test_update_module_ignore_invalid_fields - AttributeError: '_DummyConn' object has no attribute 'prepare'
ERROR tests/backend/cc/test_crud.py::TestModuleCRUD::test_delete_module_success - AttributeError: '_DummyConn' object has no attribute 'prepare'
ERROR tests/backend/cc/test_crud.py::TestModuleCRUD::test_delete_module_not_exists - AttributeError: '_DummyConn' object has no attribute 'prepare'
ERROR tests/backend/cc/test_database_schema.py::test_cc_tables_exist - AttributeError: '_DummyConn' object has no attribute 'prepare'
ERROR tests/backend/cc/test_database_schema.py::test_mem0_cc_tables_exist - AttributeError: '_DummyConn' object has no attribute 'prepare'
ERROR tests/backend/cc/test_debug_endpoints_enhanced.py::TestEnhancedDebugLogEndpoint::test_enhanced_debug_log_includes_redis_validation - AttributeError: '_DummyConn' object has no attribute 'prepare'
ERROR tests/backend/cc/test_debug_endpoints_enhanced.py::TestEnhancedDebugLogEndpoint::test_enhanced_debug_log_redis_failure_handling - AttributeError: '_DummyConn' object has no attribute 'prepare'
ERROR tests/backend/cc/test_debug_endpoints_enhanced.py::TestEnhancedDebugLogEndpoint::test_enhanced_debug_log_message_inspection - AttributeError: '_DummyConn' object has no attribute 'prepare'
ERROR tests/backend/cc/test_debug_endpoints_enhanced.py::TestRedisHealthEndpoint::test_redis_health_endpoint_exists - AttributeError: '_DummyConn' object has no attribute 'prepare'
ERROR tests/backend/cc/test_debug_endpoints_enhanced.py::TestRedisHealthEndpoint::test_redis_health_comprehensive_status - AttributeError: '_DummyConn' object has no attribute 'prepare'
ERROR tests/backend/cc/test_debug_endpoints_enhanced.py::TestRedisHealthEndpoint::test_redis_health_circuit_breaker_integration - AttributeError: '_DummyConn' object has no attribute 'prepare'
ERROR tests/backend/cc/test_debug_endpoints_enhanced.py::TestRedisHealthEndpoint::test_redis_health_connection_failure_handling - AttributeError: '_DummyConn' object has no attribute 'prepare'
ERROR tests/backend/cc/test_debug_endpoints_enhanced.py::TestRedisHealthEndpoint::test_redis_health_performance_metrics_collection - AttributeError: '_DummyConn' object has no attribute 'prepare'
ERROR tests/backend/cc/test_debug_endpoints_enhanced.py::TestRedisHealthAggregation::test_health_status_aggregation_healthy - AttributeError: '_DummyConn' object has no attribute 'prepare'
ERROR tests/backend/cc/test_debug_endpoints_enhanced.py::TestRedisHealthAggregation::test_health_status_aggregation_degraded - AttributeError: '_DummyConn' object has no attribute 'prepare'
ERROR tests/backend/cc/test_debug_endpoints_enhanced.py::TestRedisHealthAggregation::test_health_status_aggregation_offline - AttributeError: '_DummyConn' object has no attribute 'prepare'
ERROR tests/backend/cc/test_log_l1.py::TestLogL1Basic::test_basic_log_creation - AttributeError: '_DummyConn' object has no attribute 'prepare'
ERROR tests/backend/cc/test_log_l1.py::TestLogL1Basic::test_event_log_creation - AttributeError: '_DummyConn' object has no attribute 'prepare'
ERROR tests/backend/cc/test_log_l1.py::TestLogL1Basic::test_prompt_trace_creation - AttributeError: '_DummyConn' object has no attribute 'prepare'
ERROR tests/backend/cc/test_log_l1.py::TestLogL1Basic::test_combined_logging - AttributeError: '_DummyConn' object has no attribute 'prepare'
ERROR tests/backend/cc/test_log_l1.py::TestLogL1RequestHandling::test_request_id_from_context - AttributeError: '_DummyConn' object has no attribute 'prepare'
ERROR tests/backend/cc/test_log_l1.py::TestLogL1RequestHandling::test_request_id_fallback_to_uuid - AttributeError: '_DummyConn' object has no attribute 'prepare'
ERROR tests/backend/cc/test_log_l1.py::TestLogL1RequestHandling::test_provided_request_id_priority - AttributeError: '_DummyConn' object has no attribute 'prepare'
ERROR tests/backend/cc/test_log_l1.py::TestLogL1RequestHandling::test_request_id_uuid_conversion - AttributeError: '_DummyConn' object has no attribute 'prepare'
ERROR tests/backend/cc/test_log_l1.py::TestLogL1LogfireIntegration::test_trace_id_extraction - AttributeError: '_DummyConn' object has no attribute 'prepare'
ERROR tests/backend/cc/test_log_l1.py::TestLogL1LogfireIntegration::test_span_attribute_setting - AttributeError: '_DummyConn' object has no attribute 'prepare'
ERROR tests/backend/cc/test_log_l1.py::TestLogL1LogfireIntegration::test_logfire_graceful_degradation_missing_function - AttributeError: '_DummyConn' object has no attribute 'prepare'
ERROR tests/backend/cc/test_log_l1.py::TestLogL1LogfireIntegration::test_logfire_graceful_degradation_span_error - AttributeError: '_DummyConn' object has no attribute 'prepare'
ERROR tests/backend/cc/test_log_l1.py::TestLogL1LogfireIntegration::test_provided_trace_id_priority - AttributeError: '_DummyConn' object has no attribute 'prepare'
ERROR tests/backend/cc/test_log_l1.py::TestLogL1EdgeCases::test_empty_payload - AttributeError: '_DummyConn' object has no attribute 'prepare'
ERROR tests/backend/cc/test_log_l1.py::TestLogL1EdgeCases::test_empty_prompt_data - AttributeError: '_DummyConn' object has no attribute 'prepare'
ERROR tests/backend/cc/test_log_l1.py::TestLogL1EdgeCases::test_partial_prompt_data - AttributeError: '_DummyConn' object has no attribute 'prepare'
ERROR tests/backend/cc/test_log_l1.py::TestLogL1EdgeCases::test_none_values_handling - AttributeError: '_DummyConn' object has no attribute 'prepare'
ERROR tests/backend/cc/test_log_l1.py::TestLogL1EdgeCases::test_complex_payload_data - AttributeError: '_DummyConn' object has no attribute 'prepare'
ERROR tests/backend/cc/test_log_l1.py::TestLogL1DatabaseIntegrity::test_transaction_rollback_on_error - AttributeError: '_DummyConn' object has no attribute 'prepare'
ERROR tests/backend/cc/test_log_l1.py::TestLogL1DatabaseIntegrity::test_foreign_key_relationships - AttributeError: '_DummyConn' object has no attribute 'prepare'
ERROR tests/backend/cc/test_log_l1.py::TestLogL1DatabaseIntegrity::test_concurrent_logging_safety - AttributeError: '_DummyConn' object has no attribute 'prepare'
ERROR tests/backend/cc/test_mem0_crud.py::TestMem0CRUD::test_create_scratch_note_basic - AttributeError: '_DummyConn' object has no attribute 'prepare'
ERROR tests/backend/cc/test_mem0_crud.py::TestMem0CRUD::test_create_scratch_note_with_ttl - AttributeError: '_DummyConn' object has no attribute 'prepare'
ERROR tests/backend/cc/test_mem0_crud.py::TestMem0CRUD::test_get_scratch_note_by_id - AttributeError: '_DummyConn' object has no attribute 'prepare'
ERROR tests/backend/cc/test_mem0_crud.py::TestMem0CRUD::test_get_scratch_note_nonexistent - AttributeError: '_DummyConn' object has no attribute 'prepare'
ERROR tests/backend/cc/test_mem0_crud.py::TestMem0CRUD::test_get_scratch_note_by_key - AttributeError: '_DummyConn' object has no attribute 'prepare'
ERROR tests/backend/cc/test_mem0_crud.py::TestMem0CRUD::test_get_scratch_note_by_key_nonexistent - AttributeError: '_DummyConn' object has no attribute 'prepare'
ERROR tests/backend/cc/test_mem0_crud.py::TestMem0CRUD::test_update_scratch_note - AttributeError: '_DummyConn' object has no attribute 'prepare'
ERROR tests/backend/cc/test_mem0_crud.py::TestMem0CRUD::test_update_scratch_note_nonexistent - AttributeError: '_DummyConn' object has no attribute 'prepare'
ERROR tests/backend/cc/test_mem0_crud.py::TestMem0CRUD::test_delete_scratch_note - AttributeError: '_DummyConn' object has no attribute 'prepare'
ERROR tests/backend/cc/test_mem0_crud.py::TestMem0CRUD::test_delete_scratch_note_nonexistent - AttributeError: '_DummyConn' object has no attribute 'prepare'
ERROR tests/backend/cc/test_mem0_crud.py::TestMem0CRUD::test_list_scratch_notes_basic - AttributeError: '_DummyConn' object has no attribute 'prepare'
ERROR tests/backend/cc/test_mem0_crud.py::TestMem0CRUD::test_list_scratch_notes_with_key_prefix - AttributeError: '_DummyConn' object has no attribute 'prepare'
ERROR tests/backend/cc/test_mem0_crud.py::TestMem0CRUD::test_list_scratch_notes_exclude_expired - AttributeError: '_DummyConn' object has no attribute 'prepare'
ERROR tests/backend/cc/test_mem0_crud.py::TestMem0CRUD::test_list_scratch_notes_include_expired - AttributeError: '_DummyConn' object has no attribute 'prepare'
ERROR tests/backend/cc/test_mem0_crud.py::TestMem0CRUD::test_list_scratch_notes_pagination - AttributeError: '_DummyConn' object has no attribute 'prepare'
ERROR tests/backend/cc/test_mem0_crud.py::TestMem0CRUD::test_cleanup_expired_notes - AttributeError: '_DummyConn' object has no attribute 'prepare'
ERROR tests/backend/cc/test_mem0_crud.py::TestMem0CRUD::test_cleanup_expired_notes_batch_processing - AttributeError: '_DummyConn' object has no attribute 'prepare'
ERROR tests/backend/cc/test_mem0_crud.py::TestMem0CRUD::test_count_scratch_notes - AttributeError: '_DummyConn' object has no attribute 'prepare'
ERROR tests/backend/cc/test_mem0_crud.py::TestMem0CRUD::test_get_expired_notes_count - AttributeError: '_DummyConn' object has no attribute 'prepare'
ERROR tests/backend/cc/test_mem0_crud.py::TestMem0CRUD::test_error_handling_database_error - AttributeError: '_DummyConn' object has no attribute 'prepare'
ERROR tests/backend/cc/test_mem0_crud.py::TestMem0CRUD::test_transaction_rollback_on_error - AttributeError: '_DummyConn' object has no attribute 'prepare'
ERROR tests/backend/cc/test_mem0_models.py::TestScratchNoteDatabase::test_scratch_note_database_creation - AttributeError: '_DummyConn' object has no attribute 'prepare'
ERROR tests/backend/cc/test_mem0_models.py::TestScratchNoteDatabase::test_scratch_note_schema_isolation - AttributeError: '_DummyConn' object has no attribute 'prepare'
ERROR tests/backend/cc/test_mem0_models.py::TestScratchNoteDatabase::test_scratch_note_ttl_query_optimization - AttributeError: '_DummyConn' object has no attribute 'prepare'
ERROR tests/backend/cc/test_router.py::TestModuleRouterEndpoints::test_create_module_success - AttributeError: '_DummyConn' object has no attribute 'prepare'
ERROR tests/backend/cc/test_router.py::TestModuleRouterEndpoints::test_create_module_minimal_data - AttributeError: '_DummyConn' object has no attribute 'prepare'
ERROR tests/backend/cc/test_router.py::TestModuleRouterEndpoints::test_create_module_validation_error - AttributeError: '_DummyConn' object has no attribute 'prepare'
ERROR tests/backend/cc/test_router.py::TestModuleRouterEndpoints::test_create_module_duplicate_name - AttributeError: '_DummyConn' object has no attribute 'prepare'
ERROR tests/backend/cc/test_router.py::TestModuleRouterEndpoints::test_list_modules_empty - AttributeError: '_DummyConn' object has no attribute 'prepare'
ERROR tests/backend/cc/test_router.py::TestModuleRouterEndpoints::test_list_modules_with_data - AttributeError: '_DummyConn' object has no attribute 'prepare'
ERROR tests/backend/cc/test_router.py::TestModuleRouterEndpoints::test_list_modules_pagination - AttributeError: '_DummyConn' object has no attribute 'prepare'
ERROR tests/backend/cc/test_router.py::TestModuleRouterEndpoints::test_get_module_success - AttributeError: '_DummyConn' object has no attribute 'prepare'
ERROR tests/backend/cc/test_router.py::TestModuleRouterEndpoints::test_get_module_not_found - AttributeError: '_DummyConn' object has no attribute 'prepare'
ERROR tests/backend/cc/test_router.py::TestModuleRouterEndpoints::test_update_module_success - AttributeError: '_DummyConn' object has no attribute 'prepare'
ERROR tests/backend/cc/test_router.py::TestModuleRouterEndpoints::test_update_module_partial - AttributeError: '_DummyConn' object has no attribute 'prepare'
ERROR tests/backend/cc/test_router.py::TestModuleRouterEndpoints::test_update_module_not_found - AttributeError: '_DummyConn' object has no attribute 'prepare'
ERROR tests/backend/cc/test_router.py::TestModuleRouterEndpoints::test_update_module_name_conflict - AttributeError: '_DummyConn' object has no attribute 'prepare'
ERROR tests/backend/cc/test_router.py::TestModuleRouterEndpoints::test_delete_module_success - AttributeError: '_DummyConn' object has no attribute 'prepare'
ERROR tests/backend/cc/test_router.py::TestModuleRouterEndpoints::test_delete_module_not_found - AttributeError: '_DummyConn' object has no attribute 'prepare'
ERROR tests/backend/cc/test_router.py::TestModuleRouterEndpoints::test_module_crud_workflow - AttributeError: '_DummyConn' object has no attribute 'prepare'
ERROR tests/backend/cc/test_router_debug.py::TestDebugLogRouter::test_debug_log_validation_error - AttributeError: '_DummyConn' object has no attribute 'prepare'
ERROR tests/backend/cc/test_router_debug.py::TestDebugLogRouter::test_debug_log_endpoint_exists - AttributeError: '_DummyConn' object has no attribute 'prepare'
ERROR tests/backend/cc/test_services.py::TestModuleServices::test_create_module_success - AttributeError: '_DummyConn' object has no attribute 'prepare'
ERROR tests/backend/cc/test_services.py::TestModuleServices::test_create_module_with_config - AttributeError: '_DummyConn' object has no attribute 'prepare'
ERROR tests/backend/cc/test_services.py::TestModuleServices::test_create_module_duplicate_name_error - AttributeError: '_DummyConn' object has no attribute 'prepare'
ERROR tests/backend/cc/test_services.py::TestModuleServices::test_get_module_exists - AttributeError: '_DummyConn' object has no attribute 'prepare'
ERROR tests/backend/cc/test_services.py::TestModuleServices::test_get_module_not_exists - AttributeError: '_DummyConn' object has no attribute 'prepare'
ERROR tests/backend/cc/test_services.py::TestModuleServices::test_get_module_by_name_exists - AttributeError: '_DummyConn' object has no attribute 'prepare'
ERROR tests/backend/cc/test_services.py::TestModuleServices::test_get_module_by_name_not_exists - AttributeError: '_DummyConn' object has no attribute 'prepare'
ERROR tests/backend/cc/test_services.py::TestModuleServices::test_get_modules_empty - AttributeError: '_DummyConn' object has no attribute 'prepare'
ERROR tests/backend/cc/test_services.py::TestModuleServices::test_get_modules_with_data - AttributeError: '_DummyConn' object has no attribute 'prepare'
ERROR tests/backend/cc/test_services.py::TestModuleServices::test_get_modules_pagination - AttributeError: '_DummyConn' object has no attribute 'prepare'
ERROR tests/backend/cc/test_services.py::TestModuleServices::test_update_module_success - AttributeError: '_DummyConn' object has no attribute 'prepare'
ERROR tests/backend/cc/test_services.py::TestModuleServices::test_update_module_not_exists - AttributeError: '_DummyConn' object has no attribute 'prepare'
ERROR tests/backend/cc/test_services.py::TestModuleServices::test_update_module_name_conflict - AttributeError: '_DummyConn' object has no attribute 'prepare'
ERROR tests/backend/cc/test_services.py::TestModuleServices::test_update_module_same_name - AttributeError: '_DummyConn' object has no attribute 'prepare'
ERROR tests/backend/cc/test_services.py::TestModuleServices::test_delete_module_success - AttributeError: '_DummyConn' object has no attribute 'prepare'
ERROR tests/backend/cc/test_services.py::TestModuleServices::test_delete_module_not_exists - AttributeError: '_DummyConn' object has no attribute 'prepare'
ERROR tests/common/test_pubsub.py::TestRedisPubSub::test_connect_already_connected - AttributeError: module 'src.common.pubsub' has no attribute 'aioredis'
ERROR tests/common/test_pubsub.py::TestRedisPubSub::test_disconnect_success - AttributeError: module 'src.common.pubsub' has no attribute 'aioredis'
ERROR tests/common/test_pubsub.py::TestRedisPubSub::test_publish_success - AttributeError: module 'src.common.pubsub' has no attribute 'aioredis'
ERROR tests/common/test_pubsub.py::TestRedisPubSub::test_publish_redis_error - AttributeError: module 'src.common.pubsub' has no attribute 'aioredis'
ERROR tests/common/test_pubsub.py::TestRedisPubSub::test_publish_json_error - AttributeError: module 'src.common.pubsub' has no attribute 'aioredis'
ERROR tests/common/test_pubsub.py::TestRedisPubSub::test_publish_performance_warning - AttributeError: module 'src.common.pubsub' has no attribute 'aioredis'
ERROR tests/common/test_pubsub.py::TestRedisPubSub::test_subscribe_success - AttributeError: module 'src.common.pubsub' has no attribute 'aioredis'
ERROR tests/common/test_pubsub.py::TestRedisPubSub::test_subscribe_multiple_handlers - AttributeError: module 'src.common.pubsub' has no attribute 'aioredis'
ERROR tests/common/test_pubsub.py::TestRedisPubSub::test_subscribe_redis_error - AttributeError: module 'src.common.pubsub' has no attribute 'aioredis'
ERROR tests/common/test_pubsub.py::TestRedisPubSub::test_unsubscribe_specific_handler - AttributeError: module 'src.common.pubsub' has no attribute 'aioredis'
ERROR tests/common/test_pubsub.py::TestRedisPubSub::test_unsubscribe_all_handlers - AttributeError: module 'src.common.pubsub' has no attribute 'aioredis'
ERROR tests/common/test_pubsub.py::TestRedisPubSub::test_unsubscribe_last_handler - AttributeError: module 'src.common.pubsub' has no attribute 'aioredis'
ERROR tests/common/test_pubsub.py::TestRedisPubSub::test_unsubscribe_nonexistent_channel - AttributeError: module 'src.common.pubsub' has no attribute 'aioredis'
ERROR tests/common/test_pubsub.py::TestRedisPubSub::test_unsubscribe_redis_error - AttributeError: module 'src.common.pubsub' has no attribute 'aioredis'
ERROR tests/common/test_pubsub.py::TestRedisPubSub::test_handle_message_success - AttributeError: module 'src.common.pubsub' has no attribute 'aioredis'
ERROR tests/common/test_pubsub.py::TestRedisPubSub::test_handle_message_string_channel - AttributeError: module 'src.common.pubsub' has no attribute 'aioredis'
ERROR tests/common/test_pubsub.py::TestRedisPubSub::test_handle_message_no_handlers - AttributeError: module 'src.common.pubsub' has no attribute 'aioredis'
ERROR tests/common/test_pubsub.py::TestRedisPubSub::test_handle_message_json_decode_error - AttributeError: module 'src.common.pubsub' has no attribute 'aioredis'
ERROR tests/common/test_pubsub.py::TestRedisPubSub::test_handle_message_handler_exception - AttributeError: module 'src.common.pubsub' has no attribute 'aioredis'
ERROR tests/common/test_pubsub.py::TestRedisPubSub::test_listen_loop_message_processing - AttributeError: module 'src.common.pubsub' has no attribute 'aioredis'
ERROR tests/common/test_pubsub.py::TestRedisPubSub::test_listen_loop_redis_error_reconnect - AttributeError: module 'src.common.pubsub' has no attribute 'aioredis'
ERROR tests/common/test_pubsub.py::TestRedisPubSub::test_listen_loop_cancelled - AttributeError: module 'src.common.pubsub' has no attribute 'aioredis'
ERROR tests/common/test_pubsub.py::TestRedisPubSub::test_channel_subscription_context_manager - AttributeError: module 'src.common.pubsub' has no attribute 'aioredis'
ERROR tests/common/test_pubsub.py::TestRedisPubSub::test_get_subscribers_count_success - AttributeError: module 'src.common.pubsub' has no attribute 'aioredis'
ERROR tests/common/test_pubsub.py::TestRedisPubSub::test_get_subscribers_count_channel_not_found - AttributeError: module 'src.common.pubsub' has no attribute 'aioredis'
ERROR tests/common/test_pubsub.py::TestRedisPubSub::test_get_subscribers_count_redis_error - AttributeError: module 'src.common.pubsub' has no attribute 'aioredis'
ERROR tests/common/test_pubsub.py::TestRedisPubSubIntegration::test_end_to_end_pubsub - AttributeError: 'int' object has no attribute 'update_supported_errors'
ERROR tests/common/test_pubsub.py::TestRedisPubSubIntegration::test_performance_benchmark - AttributeError: 'int' object has no attribute 'update_supported_errors'
ERROR tests/db/test_connection.py::TestDatabaseConnectionIntegration::test_real_db_connection_and_session - AttributeError: '_DummyConn' object has no attribute 'prepare'
ERROR tests/db/test_connection.py::TestDatabaseConnectionIntegration::test_multiple_sessions_work_independently - AttributeError: '_DummyConn' object has no attribute 'prepare'
ERROR tests/integration/test_redis_foundation.py::TestBasicPubSub::test_pubsub_connection - AttributeError: module 'fakeredis.aioredis' has no attribute 'Redis'
ERROR tests/integration/test_redis_foundation.py::TestBasicPubSub::test_publish_without_subscribers - AttributeError: module 'fakeredis.aioredis' has no attribute 'Redis'
ERROR tests/integration/test_redis_foundation.py::TestBasicPubSub::test_basic_roundtrip - AttributeError: module 'fakeredis.aioredis' has no attribute 'Redis'
ERROR tests/integration/test_redis_foundation.py::TestBasicPubSub::test_multiple_handlers_same_channel - AttributeError: module 'fakeredis.aioredis' has no attribute 'Redis'
ERROR tests/integration/test_redis_foundation.py::TestBasicPubSub::test_unsubscribe_specific_handler - AttributeError: module 'fakeredis.aioredis' has no attribute 'Redis'
ERROR tests/integration/test_redis_foundation.py::TestCircuitBreakerIntegration::test_circuit_breaker_normal_operation - AttributeError: module 'fakeredis.aioredis' has no attribute 'Redis'
ERROR tests/integration/test_redis_foundation.py::TestCircuitBreakerIntegration::test_circuit_breaker_metrics - AttributeError: module 'fakeredis.aioredis' has no attribute 'Redis'
ERROR tests/integration/test_redis_foundation.py::TestPerformanceValidation::test_publish_latency_target - AttributeError: module 'fakeredis.aioredis' has no attribute 'Redis'
ERROR tests/integration/test_redis_foundation.py::TestHealthCheck::test_pubsub_health_check - AttributeError: module 'fakeredis.aioredis' has no attribute 'Redis'
ERROR tests/integration/test_redis_foundation.py::TestHealthCheck::test_subscriber_count_tracking - AttributeError: module 'fakeredis.aioredis' has no attribute 'Redis'
ERROR tests/integration/test_redis_performance.py::TestPublishLatencyBenchmarks::test_publish_latency_small_message - AttributeError: module 'fakeredis.aioredis' has no attribute 'Redis'
ERROR tests/integration/test_redis_performance.py::TestPublishLatencyBenchmarks::test_publish_latency_medium_message - AttributeError: module 'fakeredis.aioredis' has no attribute 'Redis'
ERROR tests/integration/test_redis_performance.py::TestPublishLatencyBenchmarks::test_publish_latency_with_serialization - AttributeError: module 'fakeredis.aioredis' has no attribute 'Redis'
ERROR tests/integration/test_redis_performance.py::TestHighConcurrencyStress::test_concurrent_publish_stress - AttributeError: module 'fakeredis.aioredis' has no attribute 'Redis'
ERROR tests/integration/test_redis_performance.py::TestHighConcurrencyStress::test_mixed_workload_stress - AttributeError: module 'fakeredis.aioredis' has no attribute 'Redis'
ERROR tests/integration/test_redis_performance.py::TestHighConcurrencyStress::test_subscriber_publication_stress - AttributeError: module 'fakeredis.aioredis' has no attribute 'Redis'
ERROR tests/integration/test_redis_performance.py::TestMemoryLeakDetection::test_memory_stability_under_load - AttributeError: module 'fakeredis.aioredis' has no attribute 'Redis'
ERROR tests/integration/test_redis_performance.py::TestCircuitBreakerPerformance::test_circuit_breaker_latency_overhead - AttributeError: module 'fakeredis.aioredis' has no attribute 'Redis'
ERROR tests/integration/test_redis_performance.py::TestPerformanceTargetValidation::test_one_ms_publish_target_validation - AttributeError: module 'fakeredis.aioredis' has no attribute 'Redis'
ERROR tests/integration/test_redis_performance.py::TestPerformanceTargetValidation::test_two_thousand_ops_two_seconds_target - AttributeError: module 'fakeredis.aioredis' has no attribute 'Redis'
ERROR tests/integration/test_redis_performance_simplified.py::TestDirectRedisBenchmarks::test_redis_set_latency - RuntimeError: <Queue at 0x7f17d44166d0 maxsize=0 tasks=3> is bound to a different event loop
ERROR tests/integration/test_redis_performance_simplified.py::TestDirectRedisBenchmarks::test_redis_get_latency - RuntimeError: <Queue at 0x7f17d45a44d0 maxsize=0 tasks=3> is bound to a different event loop
ERROR tests/integration/test_redis_performance_simplified.py::TestDirectRedisBenchmarks::test_json_serialization_latency - RuntimeError: <Queue at 0x7f17d4385e50 maxsize=0 tasks=3> is bound to a different event loop
ERROR tests/performance/test_comprehensive_benchmarks.py::TestAPIEndpointBenchmarks::test_cc_module_endpoints_latency - ValueError: benchmark mark can't have 'warmup_rounds' keyword argument.
ERROR tests/performance/test_comprehensive_benchmarks.py::TestAPIEndpointBenchmarks::test_api_percentile_validation - AttributeError: '_DummyConn' object has no attribute 'prepare'
ERROR tests/performance/test_comprehensive_benchmarks.py::TestAPIEndpointBenchmarks::test_concurrent_api_load - AttributeError: '_DummyConn' object has no attribute 'prepare'
ERROR tests/performance/test_comprehensive_benchmarks.py::TestDatabasePerformanceBenchmarks::test_database_crud_performance - ValueError: benchmark mark can't have 'warmup_rounds' keyword argument.
ERROR tests/performance/test_comprehensive_benchmarks.py::TestDatabasePerformanceBenchmarks::test_connection_pool_behavior - AttributeError: '_DummyConn' object has no attribute 'prepare'
ERROR tests/performance/test_comprehensive_benchmarks.py::TestDatabasePerformanceBenchmarks::test_bulk_operations_performance - AttributeError: '_DummyConn' object has no attribute 'prepare'
ERROR tests/performance/test_comprehensive_benchmarks.py::TestFailureScenarioTesting::test_database_connection_exhaustion - AttributeError: '_DummyConn' object has no attribute 'prepare'
ERROR tests/performance/test_comprehensive_benchmarks.py::TestRecoveryValidation::test_database_recovery_validation - AttributeError: '_DummyConn' object has no attribute 'prepare'
ERROR tests/performance/test_comprehensive_benchmarks.py::TestRecoveryValidation::test_end_to_end_recovery_validation - AttributeError: '_DummyConn' object has no attribute 'prepare'
ERROR tests/performance/test_production_readiness.py::TestDatabasePerformance::test_database_query_performance - AttributeError: '_DummyConn' object has no attribute 'prepare'
ERROR tests/performance/test_production_readiness.py::TestDatabasePerformance::test_database_concurrent_performance - AttributeError: '_DummyConn' object has no attribute 'prepare'
ERROR tests/performance/test_production_readiness.py::test_comprehensive_performance_report - AttributeError: '_DummyConn' object has no attribute 'prepare'
ERROR tests/performance/test_redis_benchmarks.py::TestConnectionPoolBenchmarks::test_connection_pool_efficiency_benchmark - ValueError: benchmark mark can't have 'warmup_rounds' keyword argument.
ERROR tests/performance/test_redis_benchmarks.py::TestRegressionDetection::test_publish_baseline_benchmark - ValueError: benchmark mark can't have 'warmup_rounds' keyword argument.
ERROR tests/unit/backend/cc/test_crud.py::TestGetSystemHealth::test_get_system_health_empty - AttributeError: '_DummyConn' object has no attribute 'prepare'
ERROR tests/unit/backend/cc/test_crud.py::TestGetSystemHealth::test_get_system_health_single_record - AttributeError: '_DummyConn' object has no attribute 'prepare'
ERROR tests/unit/backend/cc/test_crud.py::TestGetSystemHealth::test_get_system_health_returns_latest - AttributeError: '_DummyConn' object has no attribute 'prepare'
ERROR tests/unit/backend/cc/test_crud.py::TestGetSystemHealth::test_get_system_health_multiple_records_order - AttributeError: '_DummyConn' object has no attribute 'prepare'
ERROR tests/unit/backend/cc/test_crud.py::TestModuleCRUD::test_create_module_success - AttributeError: '_DummyConn' object has no attribute 'prepare'
ERROR tests/unit/backend/cc/test_crud.py::TestModuleCRUD::test_create_module_with_config - AttributeError: '_DummyConn' object has no attribute 'prepare'
ERROR tests/unit/backend/cc/test_crud.py::TestModuleCRUD::test_get_module_by_id_exists - AttributeError: '_DummyConn' object has no attribute 'prepare'
ERROR tests/unit/backend/cc/test_crud.py::TestModuleCRUD::test_get_module_by_id_not_exists - AttributeError: '_DummyConn' object has no attribute 'prepare'
ERROR tests/unit/backend/cc/test_crud.py::TestModuleCRUD::test_get_module_by_name_exists - AttributeError: '_DummyConn' object has no attribute 'prepare'
ERROR tests/unit/backend/cc/test_crud.py::TestModuleCRUD::test_get_module_by_name_not_exists - AttributeError: '_DummyConn' object has no attribute 'prepare'
ERROR tests/unit/backend/cc/test_crud.py::TestModuleCRUD::test_get_modules_empty - AttributeError: '_DummyConn' object has no attribute 'prepare'
ERROR tests/unit/backend/cc/test_crud.py::TestModuleCRUD::test_get_modules_with_data - AttributeError: '_DummyConn' object has no attribute 'prepare'
ERROR tests/unit/backend/cc/test_crud.py::TestModuleCRUD::test_get_modules_pagination - AttributeError: '_DummyConn' object has no attribute 'prepare'
ERROR tests/unit/backend/cc/test_crud.py::TestModuleCRUD::test_update_module_success - AttributeError: '_DummyConn' object has no attribute 'prepare'
ERROR tests/unit/backend/cc/test_crud.py::TestModuleCRUD::test_update_module_not_exists - AttributeError: '_DummyConn' object has no attribute 'prepare'
ERROR tests/unit/backend/cc/test_crud.py::TestModuleCRUD::test_update_module_ignore_invalid_fields - AttributeError: '_DummyConn' object has no attribute 'prepare'
ERROR tests/unit/backend/cc/test_crud.py::TestModuleCRUD::test_delete_module_success - AttributeError: '_DummyConn' object has no attribute 'prepare'
ERROR tests/unit/backend/cc/test_crud.py::TestModuleCRUD::test_delete_module_not_exists - AttributeError: '_DummyConn' object has no attribute 'prepare'
ERROR tests/unit/backend/cc/test_log_l1.py::TestLogL1BasicFunctionality::test_event_only_logging - AttributeError: '_DummyConn' object has no attribute 'prepare'
ERROR tests/unit/backend/cc/test_log_l1.py::TestLogL1BasicFunctionality::test_prompt_only_logging - AttributeError: '_DummyConn' object has no attribute 'prepare'
ERROR tests/unit/backend/cc/test_log_l1.py::TestLogL1BasicFunctionality::test_combined_logging - AttributeError: '_DummyConn' object has no attribute 'prepare'
ERROR tests/unit/backend/cc/test_log_l1.py::TestLogL1BasicFunctionality::test_minimal_logging - AttributeError: '_DummyConn' object has no attribute 'prepare'
ERROR tests/unit/backend/cc/test_log_l1.py::TestLogL1RequestIdHandling::test_request_id_from_context - AttributeError: '_DummyConn' object has no attribute 'prepare'
ERROR tests/unit/backend/cc/test_log_l1.py::TestLogL1RequestIdHandling::test_request_id_fallback - AttributeError: '_DummyConn' object has no attribute 'prepare'
ERROR tests/unit/backend/cc/test_log_l1.py::TestLogL1RequestIdHandling::test_explicit_request_id - AttributeError: '_DummyConn' object has no attribute 'prepare'
ERROR tests/unit/backend/cc/test_log_l1.py::TestLogL1LogfireIntegration::test_logfire_span_attributes - AttributeError: '_DummyConn' object has no attribute 'prepare'
ERROR tests/unit/backend/cc/test_log_l1.py::TestLogL1LogfireIntegration::test_logfire_graceful_degradation - AttributeError: '_DummyConn' object has no attribute 'prepare'
ERROR tests/unit/backend/cc/test_log_l1.py::TestLogL1ParameterHandling::test_empty_payload - AttributeError: '_DummyConn' object has no attribute 'prepare'
ERROR tests/unit/backend/cc/test_log_l1.py::TestLogL1ParameterHandling::test_partial_prompt_data - AttributeError: '_DummyConn' object has no attribute 'prepare'
ERROR tests/unit/backend/cc/test_log_l1.py::TestLogL1ParameterHandling::test_complex_payload_data - AttributeError: '_DummyConn' object has no attribute 'prepare'
ERROR tests/unit/backend/cc/test_logging_redis_publish.py::TestLogL1RedisPublishAfterCommit::test_publish_after_commit_event_log - AttributeError: '_DummyConn' object has no attribute 'prepare'
ERROR tests/unit/backend/cc/test_logging_redis_publish.py::TestLogL1RedisPublishAfterCommit::test_no_publish_without_event_log - AttributeError: '_DummyConn' object has no attribute 'prepare'
ERROR tests/unit/backend/cc/test_logging_redis_publish.py::TestLogL1RedisPublishAfterCommit::test_publish_with_trace_id - AttributeError: '_DummyConn' object has no attribute 'prepare'
ERROR tests/unit/backend/cc/test_logging_redis_publish.py::TestLogL1RedisPublishAfterCommit::test_publish_with_request_id - AttributeError: '_DummyConn' object has no attribute 'prepare'
ERROR tests/unit/backend/cc/test_logging_redis_publish.py::TestLogL1RedisPublishErrorIsolation::test_database_success_despite_publish_failure - AttributeError: '_DummyConn' object has no attribute 'prepare'
ERROR tests/unit/backend/cc/test_logging_redis_publish.py::TestLogL1RedisPublishErrorIsolation::test_publish_error_logged_but_not_raised - AttributeError: '_DummyConn' object has no attribute 'prepare'
ERROR tests/unit/backend/cc/test_logging_redis_publish.py::TestSQLAlchemyAfterCommitIntegration::test_after_commit_listener_registered - AttributeError: '_DummyConn' object has no attribute 'prepare'
ERROR tests/unit/backend/cc/test_logging_redis_publish.py::TestSQLAlchemyAfterCommitIntegration::test_outbox_pattern_session_isolation - AttributeError: '_DummyConn' object has no attribute 'prepare'
ERROR tests/unit/backend/cc/test_logging_redis_publish.py::TestRedisChannelAndMessageFormat::test_correct_channel_name - AttributeError: '_DummyConn' object has no attribute 'prepare'
ERROR tests/unit/backend/cc/test_logging_redis_publish.py::TestRedisChannelAndMessageFormat::test_message_format_structure - AttributeError: '_DummyConn' object has no attribute 'prepare'
ERROR tests/unit/backend/cc/test_logging_redis_publish.py::TestPerformanceAndLatencyTargets::test_logging_latency_target - AttributeError: '_DummyConn' object has no attribute 'prepare'
ERROR tests/unit/backend/cc/test_logging_redis_publish.py::TestPerformanceAndLatencyTargets::test_fire_and_forget_pattern - AttributeError: '_DummyConn' object has no attribute 'prepare'
ERROR tests/unit/backend/cc/test_mem0_models.py::TestBaseLogModel::test_baselog_creation_with_required_fields - AttributeError: '_DummyConn' object has no attribute 'prepare'
ERROR tests/unit/backend/cc/test_mem0_models.py::TestBaseLogModel::test_baselog_with_payload - AttributeError: '_DummyConn' object has no attribute 'prepare'
ERROR tests/unit/backend/cc/test_mem0_models.py::TestBaseLogModel::test_baselog_string_representation - AttributeError: '_DummyConn' object has no attribute 'prepare'
ERROR tests/unit/backend/cc/test_mem0_models.py::TestPromptTraceModel::test_prompttrace_creation_with_required_fields - AttributeError: '_DummyConn' object has no attribute 'prepare'
ERROR tests/unit/backend/cc/test_mem0_models.py::TestPromptTraceModel::test_prompttrace_with_optional_fields - AttributeError: '_DummyConn' object has no attribute 'prepare'
ERROR tests/unit/backend/cc/test_mem0_models.py::TestEventLogModel::test_eventlog_creation_with_required_fields - AttributeError: '_DummyConn' object has no attribute 'prepare'
ERROR tests/unit/backend/cc/test_mem0_models.py::TestEventLogModel::test_eventlog_with_event_data - AttributeError: '_DummyConn' object has no attribute 'prepare'
ERROR tests/unit/backend/cc/test_mem0_models.py::TestModelBasicIntegration::test_cascade_delete_behavior - AttributeError: '_DummyConn' object has no attribute 'prepare'
ERROR tests/unit/common/test_base_subscriber_comprehensive.py::TestBaseSubscriberAdvancedScenarios::test_memory_cleanup_on_stop
ERROR tests/unit/common/test_base_subscriber_comprehensive.py::TestBaseSubscriberAdvancedScenarios::test_message_ttl_handling
ERROR tests/unit/common/test_base_subscriber_comprehensive.py::TestBaseSubscriberAdvancedScenarios::test_batch_processing_edge_cases
ERROR tests/unit/common/test_redis_config_matrix.py::TestRedisConfigurationInDockerEnvironments::test_docker_compose_service_discovery
ERROR tests/unit/common/test_redis_config_matrix.py::TestRedisConfigurationInDockerEnvironments::test_kubernetes_environment_variables
ERROR tests/unit/common/test_redis_config_matrix.py::TestRedisConfigurationInDockerEnvironments::test_cloud_provider_configurations
ERROR tests/unit/common/test_redis_config_matrix.py::TestRedisConfigurationSecurity::test_password_url_encoding
ERROR tests/unit/common/test_redis_config_matrix.py::TestRedisConfigurationSecurity::test_credential_masking_in_logs
ERROR tests/unit/common/test_redis_config_matrix.py::TestRedisConfigurationSecurity::test_configuration_validation
ERROR tests/unit/common/test_redis_pubsub_comprehensive.py::TestRedisPubSubComprehensive::test_disconnect_partial_cleanup_scenarios - Exception: Cleanup error
ERROR tests/unit/common/test_redis_pubsub_comprehensive.py::TestCircuitBreakerIntegration::test_circuit_breaker_protects_all_operations
ERROR tests/unit/common/test_redis_pubsub_comprehensive.py::TestCircuitBreakerIntegration::test_circuit_breaker_recovery_scenarios
= 134 failed, 622 passed, 391 skipped, 2 xfailed, 17 warnings, 241 errors in 442.75s (0:07:22) =
⚠️  Tests failed as expected during Phase 2 Sprint 1 - database infrastructure pending
📊 Analyzing new code coverage...
Collecting diff-cover
  Downloading diff_cover-9.4.1-py3-none-any.whl.metadata (18 kB)
Requirement already satisfied: Jinja2>=2.7.1 in /opt/hostedtoolcache/Python/3.13.5/x64/lib/python3.13/site-packages (from diff-cover) (3.1.6)
Requirement already satisfied: Pygments<3.0.0,>=2.19.1 in /opt/hostedtoolcache/Python/3.13.5/x64/lib/python3.13/site-packages (from diff-cover) (2.19.2)
Collecting chardet>=3.0.0 (from diff-cover)
  Downloading chardet-5.2.0-py3-none-any.whl.metadata (3.4 kB)
Requirement already satisfied: pluggy<2,>=0.13.1 in /opt/hostedtoolcache/Python/3.13.5/x64/lib/python3.13/site-packages (from diff-cover) (1.6.0)
Requirement already satisfied: MarkupSafe>=2.0 in /opt/hostedtoolcache/Python/3.13.5/x64/lib/python3.13/site-packages (from Jinja2>=2.7.1->diff-cover) (3.0.2)
Downloading diff_cover-9.4.1-py3-none-any.whl (54 kB)
Downloading chardet-5.2.0-py3-none-any.whl (199 kB)
Installing collected packages: chardet, diff-cover
Successfully installed chardet-5.2.0 diff-cover-9.4.1
/opt/hostedtoolcache/Python/3.13.5/x64/lib/python3.13/site-packages/diff_cover/diff_cover_tool.py:295: UserWarning: The --html-report option is deprecated. Use --format html:diff-coverage.html instead.
  warnings.warn(
Traceback (most recent call last):
  File "/opt/hostedtoolcache/Python/3.13.5/x64/lib/python3.13/site-packages/diff_cover/git_diff.py", line 70, in diff_committed
    return execute(
           ~~~~~~~^
        self._default_git_args + self._default_diff_args + [diff_range]
        ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    )[0]
    ^
  File "/opt/hostedtoolcache/Python/3.13.5/x64/lib/python3.13/site-packages/diff_cover/command_runner.py", line 36, in execute
    raise CommandError(stderr)
diff_cover.command_runner.CommandError: fatal: ambiguous argument 'origin/release/phase2-sprint2...HEAD': unknown revision or path not in the working tree.
Use '--' to separate paths from revisions, like this:
'git <command> [<revision>...] -- [<file>...]'
The above exception was the direct cause of the following exception:
Traceback (most recent call last):
  File "/opt/hostedtoolcache/Python/3.13.5/x64/bin/diff-cover", line 8, in <module>
    sys.exit(main())
             ~~~~^^
  File "/opt/hostedtoolcache/Python/3.13.5/x64/lib/python3.13/site-packages/diff_cover/diff_cover_tool.py", line 354, in main
    percent_covered = generate_coverage_report(
        arg_dict["coverage_files"],
    ...<12 lines>...
        expand_coverage_report=arg_dict["expand_coverage_report"],
    )
  File "/opt/hostedtoolcache/Python/3.13.5/x64/lib/python3.13/site-packages/diff_cover/diff_cover_tool.py", line 255, in generate_coverage_report
    reporter.generate_report(output_file)
    ~~~~~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^
  File "/opt/hostedtoolcache/Python/3.13.5/x64/lib/python3.13/site-packages/diff_cover/report_generator.py", line 302, in generate_report
    report = template.render(self._context())
                             ~~~~~~~~~~~~~^^
  File "/opt/hostedtoolcache/Python/3.13.5/x64/lib/python3.13/site-packages/diff_cover/report_generator.py", line 351, in _context
    context = super().report_dict()
  File "/opt/hostedtoolcache/Python/3.13.5/x64/lib/python3.13/site-packages/diff_cover/report_generator.py", line 220, in report_dict
    src_stats = {src: self._src_path_stats(src) for src in self.src_paths()}
                                                           ~~~~~~~~~~~~~~^^
  File "/opt/hostedtoolcache/Python/3.13.5/x64/lib/python3.13/site-packages/diff_cover/report_generator.py", line 86, in src_paths
    for src, summary in self._diff_violations().items()
                        ~~~~~~~~~~~~~~~~~~~~~^^
  File "/opt/hostedtoolcache/Python/3.13.5/x64/lib/python3.13/site-packages/diff_cover/report_generator.py", line 196, in _diff_violations
    src_paths_changed = self._diff.src_paths_changed()
  File "/opt/hostedtoolcache/Python/3.13.5/x64/lib/python3.13/site-packages/diff_cover/diff_reporter.py", line 167, in src_paths_changed
    diff_dict = self._git_diff()
  File "/opt/hostedtoolcache/Python/3.13.5/x64/lib/python3.13/site-packages/diff_cover/diff_reporter.py", line 235, in _git_diff
    for diff_str in self._get_included_diff_results():
                    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^^
  File "/opt/hostedtoolcache/Python/3.13.5/x64/lib/python3.13/site-packages/diff_cover/diff_reporter.py", line 209, in _get_included_diff_results
    included = [self._git_diff_tool.diff_committed(self._compare_branch)]
                ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^
  File "/opt/hostedtoolcache/Python/3.13.5/x64/lib/python3.13/site-packages/diff_cover/git_diff.py", line 75, in diff_committed
    raise ValueError(
    ...<6 lines>...
    ) from e
ValueError:
Could not find the branch to compare to. Does 'origin/release/phase2-sprint2' exist?
the `--compare-branch` argument allows you to set a different branch.
❌ New code coverage below 97% threshold
📈 All new code must achieve ≥97% test coverage
Error: Process completed with exit code 1.
