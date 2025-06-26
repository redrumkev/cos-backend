# COS Module Standards & Patterns

## Constitutional Foundation (Always Applied)

### Dual Mandate (Non-Negotiable)
**100% Quality + 100% Efficiency** - Every architectural decision, code pattern, and implementation must honor both principles simultaneously. Quality without efficiency is unsustainable; efficiency without quality is technical debt.

### FORWARD Principles (Technical DNA)
- **Frictionless**: Standard structures, rapid scaffolding, zero manual deployment
- **Orchestrated**: Intelligent automation with human-in-the-loop oversight
- **Real-Time**: New capabilities in <1 day, zero downtime expansion
- **Wide-Angle**: Decisions for centuries, not sprints
- **Adaptive**: 10x growth without performance degradation
- **Relentless**: Every failure is fuel, every success is seed
- **Destiny-Driven**: All code serves the 100+ book legacy vision

## Module Architecture (Immutable)

Each module = Self-contained vertical slice (API → DB → Graph → MCP)
Gold Standard = cc module (contains ALL wiring patterns)
Cross-Module = REST APIs + Redis pub-sub only (NO direct imports)
Data Isolation = Schema per module, label per module, channel per module

## File Structure (Standard)
backend/<module>/
├── <module>_main.py     # FastAPI app, router mounting, lifespan
├── router.py            # API endpoints, request validation
├── schemas.py           # Pydantic models (request/response/internal)
├── services.py          # Business logic, orchestrates CRUD
├── crud.py              # Direct SQLAlchemy DB operations
├── models.py            # ORM models (primary schema)
├── mem0_models.py       # ORM models (mem0 schema)
├── graph_models.py      # Neo4j node/relationship definitions
├── deps.py              # FastAPI dependencies (DB, Redis sessions)
├── utils.py             # Module utilities
└── tests/               # All pytest tests (unit, integration, API)

## Naming Conventions
- Module schema: `<module>` (primary), `mem0_<module>` (ephemeral)
- Neo4j labels: `:<Type>:<module>` (e.g., `:Prompt:cc`)
- Redis channels: `<topic>.<module>` (e.g., `mem0.recorded.cc`)
- Service names: `cos-<module>` (e.g., `cos-cc`)
