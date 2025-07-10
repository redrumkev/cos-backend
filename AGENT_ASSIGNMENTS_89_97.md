# Agent Assignment Cards: Coverage Elevation Mission

## 🎯 Mission Brief
Elevate 10 files from 89-97% to 98%+ coverage using characterization tests that reflect real business scenarios.

---

## Phase 1: Quick Elevation Agents (Junior Level)

### Agent J1: Message Format Specialist
**File**: `src/common/message_format.py`
**Current Coverage**: 97% → Target: 98%+
**Missing Lines**: 41-42 (2 lines)
**Complexity**: LOW
**Time Estimate**: 1-2 hours

**Investigation Focus**:
```python
# Lines 41-42 appear to be in error handling for imports
# Likely orjson import fallback or error condition
```

**Test Strategy**:
- Simulate orjson import failure scenario
- Test JSON serialization fallback behavior
- Verify error message formatting

---

### Agent J2: CRUD Operations Specialist
**File**: `src/backend/cc/crud.py`
**Current Coverage**: 95% → Target: 98%+
**Missing Lines**: 298-300 (3 lines)
**Complexity**: LOW-MEDIUM
**Time Estimate**: 2-3 hours

**Investigation Focus**:
```python
# Lines 298-300 likely in delete or error handling
# Check for cascade delete or constraint violations
```

**Test Strategy**:
- Test deletion with foreign key constraints
- Simulate database connection errors
- Verify rollback behavior

---

### Agent J3: Mem0 CRUD Specialist
**File**: `src/backend/cc/mem0_crud.py`
**Current Coverage**: 95% → Target: 98%+
**Missing Lines**: 78, 139-140, 152 (4 lines)
**Complexity**: MEDIUM
**Time Estimate**: 2-3 hours

**Investigation Focus**:
```python
# Line 78: Likely validation or error handling
# Lines 139-140: Possibly in update operation
# Line 152: Could be in query filtering
```

**Test Strategy**:
- Test edge cases in memory operations
- Verify error handling for invalid IDs
- Test concurrent access scenarios

---

### Agent J4: Mem0 Models Specialist
**File**: `src/backend/cc/mem0_models.py`
**Current Coverage**: 95% → Target: 98%+
**Missing Lines**: 39, 150, 217, 293 (4 lines)
**Complexity**: LOW
**Time Estimate**: 2-3 hours

**Investigation Focus**:
```python
# Line 39: Likely in model validation
# Line 150: Possibly in relationship definition
# Line 217: Could be in custom property
# Line 293: Might be in string representation
```

**Test Strategy**:
- Test model validation edge cases
- Verify relationship loading
- Test serialization scenarios

---

### Agent J5: Logger Integration Specialist
**File**: `src/common/logger_logfire.py`
**Current Coverage**: 89% → Target: 98%+
**Missing Lines**: 21, 30-33 (4 lines)
**Complexity**: LOW
**Time Estimate**: 2-3 hours

**Investigation Focus**:
```python
# Line 21: TYPE_CHECKING import block
# Lines 30-33: Logfire initialization error handling
```

**Test Strategy**:
- Mock import errors for logfire
- Test initialization without API token
- Verify fallback logging behavior

---

## Phase 2: Medium Complexity Agents

### Agent M1: FastAPI Main Specialist
**File**: `src/backend/cc/cc_main.py`
**Current Coverage**: 93% → Target: 98%+
**Missing Lines**: 35-37, 80, 147 (5 lines)
**Complexity**: MEDIUM
**Time Estimate**: 3-4 hours

**Investigation Focus**:
```python
# Lines 35-37: Likely in startup event handlers
# Line 80: Possibly in middleware configuration
# Line 147: Could be in exception handler
```

**Test Strategy**:
- Test application lifecycle events
- Verify middleware error handling
- Test custom exception handlers

---

### Agent M2: Redis Config Specialist
**File**: `src/common/redis_config.py`
**Current Coverage**: 89% → Target: 98%+
**Missing Lines**: 32-34, 148-149, 157-158, 166-167, 175-176, 184-185, 244 (14 lines)
**Complexity**: MEDIUM
**Time Estimate**: 4-5 hours

**Investigation Focus**:
```python
# Lines 32-34: Import error handling
# Lines 148-149, 157-158, etc.: Environment variable fallbacks
# Line 244: Configuration validation
```

**Test Strategy**:
- Test with missing environment variables
- Verify configuration precedence
- Test connection string parsing edge cases

---

### Agent M3: Mem0 Service Specialist
**File**: `src/backend/cc/mem0_service.py`
**Current Coverage**: 95% → Target: 98%+
**Missing Lines**: 79, 145-151 (3 lines in error block)
**Complexity**: MEDIUM
**Time Estimate**: 2-3 hours

**Investigation Focus**:
```python
# Line 79: Service initialization error
# Lines 145-151: Batch operation error handling
```

**Test Strategy**:
- Test service initialization failures
- Simulate batch operation partial failures
- Verify transaction rollback

---

## Phase 3: Senior Level Agents

### Agent S1: PubSub Architecture Expert
**File**: `src/common/pubsub.py`
**Current Coverage**: 94% → Target: 98%+
**Missing Lines**: 36 lines across multiple sections
**Complexity**: HIGH
**Time Estimate**: 6-8 hours

**Investigation Focus**:
```python
# Lines 33-34, 45-47, 54-56: Import and type checking
# Lines 108-110, 381-382, 402-405: Error handling
# Lines 461-462, 477, 485-487: Connection management
# Lines 541-542, 557-558, 565-566: Cleanup paths
# Lines 831-832, 868-869: Circuit breaker integration
# Lines 989, 1207-1209: Health check edge cases
```

**Test Strategy**:
- Test circuit breaker state transitions
- Verify reconnection logic under various failures
- Test concurrent subscription management
- Validate health check timeout scenarios

**Special Notes**:
- Fix mock listen() issue first (already identified)
- Coordinate with Redis health monitor testing
- Focus on real-world failure scenarios

---

### Agent S2: Redis Health Monitor Expert
**File**: `src/common/redis_health_monitor.py`
**Current Coverage**: 94% → Target: 98%+
**Missing Lines**: 33-37, 145-150, 308-309, 336, 424-425 (15 lines)
**Complexity**: HIGH
**Time Estimate**: 4-6 hours

**Investigation Focus**:
```python
# Lines 33-37: Import handling
# Lines 145-150: Circuit breaker callback
# Lines 308-309: Health check edge case
# Line 336: Metric calculation error
# Lines 424-425: Cleanup error handling
```

**Test Strategy**:
- Test circuit breaker integration points
- Simulate various Redis failure modes
- Test metric calculation edge cases
- Verify graceful degradation

---

## Success Criteria for All Agents

1. **Coverage**: File must reach 98%+ coverage
2. **Quality**: Only real business scenarios tested
3. **Performance**: No regression in test execution time
4. **Patterns**: Follow Living Patterns v2.1.0
5. **Integration**: All tests remain green

## Coordination Guidelines

1. **Phase 1 Agents**: Can work fully in parallel
2. **Phase 2 Agents**: M1 and M3 can work in parallel with Phase 1
3. **Phase 3 Agents**: Should start after mock issue is fixed
4. **Communication**: Update progress in shared tracking document
5. **Blockers**: Escalate immediately to orchestrator

## Pre-Flight Checklist

- [ ] Check out `feature/common-coverage-patterns` branch
- [ ] Run baseline coverage report for your file
- [ ] Review existing tests for patterns
- [ ] Identify specific missing line numbers
- [ ] Plan characterization test scenarios
- [ ] Verify local test environment works

---

**Mission Start**: 2025-07-09
**Phase 1 Deadline**: 2025-07-09 EOD
**Phase 2 Deadline**: 2025-07-10 Noon
**Phase 3 Deadline**: 2025-07-10 EOD
**Mission Complete**: 2025-07-11 Morning

**Remember**: We're not just hitting numbers - we're ensuring these critical paths are properly tested for production reliability!
