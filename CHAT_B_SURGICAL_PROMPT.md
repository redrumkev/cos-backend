# Chat B: Surgical src/db/migrations/env.py Cleanup

## Mission: Database Migration Layer Foundation
**Target**: `/Users/kevinmba/dev/cos/src/db/migrations/env.py` (13 ruff/mypy bypasses)
**Branch**: `feat/cc-goldPh2S2`
**Impact**: Core database migration infrastructure

## Context Loading Protocol
```bash
cd /Users/kevinmba/dev/cos
git checkout feat/cc-goldPh2S2
git status
```

**MUST READ**: `/Users/kevinmba/dev/cos/PHASE_2_SPRINT_2_COORDINATION.md` for full context

## Execution Steps

### 1. Assessment Phase
```bash
# Check current bypasses
rg "# noqa|# type: ignore" src/db/migrations/env.py

# Understand migration status
alembic current
alembic history
```

### 2. Systematic Cleanup
**Priority Order:**
1. **Import organization** (high impact, low risk)
2. **Type annotations for configuration** (alembic config objects)
3. **Database connection handling** (async engine setup)
4. **Migration context setup** (alembic environment)

**Common Issues Expected:**
- Alembic import type annotations
- Dynamic configuration loading
- Async engine setup in migration context
- SQLAlchemy metadata imports

### 3. Quality Gates After Each Fix
```bash
# Validate migrations still work
alembic check
alembic upgrade head --sql  # dry run

# Quality checks
uv run pre-commit run --files src/db/migrations/env.py
mypy src/db/migrations/env.py --strict
ruff check src/db/migrations/env.py
```

### 4. Migration Testing
```bash
# Test actual migration execution (if safe)
alembic downgrade -1
alembic upgrade +1

# Verify database state intact
psql -h localhost -p 5433 -U cos_user -d cos_db_dev -c "\dt"
```

## Success Criteria
- ✅ Zero `# noqa` bypasses in migrations/env.py
- ✅ Zero `# type: ignore` bypasses in migrations/env.py
- ✅ Alembic migrations function correctly
- ✅ Pre-commit hooks pass
- ✅ Strict mypy compliance
- ✅ Database migrations execute without errors

## Risk Mitigation
**CRITICAL**: Database migrations are sensitive infrastructure
- Test each change with `alembic check`
- Verify on dev database (port 5433) only
- Keep incremental commits for easy rollback
- Never modify migration files themselves, only env.py

## Expected Bypass Categories
Based on alembic patterns:
- Dynamic import bypasses for SQLAlchemy
- Configuration object typing
- Async context manager annotations
- Migration environment setup

## Commit Strategy
```bash
# Conservative, incremental commits:
git add src/db/migrations/env.py
git commit -m "fix: improve type safety in alembic migration env

- Remove X import-related bypasses
- Add proper typing for alembic config objects
- Improve async engine type annotations
- Maintain migration functionality"

git push origin feat/cc-goldPh2S2
```

## Handoff Protocol
**Upon Completion:**
1. Update `PHASE_2_SPRINT_2_COORDINATION.md`
2. Mark Chat B as ✅ COMPLETED
3. Unblock Chat C (Redis/PubSub infrastructure)
4. Report migration system status

## Emergency Fallback
If migrations break:
```bash
# Immediate rollback
git checkout HEAD~1 src/db/migrations/env.py
alembic check

# Verify database still accessible
psql -h localhost -p 5433 -U cos_user -d cos_db_dev -c "SELECT 1"
```

---
**Estimated Duration**: 25-35 minutes
**Criticality**: HIGH - Database layer affects all data operations
**Next**: Chat C (Redis/PubSub) can start after completion
