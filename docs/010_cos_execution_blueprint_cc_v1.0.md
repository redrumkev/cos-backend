# COS Execution Blueprint: cc v1.0 (Condensed)

## 1. Alignment & Vision
- `cc` module sets the Gold Standard for all COS modules (template for structure, testing, quality gates).

## 2. Key Refinements
1. **mem0 Schema Isolation:**
   Each module has its own `mem0_<module>` schema, set via env vars, Alembic managed.
2. **Neo4j Driver Pooling:**
   Singleton pattern for async driver.
3. **Graph Registry Auto-Import:**
   Future: auto-discovery of graph models.
4. **CI/CD "Red Bar":**
   97%+ test coverage, strict lint/type gates, stop pipeline on first fail.

### 3. Actionable Work Chunks
- **Each chunk = 1 commit.**
```yaml
# use task-master mcp for details on each step/task necessary for dual mandate execution
0: Prune legacy DB code; solidify Base.
1: Gold config (`common/config.py`, env vars, TDD config).
2: Connection gold (TDD DB connection/session).
3: Robust test fixtures (DB/Redis sessions for test isolation).
4: Alembic setup & initial migrations (`cc`, `mem0_cc` schemas).
5: Deps refactor (real DB/Redis deps in cc/deps.py).
6: CRUD TDD pass 1 (system_health).
7: CRUD TDD pass 2 (all other cc CRUD; mem0 logs if needed).
8: Router/services/tests alignment, reduce mocks.
9: Quality gate enforcement (coverage, ruff, mypy).
10: `generate_module.py` MVP (auto-template new modules, correct all schema/label naming).
```

**Post-Chunk 10 Milestone:**
- All deps installed, core services up (`docker compose up ...`)
- `pytest` passes, 97%+ coverage, zero lint/type errors.
- Generator creates new compliant modules in one step.

## 4. Outcomes
- **Frictionless Duplication:** Instant, correct module creation.
- **True Data Isolation:** Module namespacing at DB/graph level.
- **No Technical Debt:** Pre-commit and CI prevent quality drift.
- **Cognitive Simplicity:** One mental model: domain → module → type.
- **cc as Living Template:** The reference for all future modules.
