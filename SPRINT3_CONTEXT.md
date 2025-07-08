# Sprint 3 Context Handoff - Bulletin Board (Event Recorder)

## Current State (2025-07-08)
- **Location**: `/Users/kevinmba/dev/cos`
- **Branch**: `main` (up to date with origin)
- **Last PR**: #10 merged - CI fixes complete
- **GitHub Status**: Actions disabled, rulesets disabled, pure backup mode

## Sprint 2 Completion Summary
- ✅ Redis Pub/Sub Highway implemented with TDD
- ✅ 86% test coverage (ALL GREEN!)
- ✅ Performance targets met: <1ms publish latency
- ✅ GitHub CI issues resolved (then CI disabled for GitLab migration)

## Sprint 3 Focus: Bulletin Board (Event Recorder) + Tool Registry

### Core Requirements
1. **Durable Event Log**:
   - Redis Streams for event capture
   - PostgreSQL for persistence
   - Event replay capability

2. **Tool Registry**:
   - `@tool` decorator for auto-discovery
   - Dynamic registration system
   - Tool metadata and versioning

### Architecture Context
- **Redis Streams**: For durable message queue (upgrade from pub/sub)
- **PostgreSQL**: Event storage with schema in CC module
- **Pattern**: Event sourcing with replay capability

### Key Files to Review
- `src/backend/cc/` - Control Center module (home for event recorder)
- `src/common/redis_config.py` - Redis configuration (add Streams support)
- `src/common/pubsub.py` - Current pub/sub implementation (reference)
- `tests/backend/cc/` - CC module tests

### TDD Workflow Reminder
1. Write ~10 lines of failing test
2. Write minimal code to pass
3. Refactor while keeping ALL tests green
4. Run full suite: `uv run pytest --cov=src`
5. Pre-commit check: `uv run pre-commit run --all-files`

### Git Workflow
- Feature development: `feat/*` branches
- Release candidates: `release/*` branches
- Main: Protected, requires PR

### Next Steps
1. Create feature branch: `git checkout -b feat/bulletin-board`
2. Start with Redis Streams spike/test
3. Design event schema for PostgreSQL
4. Implement @tool decorator pattern
5. Build event recorder with TDD

### Environment Check
```bash
# Verify setup
cd /Users/kevinmba/dev/cos
uv run pytest --co -q | head -5  # Check test discovery
docker ps | grep -E "postgres|redis"  # Check services
```

### Important Context
- **Mac Studio M4 Max**: On order for local GitLab CI (10-20x faster)
- **GitHub**: Now just backup, no CI/CD overhead
- **Philosophy**: 100% Quality + 100% Efficiency (Dual Mandate)
- **Coverage Floor**: 79% progressive (current - 2%)

### Working Patterns
- Use sub-agents (Task tool) liberally for context management
- Zen MCP tools for complex analysis (o3/gemini-2.5-pro)
- Sequential thinking for systematic problem solving
- Update progress trackers for resumability

## Session End State
- All CI fixes merged
- GitHub simplified to backup-only
- Ready to start Sprint 3 development
- No uncommitted changes
