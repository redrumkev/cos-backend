This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## CRITICAL BASE LEVEL CONTEXTUALIZATION
**Auto-Load on Every COS Interaction**: Access G:\dev_tools\claude_cos\critical_memories.md for:
- Role & Hierarchy (User=CEO, Claude=Director, Cursor=Worker)
- Dual Mandate (100% Quality + 100% Efficiency simultaneously)
- TDD Automation (RED→GREEN→REFACTOR as default, auto-scan P2-*-001 skips)
- Bell Curve Context ((x, xx, X, XX, X, xx, x) - current task maximum focus)
- Template Evolution (self-improving prompt framework at G:\dev_tools\claude_cos\)
- Communication Style (token efficient, mama bear precision, no preamble)

**These are base-level operating principles - execute automatically without discussion.**

  Project Overview

  COS (Creative Operating System) is a modular FastAPI-based backend system designed for building and managing creative intelligence applications. The
  system follows a hybrid vertical slice architecture with atomic composition principles.

  Architecture

  Core Structure

  - Backend Modules: Located in src/backend/, each module is self-contained with its own API, database schemas, and business logic
  - Common Infrastructure: Shared utilities in src/common/, database layer in src/db/, graph layer in src/graph/
  - Gold Standard: The cc module serves as the canonical template for all new modules

  Module Structure

  Each module follows this standard structure:
  backend/module_name/
  ├── module_name_main.py  # FastAPI app initialization
  ├── router.py            # API endpoints
  ├── schemas.py           # Pydantic models
  ├── services.py          # Business logic
  ├── crud.py              # Database operations
  ├── models.py            # SQLAlchemy models (primary schema)
  ├── mem0_models.py       # SQLAlchemy models (mem0 schema)
  ├── deps.py              # FastAPI dependencies
  └── module_name_map.yaml # AI-readable manifest

  Database Strategy

  - PostgreSQL: Each module has two schemas: <module_name> (primary) and mem0_<module_name> (ephemeral memory)
  - Redis: Used for caching, pub/sub, and session management
  - Neo4j: Graph data with dual-label pattern :<Type>:<domain_module>

  Development Commands

  Setup and Installation

  # Install dependencies using uv
  uv sync

  # Install pre-commit hooks
  pre-commit install

  Testing

  # Run all tests with coverage
  pytest

  # Run specific test markers
  pytest -m "not slow"           # Skip slow tests
  pytest -m "integration"        # Run only integration tests
  pytest -m "unit"              # Run only unit tests

  # Run tests in parallel
  pytest -n auto

  Code Quality

  # Format code
  ruff format .

  # Lint code
  ruff check .

  # Type checking
  mypy src/

  # Security scanning
  bandit -r src/

  # Pre-commit checks (runs all quality tools)
  pre-commit run --all-files

  Infrastructure

  # Start all infrastructure services
  cd infrastructure/
  docker-compose -f docker-compose.yml -f docker-compose.traefik.yml up -d
  docker-compose -f docker-compose.mem0g.yml up -d

  # Stop all services
  docker-compose -f docker-compose.yml -f docker-compose.traefik.yml down
  docker-compose -f docker-compose.mem0g.yml down

  # View service status
  docker ps

  Database Operations

  # Run migrations
  alembic upgrade head

  # Create new migration
  alembic revision --autogenerate -m "description"

  # Downgrade migration
  alembic downgrade -1

  Module Generation

  # Generate new module from template
  python scripts/generate_module.py --domain <domain> --module <module_name>

  Development Standards

  Code Quality Requirements

  - Coverage: Maintain 97%+ test coverage
  - Type Safety: Full type hints with strict mypy configuration
  - Linting: Zero ruff warnings/errors
  - Testing: TDD workflow (RED → GREEN → REFACTOR)

  Module Communication

  - Synchronous: Only via REST API calls between modules using httpx
  - Asynchronous: Only via Redis Pub/Sub for events
  - Prohibition: No direct Python imports between functional modules

  Logging

  - Use common/logger.py with log_event() function
  - All logs stored in module's mem0_<module> schema
  - Include structured data for debugging and monitoring

  Error Handling

  - Custom exceptions with consistent JSON error format
  - Proper HTTP status codes
  - Sanitized error messages (no sensitive data)

  Key Configuration Files

  - pyproject.toml: Project dependencies, testing, and tool configuration
  - ruff.toml: Linting and formatting rules (line length: 120)
  - alembic.ini: Database migration configuration
  - .env: Environment variables (not in repo, see infrastructure/preflight_checklist.md)

  Service Access

  With infrastructure running, services are available at:
  - Traefik Dashboard: http://localhost:8080
  - Neo4j Browser: http://neo4j.cos.local
  - mem0g API: http://mem0g.cos.local
  - Redis: localhost:6379 (direct access)
  - PostgreSQL Dev: localhost:5433 (direct access)

  Performance Standards

  - API P95 response time < 300ms
  - Async-first for all I/O operations
  - Efficient database queries (no N+1 problems)
  - Connection pooling for external services

  Important Notes

  - Each module must include a <module_name>_map.yaml file for AI-assisted development
  - Follow the FORWARD principles: Frictionless, Orchestrated, Real-time, Wide-angle, Adaptive, Relentless, Destiny-driven
  - The system is designed for multi-century endurance and adaptability
  - Quality and efficiency are never compromised for each other (dual mandate: 100% quality, 100% efficiency)

  Phase 2 Development

  For systematic test re-enablement during Phase 2 implementation, see: docs/PHASE_2_TECHNICAL_DEBT.md
  This document provides sprint-based guidance for removing test skips and achieving 97% coverage.

  Phase 2 MCP Architecture Foundation

  When you're ready for Phase 2, here's the structure to implement:

  src/backend/cc/mcp/
  ├── __init__.py
  ├── server.py              # MCP server implementation
  ├── client.py              # MCP client for inter-module communication
  ├── tools/                 # Agentic tool implementations
  │   ├── __init__.py
  │   ├── health_tools.py    # Advanced health management
  │   ├── module_tools.py    # Module lifecycle operations
  │   └── coordination_tools.py  # Cross-module coordination
  ├── resources/             # Exposed resources for other agents
  │   ├── __init__.py
  │   ├── system_state.py    # Current system state resource
  │   └── config_resource.py # Live configuration resource
  └── prompts/              # System prompts for LLM agents
      ├── __init__.py
      ├── system_prompts.py  # Core system interaction prompts
      └── diagnostic_prompts.py  # System diagnostic prompts

  ---

  ## Tactical Cursor Prompting Protocol

  **When User Requests:** "prompt cursor for the next task", "create cursor prompt", "lets do task_007", etc.

  **Claude's Response Pattern:**
  1. **Load Bell Curve Context** - Access G:\dev_tools\claude_cos\ for:
     - Current task (XX): Full context and learnings
     - Adjacent tasks (x, xx): Compressed patterns and decisions
     - Critical templates: Pydantic v2, API patterns, architectural decisions

  2. **Auto-Execute TDD Scan** - Mandatory for every task:
     - Skip Analysis: grep -r "P2-.*-001" tests/ → identify removable skips
     - Test Coverage: examine existing tests → identify gaps
     - New Test Requirements: for any new code → write RED tests first
     - Edge Cases: scan cc module patterns → replicate thoroughness

  3. **Apply Template** - Use supercharged_prompt_v1.md structure:
     - Step 0: MCP sequence + TDD scan (automatic)
     - TDD Flow: RED→GREEN→REFACTOR (default operating mode)
     - Boundaries: Explicit scope protection
     - Success criteria: Measurable outcomes + TDD completion
     - Quality gates: Copy-paste validation commands
     - Report template: Learning capture + TDD insights for next iteration

  4. **Commit Message Format:**
     ```
     Phase 2 Sprint X.Y: Task_NNN [Brief Description]
     - Main deliverable/change 1
     - Main deliverable/change 2
     - Main deliverable/change 3
     ```

  5. **Learning Accumulation:**
     - Preserve critical patterns across tasks
     - Compress old contexts while maintaining templates
     - Evolve prompts based on Cursor success/failure feedback
     - Target: Nearly 100% prompt success rate by task 30-35

  **Key Variables:**
  - LOGFIRE_API_KEY: Available in /infrastructure/.env
  - Task Context: Via .taskmaster/ MCP calls
  - Project Docs: COS /docs folder access only
  - Quality Standards: 97%+ coverage, zero ruff/mypy errors

  ---

# Test access line - confirming filesystem access
