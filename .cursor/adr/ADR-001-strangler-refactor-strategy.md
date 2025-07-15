# ADR-001: Strangler Fig Refactor Strategy for COS

## Status

Accepted - Partially Implemented

### Implementation Progress:
- ✅ Core V2 directory structure created
- ✅ Pattern system established (per ADR-002)
- ⚠️ Shim import strategy not yet implemented
- ⚠️ Feature-based migration in early stages
- ✅ Test-driven migration principles being followed
- ✅ Redis Pub/Sub facilitator in place

## Context

The Creative Operating System (COS) is rapidly evolving to support a 100+ book legacy vision. As the system grows, we face several challenges:

1. **Technical Debt Accumulation**: The current codebase has evolved organically through rapid prototyping, resulting in some areas that need restructuring for long-term maintainability.

2. **Module Interdependencies**: The existing code has tight coupling between components that will eventually need to be separated into independent modules (CC, PEM, AIC, etc.).

3. **Production Stability Requirements**: COS must maintain continuous operation while undergoing significant architectural changes, as it serves the author's creative workflow.

4. **Test Coverage Goals**: We need to achieve and maintain 97%+ test coverage while refactoring, ensuring we can "step forward and refactor without fear."

5. **Multi-Layer Memory Architecture**: The system's complex memory hierarchy (L1-L4) requires careful migration to avoid data loss or corruption.

The Strangler Fig pattern, coined by Martin Fowler, provides a proven approach for gradually modernizing systems while maintaining production stability. Like its namesake plant that slowly envelops and replaces a host tree, this pattern allows us to incrementally replace old code with new implementations.

## Decision

We will adopt the Strangler Fig pattern for refactoring COS, implementing it through the following strategy:

### 1. Core V2 Parallel Structure

Create a `core_v2` package alongside the existing code structure:

```
src/
├── backend/          # Existing code
│   └── cc/
├── common/          # Existing shared utilities
├── core_v2/         # New refactored code
│   ├── cc/
│   ├── common/
│   └── shared/
```

### 2. Shim Import Strategy

Implement intelligent import shims that gradually redirect from old to new code:

```python
# src/backend/cc/__init__.py
try:
    # Attempt to use new implementation
    from src.core_v2.cc import *
except ImportError:
    # Fall back to existing implementation
    from src.backend.cc.legacy import *
```

### 3. Feature-Based Migration

Migrate functionality in thin, testable slices:
- Each slice must be independently deployable
- Maintain feature parity during migration
- Use feature flags for controlled rollout

### 4. Test-Driven Migration

Every migration step follows strict TDD principles:
- Write tests for existing behavior first
- Ensure tests pass with old implementation
- Implement new code to pass same tests
- Gradually extend tests for improvements

### 5. Redis Pub/Sub as Migration Facilitator

Leverage the existing Redis event highway to decouple old and new code:
- Old code publishes events
- New code subscribes and processes
- Gradual transition of publishers

## Consequences

### Positive Consequences

1. **Zero Downtime Migration**: The system remains fully operational throughout the refactoring process.

2. **Incremental Risk Management**: Each change is small and reversible, reducing the blast radius of any issues.

3. **Parallel Development**: Team members can work on new implementations while others maintain existing code.

4. **Progressive Improvement**: We can introduce better patterns and practices incrementally rather than all at once.

5. **Testing Confidence**: The parallel structure allows comprehensive testing of new code against existing behavior.

6. **Gradual Module Separation**: Natural boundaries emerge as we refactor, preparing for future multi-module architecture.

### Trade-offs and Challenges

1. **Temporary Complexity**: During migration, the codebase will have dual implementations, increasing cognitive load.

2. **Maintenance Overhead**: Bug fixes may need to be applied to both old and new code during transition.

3. **Extended Timeline**: The incremental approach takes longer than a "big bang" rewrite but with significantly less risk.

4. **Routing Complexity**: Managing the routing between old and new implementations requires careful orchestration.

5. **Resource Requirements**: Running parallel systems may temporarily increase infrastructure costs.

## Implementation Details

### Phase 1: Infrastructure Setup (Week 1) - PARTIALLY COMPLETE
- ✅ Create `core_v2` directory structure
- ❌ Implement base shim import system (not started)
- ⚠️ Set up parallel test suites (tests exist but not parallel structure)
- ❌ Configure feature flags (not implemented)

### Phase 2: Common Module Migration (Weeks 2-3) - IN PROGRESS
- ⚠️ Migrate database connection management (patterns used but not fully migrated)
- ✅ Refactor Redis configuration with new patterns (error_handling.py adopted)
- ✅ Update logging and middleware components (using patterns)
- ✅ Ensure 100% backward compatibility (maintained)

### Phase 3: CC Module Refactoring (Weeks 4-6) - NOT STARTED
- ❌ Extract health check functionality
- ❌ Separate concerns for settings management
- ❌ Implement new router structure (pattern exists but not applied)
- ❌ Migrate mem0 integration

### Phase 4: Validation and Cutover (Week 7) - NOT STARTED
- ❌ Comprehensive integration testing
- ❌ Performance benchmarking
- ❌ Gradual traffic migration
- ❌ Old code deprecation

### Monitoring and Rollback Strategy

1. **Dual Metrics**: Monitor both old and new implementations
2. **Circuit Breakers**: Automatic fallback to old code on errors
3. **Feature Flags**: Instant rollback capability per feature
4. **A/B Testing**: Validate new implementations with subset of traffic

### Success Criteria

- All tests remain green throughout migration
- No degradation in performance metrics
- 97%+ test coverage maintained
- Zero production incidents during migration
- Clean separation of module boundaries

## References

- Martin Fowler's original article on the Strangler Fig Application
- Shopify's experience with Strangler Fig pattern
- Microsoft Azure Architecture Center - Strangler Fig Pattern
- COS CLAUDE.md and architectural guidelines

## Decision Date

2025-07-06

## Decision Makers

- Kevin MBA (Strategist/Visionary)
- Claude Code (Tactical Orchestrator)

## Review Schedule

This ADR will be reviewed after Phase 1 completion and adjusted based on learnings.
