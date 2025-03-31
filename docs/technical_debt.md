# Technical Debt Tracking: Code Suppressions

This document tracks temporary code suppressions (`# noqa`, `# type: ignore`) added to the codebase. It serves as the initial tracking mechanism until the `mem0` layer is operational, at which point this information may be migrated or used to inform `mem0` for automated reminders and agent awareness.

The goal is to ensure these suppressions are revisited and resolved according to the "Relentless Evolution" principle of COS.

**Developer Checklist:** When adding a `# noqa` or `# type: ignore`, update this file in the *same commit*.

---

## Suppression Entries

Each entry details a specific suppression instance:

*   **File Path:** Relative path from the repository root.
*   **Line Number:** The line where the suppression occurs.
*   **Suppression Code:** The exact code used (e.g., `# noqa: E501`, `# type: ignore[attr-defined]`).
*   **Commit Hash:** The commit hash when the suppression was added (or last reviewed).
*   **Justification:** Why the suppression is necessary.
*   **Review Trigger:** Criteria for revisiting the suppression.
*   **Status:** Open | Under Review | Resolved

---

### Entry 1

*   **File Path:** `src/common/ledger_view.py`
*   **Line Number:** 9
*   **Suppression Code:** `# noqa: UP040`
*   **Commit Hash:** `444771f` (Placeholder - added during initial setup commit)
*   **Justification:** Temporary workaround for Ruff/MyPy rule conflict. Ruff prefers the `type` keyword (PEP 695), but MyPy version used in pre-commit does not yet support it. MyPy's stricter checks take precedence.
*   **Review Trigger:** On next MyPy version update or when MyPy adds stable PEP 695 support.
*   **Status:** Open

---

### Entry 2

*   **File Path:** `src/common/ledger_view.py`
*   **Line Number:** 10
*   **Suppression Code:** `# noqa: UP040`
*   **Commit Hash:** `444771f` (Placeholder - added during initial setup commit)
*   **Justification:** Temporary workaround for Ruff/MyPy rule conflict. Ruff prefers the `type` keyword (PEP 695), but MyPy version used in pre-commit does not yet support it. MyPy's stricter checks take precedence.
*   **Review Trigger:** On next MyPy version update or when MyPy adds stable PEP 695 support.
*   **Status:** Open

---

### Entry 3

*   **File Path:** `src/infrastructure/mem0/main.py`
*   **Line Number:** 12
*   **Suppression Code:** `# type: ignore[misc]`
*   **Commit Hash:** `444771f` (Placeholder - added during initial setup commit)
*   **Justification:** Known interaction issue where MyPy struggles to correctly infer types for complex decorators like FastAPI's route decorators, even when the underlying function is correctly typed.
*   **Review Trigger:** On next MyPy or FastAPI version update. Quarterly Review.
*   **Status:** Open

---

### Entry 4

*   **File Path:** `src/infrastructure/mem0/main.py`
*   **Line Number:** 17
*   **Suppression Code:** `# type: ignore[misc]`
*   **Commit Hash:** `444771f` (Placeholder - added during initial setup commit)
*   **Justification:** Known interaction issue where MyPy struggles to correctly infer types for complex decorators like FastAPI's route decorators, even when the underlying function is correctly typed.
*   **Review Trigger:** On next MyPy or FastAPI version update. Quarterly Review.
*   **Status:** Open

---

### Entry 5

*   **File Path:** `src/infrastructure/mem0/main.py`
*   **Line Number:** 34
*   **Suppression Code:** `# type: ignore[misc]`
*   **Commit Hash:** `444771f` (Placeholder - added during initial setup commit)
*   **Justification:** Known interaction issue where MyPy struggles to correctly infer types for complex decorators like FastAPI's route decorators, even when the underlying function is correctly typed.
*   **Review Trigger:** On next MyPy or FastAPI version update. Quarterly Review.
*   **Status:** Open

---

### Entry 6

*   **File Path:** `src/backend/cc/router.py`
*   **Line Number:** 10
*   **Suppression Code:** `# type: ignore[misc]`
*   **Commit Hash:** `444771f` (Placeholder - added during initial setup commit)
*   **Justification:** Known interaction issue where MyPy struggles to correctly infer types for complex decorators like FastAPI's route decorators, even when the underlying function is correctly typed.
*   **Review Trigger:** On next MyPy or FastAPI version update. Quarterly Review.
*   **Status:** Open

---

### Entry 7

*   **File Path:** `cursor/cursor_memory.py`
*   **Line Number:** 50
*   **Suppression Code:** `# noqa: T201`
*   **Commit Hash:** `444771f` (Placeholder - added during initial setup commit)
*   **Justification:** `print` statement is intentionally used within an `if __name__ == "__main__":` block for example usage/demonstration purposes, not for production logging.
*   **Review Trigger:** If example usage block is removed or refactored.
*   **Status:** Open

---
