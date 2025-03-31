# Prompt Guide: TDD Cycle – Red → Green → Refactor

## Purpose
Reinforces proper TDD workflow for each function, route, or feature.

## Prompt Pattern
```
1. Write a failing test (RED)
2. Write just enough code to pass the test (GREEN)
3. Refactor for elegance, reuse, and Dual Mandate compliance (REFACTOR)

Repeat this cycle for each feature.
```

## Example
```
Step: Implement `/health` endpoint
- RED: Write test that fails (expect 200 OK, JSON: `{"status": "ok"}`)
- GREEN: Implement FastAPI route
- REFACTOR: Extract to controller, add logging, ensure MDC tag present
```

## MDC Link
# MDC: tdd_pattern
