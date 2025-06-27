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

## Detailed P2 Trigger Definitions (Historical Reference)

### P2-ASYNC-001: Async/SQLAlchemy Configuration
- **Files**: `tests/backend/cc/test_crud.py`
- **Issue**: Event loop mismatch in async database operations
- **Root Cause**: pytest-asyncio fixtures and SQLAlchemy async operations not properly configured
- **Solution**: Configure pytest-asyncio fixtures properly, ensure proper async session management
- **Sprint**: Sprint 2.1 (Database Foundation)
- **Estimated Tests**: ~45 tests

### P2-MEM0-001: Mem0 Module Implementation
- **Files**: `tests/backend/cc/test_mem0_*.py`
- **Issue**: Mem0 CRUD, router, service stubs need full implementation
- **Root Cause**: ScratchNote model, TTL cleanup, background tasks are stubbed
- **Solution**: Implement complete Mem0 CRUD operations, TTL cleanup service, background task orchestration
- **Sprint**: Sprint 2.2 (Memory Layer)
- **Estimated Tests**: ~85 tests

### P2-SCHEMA-001: Database Schema Creation
- **Files**: `tests/backend/cc/test_database_schema.py`
- **Issue**: cc_* tables not created by migrations
- **Root Cause**: Alembic migration scripts incomplete
- **Solution**: Write idempotent Alembic scripts for all cc module tables
- **Sprint**: Sprint 2.1 (Database Foundation)
- **Estimated Tests**: ~25 tests

### P2-MODELS-001: SQLAlchemy Model Alignment
- **Files**: `tests/backend/cc/test_models.py`
- **Issue**: Column types don't match test expectations
- **Root Cause**: UUID, JSON, Timestamp column definitions inconsistent
- **Solution**: Align SQLAlchemy model definitions with test expectations
- **Sprint**: Sprint 2.1 (Database Foundation)
- **Estimated Tests**: ~35 tests

### P2-ROUTER-001: Router Implementation
- **Files**: `tests/backend/cc/test_router*.py`
- **Issue**: Router endpoints not fully wired
- **Root Cause**: FastAPI router mounting, dependency injection incomplete
- **Solution**: Mount /cc router, wire all dependencies, add request/response validation
- **Sprint**: Sprint 2.2 (Application Layer)
- **Estimated Tests**: ~65 tests

### P2-SERVICE-001: Service Layer Implementation
- **Files**: `tests/backend/cc/test_services.py`
- **Issue**: Service functions are stubs
- **Root Cause**: Business logic layer not implemented
- **Solution**: Wire services to CRUD, implement error handling, pagination, validation
- **Sprint**: Sprint 2.2 (Application Layer)
- **Estimated Tests**: ~55 tests

### P2-ALEMBIC-001: Migration Scripts
- **Files**: `tests/db/test_alembic_migrations.py`
- **Issue**: Non-idempotent migration scripts
- **Root Cause**: Migration upgrade/downgrade logic incomplete
- **Solution**: Fix upgrade/downgrade operations, ensure schema target consistency
- **Sprint**: Sprint 2.1 (Database Foundation)
- **Estimated Tests**: ~20 tests

### P2-CONNECT-001: Database Connection Logic
- **Files**: `tests/db/test_connection.py`
- **Issue**: URL construction and pool settings failures
- **Root Cause**: Test vs production mode configuration, async engine setup
- **Solution**: Fix connection URL construction, async engine configuration, pool settings
- **Sprint**: Sprint 2.1 (Database Foundation)
- **Estimated Tests**: ~30 tests

### P2-GRAPH-001: Neo4j Client Implementation
- **Files**: `tests/graph/test_base.py`
- **Issue**: Graph client auto-connect and error handling
- **Root Cause**: Neo4j session management, transaction handling not implemented
- **Solution**: Implement Neo4j session management, transaction handling, connection pooling
- **Sprint**: Sprint 2.3 (Graph Layer)
- **Estimated Tests**: ~40 tests

### P2-INTEGRATION-001: End-to-End Integration
- **Files**: `tests/integration/backend/cc/`
- **Issue**: Real database integration not ready
- **Root Cause**: Full stack wiring incomplete
- **Solution**: Wire complete stack with test database, implement end-to-end workflows
- **Sprint**: Sprint 2.4 (Integration Layer)
- **Estimated Tests**: ~165 tests

## Total Test Impact
- **Total Skipped Tests**: ~565 tests
- **Current Passing Tests**: ~5-10 tests (basic unit tests)
- **Phase 2 Target**: 570+ tests with 97% coverage

---

**Generated**: Phase 2 Plan Reference
**Extracted**: June 27, 2025
**Source**: Original PHASE_2_TECHNICAL_DEBT.md (lines 109-271)
**Status**: Methodology validated - all P2 triggers successfully completed
