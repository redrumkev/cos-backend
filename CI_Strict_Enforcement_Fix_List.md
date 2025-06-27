# Strict Ruff CI Enforcement — Guided Fix List

Your task:
1. Use the file `CI_Strict_Enforcement_Fix_List.md` at the project root as your master to-do list.
2. Sequentially work through the files in the list, starting from the top or the last file marked as "in progress."
3. For each file:
    - Open it.
    - Fix all Ruff errors and warnings until it is 100% clean.
    - Mark your progress in the `CI_Strict_Enforcement_Fix_List.md` file as follows:
        - `[FIXED] path/to/file.py` when completed
        - `[IN PROGRESS] path/to/file.py` while working (remove this after finishing)
        - Leave untouched files as plain paths.
4. After each batch of 3–5 files, **exit or pause**, commit changes, and save the updated `CI_Strict_Enforcement_Fix_List.md`.
5. On next run, **re-read the list** and continue from the first file **not yet marked as `[FIXED]`**.

## Special Instructions
- DO NOT touch files not in the list.
- Do NOT “fix” already marked `[FIXED]` files.
- If you run into unclear rules, consult Ruff documentation or insert a TODO in the fix list for manual review.
- If the file can’t be auto-fixed, add `[BLOCKED] path/to/file.py` and a short note in the MD file.

## Example Status Format in `CI_Strict_Enforcement_Fix_List.md`:
[FIXED] scripts/run_performance_tests.py
[FIXED] src/common/base_subscriber.py
[IN PROGRESS] src/common/message_format.py
src/common/pubsub.py
src/common/redis_config.py
...

pgsql
Copy
Edit

## Resume Workflow
- **Each run:** Scan the list, pick up from first non-[FIXED] file, repeat.
- **After large changes:** Save and commit the current progress. The same prompt will always resume correctly.

## Your Next Action
- Begin with the next unmarked or `[IN PROGRESS]` file, fix all Ruff CI issues, and update the markdown list.

---

*This workflow ensures you never lose your place, never re-fix, and always move forward with perfect CI focus. When in doubt, always check `CI_Strict_Enforcement_Fix_List.md` for authoritative state.*

------

List to Fix:
[FIXED] scripts/run_performance_tests.py
[FIXED] src/common/base_subscriber.py
[FIXED] src/common/message_format.py
[FIXED] src/common/pubsub.py
[FIXED] src/common/redis_config.py
[FIXED] src/db/migrations/versions/07f2af238b83_fix_timezone_columns_for_cc_tables.py
[FIXED] tests/backend/cc/test_debug_endpoints_enhanced.py
[FIXED] tests/common/test_base_subscriber.py
[FIXED] tests/common/test_message_format.py
[FIXED] tests/common/test_pubsub.py
tests/common/test_pubsub_circuit_breaker.py
tests/common/test_pubsub_simple.py
tests/common/test_redis_config.py
tests/integration/test_redis_foundation.py
tests/integration/test_redis_performance.py
tests/integration/test_redis_performance_final.py
tests/integration/test_redis_performance_simplified.py
tests/integration/test_redis_resilience.py
tests/performance/__init__.py
tests/performance/conftest.py
tests/performance/test_comprehensive_benchmarks.py
tests/performance/test_failure_scenarios.py
tests/performance/test_performance_metrics.py
tests/performance/test_production_readiness.py
tests/performance/test_redis_benchmarks.py
tests/unit/backend/cc/test_logging_redis_publish.py
tests/unit/backend/cc/test_logging_redis_simple.py
tests/unit/common/conftest.py
tests/unit/common/test_base_subscriber_comprehensive.py
tests/unit/common/test_circuit_breaker.py
tests/unit/common/test_circuit_breaker_edge.py
tests/unit/common/test_coverage_check.py
tests/unit/common/test_enhanced_error_handling.py
tests/unit/common/test_enhanced_redis_pubsub_suite.py
tests/unit/common/test_pubsub_failures.py
tests/unit/common/test_pubsub_performance.py
tests/unit/common/test_redis_config_comprehensive.py
tests/unit/common/test_redis_config_matrix.py
tests/unit/common/test_redis_pubsub_comprehensive.py
