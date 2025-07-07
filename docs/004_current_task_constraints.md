## **004_current_task_constraints.md**
```markdown
# Current Task Constraints & Scope

*Updated per task - contains specific constraints for current work*

## Constitutional Adherence (Non-Negotiable)
**Dual Mandate**: 100% Quality + 100% Efficiency - Never compromise either
**FORWARD Principles**: Every decision must align with Frictionless, Orchestrated, Real-Time, Wide-Angle, Adaptive, Relentless, Destiny-Driven principles

## Cursor Behavioral Requirements (Critical)

### Commit Message Preservation
- **MUST commit EXACTLY what is provided** - no format changes, style modifications, or shortening
- Kevin's format: `Phase 2 Sprint 1.12: Task_012 - Description with sub-points`
- Do NOT change to: `Phase 2 - Sprint 1 task 12` or any other variation
- Preserve all bullet points, spacing, and multi-line structure exactly as given

### Quality Gate Enforcement
- **Fix ALL lint/errors before commit** - no `# ruff: noqa` comments unless explicitly required
- **Pass ALL quality gates**: pre-commit hooks, commit hooks, CI requirements
- Commenting out future issues creates technical debt and CI failures
- If something will break in 10 commits, architect it properly now

### Code Completion Standards
- Implement complete solutions, not placeholders
- Every function must have proper error handling
- All async operations must be properly awaited
- Type hints are mandatory, not optional

## Active Task: [Updated by .taskmaster]
**Task ID**: task_0xx.txt
**Scope**: [Specific deliverables for current task]
**Files to Modify**: [Exact file paths allowed]
**Files NOT to Touch**: [Explicit exclusions]

## Current Sprint Constraints
- Redis operations must be async
- Maintain existing log_l1() function signature
- Publish only after successful DB commit
- All new code requires 97% unit test coverage
- Integration tests must pass <5ms round-trip requirement

## Dependencies Available
- ✅ log_l1() function (Sprint 1)
- ✅ BaseLog, PromptTrace, EventLog models (Sprint 1)
- ✅ Request ID middleware (Sprint 1)
- ✅ Logfire tracing setup (Sprint 1)

## Forbidden Changes
- Do not modify Sprint 1 deliverables
- Do not add new database tables
- Do not change existing API signatures
- Do not implement Sprint 3+ features (Neo4j, graph models)
- Do not modify CI/CD pipeline unless explicitly required

## Quality Gates This Task
- All tests must pass
- Coverage gate: 97% unit, 90% overall
- Linting: zero ruff/mypy warnings
- Performance: publish latency < 1ms local
- Dual Mandate: Quality AND Efficiency both at 100%
