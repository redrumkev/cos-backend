⏺ COS Test Suite Infrastructure Stability - 4-Agent Orchestration for All Green State

## Context

Building on the MASSIVE SUCCESS of the first 4-agent orchestration (95.8% pass rate achieved!), we now tackle the final 53 infrastructure stability failures to reach the coveted "All Green" state. This session focuses on async coordination, container lifecycle management, and Redis integration stability.

## Your Role

You are the orchestrator (Claude/Opus) managing 4 specialized infrastructure agents to eliminate the remaining 53 test failures and achieve 98%+ pass rate with zero manual intervention required.

## Current Achievement Status

**First Orchestration Results:**
- **From**: 84.4% pass rate (113 failures)
- **To**: 95.8% pass rate (53 failures)
- **Achievement**: 60 failures eliminated, exceeded 90% target by 5.8%!
- **Success**: Model defaults, UUID types, API conflicts, schema issues ✅

## Current Test Status

- **Total**: 1,322 tests
- **Passed**: 1,269 (95.8%)
- **Failed**: 53 (4.0%)
- **Target**: Fix 42-50 tests to reach 98%+ pass rate (All Green State)

## Critical User Pain Point to Solve

**Docker Container Manual Intervention**: User must manually click "play" in Docker Desktop 5-6 times per test run when Redis containers pause and fail to unpause automatically. This MUST be eliminated.

## Infrastructure Stability Orchestration Plan

Launch all 4 agents in parallel targeting infrastructure reliability:

### Agent 1: Async Event Loop Stabilizer (12-15 test fixes)

**Target Pattern**: `RuntimeError: asyncio.run() cannot be called from a running event loop`

**Target Files**:
- `tests/performance/test_comprehensive_benchmarks.py`
- Redis performance tests with Queue event loop binding issues

**Mission**:
1. Use Read to examine performance test files with async conflicts
2. Replace asyncio.run() calls with proper async fixtures
3. Fix "Queue bound to different event loop" errors in Redis tests
4. Ensure all performance tests use existing event loop properly
5. Use mcp__zen__debug with o3-mini-high to trace complex async issues
6. Run pytest on specific failing async tests to verify fixes

**Expected fixes**: All asyncio runtime errors and event loop conflicts

### Agent 2: Docker Container Lifecycle Manager (8-12 test fixes)

**Target Pattern**: `subprocess.CalledProcessError: Command '['/usr/local/bin/docker', 'unpause', 'cos_redis']' returned non-zero exit status 1`

**Critical Mission**: **ELIMINATE MANUAL DOCKER DESKTOP INTERVENTION**

**Target Files**:
- `tests/performance/test_failure_scenarios.py`
- `tests/performance/test_production_readiness.py`

**Mission**:
1. Use Grep to find all docker pause/unpause commands in test files
2. Implement graceful container state checking before pause/unpause operations
3. Add container health verification and retry logic
4. Replace brittle pause/unpause cycles with stable test isolation
5. Use mcp__zen__thinkdeep with o3 to design robust container lifecycle patterns
6. Ensure tests handle Redis unavailability gracefully without manual intervention

**Expected fixes**: All Docker container management failures + zero manual clicks required

### Agent 3: API Endpoint & Dependencies Fixer (10-12 test fixes)

**Target Patterns**:
- `assert 404 == 200` (endpoints returning 404 instead of 200)
- `assert False` in deps.py tests

**Target Files**:
- `tests/unit/backend/cc/test_deps.py`
- Various API endpoint tests with 404 errors

**Mission**:
1. Use Read to examine dependency injection setup in test_deps.py
2. Investigate why API endpoints return 404 instead of 200
3. Fix database session dependency injection in test environment
4. Ensure test server configuration matches expectations
5. Use mcp__zen__codereview with gemini-2.5-pro to validate dependency patterns
6. Run targeted API endpoint tests to verify routing works

**Expected fixes**: All API endpoint 404 errors and dependency injection failures

### Agent 4: Redis Pub/Sub Integration Restorer (12-15 test fixes)

**Target Pattern**: `Expected '_publish_l1_event' to have been called once. Called 0 times`

**Target Files**:
- `tests/unit/backend/cc/test_logging_redis_publish.py`
- `tests/unit/backend/cc/test_logging_redis_simple.py`

**Mission**:
1. Use Read to examine SQLAlchemy after-commit hook integration
2. Investigate why _publish_l1_event is not being called
3. Restore Redis pub/sub integration with SQLAlchemy sessions
4. Fix after-commit listener registration in test environment
5. Use mcp__zen__tracer with o3-mini to trace the pub/sub integration flow
6. Ensure Redis publishing works properly in test isolation

**Expected fixes**: All Redis pub/sub integration failures + L1.5 memory layer restoration

## Success Criteria

- **All 4 agents complete their infrastructure missions**
- **42-50 tests fixed** (targeting 95.8% → 98%+ pass rate)
- **Zero manual Docker Desktop intervention required**
- **Full test suite runs start to finish automatically**
- **All async, container, API, and Redis integration systems stable**
- **True "All Green" state achieved**

## Enhanced Tooling Strategy

**For Complex Issues**: Use Zen MCP tools with high reasoning:
- `mcp__zen__debug` with o3-mini-high for async tracing
- `mcp__zen__thinkdeep` with o3 for container lifecycle design
- `mcp__zen__codereview` with gemini-2.5-pro for dependency validation
- `mcp__zen__tracer` with o3-mini for Redis integration flow analysis

## Verification Commands

After all agents complete:

### Quick Targeted Verification
```bash
# Test each agent's focus area
uv run pytest tests/performance/test_comprehensive_benchmarks.py::TestAPIEndpointBenchmarks::test_cc_module_endpoints_latency -v
uv run pytest tests/performance/test_failure_scenarios.py::TestRedisFailureScenarios::test_redis_connection_failure_graceful_degradation -v
uv run pytest tests/unit/backend/cc/test_deps.py::test_get_cc_db_returns_session -v
uv run pytest tests/unit/backend/cc/test_logging_redis_publish.py::TestLogL1RedisPublishAfterCommit::test_publish_after_commit_event_log -v
```

### Infrastructure Stability Test
```bash
# Include infrastructure tests, exclude only the slowest
uv run pytest tests/ --tb=short -q \
  --ignore=tests/common/test_pubsub.py \
  --ignore=tests/unit/common/test_redis_pubsub_comprehensive.py
```

### All Green Validation (Ultimate Goal)
```bash
# Final verification - entire suite with zero manual intervention
uv run pytest tests/ --tb=short -q
```

## Tools to Use

- **Standard**: Read/Grep/Edit for code changes
- **Enhanced**: Zen MCP tools for complex infrastructure debugging
- **Async**: mcp__zen__debug for event loop conflicts
- **Container**: mcp__zen__thinkdeep for lifecycle management
- **API**: mcp__zen__codereview for dependency patterns
- **Redis**: mcp__zen__tracer for pub/sub integration
- **Bash**: For running targeted tests and verification
- **Task**: For parallel agent execution

## Strategic Vision

This orchestration represents the final push toward a rock-solid Creative Operating System foundation. Once achieved, authors can iterate fearlessly on their 100+ book legacy vision, knowing the technical infrastructure provides instant feedback without manual intervention interruptions.

**The Goal**: Transform from "pretty good" (95.8%) to "bulletproof" (98%+) reliability.

Begin by launching all 4 infrastructure agents simultaneously to eliminate the final 53 barriers to All Green State!
