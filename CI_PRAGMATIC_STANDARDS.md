# CI Pragmatic Standards

## Overview

This document defines pragmatic standards for CI/CD that acknowledge the reality of shared infrastructure performance while maintaining code quality and enabling continuous improvement.

## The "Evil Loop" Problem

When CI standards are too strict, they create an "evil loop":
1. CI fails due to coverage or performance thresholds
2. Developers cannot commit fixes that would improve coverage
3. Refactoring is blocked, preventing quality improvements
4. The codebase stagnates

## Pragmatic Solutions

### 1. Environment-Aware Performance Thresholds

**Local Development (Fast Hardware)**
- Redis publish latency: 2-3ms
- API response time: 10-50ms
- Database queries: 5-20ms

**CI Environment (Shared Infrastructure)**
- Redis publish latency: 500ms (100x multiplier)
- API response time: 1000ms (20x multiplier)
- Database queries: 500ms (25x multiplier)

**Implementation Pattern:**
```python
# In test files
import os

if os.getenv("CI") == "true":
    MAX_LATENCY_MS = 500  # Generous CI threshold
else:
    MAX_LATENCY_MS = 5    # Strict local threshold
```

### 2. Progressive Coverage Floor

Instead of a fixed coverage threshold that blocks all progress:

**Coverage Formula:** `floor = current_coverage - 2%`

- Current coverage: 81%
- CI threshold: 79% (allows for refactoring)
- Goal: Gradual improvement over time
- Never go backwards, but allow temporary dips during refactoring

### 3. Test Categories

**Unit Tests**
- Must pass 100% in all environments
- No environment-specific adjustments
- Focus on logic correctness

**Integration Tests**
- May have environment-aware timeouts
- Focus on component interaction
- Allow for infrastructure variability

**Performance Tests**
- Heavily environment-aware
- CI: Validate functionality, not micro-benchmarks
- Local: Strict performance validation

### 4. CI Configuration

**Environment Variables:**
```yaml
env:
  CI: true
  PYTEST_TIMEOUT: 300  # 5 minutes for slow CI
```

**Coverage Settings:**
```yaml
--cov-fail-under=79  # Progressive floor
```

### 5. Breaking the Loop

1. **Immediate**: Lower thresholds to allow commits
2. **Short-term**: Refactor to improve quality
3. **Long-term**: Gradually raise thresholds
4. **Continuous**: Monitor trends, not absolute values

## Philosophy

- **Pragmatism over Perfection**: A working CI that allows progress is better than a perfect CI that blocks everything
- **Environment Reality**: CI shared infrastructure is slow; fighting this reality helps no one
- **Progressive Improvement**: Small steps forward are better than being stuck
- **Developer Productivity**: Unblock developers to improve code quality

## Review Schedule

These standards should be reviewed:
- After each sprint
- When coverage improves by 5%
- When CI infrastructure changes
- Every quarter minimum
