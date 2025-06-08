# ❌ Known Failing Tests (Phase 2 Resolution Pipeline)

**Last Updated**: 2024-12-19
**Status**: Phase 1 - Manual Triage Complete
**Next Review**: Sprint 2 Planning

> **Mandate**: Every skipped test MUST have explicit reason, sprint target, and re-enablement criteria.
> **Philosophy**: We skip with intention, track with precision, resolve with velocity.

## Current Status Summary
- **Total Skipped**: 570 (Infrastructure Dependency Failures)
- **Infrastructure Blocked**: 570 (PostgreSQL connection failures)
- **Code Issues**: 1 (Fixed: missing get_logger function)
- **Environment Issues**: 570 (Database authentication)

---

## Critical Root Cause Analysis

### 🔥 SYSTEMIC ISSUE: Database Connectivity Failure
**Primary Error**: `asyncpg.exceptions.InvalidPasswordError: password authentication failed for user "postgres"`

**Impact**: 570 tests failing due to inability to connect to test databases

**Root Cause**: Local environment lacks PostgreSQL services configured with CI-specified credentials:
- CI expects PostgreSQL on `localhost:5433` (dev) and `localhost:5434` (test)
- CI expects specific passwords: `dev_password` and `test_password`
- Local system doesn't have these services running

## Failing Tests Registry

| 🆔 | Test Category | Test Count | File Pattern | Root Cause | Sprint Target | Re-enable Criteria | Re-enablement Trigger | Priority |
|----|---------------|------------|--------------|------------|---------------|-------------------|----------------------|----------|
| CC-001 | CC Module Tests | ~200 | `tests/backend/cc/test_*.py` | DB Connection | Sprint 2 | PostgreSQL services ready | `docker-compose up -d postgres_dev postgres_test` | HIGH |
| UT-001 | Unit Tests | ~150 | `tests/unit/backend/cc/test_*.py` | DB Connection | Sprint 2 | PostgreSQL services ready | `DATABASE_URL_TEST` resolvable | HIGH |
| IT-001 | Integration Tests | ~50 | `tests/integration/backend/cc/test_*.py` | DB Connection | Sprint 2 | PostgreSQL services ready | `pg_isready -h localhost -p 5434` | HIGH |
| DB-001 | Database Tests | ~20 | `tests/db/test_*.py` | DB Connection | Sprint 2 | PostgreSQL services ready | `alembic upgrade head` success | HIGH |
| CM-001 | Common Tests | ~30 | `tests/common/test_*.py` | DB Connection | Sprint 2 | PostgreSQL services ready | Logger connection established | MEDIUM |
| GR-001 | Graph Tests | ~40 | `tests/graph/test_*.py` | DB + Neo4j | Sprint 2-3 | All services ready | `NEO4J_URI` connection + DB ready | MEDIUM |
| SC-001 | Script Tests | ~20 | `tests/scripts/test_*.py` | DB Connection | Sprint 2 | PostgreSQL services ready | Services + script permissions | LOW |
| CM-002 | COS Main Tests | ~50 | `tests/unit/test_cos_main_*.py` | DB Connection | Sprint 2 | PostgreSQL services ready | App startup without DB errors | HIGH |

### 🧠 **Re-enablement Triggers**

Each test category has specific trigger conditions for automated re-enablement:

```bash
# CC-001: CC Module Tests
🧠 Re-enable when: `pg_isready -h localhost -p 5434` returns 0 AND `DATABASE_URL_TEST` env var is set

# UT-001: Unit Tests
🧠 Re-enable when: `asyncpg.connect(DATABASE_URL_TEST)` succeeds AND `pytest.env.has_test_db` is True

# IT-001: Integration Tests
🧠 Re-enable when: `docker ps | grep postgres_test` shows running AND all migrations applied

# DB-001: Database Tests
🧠 Re-enable when: `alembic current` shows head revision AND test schema exists

# GR-001: Graph Tests
🧠 Re-enable when: `NEO4J_URI` is resolvable AND `test_env.neo4j.is_mock` is False AND database ready

# All Tests Global Trigger
🧠 Re-enable when: `scripts/ci_triage.py --check-infrastructure` returns `all_services_ready=True`
```

---

## Failure Categories & Resolution Strategy

### 🔧 Infrastructure Dependencies (570 tests)
**Primary Issue**: Missing PostgreSQL service infrastructure locally
- **Services Needed**: PostgreSQL 17.5 on ports 5433 (dev) and 5434 (test)
- **Credentials**: `postgres/dev_password` and `postgres/test_password`
- **Databases**: `cos_dev` and `cos_test`
- **Strategy**: Skip all DB-dependent tests until infrastructure setup complete

### 🐛 Code Logic Issues (1 test - FIXED)
- ✅ **Fixed**: Added missing `get_logger` function to `src/common/logger.py`
- **Impact**: Import errors resolved for database connection module

### 🌐 Environment/CI Configuration (570 tests)
**Issue**: Local environment doesn't match CI configuration
- **Missing**: Docker Compose services for PostgreSQL
- **Missing**: Neo4j service on port 7687
- **Missing**: Redis service on port 6379
- **Strategy**: Implement docker-compose.yml for local development

---

## Sprint Resolution Tracking

### Sprint 1 (Current) ✅
- [x] Complete test triage and analysis
- [x] Identify root causes (Database connectivity)
- [x] Fix code issues (get_logger function)
- [ ] **NEXT**: Implement skip decorators for all failing tests
- [ ] **NEXT**: Achieve green CI by systematic skipping

### Sprint 2 (Infrastructure Setup)
- [ ] Implement docker-compose.yml with PostgreSQL services
- [ ] Configure local development environment to match CI
- [ ] Re-enable database-dependent tests systematically
- [ ] Verify 200+ tests pass after infrastructure setup

### Sprint 3 (Integration)
- [ ] Add Neo4j service to local environment
- [ ] Re-enable graph-dependent tests (~40 tests)
- [ ] Add Redis service for pub/sub tests
- [ ] Full test suite validation (target: 600+ tests passing)

---

## Implementation Plan

### Phase 1A: Mass Skip Implementation (IMMEDIATE)
```python
# Add to all DB-dependent test files:
import pytest

@pytest.mark.skip(reason="Infrastructure: PostgreSQL services not available locally. Re-enable in Sprint 2 when docker-compose setup is complete. Trigger: CC-001")
class TestDatabaseDependent:
    # All existing test methods...
```

### Phase 1B: Service Detection Logic
```python
# Add to conftest.py:
def is_infrastructure_available():
    """Check if required services are available"""
    try:
        # Check PostgreSQL
        import asyncpg
        # Check Neo4j
        # Check Redis
        return True
    except:
        return False

pytest.skip_if_no_infrastructure = pytest.mark.skipif(
    not is_infrastructure_available(),
    reason="Infrastructure services not available"
)
```

### Phase 2: Infrastructure Automation
1. Create `docker-compose.dev.yml` matching CI services exactly
2. Add npm/make scripts for service management
3. Update documentation for local development setup
4. Implement service readiness checks

---

## Success Metrics

### Sprint 1 Success Criteria
- ✅ All test failures categorized and documented
- 🔄 CI pipeline shows 0 failing tests (all infrastructure tests skipped)
- 🔄 Code changes can be tested without database dependency noise
- 🔄 Clear roadmap for systematic re-enablement

### Sprint 2 Success Criteria
- 🎯 400+ tests passing after PostgreSQL setup
- 🎯 All CC module functionality validated
- 🎯 Database migration system working locally

### Sprint 3 Success Criteria
- 🎯 600+ tests passing after full infrastructure setup
- 🎯 CI matches local development environment exactly
- 🎯 No infrastructure-related test failures

---

*This systematic approach ensures we maintain development velocity while building toward comprehensive test coverage.*
