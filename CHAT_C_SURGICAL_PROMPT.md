# Chat C: Surgical Redis/PubSub Infrastructure Cleanup

## Mission: Core Service Infrastructure Foundation
**Targets**:
- `/Users/kevinmba/dev/cos/src/common/redis_config.py`
- `/Users/kevinmba/dev/cos/src/common/pubsub.py`
**Branch**: `feat/cc-goldPh2S2`
**Impact**: Redis/PubSub core services infrastructure

## Context Loading Protocol
```bash
cd /Users/kevinmba/dev/cos
git checkout feat/cc-goldPh2S2
git status
```

**MUST READ**: `/Users/kevinmba/dev/cos/PHASE_2_SPRINT_2_COORDINATION.md` for full context

## Current Bypass Assessment
```bash
# Check current bypasses in both files
rg "# noqa|# type: ignore" src/common/redis_config.py src/common/pubsub.py

# Count total bypasses
rg "# noqa|# type: ignore" src/common/redis_config.py src/common/pubsub.py | wc -l
```

## Execution Steps

### 1. Assessment Phase
```bash
# Identify bypass types
rg "# noqa|# type: ignore" src/common/redis_config.py --context 2
rg "# noqa|# type: ignore" src/common/pubsub.py --context 2

# Test current Redis functionality
pytest tests/unit/common/test_redis_config.py -v
pytest tests/unit/common/test_pubsub_*.py -v
```

### 2. Systematic Cleanup Strategy
**Priority Order:**

#### Phase C1: redis_config.py
1. **Import organization** (fix unused imports, resolve import-related bypasses)
2. **Type annotations** (Redis client typing, config object types)
3. **Configuration validation** (improve error handling type safety)
4. **Connection management** (async Redis client lifecycle)

#### Phase C2: pubsub.py
1. **Redis client typing** (async Redis operations)
2. **Message serialization** (JSON/bytes type handling)
3. **Error handling** (Redis exceptions, connection failures)
4. **Pub/Sub lifecycle** (subscription management, cleanup)

### 3. Quality Gates After Each Change
```bash
# Pre-commit validation
uv run pre-commit run --files src/common/redis_config.py src/common/pubsub.py

# Type checking
mypy src/common/redis_config.py --strict
mypy src/common/pubsub.py --strict

# Linting
ruff check src/common/redis_config.py src/common/pubsub.py

# Test Redis functionality
pytest tests/unit/common/test_redis_config*.py -v
pytest tests/unit/common/test_pubsub*.py -v --tb=short
```

### 4. Integration Testing
```bash
# Test Redis/PubSub integration
pytest tests/integration/test_redis_*.py -v

# Performance impact check
pytest tests/performance/test_redis_*.py -v --tb=short
```

## Success Criteria
- ✅ Zero `# noqa` bypasses in redis_config.py
- ✅ Zero `# type: ignore` bypasses in redis_config.py
- ✅ Zero `# noqa` bypasses in pubsub.py
- ✅ Zero `# type: ignore` bypasses in pubsub.py
- ✅ All Redis/PubSub tests pass
- ✅ Pre-commit hooks pass on both files
- ✅ Strict mypy compliance
- ✅ Redis connection and pub/sub functionality intact

## Expected Bypass Categories
Based on Redis/async patterns:
- Redis client type annotations (`redis.asyncio.Redis`)
- Async context manager typing
- JSON serialization type handling
- Dynamic import bypasses for optional Redis features
- Exception handling for Redis connection errors

## Risk Mitigation
**CRITICAL**: Redis/PubSub affects all messaging infrastructure
- Test connection functionality after each change
- Verify pub/sub messaging works correctly
- Keep incremental commits for easy rollback
- Monitor performance impact during cleanup

## Commit Strategy
```bash
# Incremental commits per file:
git add src/common/redis_config.py
git commit -m "fix: clean quality bypasses in redis_config.py

- Remove X ruff/mypy bypasses
- Improve Redis client type annotations
- Fix import organization
- Maintain connection functionality"

git add src/common/pubsub.py
git commit -m "fix: clean quality bypasses in pubsub.py

- Remove X ruff/mypy bypasses
- Improve pub/sub type safety
- Fix message serialization typing
- Maintain messaging functionality"

git push origin feat/cc-goldPh2S2
```

## Handoff Protocol
**Upon Completion:**
1. Update `PHASE_2_SPRINT_2_COORDINATION.md`
2. Mark Chat C as ✅ COMPLETED
3. **Enable Phase 2**: Unblock parallel cleanup (D,E,F,G)
4. Report Redis/PubSub system status

## Emergency Fallback
If Redis/PubSub breaks:
```bash
# Immediate rollback
git checkout HEAD~1 src/common/redis_config.py src/common/pubsub.py

# Verify Redis still functional
pytest tests/unit/common/test_redis_config.py -x
pytest tests/unit/common/test_pubsub_simple.py -x
```

---
**Estimated Duration**: 35-45 minutes
**Criticality**: HIGH - Messaging infrastructure affects all async operations
**Next**: Phase 2 parallel cleanup (D,E,F,G) can start after completion
