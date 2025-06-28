# COS (Creative Operating System) - Development Guide

## Project Overview
**COS** is a high-performance Creative Operating System backend built with FastAPI, SQLAlchemy, Redis, and Neo4j. Currently in **Phase 2 Sprint 2** implementing the Redis pub/sub highway for real-time event orchestration.

## Constitutional Principles
### Dual Mandate (Never Compromise)
**100% Quality + 100% Efficiency** - Every decision must honor both. If forced to choose, we've designed wrong.

### FORWARD Principles (Technical DNA)
- **Frictionless**: Standard structures, rapid scaffolding, zero manual deployment
- **Orchestrated**: Intelligent automation with human-in-the-loop oversight
- **Real-Time**: New capabilities in <1 day, zero downtime expansion
- **Wide-Angle**: Decisions for centuries, not sprints
- **Adaptive**: 10x growth without performance degradation
- **Relentless**: Every failure is fuel, every success is seed
- **Destiny-Driven**: All code serves the 100+ book legacy vision

## Architecture Overview

### Core Stack
- **FastAPI**: Async web framework with automatic OpenAPI docs
- **SQLAlchemy 2.x**: Async ORM with PostgreSQL backend via asyncpg
- **Redis**: High-performance pub/sub messaging with circuit breaker resilience
- **Neo4j**: Graph database with Rust-enhanced driver support
- **Logfire**: Observability and distributed tracing
- **Python 3.13**: Latest Python with strict typing

### Intelligence Layers
- **L1 (PostgreSQL)**: Immediate persistence (`mem0_cc` schema)
- **L1.5 (Redis)**: Real-time event bus (current sprint focus)
- **L2 (Neo4j)**: Graph relationships (Sprint 3)
- **L3 (ZK)**: Curated knowledge (Phase 3+)
- **L4 (Canonical)**: Archived (Phase 3+)

### Key Modules
```
src/
├── backend/cc/           # Creative Conductor (main API module)
├── common/              # Shared infrastructure (Redis, DB, logging)
├── graph/               # Neo4j graph operations
├── db/                  # Database models, migrations, schemas
└── cos_main.py          # FastAPI application entry point
```

## Development Environment

### Requirements
- **Python 3.13+** (use `uv` package manager)
- **PostgreSQL** (dev on port 5433)
- **Redis** (pub/sub messaging)
- **Neo4j** (optional, graph operations)

### Environment Setup
```bash
# Install dependencies
uv sync

# Start infrastructure services
docker-compose up postgres_dev redis neo4j

# Run application
uv run uvicorn src.cos_main:app --reload --host 0.0.0.0 --port 8000
```

### Pre-Commit Workflow (Zero-Surprise Commits)
**Problem**: Direct tool runs (ruff, mypy) ≠ pre-commit environment → commit failures
**Solution**: Always run exact pre-commit environment before commit

```bash
# Run pre-commit on specific files to match exact commit environment
uv run pre-commit run --files [file1] [file2] [file3]

# Or run on all files
uv run pre-commit run --all-files
```

**Workflow**:
1. 🎯 Run `uv run pre-commit run --files` to match exact commit environment
2. 🔧 Fix issues found by the actual hooks that will run
3. ✅ Commit passes on first try with zero surprises

## Testing Standards

### Testing Philosophy
- **97% unit test coverage** requirement
- **DELTA/EPSILON/ZETA methodology**
- **Mock vs Integration modes** for optimal CI/CD performance

### Test Execution
```bash
# Fast mock mode (default for CI/CD)
uv run pytest

# Full integration mode (real infrastructure)
RUN_INTEGRATION=1 uv run pytest

# Coverage reporting
uv run pytest --cov=src --cov-report=html

# Performance benchmarks
uv run pytest tests/performance/ -m benchmark
```

### Test Organization
```
tests/
├── unit/           # Pure unit tests with mocks (fast)
├── integration/    # Real infrastructure tests (thorough)
├── performance/    # Benchmarks and load testing
├── backend/cc/     # CC module specific tests
└── common/         # Shared component tests
```

## Current Sprint: Phase 2 Sprint 2

### Sprint Focus: Redis Pub/Sub Highway
**Status**: IN PROGRESS
**Performance Targets**:
- Publish latency: <1ms
- Round-trip messaging: <5ms local
- Circuit breaker resilience: 3 failures → open, 30s recovery

### Core Deliverables
- ✅ `common/pubsub.py` async Redis wrapper with circuit breaker
- ✅ High-performance messaging with <1ms publish latency
- 🔄 Integration with `log_l1()` → `mem0.recorded.cc` channel
- 🔄 Generic subscriber base class
- 📋 Integration tests: round-trip <5ms validation

### Sprint Constraints
- Only modify files within scope: `common/`, `backend/cc/services/`, `tests/`
- Maintain 97% unit test coverage
- All Redis operations must be async
- No changes to Sprint 1 deliverables unless critical bug
- Performance requirement: publish <1ms latency

## Code Quality Standards

### Style & Linting
```bash
# Ruff (linting and formatting)
uv run ruff check src/ tests/
uv run ruff format src/ tests/

# Type checking
uv run mypy src/

# Security scanning
uv run bandit -r src/
```

### Quality Gates
- **Ruff**: 120 char line length, comprehensive rule set
- **mypy**: Strict mode with Pydantic plugin
- **bandit**: Security vulnerability scanning
- **Coverage**: 97% minimum requirement

## Database Operations

### Development Database
```bash
# Connect to development database (port 5433)
psql postgresql://cos_user:cos_pass@localhost:5433/cos_db

# Run migrations
uv run alembic upgrade head

# Create new migration
uv run alembic revision --autogenerate -m "description"
```

### Test Database Isolation
- Tests use **SAVEPOINT transactions** for hermetic isolation
- Force port 5433 for development database
- Automatic rollback after each test

## Performance Requirements

### Redis Pub/Sub Performance
- **Publish latency**: <1ms target with monitoring
- **Circuit breaker**: 3 failures → open, 30s timeout, 2 successes → close
- **Connection pooling**: Optimized settings for high throughput
- **Observability**: Comprehensive Logfire integration

### Testing Performance
- **Mock mode**: Extremely fast for CI/CD (<30s full suite)
- **Integration mode**: Full behavior verification (~2-3 minutes)
- **Benchmark tests**: Performance regression detection

## API Documentation

### FastAPI Automatic Docs
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **OpenAPI JSON**: http://localhost:8000/openapi.json

### API Modules
- **CC API**: `/cc/*` - Creative Conductor operations
- **Graph API**: `/graph/*` - Neo4j graph operations
- **Health**: Standard health check endpoints

## Debugging & Observability

### Logfire Integration
```python
# Automatic request tracing with correlation IDs
from common.logger import log_event

log_event(source="module_name", data={"key": "value"}, memo="Description")
```

### Development Tools
```bash
# View logs with structured output
docker-compose logs -f cos_backend

# Redis monitoring
redis-cli monitor

# Database query logging
# Set SQLALCHEMY_LOG_LEVEL=debug in environment
```

## Common Commands

### Development Workflow
```bash
# Full development cycle
uv run pre-commit run --all-files    # Quality gates
uv run pytest                       # Fast testing
RUN_INTEGRATION=1 uv run pytest     # Full integration
uv run uvicorn src.cos_main:app --reload  # Run server

# Infrastructure management
docker-compose up postgres_dev redis neo4j  # Start services
docker-compose down                          # Stop services
docker-compose logs -f [service]            # View logs
```

### Performance Monitoring
```bash
# Redis performance testing
uv run pytest tests/performance/test_redis_benchmarks.py -v

# Database performance
uv run pytest tests/performance/ -m database

# Memory profiling
uv run pytest --memray tests/performance/
```

## Troubleshooting

### Common Issues

**Import Errors**: Ensure `src/` is in PYTHONPATH or use `uv run` commands

**Database Connection**: Check PostgreSQL is running on port 5433
```bash
docker-compose up postgres_dev
```

**Redis Connection**: Verify Redis is accessible
```bash
docker-compose up redis
redis-cli ping  # Should return PONG
```

**Test Failures**: Run with verbose output
```bash
uv run pytest -v --tb=long tests/path/to/failing_test.py
```

### Performance Issues
**Slow Tests**: Ensure using mock mode for development
```bash
# Fast mode (default)
uv run pytest

# If accidentally in integration mode
unset RUN_INTEGRATION
```

**Redis Latency**: Check circuit breaker status and connection pooling
```python
# In Python shell
from common.pubsub import RedisPubSub
pubsub = RedisPubSub()
await pubsub.health_check()  # View detailed status
```

## Contributing Guidelines

### Before Making Changes
1. Read sprint context in `docs/000_current_sprint_context.md`
2. Check current constraints and deliverables
3. Ensure changes align with FORWARD principles
4. Plan for 100% Quality + 100% Efficiency

### Code Contribution Process
1. **Plan**: Use sprint constraints and deliverable guidelines
2. **Implement**: Follow existing patterns and conventions
3. **Test**: Achieve 97% coverage with both mock and integration tests
4. **Quality**: Pass all pre-commit hooks before committing
5. **Performance**: Meet latency and throughput requirements

### Review Checklist
- [ ] Follows FORWARD principles
- [ ] Maintains 97% test coverage
- [ ] Passes all quality gates (ruff, mypy, bandit)
- [ ] Performance requirements met
- [ ] Integration tests pass
- [ ] Documentation updated if needed

---

**Remember**: This is a destiny-driven codebase serving a 100+ book legacy vision. Every line of code should reflect the constitutional principles of 100% Quality + 100% Efficiency.
