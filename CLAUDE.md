# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 🚨 CURRENT WORK IN PROGRESS 🚨
**Active Task Tracker**: [CI_FIX_PROGRESS.md](./CI_FIX_PROGRESS.md)
- Fixing 3 failing GitHub Actions workflows
- Standardizing Redis to NO PASSWORD across all environments
- Check the progress tracker FIRST when resuming work

## Project Context & Vision

**COS (Creative Operating System)** is a toolkit built to serve a 100+ book legacy vision by an aspiring NYT bestselling author who began coding less than a year ago. This system represents the translation of life-student insights into a technical foundation for creating classic non-fiction works.

**Roles & Orchestration:**
- **Strategist/Visionary**: Human author driving the legacy vision
- **Tactical Orchestrator**: Claude Code (you) handling NLP and coordination
- **Operational Agents**: Sub-agents executing specific coding tasks

## Constitutional Principles & Philosophy

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

### Testing Philosophy & True TDD
**Current Reality**: Sprint 2 technically "done" but NOT at "all green" state
**Goal**: Achieve true TDD workflow where we can step forward, refactor without fear
**Method**: Write minimal test (red) → minimal code (green) → iterate until ALL green and ALL repo REMAINS green

**Test Modes:**
- **Mock Mode** (default): Fast CI/CD with mocked dependencies
- **Integration Mode**: `RUN_INTEGRATION=1` for real infrastructure testing
- **Coverage Requirement**: 97% minimum

### Pre-Commit Workflow (Zero-Surprise Commits)
Always run exact pre-commit environment before commit:
```bash
# Match exact commit environment
uv run pre-commit run --files [file1] [file2] [file3]
# Or all files
uv run pre-commit run --all-files
```

### Advanced Tools Integration
**Multi-Tool Problem Solving:**
- **Sequential Thinking MCP**: For systematic analysis outside of zen
- **Zen MCP**: Extension with o3/o4-mini reasoning for complex workflows
- **Context7 + Tavily**: Research-backed solutions

**Orchestration Pattern:**
1. Zen MCP processes complex problems with high reasoning
2. Sequential Thinking MCP contextualizes results into coherent solutions
3. Sub-agents execute operational coding tasks
4. Claude Code orchestrates at tactical level

## Essential Commands

### Testing & Quality
```bash
# Run all tests with coverage
uv run pytest --cov=src --cov-report=html --cov-report=term

# Run specific test types
uv run pytest -m "unit"                    # Unit tests only
uv run pytest -m "integration"             # Integration tests
uv run pytest -m "not slow"                # Skip slow tests
uv run pytest tests/backend/cc/            # CC module tests
uv run pytest tests/common/                # Common module tests

# Run single test file
uv run pytest tests/backend/cc/test_router.py -v

# Performance tests
uv run pytest -m "benchmark" --benchmark-only

# Code quality checks
uv run ruff check .                        # Linting
uv run ruff format .                       # Formatting
uv run mypy src/                           # Type checking
uv run bandit -r src/                      # Security scanning

# Pre-commit validation (REQUIRED before commits)
uv run pre-commit run --all-files
```

### Development Server
```bash
# Start FastAPI server
uv run uvicorn src.cos_main:app --reload --host 0.0.0.0 --port 8000

# Infrastructure services (Docker required)
cd infrastructure/
docker-compose -f docker-compose.yml -f docker-compose.traefik.yml -f docker-compose.mem0g.yml up -d
```

### Database Operations
```bash
# Run Alembic migrations
uv run alembic upgrade head

# Create new migration
uv run alembic revision --autogenerate -m "description"

# Connect to dev database
docker exec -it cos_postgres_dev psql -U cos_user -d cos_db_dev

# Connect to Redis
docker exec -e REDISCLI_AUTH="Police9119!!Red" cos_redis redis-cli ping
```

## Architecture Overview

### Multi-Layer Memory System
COS implements a sophisticated memory hierarchy:
- **L1 (PostgreSQL)**: Immediate storage with mem0 integration
- **L1.5 (Redis)**: Real-time pub/sub event highway
- **L2 (Neo4j)**: Graph relationships and semantic connections
- **L3 (ZK)**: Curated knowledge layer (planned)
- **L4 (Canonical)**: Immutable archival storage

### Core Modules

**Control Center (CC)** - `src/backend/cc/`
- Main coordination module with FastAPI router
- Mem0 integration for scratch data management
- Health monitoring and system diagnostics
- Logfire distributed tracing integration

**Graph Module** - `src/graph/`
- Neo4j operations for L2 memory layer
- Node and relationship CRUD operations
- Graph search and analytics

**Common Module** - `src/common/`
- Shared infrastructure components
- Database connection management with pooling
- Redis configuration with circuit breaker pattern
- Logging, middleware, and configuration utilities

### Database Patterns

**PostgreSQL Configuration**:
- SQLAlchemy 2.0 async with connection pooling
- Schema-based organization (cc, mem0_cc)
- Agent-based connections for multi-tenant support
- Alembic migrations in `src/db/migrations/`

**Redis Configuration**:
- Circuit breaker for fault tolerance
- PubSub wrapper for event-driven architecture
- Health monitoring with auto-recovery
- Configuration in `src/common/redis_config.py`

**Neo4j Integration**:
- Async client with connection management
- Registry pattern for node/relationship types
- Graph operations in `src/graph/`

## Development Standards

### Testing Requirements
- **Coverage Target**: 79%+ progressive floor (current coverage - 2%)
- **Test Organization**: Unit, integration, performance markers
- **Infrastructure Tests**: Use testcontainers for Redis/PostgreSQL
- **Performance Targets**: <5ms round-trip, <1ms publish latency

### Code Quality
- **Python Version**: 3.13+
- **Type Checking**: MyPy strict mode enabled
- **Linting**: Ruff with comprehensive rule set
- **Security**: Bandit security scanning
- **Formatting**: Ruff formatter (120 char line length)

### Configuration Management
- Use Pydantic Settings for type-safe configuration
- Environment variables with `.env` support
- Cached settings with dependency injection pattern
- Never commit secrets (use environment variables)

## Key Design Patterns

### Error Handling
- Circuit breaker pattern for external services
- Graceful degradation for optional components
- Structured error responses with correlation IDs

### Observability
- Logfire integration for distributed tracing
- Request ID middleware for correlation
- Rich console logging for development
- Health check endpoints at multiple levels

### Production Readiness
- Connection pooling for all database connections
- Health monitoring with auto-recovery mechanisms
- Comprehensive test coverage including failure scenarios
- Docker-based infrastructure with service discovery

## Current Working Status

### ✅ "All Green" State Achieved!
**Current Reality**: Sprint 2 complete with ALL tests passing (86% coverage, 6 legitimate skips)
**Achievement**: Rich terminal output with all green checkmarks - fearless iteration enabled
**Workflow**: True TDD-only development - write ~10 lines of failing test → minimal code to pass → refactor

### Current Sprint Context
- **Phase 2 Sprint 2**: Redis Pub/Sub Highway implementation
- **Technical Status**: Features implemented but iterative loop to achieve true TDD state
- **Next**: Phase 2 Sprint 3 with true TDD workflow established

### TDD-Only Development Process
1. **Red**: Write ~10 lines of failing test for new functionality
2. **Green**: Write minimal code to make test pass (following patterns/best practices)
3. **Refactor**: Improve code while keeping ALL tests green
4. **Verify**: Run full test suite including linting before commit
5. **CI Check**: Push to release branch to verify GitHub Actions pass

### TDD Philosophy - "Clean Agile: Back to Basics"
- **Small Steps**: ~10 lines of test represents iterative approach, not a hard rule
- **Immediate Feedback**: Write test → see it fail → make it pass → refactor
- **Living Documentation**: Tests serve as executable documentation
- **Refactor Confidence**: Comprehensive test suite enables fearless changes
- **Catch Regressions**: Automated tests prevent breaking existing functionality
- **Design Emergence**: TDD naturally leads to better, more modular design

### Development Constraints (Maintain Green)
- **TDD Discipline**: ALWAYS write failing test first, then code
- **Performance Targets**: <1ms publish latency, <5ms round-trip
- **Coverage Maintenance**: 79% progressive floor (allows refactoring)
- **CI Must Pass**: Every commit must maintain green status locally AND in CI

## Troubleshooting

### Common Issues
**Import Errors**: Ensure using `uv run` commands for proper environment
**Database Connection**: Check PostgreSQL on port 5433: `docker-compose up postgres_dev`
**Redis Connection**: Verify Redis accessibility: `docker exec -e REDISCLI_AUTH="Police9119!!Red" cos_redis redis-cli ping`
**Test Failures**: Run verbose: `uv run pytest -v --tb=long tests/path/to/failing_test.py`

### Performance Issues
**Slow Tests**: Ensure mock mode: `uv run pytest` (not integration mode)
**Redis Latency**: Check circuit breaker:
```python
from common.pubsub import RedisPubSub
pubsub = RedisPubSub()
await pubsub.health_check()  # View detailed status
```

### Development Tools
- **Logs**: `docker-compose logs -f cos_backend`
- **Redis Monitor**: `redis-cli monitor`
- **DB Query Log**: Set `SQLALCHEMY_LOG_LEVEL=debug`
- **Memory Profile**: `uv run pytest --memray tests/performance/`

## Service Access Points
- **Main API**: http://localhost:8000
- **Traefik Dashboard**: http://localhost:8080
- **Neo4j Browser**: http://localhost:7474
- **PostgreSQL Dev**: localhost:5433
- **Redis**: Via docker exec with authentication

## Development Context
- **Infrastructure**: All services containerized and health-monitored
- **Test Coverage**: 86% overall coverage with ALL tests passing (1451 passed, 6 skipped)
- **Architecture**: Multi-layer memory system (L1-L4) with Redis pub/sub highway

## Future Multi-Module Architecture (Post-CC Gold Standard)
**COS System**: Operates collectively as true Anthropic agent definition
**CC Module**: Control Center/Dashboard (health checks, settings, permissions, kanban, homepage functionality)
**PEM Module**: Prompt Engineering specialist (writes prompts for other modules, self-improves)
**AIC Module**: AI Coach (ingests research papers/best practices → system improvements via A/B testing)
**Creative Modules**: Focus on creative output while PEM/AIC handle technical optimization
**Module Pattern**: `/cc`, `/pem`, `/aic` routers with schema-per-module (cc.tables, pem.tables)
**Interconnection**: Redis pub/sub messaging, future Slack integration, agentic communication
**Testing Strategy**: CC gold standard first, then multi-module isolation patterns
**Design Philosophy**: Specialized modules enhance each other rather than competing for resources
**Note**: Review common/ architecture for multi-module readiness before duplication script
