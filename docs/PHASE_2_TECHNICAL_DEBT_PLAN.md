# Phase 2 Technical Debt - Methodology & Reference

---
status: reference
purpose: systematic_test_restoration_methodology
last_updated: 2025-06-27
phase_status: methodology_validated
---

## Sprint-Based Re-enablement Plan

### Sprint 2.1: Database Foundation
**Priority**: CRITICAL - Foundation for all other layers
**Duration**: 2 weeks
**Remove skips from**: P2-ASYNC-001, P2-SCHEMA-001, P2-MODELS-001, P2-ALEMBIC-001, P2-CONNECT-001
**Expected Tests Restored**: ~155 tests
**Success Criteria**: All database and migration tests pass

### Sprint 2.2: Application Layer
**Priority**: HIGH - Core business logic
**Duration**: 2 weeks
**Remove skips from**: P2-MEM0-001, P2-ROUTER-001, P2-SERVICE-001
**Expected Tests Restored**: ~205 tests
**Success Criteria**: API endpoints and service logic fully functional

### Sprint 2.3: Graph Layer
**Priority**: MEDIUM - Semantic features
**Duration**: 1 week
**Remove skips from**: P2-GRAPH-001
**Expected Tests Restored**: ~40 tests
**Success Criteria**: Neo4j integration working with async patterns

### Sprint 2.4: Integration Layer
**Priority**: HIGH - End-to-end validation
**Duration**: 1 week
**Remove skips from**: P2-INTEGRATION-001
**Expected Tests Restored**: ~165 tests
**Success Criteria**: Full stack integration tests pass, 97% coverage achieved

## Re-enablement Commands

```bash
# Sprint 2.1: Database Foundation
# Find and remove skip decorators for database-related tests
find tests/ -name "*.py" -exec grep -l "P2-ASYNC-001\|P2-SCHEMA-001\|P2-MODELS-001\|P2-ALEMBIC-001\|P2-CONNECT-001" {} \;

# Sprint 2.2: Application Layer
# Find and remove skip decorators for application tests
find tests/ -name "*.py" -exec grep -l "P2-MEM0-001\|P2-ROUTER-001\|P2-SERVICE-001" {} \;

# Sprint 2.3: Graph Layer
# Find and remove skip decorators for graph tests
find tests/ -name "*.py" -exec grep -l "P2-GRAPH-001" {} \;

# Sprint 2.4: Integration Layer
# Find and remove skip decorators for integration tests
find tests/ -name "*.py" -exec grep -l "P2-INTEGRATION-001" {} \;
```

## Monitoring and Progress Tracking

### Success Metrics per Sprint
- **Test Count**: Track number of passing tests after skip removal
- **Coverage**: Monitor coverage percentage improvement
- **CI Duration**: Ensure CI runtime remains under 10 minutes
- **Error Types**: Track and categorize any new error patterns

### Quality Gates
- All removed skips must result in passing tests
- No new test failures introduced during skip removal
- Coverage must increase proportionally with restored tests
- No performance degradation in CI pipeline

## Risk Mitigation

### High-Risk Areas
1. **Database Connection Pooling**: May require careful async configuration
2. **Neo4j Integration**: External service dependency timing
3. **Integration Tests**: Complex setup/teardown requirements

### Fallback Strategy
- If any sprint introduces instability, temporarily re-add skip decorators
- Fix underlying issues before proceeding to next sprint
- Maintain branch stability at all times

## Open P2 Trigger Cleanup Focus

Below are the **only** Phase-2 tags that still have live `pytest.mark.skip` lines in the codebase. Each row shows the grep pattern to search for and the exact files/lines that need attention. Once every file in a row is fixed (skip removed or converted to an assertion), the row should be deleted from this list.

| Trigger Pattern | Active Skip Locations |
|-----------------|-----------------------|
| `P2-SCHEMA-001` | tests/backend/cc/test_schemas_coverage.py:24<br/>tests/backend/cc/test_schemas.py:21<br/>tests/unit/backend/cc/test_schemas.py:22<br/>tests/unit/backend/cc/test_database_schema.py:9 |
| `P2-MODELS-001` | tests/backend/cc/test_models_coverage.py:19<br/>tests/unit/backend/cc/test_models_coverage.py:19<br/>tests/unit/backend/cc/test_models.py:19 |
| `P2-ALEMBIC-001` | tests/unit/db/test_alembic_env.py:16 |
| `P2-ROUTER-001` | tests/unit/backend/cc/test_router.py:14 |
| `P2-SERVICE-001` | tests/backend/cc/test_services_edge_cases.py:28<br/>tests/unit/backend/cc/test_services.py:23 |
| `P2-GRAPH-001` | tests/graph/test_router.py:14<br/>tests/graph/test_registry.py:18<br/>tests/graph/test_service.py:13 |

> **Goal:** Iterate until this table is empty—meaning **zero** `P2-*` skip markers remain in the repo.

---

*The legacy, fully-resolved triggers (`P2-ASYNC-001`, `P2-CONNECT-001`, `P2-MEM0-001`, `P2-INTEGRATION-001`) have been removed from this document; their work is archived in the history file.*

## Total Test Impact
- **Total Skipped Tests**: ~565 tests
- **Current Passing Tests**: ~5-10 tests (basic unit tests)
- **Phase 2 Target**: 570+ tests with 97% coverage

## Current Technical Priorities

*Phase 2 functional work is declared **100 % complete**, but only **~322 of 565** tests (≈ 57 %) execute green.  The remaining ~240 tests are still blocked by `pytest.skip` markers or lingering infrastructure gaps.*

1. **Eliminate all active `P2-*` skip markers**
   • Work through the two tables below (core triggers + other tags) and remove each skip.
   • Re-run the suite after every small batch to surface real failures early.
2. **Fix failing tests uncovered by skip removal**
   • Prioritise database → models → router/service → graph to minimise cascading failures.
3. **Drive coverage to ≥ 97 %**
   • Once skips are gone, create new tests for any code still uncovered.
4. **CI signal must stay green & < 10 min**
   • Optimise fixtures where needed; watch for DB-locking or long-running integration cases.

### Other Phase-2 Tags With Active `skip` Markers

| Tag | Active Skip Locations |
|-----|-----------------------|
| `P2-DEPS-001` | tests/backend/cc/test_deps.py:10<br/>tests/backend/cc/test_deps_coverage.py:15<br/>tests/unit/backend/cc/test_deps_isolated.py:17<br/>tests/unit/backend/cc/test_deps.py:9 |
| `P2-CRUD-001` | tests/backend/cc/test_crud_coverage.py:15 |
| `P2-CONFIG-001` | tests/common/test_config.py:9 |
| `P2-COVERAGE-001` | tests/unit/backend/cc/test_coverage_focused.py:19 |
| `P2-MAIN-001` | tests/unit/backend/cc/test_cc_main.py:13 |

> **Note:** Tags such as `P2-DB-001`, `P2-UTILS-001`, etc. now appear **only in commented lines**. Keep an eye out, but they no longer gate test execution.

---

- **Total Skipped Tests Remaining**: *dynamic* — equal to the count of rows in the two tables above.
- **Passing Tests**: ~322 / 565
- **Target**: 565 / 565 tests passing, ≥ 97 % coverage, zero `P2-*` strings in repo.

---

**Generated**: Phase 2 Plan Reference
**Extracted**: June 27, 2025
**Source**: Original PHASE_2_TECHNICAL_DEBT.md (lines 109-271)
**Status**: Methodology validated - all P2 triggers successfully completed
