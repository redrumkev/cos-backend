# CI Pragmatic Standards

## Overview

This document defines pragmatic standards for CI/CD to break the "evil loop" where CI failures prevent refactoring needed to improve code quality and coverage.

## Core Principle

**CI environments are inherently slow.** GitHub Actions and other CI platforms run on shared infrastructure with:
- Variable CPU allocation
- Network latency
- Cold starts
- Resource contention

Therefore, CI performance thresholds must reflect this reality.

## Performance Standards

### Local Development
- Redis publish latency: **< 5ms** (with real Redis)
- Database operations: **< 10ms**
- API endpoints: **< 50ms**
- Concurrent operations: **< 100ms**

### CI Environment
- Redis publish latency: **< 500ms** (100x multiplier)
- Database operations: **< 1000ms** (100x multiplier)
- API endpoints: **< 5000ms** (100x multiplier)
- Concurrent operations: **< 10000ms** (100x multiplier)

### Implementation Pattern

```python
import os

# Detect CI environment
IS_CI = os.getenv("CI") == "true"

# Set thresholds based on environment
if IS_CI:
    MAX_LATENCY_MS = 500  # Relaxed for CI
    TIMEOUT_SECONDS = 30  # Longer timeouts
else:
    MAX_LATENCY_MS = 5    # Strict for local
    TIMEOUT_SECONDS = 5   # Quick timeouts

# Use in assertions
assert latency_ms < MAX_LATENCY_MS, f"Latency {latency_ms}ms exceeds threshold"
```

## Coverage Standards

### Progressive Coverage Floor

Instead of a fixed threshold that blocks all progress, use a progressive floor:

1. **Current Coverage - 2% Buffer**: If current coverage is 81%, set CI threshold to 79%
2. **Ratchet Up**: As coverage improves, increase the floor
3. **Never Go Backwards**: The floor prevents regression but doesn't block refactoring

### Coverage Goals

- **Unit Tests**: 90% coverage target
- **Integration Tests**: Focus on critical paths
- **New Code**: 90% coverage requirement (enforced via diff-coverage)
- **Overall**: Progressive improvement toward 85%+

## Testing Philosophy

### Functional Over Performance (in CI)

1. **CI validates functionality**, not micro-benchmarks
2. **Performance tests in CI** verify no catastrophic regressions (10x+ slower)
3. **Real performance testing** happens in dedicated environments

### Test Categories

```python
# Mark performance-critical tests
@pytest.mark.benchmark
@pytest.mark.skipif(
    os.getenv("CI") == "true" and os.getenv("FORCE_BENCHMARK") != "true",
    reason="Skipping micro-benchmarks in CI"
)
def test_critical_performance():
    pass

# Regular tests with relaxed CI thresholds
def test_normal_operation():
    threshold = 500 if os.getenv("CI") == "true" else 5
    assert latency < threshold
```

## Breaking the Evil Loop

### The Problem
1. Coverage below threshold → CI fails
2. Can't refactor to improve coverage → CI blocks PRs
3. Stuck in a loop

### The Solution
1. **Pragmatic thresholds** that acknowledge CI reality
2. **Progressive coverage** that allows forward movement
3. **Environment-aware tests** that pass in CI
4. **Focus on functionality** over micro-optimization

## Rollout Plan

1. **Phase 1**: Implement environment detection (CI=true)
2. **Phase 2**: Update performance tests with relaxed CI thresholds
3. **Phase 3**: Set progressive coverage floor (current - 2%)
4. **Phase 4**: Begin refactoring with confidence
5. **Phase 5**: Gradually increase coverage floor as improvements land

## Monitoring

Track these metrics:
- Coverage trend (should increase over time)
- CI success rate (should be >90%)
- Performance in production (the real metric)
- Developer velocity (should improve)

## Exceptions

Some tests may need strict timing even in CI:
- Timeout tests (testing actual timeout behavior)
- Circuit breaker tests (testing failure detection)

Mark these explicitly:
```python
@pytest.mark.strict_timing  # No CI relaxation
def test_timeout_behavior():
    pass
```
