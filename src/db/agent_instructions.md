# 🤖 Agent Execution Instructions: COS Database Layer (L4)

This file provides explicit steps for IDE agents (e.g., Cursor or Claude) to safely initialize, migrate, and manage the canonical PostgreSQL storage system (`src/db/`) within the COS project.

---

## 🧠 Project Context

- COS uses **modular schemas** per backend module (e.g., `cc`, `pem`, `aic`)
- PostgreSQL stores immutable logs, outputs, and PRD history
- Alembic handles migrations centrally, even with multi-schema support
- DB models reside in: `src/db/models/`
- Pydantic schemas in: `src/db/schemas/`

---

## 🧪 When Docker is Running (PostgreSQL Services)

```bash
# One-time Alembic setup (should already be scaffolded):
alembic init src/db/migrations
```

Ensure `alembic.ini` contains:
```ini
script_location = src/db/migrations
sqlalchemy.url = postgresql://cos_user:cos_prod_pw@cos_postgres_prod:5432/cos_db_prod
```

Then:

```bash
# Auto-detect model changes and generate migration file
alembic revision --autogenerate -m "initial schema"

# Apply migration to live PostgreSQL container
alembic upgrade head
```

---

## ⚠️ Notes for IDE Coders / Agents

- Always import models into `env.py` to make Alembic aware of them.
- If you create a new module (e.g., `pipeline`, `quote`), use:
```python
__table_args__ = {"schema": "pipeline"}
```

- Avoid editing manually generated Alembic files unless you're correcting a specific SQL operation.
- Alembic versions are stored in: `src/db/migrations/versions/`

---

## ✅ Once Applied, You Should Be Able To:

- Create or query logs using models like:
  - `PRDLog`
  - `EventTrace`
  - `MemoryLink`

- Reference validated data structures via Pydantic schemas in:
  - `src/db/schemas/prd_log.py`

---

## 📌 Expansion Roadmap

Agents may:
- Add models under `src/db/models/`
- Auto-link to L3 (`mem0g`) by extending `memory_link.py`
- Reflect `ZK` node persistence in future schemas
- Archive voice → MBQ lineage inside L4
