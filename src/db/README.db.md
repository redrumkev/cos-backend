# 🗄️ COS Canonical Storage – `src/db/README.db.md`

This document defines how to structure and operate the **L4 memory layer** in COS — the canonical, structured store for logs, outputs, PRDs, and publishing artifacts.

---

## 🧠 Purpose of L4

The L4 layer serves as:
- The **system of record** (immutable truths)
- Long-term archival of high-integrity events
- Source of **publishing lineage**
- Audit trail for agents, tasks, and transformations

---

## 🛠️ Technologies Used

- **PostgreSQL**: Primary database engine (3 instances)
- **SQLAlchemy**: ORM for Python
- **Pydantic**: For validation + FastAPI schema sharing
- **Alembic**: For migrations
- **Asyncpg / psycopg2**: For async + sync db access

---

## 🧱 Database Instances

| Environment | Port | DB Name       | Purpose                     |
|-------------|------|---------------|-----------------------------|
| prod        | 5432 | cos_db_prod   | Final truth, publishing DB  |
| dev         | 5433 | cos_db_dev    | Agent dev, module testing   |
| test        | 5434 | cos_db_test   | Isolated CI/test container  |

---

## 📁 Suggested Structure

```
src/db/
├── base.py              ← SQLAlchemy base & session mgmt
├── connection.py        ← DB URI loader (env-based)
├── models/
│   ├── prd_log.py       ← PRD evolution logs
│   ├── event_trace.py   ← Event lineage
│   └── memory_link.py   ← (Optional) Links to L3 from L4
├── schemas/
│   └── prd_log.py       ← Pydantic validators
├── migrations/
│   └── versions/        ← Alembic-generated change sets
├── alembic.ini          ← Migration config file
└── README.db.md
```

---

## 🔐 Environment Variables (suggested from `.env`)

```env
POSTGRES_USER=cos_user
POSTGRES_PASSWORD=cos_prod_pw
POSTGRES_DB=cos_db_prod
DATABASE_URL=postgresql://cos_user:cos_prod_pw@cos_postgres_prod:5432/cos_db_prod
```

> Adjust the above per target (`dev`, `test`, etc.) or inject via `pydantic.BaseSettings`.

---

## 🔄 Using Alembic

Initialize (once):
```bash
alembic init migrations
```

Run migration:
```bash
alembic revision --autogenerate -m "initial"
alembic upgrade head
```

---

## ✅ Next Suggestions

- Scaffold `base.py` and `connection.py`
- Use SQLAlchemy models with schema separation logic (`__table_args__ = {"schema": "cc"}`)
- Add agent endpoint to query or archive outputs from L4

## 🧪 Once Docker is Running

```bash
# One-time Alembic setup (already scaffolded):
alembic init src/db/migrations

# Create first migration:
alembic revision --autogenerate -m "initial schema"

# Apply it to PostgreSQL (prod/dev/test):
alembic upgrade head
```
> - Tip: Each module can have its own schema in the same DB by setting:
__table_args__ = {"schema": "<module_name>"} in each model file.
