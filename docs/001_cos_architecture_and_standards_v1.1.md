# COS Architecture & Standards v1.1 (Condensed)

## I. System Architecture

### 1.1. Hybrid Vertical Slice + Atomic Design
- Each module: Self-contained, from API to its DB schemas/graph labels.
- Internal: All logic in atomic, testable units (function/class).
- Enables: Maximum AI-readability, easy module generation, TDD.

### 1.2. Standard Module Structure
```bash
backend/
├── module_name/
│   ├── module_name_main.py  # FastAPI app init
│   ├── router.py            # API endpoints
│   ├── schemas.py           # Pydantic models
│   ├── services.py          # Business logic
│   ├── crud.py              # DB operations
│   ├── models.py            # SQLAlchemy (primary schema)
│   ├── mem0_models.py       # SQLAlchemy (mem0 schema)
│   ├── graph_models.py      # Neo4j nodes/relations (optional)
│   ├── deps.py              # FastAPI deps
│   ├── utils.py             # Utilities
│   └── tests/               # Unit/integration/API tests
│   └── module_name_map.yaml # AI manifest
```

*   **Key Files Purpose Snapshot:**
    *   `*_main.py`: FastAPI app init, router mounting, lifespan.
    *   `router.py`: APIRouter, endpoint definitions, request validation via schemas, dependency injection.
    *   `schemas.py`: Pydantic models for API request/response and internal data transfer.
    *   `services.py`: Orchestrates business logic, calling CRUD operations and other services.
    *   `crud.py`: Contains functions for direct, atomic database interactions (SQLAlchemy).
    *   `models.py`: Defines SQLAlchemy ORM models for the module's primary PostgreSQL schema (e.g., `schema="<module_name>"`).
    *   `mem0_models.py`: Defines SQLAlchemy ORM models for the module's L1 ephemeral `mem0` PostgreSQL schema (e.g., `schema="mem0_<module_name>"`).
    *   `graph_models.py`: Defines classes/logic for interacting with the module's namespaced data in Neo4j.
    *   `deps.py`: Provides FastAPI dependencies like `DBSession`, `RedisClient`.

### 1.3. Cross-Module Communication (The "Interconnections")
*   **Synchronous Operations:** Exclusively via REST API calls between modules, facilitated by an HTTP client (e.g., `httpx`).
*   **Asynchronous Events:** Exclusively via Redis Pub/Sub for event notifications and decoupled workflows.
*   **Prohibition:** No direct Python imports between different functional modules (e.g., `from backend.pem import ...` in `backend.cc` is forbidden).
*   **Shared Data Access:** Only through the database (PostgreSQL for structured data, Neo4j for graph data, Redis for cache/ephemeral state). Each module respects schema/label boundaries.

### 1.4. Common & Core Infrastructure Code (The "Shared Foundations")
*   **`src/common/` Directory:**
    *   **Usage:** Houses truly universal, application-agnostic utilities and clients.
    *   **Examples:** `config.py` (Pydantic settings), `logger.py` (standardized logging to `mem0`), `redis_client.py`, `mem0_client.py` (if `mem0` had a direct API distinct from logging).
    *   **Strict Inclusion:** No module-specific business logic or utilities.
*   **`src/db/` Directory:**
    *   **Usage:** Core database infrastructure.
    *   **Components:** `base.py` (SQLAlchemy `DeclarativeBase`), `connection.py` (engine/session setup using `common/config.py`).
*   **`src/graph/` Directory:**
    *   **Usage:** Core graph database infrastructure.
    *   **Components:** `base.py` (Neo4j driver/session setup), `config.py` (graph-specific config), `registry.py` (dynamic model loading), `modules/` (domain-specific graph models).

### 1.5. Module Map YAML (`<module_name>_map.yaml`)
*   **Purpose:** An AI-readable manifest detailing a module's structure, files, purposes, dependencies, API endpoints, and database/graph schemas. Essential for AI-assisted development and system understanding.
*   **Structure Example (referencing `cc_map.yaml` from Gold Standard):**

```yaml
# module_name_map.yaml
    module:
      name: "module_name"
      description: "Core purpose statement"
      version: "1.0"
      # ... files, database (main & mem0 schemas), graph_layer, api_endpoints, integrations ...
```

### 1.6. Module Generation & Evolution (`scripts/generate_module.py`)
*   **Purpose:** Automates the creation of new COS modules by cloning the current Gold Standard (initially `cc` v1.0).
*   **Functionality:** Takes `domain` and `module_name` as input. Scaffolds the directory structure; templatizes file contents (module names, schema names, graph labels); generates placeholder `models.py`, `mem0_models.py`, `graph_models.py`, and `tests/`; updates `.env` stubs.
*   **Outcome:** Produces a new module skeleton that adheres to all standards, ready for TDD implementation of its specific logic.

## II. Development Standards

### 2.1. TDD Workflow: RED → GREEN → REFACTOR
- Failing test → minimal code → refactor.
- **97%+** coverage required. All types: unit, integration, API, edge.

### 2.2. Code Quality
- Full type hints, strict mypy.
- Pydantic for API/internal validation.
- black, ruff (zero warnings/errors), isort.
- Clear naming, docstrings, ticketed TODOs.

### 2.3. Logging
- Use `common/logger.py` (`log_event`).
- Logs go to module's `mem0_<module>` schema.

### 2.4. Database/Graph Practices
- Each module: own Postgres schemas (`<module>`, `mem0_<module>`), managed by Alembic.
- Neo4j: dual-label (`:<Type>:<domain_module>`), models in `graph_models.py`.
- SQL: explicit columns, no N+1s, batch, index, transaction safety.

### 2.5. Error Handling
- Custom exceptions; consistent JSON error format.

### 2.6. Security
- No secrets in code/logs; sanitize inputs; (future: RBAC, auth).

### 2.7. Performance
- Default async for I/O.
- API P95 <300ms, efficient resource use, connection pools.
