# PRD: COS Phase 2 - Sprint 1 - Foundational Observability & L1 Memory Plumbing

**Metadata:**

*   **Phase:** 2
*   **Sprint:** 1
*   **Title:** Foundational Observability & L1 Memory Plumbing for `cc` Module
*   **Date:** 2025-06-05
*   **Owner:** Kevin
*   **Tech Lead:** `cc-core-team` (or AI Agent executing)
*   **Dual Mandate Alignment:** [Quality: "100%", Efficiency: "100%"]
*   **FORWARD Principles:** Must adhere to all FORWARD principles in implementation.

---

## 1. Objective

This sprint aims to establish foundational observability and L1 data capture capabilities within the `cc` (Control Center) module. Key outcomes include:

1.  Seamless integration of **Logfire tracing** for end-to-end request visibility.
2.  Creation of a dedicated PostgreSQL schema, **`mem0_cc`**, to serve as the L1 ephemeral memory store for the `cc` module.
3.  Implementation of an **asynchronous logging helper (`log_l1`)** within `cc` services to write structured data to `mem0_cc`.
4.  Implementation of **request-ID middleware** to ensure traceability across Logfire spans and `mem0_cc` records.

These components are critical prerequisites for subsequent sprints focused on Redis eventing, L2 graph integration (Neo4j), and full MCP server implementation. All deliverables must meet the Dual Mandate quality and efficiency gates from day one.

---

## 2. Scope

### In Scope for Sprint 1:

*   **Logfire Integration:**
    *   Adding `logfire` SDK as a project dependency.
    *   Secure sourcing of `LOGFIRE_TOKEN` via environment variable; graceful degradation if token is absent (disable tracing with a warning).
    *   Auto-instrumentation of the FastAPI application (`cc_main.py`) for basic request/response tracing.
    *   Implementation of `src/common/logger_logfire.py` bootstrap module.
*   **Request ID Management:**
    *   Creation of `src/common/request_id_middleware.py`.
    *   Middleware to generate a UUID v4 request ID if `X-Request-ID` header is absent.
    *   Storage of the request ID in `request.state.request_id` (or `contextvars`) for downstream access.
    *   Ensuring Logfire spans are tagged with this `request_id`.
*   **L1 `mem0_cc` Data Layer:**
    *   Design and implementation of SQLAlchemy models in `src/backend/cc/mem0_models.py` for:
        *   `BaseLog(id: UUID, timestamp: DateTime, source_module: str, request_id: str, trace_id: str)`
        *   `PromptTrace(role: str, content: Text, tokens_in: int, tokens_out: int, base_log_id: FK to BaseLog.id)`
        *   `EventLog(event_type: str, payload: JSONB, base_log_id: FK to BaseLog.id)`
        *   (Note: `source_module` will be hardcoded to "cc" for this sprint. `trace_id` from Logfire. `request_id` from middleware.)
    *   Generation and manual curation of an Alembic migration script (`migrations/versions/ae_xyz_mem0_init.py`) to create the `mem0_cc` schema and these tables in PostgreSQL.
*   **Async Logging Helper:**
    *   Creation of an asynchronous helper function `log_l1()` in `src/backend/cc/services/logging.py`.
    *   This helper will accept structured data (e.g., type of event, payload) and the `request_id`.
    *   It will use a dependency-injected SQLAlchemy `AsyncSession` (from `cc.deps.get_db_session`) for database writes.
    *   It will construct and insert records into the appropriate `mem0_cc` tables (`PromptTrace` or `EventLog`, linking to a new `BaseLog` record).
    *   It will add custom attributes to the current Logfire span (e.g., `mem0.event_type`, `mem0.record_id`).
*   **Initial Integration & Test Endpoint:**
    *   Integration of `log_l1()` via FastAPI router hooks (e.g., a response hook) or explicit calls for specific events.
    *   Creation of a temporary `debug_router.py` with a `/test-log` POST endpoint. This endpoint will:
        *   Accept a minimal JSON payload.
        *   Call `log_l1()` to record a `PromptTrace` (simulating an LLM interaction log) and an `EventLog` (simulating a generic system event).
        *   Return a 200 OK response.
        *   (This endpoint is for testing purposes in S1 and will likely be removed or refactored in later sprints).
*   **Testing & Quality:**
    *   Comprehensive unit tests for all new Python modules and functions, achieving ≥ 97% unit test coverage.
    *   Latency benchmark tests for the `log_l1()` insertion process.
*   **CI/CD & Developer Experience:**
    *   Creation of placeholder directories: `src/backend/cc/cc_mcp/tools/` and `src/backend/cc/cc_mcp/resources/` (each containing a `.gitkeep` file).
    *   Creation of a placeholder script: `scripts/check_mcp_filename_drift.py`. For Sprint 1, this script will contain a main function that simply `pass`es and includes a `# TODO: Implement full logic in Sprint 4.` comment. It should be executable and exit with 0.
    *   Updates to `.github/workflows/ci.yml` to include new coverage gates, linting, strict MyPy checks, and execution of the placeholder drift checker.

### Out of Scope for Sprint 1:

*   Redis Pub/Sub integration for `mem0.recorded.cc` events (deferred to Sprint 2).
*   Neo4j schema (`graph_models.py`) and L1->L2 graph consumer implementation (deferred to Sprint 3).
*   Full MCP server implementation, including `/mcp/capabilities` endpoint and detailed Tool/Resource YAML definitions (deferred to Sprint 4).
*   Semantic or content-based logic within the placeholder `check_mcp_filename_drift.py` script.
*   AlphaEvolve integration or any advanced analytics on Logfire traces.

---

## 3. Success Metrics (Quantitative)

*   **`logfire_span_complete_rate`:** ≥ 95% of requests to `/test-log` (and eventually other key `cc` endpoints) result in traceable end-to-end spans in Logfire (from request entry to `log_l1` completion).
*   **`mem0_insert_p95_ms`:** p95 latency for the `log_l1()` database insertion operation (including creating `BaseLog` and linked `PromptTrace`/`EventLog`) is < 2 milliseconds, as measured by local development benchmarks.
*   **`coverage_unit`:** ≥ 97% unit test coverage for all new and modified Python code delivered in this sprint. Overall project coverage must be ≥ 90%.
*   **`ci_green_on_main`:** All CI checks (linting, MyPy strict, Bandit, unit tests, coverage gates, placeholder drift check) pass on the main branch upon sprint completion.

---

## 4. Deliverables

*   **Code:**
    *   `src/common/logger_logfire.py`
    *   `src/common/request_id_middleware.py`
    *   `src/backend/cc/mem0_models.py`
    *   `src/backend/cc/services/logging.py` (containing `log_l1()` helper)
    *   `migrations/versions/ae_XYZ_mem0_init.py` (Alembic migration script, `XYZ` to be replaced by actual hash)
    *   `scripts/check_mcp_filename_drift.py` (placeholder script)
    *   `src/backend/cc/routers/debug_router.py` (containing `/test-log` endpoint)
    *   `.gitkeep` files in `src/backend/cc/cc_mcp/tools/` and `src/backend/cc/cc_mcp/resources/`
*   **Tests:**
    *   `tests/unit/common/test_logger_logfire.py`
    *   `tests/unit/common/test_request_id_middleware.py`
    *   `tests/unit/backend/cc/test_mem0_models.py`
    *   `tests/unit/backend/cc/test_log_l1.py` (including latency benchmarks)
*   **Documentation:**
    *   `docs/phase2/sprint1_results.md`: A summary document detailing achieved success metrics, key learnings, any challenges encountered, and a screenshot of Logfire traces for the `/test-log` endpoint.
*   **CI Configuration:**
    *   Updated `.github/workflows/ci.yml` reflecting new test paths, coverage requirements, and the placeholder drift checker step.

---

## 5. Acceptance Criteria (Qualitative & Testable)

*   [ ] **Logfire Tracing:** A POST request to the new `/test-log` endpoint generates a complete Logfire trace. This trace must include tags/attributes indicating `layer=api` and `layer=service` (for `log_l1`), and the `request_id` must be present in all relevant spans.
*   [ ] **`mem0_cc` Data Integrity:** Following a successful POST to `/test-log`, new corresponding records are created in `mem0_cc.base_log` and linked records in `mem0_cc.prompt_trace` and `mem0_cc.event_log`. The `request_id` and Logfire `trace_id` must be correctly populated in `mem0_cc.base_log`.
*   [ ] **Performance:** The p95 latency for the `log_l1()` database insertion operations is verified to be < 2ms via `pytest-benchmark` or a similar local testing setup.
*   [ ] **Test Coverage:** `pytest --cov` report shows unit test coverage ≥ 97% for new/modified modules and overall project coverage ≥ 90%.
*   [ ] **Logfire Visibility:** Logfire spans for the `cos-cc` service are visible in the designated Logfire project (either cloud dashboard or local dashboard if self-hosting Logfire, contingent on `LOGFIRE_TOKEN` being set).
*   [ ] **Drift Checker Stub:** The `scripts/check_mcp_filename_drift.py` script exists, is executable, and exits with code 0. The placeholder directories `src/backend/cc/cc_mcp/tools/` and `src/backend/cc/cc_mcp/resources/` are created.
*   [ ] **Sprint Results Documentation:** `docs/phase2/sprint1_results.md` is created and contains the summary of metrics and at least one screenshot of a Logfire trace for the `/test-log` endpoint.
*   [ ] **CI Pipeline:** All CI checks pass successfully on the commit that finalizes this sprint's work.

---

## 6. Risks & Mitigation Strategies

*   **Logfire Instrumentation Overhead:**
    *   *Risk:* Auto-instrumentation or custom spanning adds unacceptable latency to requests.
    *   *Mitigation:* Continuously monitor p95 latency of `/test-log` and other critical endpoints. If overhead is detected, investigate Logfire sampling options or move `log_l1` calls to a background task/async queue (though this complicates trace correlation and is a last resort for S1).
*   **Alembic Migration Issues / Schema Mismatch:**
    *   *Risk:* Autogenerated migration is incorrect or doesn't match model definitions precisely.
    *   *Mitigation:* Manually review and curate the auto-generated Alembic script. CI pipeline should include a step to run migrations against a fresh, throw-away database to catch errors early.
*   **Complexity in Request ID Propagation:**
    *   *Risk:* Difficulty in reliably passing the request ID from middleware to router hooks and then into the `log_l1` service and Logfire spans.
    *   *Mitigation:* Prioritize standard FastAPI mechanisms like `request.state` or `contextvars.ContextVar`. Thoroughly unit test the middleware and its interaction with downstream consumers of the request ID.
*   **Placeholder Drift Checker Confusion:**
    *   *Risk:* Team (or AI Coder) attempts to implement full logic for the drift checker in S1 due to unclear "placeholder" definition.
    *   *Mitigation:* The scope note "For Sprint 1, this script will contain a main function that simply `pass`es..." must be strictly adhered to.

---

## 7. Guard Rails for IDE Coder (Cursor) Execution

*   **Strict Scope Adherence:** Implement **only** the features and deliverables explicitly listed within the "In Scope for Sprint 1" section of this PRD. Do not implement features marked "Out of Scope" or those planned for future sprints.
*   **File Modifications:** Only modify or create files listed under "Deliverables: Code" and "Deliverables: Tests." Do not alter other existing project files unless it's a direct and unavoidable consequence of implementing a scoped item (e.g., adding an import to `cc_main.py` for new middleware).
*   **Focus on Foundations:** This sprint is about building solid, testable foundations for logging and L1 data. Avoid premature optimization or overly complex solutions for the `log_l1` helper or middleware. Simplicity and correctness are paramount.
*   **Testing is Paramount:** Every new piece of logic *must* be accompanied by comprehensive unit tests. Adhere to the 97% unit coverage target for new code.
*   **Async All The Way:** All I/O operations, especially database writes in `log_l1()`, must be fully asynchronous and non-blocking to the main request thread. Utilize `async/await` and ensure the SQLAlchemy session is async.
*   **No TODOs in Shippable Code:** Code delivered at the end of the sprint should be complete for the defined scope. If a thought for future improvement arises, note it for Kevin/discussion, but do not leave `# TODO` comments in the S1 deliverables that imply incompleteness for S1 scope.
*   **Configuration via Environment:** Adhere to using environment variables for all external service configurations (e.g., `LOGFIRE_TOKEN`, Database URLs). Do not hardcode secrets or environment-specific values.
*   **Adherence to Existing Patterns:** For things like dependency injection (e.g., for DB sessions in `log_l1`), follow existing patterns within the `cc` module to maintain consistency.

---
