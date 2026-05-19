---
name: mathbattle-feature-dev
description: Use when implementing any new feature or sub-function (SF) in MathBattle-BE, from spec to passing tests
---

# MathBattle Feature Development Workflow

## Overview

13-step process for implementing any SF in MathBattle-BE. Follow in order — each step gates the next.

## Checklist

### Phase 1: Understand

1. **Read the spec** — `docs/01_Design/BE/sub_functions/G{group}_F{feature}_SF{n}.md`
   - Business logic, inputs/outputs, edge cases
2. **Design database schema** — tables, relationships, fields

### Phase 2: Database

3. **Create/update SQLAlchemy model** — `app/models/`
4. **Write Alembic migration**
   ```bash
   alembic revision --autogenerate -m "description"
   alembic upgrade head
   ```
5. **Validate schema (MANDATORY)** — insert sample data, query back, confirm schema works before moving on

### Phase 3: Implementation

6. **Define Pydantic schemas** — `app/schemas/` (request/response)
7. **Implement service layer** — `app/services/` (business logic only, no API logic)
8. **Create route handler** — `app/api/v1/` (thin: request → service → response)
9. **Register router** (if new module) — `app/main.py`

### Phase 4: Tests

10. **Write tests** — `tests/` (mirror feature name)
    - Happy path
    - Edge cases
    - Invalid inputs

### Phase 5: Validate

11. **Test loop** — repeat until all pass:
    ```
    pytest -v → identify failures → debug → fix → repeat
    ```
    ⚠️ Do NOT proceed while tests are failing.

12. **Final validation** — 100% tests pass, no regression, no `print()`, clean code

13. **Commit and push**
    ```bash
    git add <specific files changed>
    git commit -m "feat(<module>): implement <SF name>"
    git push origin main
    ```
    Commit message examples:
    - `feat(auth): implement G01_F01_SF05 resend verification email`
    - `feat(profile): implement G01_F02_SF02 get profile`
    - `feat(game): implement G02_F04_SF03 submit answer`

14. **Done**

## Code Standards Quick Reference

| Rule | Example |
|------|---------|
| Type hints | `async def create(user_id: int) -> UserProfile:` |
| Async DB | `async def get(db: AsyncSession, ...) -> Model:` |
| Absolute imports | `from app.models.user import User` |
| HTTP errors | `raise HTTPException(status_code=..., detail={"code": "...", "message": "..."})` |
| Response format | `{"success": True, "data": {...}, "error": None}` |
| Status codes | 200 GET/action, 201 created, 400 bad input, 401 unauth, 409 conflict |

## Common Mistakes

- Skipping step 5 (schema validation) → broken migrations found too late
- Business logic in route handler → belongs in service layer
- Using `print()` → use `logging.getLogger(__name__)`
- Relative imports → always absolute (`from app.xxx`)
- Bare `Exception` → always `raise HTTPException(...)`
