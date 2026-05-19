---
name: mathbattle-fixbug
description: Use when encountering a bug, test failure, or unexpected behavior in MathBattle-BE, before proposing fixes
---

# MathBattle Fix Bug Workflow

## Overview

Systematic debugging process for MathBattle-BE. Always find root cause before fixing — never patch symptoms.

## Checklist

### Phase 1: Reproduce

1. **Capture the exact error** — full stack trace, test output, or observed behavior
2. **Reproduce reliably** — run the failing test or trigger the bug consistently
   ```bash
   pytest tests/test_xxx.py::TestClass::test_method -v
   ```
3. **Narrow the scope** — which module: model / schema / service / route?

### Phase 2: Root Cause

4. **Read the relevant code** — read the full function/class, not just the error line
5. **Trace the data flow** — follow: request → route → service → DB → response
6. **Form a hypothesis** — state what you think is wrong and why
7. **Verify with minimal reproduction** — if needed, isolate in a small test

### Phase 3: Fix

8. **Fix the root cause** — not the symptom
   - Bug in model → fix model, check if migration needed
   - Bug in service → fix service logic
   - Bug in route → fix validation or response format
   - Bug in test → only fix test if the test itself is wrong, not to make it pass
9. **Check for the same bug elsewhere** — grep for similar patterns

### Phase 4: Verify

10. **Run the failing test** — must pass now
    ```bash
    pytest tests/test_xxx.py -v
    ```
11. **Run full test suite** — no regression
    ```bash
    pytest -v
    ```
12. **No `print()` left** — remove any debug prints added during investigation

### Phase 5: Commit and Push

13. **Stage and commit the fix**
    ```bash
    git add <specific files changed>
    git commit -m "fix(<module>): <what was wrong and how fixed>"
    git push origin main
    ```
    Commit message examples:
    - `fix(auth): handle expired token in refresh flow`
    - `fix(profile): return 409 instead of 500 on duplicate username`
    - `fix(game): correct score calculation on timeout`

## Debugging Cheatsheet

| Symptom | Where to look |
|---------|--------------|
| 422 Unprocessable Entity | Pydantic schema — field types, validators |
| 500 Internal Server Error | Service — unhandled exception, bad DB query |
| 401 but token is valid | `get_current_user_id()` in `app/api/deps.py` |
| Test passes alone, fails together | DB isolation — leftover state from another test |
| Alembic error on upgrade | Check migration file for conflicting heads |
| Async error / event loop | Missing `await`, or sync function called in async context |

## Common Mistakes

- Fixing the test to make it green without fixing the code → don't
- Adding `try/except` to silence the error → find root cause instead
- Modifying multiple things at once → change one thing, re-run, confirm
- Forgetting to run the full suite after fix → always `pytest -v` at the end
