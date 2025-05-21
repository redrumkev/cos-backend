<context>
# Overview
The **“CC Gold-Standard”** sprint upgrades the `cc` FastAPI module into a template-grade vertical slice:

* ≥ 97 % real test coverage, Ruff/Mypy clean
* Postgres schema isolation (`cc`, `mem0_cc`)
* Neo4j single-DB, dual-label isolation (`:Module:tech_cc`) via **neo4j-rust** driver
* Generator script that clones this slice into any future domain/module (tech, zk, publishing…)

This becomes the canonical backend pattern for COS, Pipeline, Publishing, etc.

# Core Features
| # | Feature | What | Why | How |
|---|---------|------|-----|-----|
| 1 | **Canonical DB Core** | Asyncpg engine/session (dev, test) | No config drift | `src/db/connection.py` |
| 2 | **Abstract Base** | One SQLAlchemy Base | Shared conventions | `src/db/base.py` |
| 3 | **Schema-per-Module** | `__table_args__={'schema': 'cc'}` | Data siloing | Alembic + fixtures |
| 4 | **mem0 SQL Scratch** | `mem0_cc` schema for temp structured data | Prevents cross-module bleed until Redis mem0 lands | `MEM0_SCHEMA` env + models |
| 5 | **Neo4j Rust Adapter** | Pooled driver/sessions | Low-latency graph ops | `src/graph/base.py` |
| 6 | **Dual-Label Convention** | `:<Type>` + `:<domain_module>` | Readable cross-module queries | generator + registry |
| 7 | **Module Generator** | `generate_module.py tech pem` | One-command duplication | Copies template, rewrites placeholders, patches `alembic/env.py` |
| 8 | **CI Red-Bar Gate** | Ruff → Mypy(strict) → Pytest 97 % | Blocks regressions | `.github/workflows/ci.yml` |

# Developer XP
1. `git checkout -b feature/...`, run generator, code.
2. `docker compose up -d` + `uv pip sync` → app runs.
3. `pytest -q` ≥ 97 % before merge.
4. New module nodes auto-appear in Neo4j with `:Type:domain_module` labels.

</context>

<PRD>
# Technical Architecture
* **Relational stack** – `src/db/base.py`, `src/db/connection.py`, `alembic/`
* **Graph stack** – `src/graph/base.py`, `src/graph/registry.py`, label constants per module
* **Back-end slice** – `src/backend/cc` (models, crud, deps, services, router)
* **Module generator** – `scripts/generate_module.py`
* **CI** – GitHub Actions: Ruff › Mypy › Pytest 97
* **Compose files** – `docker-compose.yml` (core); `docker-compose.mem0g.yml` (neo4j)

# Data Models
| Layer | Object | Storage |
|-------|--------|---------|
| Persistent | `cc.health_status`, `cc.modules` | Postgres |
| Scratch | `mem0_cc.scratch_note` | Postgres |
| Graph | `:Module:tech_cc` nodes | Neo4j |

# Development Roadmap
| Phase | Tasks | Outcome |
|-------|-------|---------|
| **P0** | Housekeeping commit `#0a` | Remove obsolete infra/memory stubs |
| **P1** | Tasks 1-4 | Green baseline (config, connection, fixtures) |
| **P2** | Tasks 5-6 | Alembic init, deps swap |
| **P3** | Tasks 7-8 | CRUD + router fully real |
| **P4** | Task 9 | mem0 SQL scratch schema live |
| **P5** | Task 10 | Neo4j rust driver & registry |
| **P6** | Task 11 | Module generator MVP |
| **P7** | Task 12 | CI red-bar gate active |
| **P8** | Task 13 | Docs + tag `cc-v1.0` |

## Commit-Level Checklist
| # | Commit message | Key actions |
|---|----------------|-------------|
| 0 | **`#0: prune legacy code`** | rm `src/infrastructure`, `src/memory`, `src/common/mem0_client.py`; mark Base abstract |
| 1 | **`#1: config-gold (MEM0_SCHEMA)`** | .env template, settings var, `tests/common/test_config.py` |
| 2 | **`#2: connection-gold`** | Implement `src/db/connection.py`; `tests/db/test_connection.py` |
| 3 | **`#3: fixtures-gold`** | `tests/conftest.py` with `test_db_session`, `mem0_db_session`, `client` |
| 4 | **`#4: alembic-init cc`** | Update `alembic.ini` + `env.py`; first migration; table-exist tests |
| 5 | **`#5: deps-refactor`** | Replace mock DB dep; `tests/backend/cc/test_deps.py` |
| 6 | **`#6: crud-pass1`** | Implement `get_system_health` with tests |
| 7 | **`#7: crud-pass2`** | Complete CRUD/services/router; un-mock tests |
| 8 | **`#8: coverage + lint gate`** | Ruff, Mypy strict config; enable pytest fail-under 97 |
| 9 | **`#9: mem0 sql scratch`** | `backend/cc/mem0_models.py`; migration; tests |
| 10 | **`#10: neo4j rust adapter`** | `graph/base.py`, `registry.py`; smoke test |
| 11 | **`#11: module generator MVP`** | Generator script; patches `alembic/env.py`; creates stub tests |
| 12 | **`#12: CI workflow`** | `.github/workflows/ci.yml` with service containers |
| 13 | **`#13: docs + tag cc-v1.0`** | README updates; git tag |

# Logical Dependency Chain
1 → 2 → 3 → 4 → 5/6/7 → 8 → 9 → 10 → 11 → 12 → 13

# Risks / Mitigations
* Neo4j rust driver Python bindings immature → wrap in try/except with fallback to bolt driver.
* Coverage dip Tasks 0-3 → fail-under off until Task 5 then on @ 97.
* Alembic env drift → generator auto-appends import lines.

# Out of Scope
* Redis L1 mem0 client and service (Sprint 2).
* Front-end graph explorer.
* Cross-module analytical jobs.

</PRD>
