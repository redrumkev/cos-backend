This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## AUTO-LOAD PROTOCOL - Execute Automatically on Every COS Interaction

### MUST-READ Files (100% Auto-Load)
**Read these immediately when starting any COS conversation:**
1. `/mnt/g/dev_tools/claude_cos/critical_memories.md` - Base operating principles, role hierarchy, dual mandate
2. `/mnt/g/dev_tools/claude_cos/cold_start_state.md` - Current sprint context, efficiency patterns, success formula

### Conditional Read Files (Context-Driven Auto-Load)
**Executive Summaries - Read full file when context matches:**

**`supercharged_prompt_v1.md`** - READ WHEN: Creating cursor prompts, task execution planning
*Contains: Step 0 MCP sequences, TDD scan automation, commit patterns, quality gates*

**`learning_iterations.md`** - READ WHEN: Analyzing task execution, improving prompts, capturing friction
*Contains: Task execution analysis, friction patterns, template evolution metrics, success predictions*

**`cursor_prompting/*.md`** - READ WHEN: Working on similar tasks, referencing execution patterns
*Contains: Task-specific prompts with learnings, execution issues, pattern improvements*

### Automatic Workflow Triggers
**Execute without asking when user mentions:**
- "cursor prompt for task_X" → Auto-create prompt with Step 0 MCP sequence
- "task_X feedback" → Auto-analyze, capture learnings, update templates
- "next task" → Auto-check taskmaster, prepare context, create prompt
- Task execution issues → Auto-capture in learning_iterations.md

### Agentic Behaviors - Execute Proactively
1. **Task Learning**: After any cursor task discussion, automatically capture patterns
2. **Prompt Evolution**: Auto-improve templates based on execution feedback
3. **Context Loading**: Auto-read relevant files based on conversation context
4. **Quality Assurance**: Auto-include pytest fixes, UV-only policies, PostgreSQL strategies
5. **Scope Protection**: Auto-enforce boundaries, prevent scope creep
6. **MCP Integration**: Auto-include taskmaster calls, Context7 research, documentation loading

### Cold Start Recovery
**If you ever need to "catch up" in a conversation:**
1. Read MUST-READ files immediately
2. Scan conversation for task numbers, execution patterns, issues
3. Check `/mnt/g/dev_tools/claude_cos/cursor_prompting/` for relevant task context
4. Auto-apply learned patterns from `learning_iterations.md`
5. Proceed with full context without asking for guidance

**Mama Bear Principle**: Just enough auto-loading to be effective, not so much as to flood context. Smart conditional reading based on conversation signals.

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

  Database Environment Strategy (Phase 2)

  **PostgreSQL-Only Policy**: Use PostgreSQL exclusively for all environments
  - Production database: PostgreSQL 17.5 with native schemas, UUID, timezone support
  - Development/testing: Same PostgreSQL version for production parity
  - NO SQLite: Eliminates dialect differences, simplifies code, ensures compatibility

  **Current Development**: Use cos_postgres_dev (port 5433) as single source of truth
  - _dev environment serves as "future _prod" while building toward v1.0
  - _test environment (port 5434) is IGNORED until Phase 3+ when live production exists
  - No three-tier complexity until there's something production-worthy to protect

  **Future Migration** (Post-Backend Completion):
  - Promote stable _dev → _prod v1.0
  - Reset _dev to v1.01+ for continued iteration
  - Introduce _test for granular testing when tic/tock development begins

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

  ## Cursor Prompt File Format Standard

  **CRITICAL**: All cursor prompts must follow this exact format to prevent context pollution and ensure clean copy-paste operations.

  **File Structure:**
  ```
  --- CURSOR PROMPT RANGE START ---
  [All content that goes to Cursor - clean, focused, no cross-task references]
  --- CURSOR PROMPT RANGE END ---

  ## Claude/User Strategic Context
  [Bell curve context, template evolution, task progression, critical variables]
  ```

  **Cursor Range Content (Above separator):**
  - Task title and sprint info
  - MCP sequence and TDD scan commands
  - TDD flow (RED→GREEN→REFACTOR)
  - Boundaries and scope protection
  - Success criteria and quality gates
  - Dual mandate statement
  - NO references to other tasks (task_001, task_003, etc.)
  - NO Bell curve context or template evolution notes

  **Strategic Context (Below separator):**
  - Critical context variables and file paths
  - Template evolution notes and pattern learnings
  - Bell curve context (current XX, adjacent x/xx)
  - Task progression (previous/current/next)
  - Generation metadata and protocol version

  **Auto-Application**: Claude must automatically apply this format to all cursor prompts saved to `/mnt/g/dev_tools/claude_cos/cursor_prompting/` without discussion.

  ---

# Test access line - confirming filesystem access
