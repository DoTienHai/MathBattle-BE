# CLAUDE.md — MathBattle-BE

## Project Overview

**MathBattle-BE** is a FastAPI backend for an interactive math learning game platform. Players register, log in, and compete in math challenges. The project is in early development — only the auth module (Register, Login, Logout) is implemented.

**See also:**
- `AGENTS.md` — architecture and data flow ("what the system does")
- `.github/copilot-instructions.md` — full coding rules ("how to write code")
- `docs/01_Design/BE/sub_functions/` — per-feature specs (inputs, outputs, business logic, flows)

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Web Framework | FastAPI 0.104 (async-first) |
| Database | PostgreSQL via asyncpg |
| ORM | SQLAlchemy 2.0 (async) |
| Migrations | Alembic |
| Validation | Pydantic v2 |
| Auth | JWT (python-jose) + bcrypt |
| Email | SendGrid |
| Rate Limiting | slowapi |
| Testing | pytest + pytest-asyncio + httpx |
| Formatter | Black (max 100 chars/line) |
| Linter | flake8 + isort |

---

## Project Structure

```
app/
├── api/v1/           # Route handlers — thin, delegate to services
├── models/           # SQLAlchemy ORM models (database schema)
├── schemas/          # Pydantic schemas (request/response validation)
├── services/         # Business logic (all DB queries live here)
├── utils/            # Helpers: security.py (JWT, bcrypt, email)
├── database/         # Async engine + session factory
├── config.py         # Pydantic Settings (loads from .env)
└── main.py           # App entry point, router registration, CORS

tests/
├── conftest.py       # Fixtures: async_client, test_db, user variants
├── test_auth.py      # Registration tests
├── test_login.py     # Login tests
└── test_logout.py    # Logout tests

docs/01_Design/BE/sub_functions/   # Feature specs (read before implementing)
```

---

## Development Workflow

Always follow this order for each feature:

# Backend Feature Development Flow

Always follow this order for each feature:

1. **Read the spec**  
   - Path: `docs/01_Design/BE/sub_functions/`  
   - Understand business logic, inputs/outputs, edge cases.

2. **Design database schema (quick draft)**  
   - Identify required tables, relationships, and fields.  
   - Think about scalability and future extensions.

3. **Create / update SQLAlchemy models**  
   - Path: `app/models/`  

4. **Write Alembic migration**  
   - Generate migration  
   - Run migration to apply changes

5. **Quick database validation (MANDATORY)**  
   - Insert sample data  
   - Query data manually  
   - Ensure schema works as expected before moving on

6. **Define Pydantic schemas**  
   - Path: `app/schemas/`  
   - Include request/response validation

7. **Implement service layer**  
   - Path: `app/services/`  
   - Handle business logic only (no API logic)

8. **Create route handler**  
   - Path: `app/api/v1/`  
   - Connect request → service → response

9. **Register router (if new module)**  
   - File: `app/main.py`

10. **Write tests (REQUIRED)**  
   - Path: `tests/`  
   - Mirror feature name  
   - Include:
     - Happy path
     - Edge cases
     - Invalid inputs

11. **Continuous Testing & Bug Fix Loop (CRITICAL)**  

   Repeat until all tests pass:

   - Run tests (`pytest`)
   - Identify failures
   - Debug root cause
   - Fix code (model / schema / service / API)
   - Re-run tests

   ⚠️ Do NOT move forward while tests are failing

12. **Final validation**  
   - All tests pass 100%  
   - No regression  
   - Clean and readable code  
   - Remove debug logs if any

13. **Done**

---

## Documentation Standards

All design documents live in `docs/01_Design/BE/sub_functions/`. Each file documents one sub-function.

### Template

Follow `docs/01_Design/BE/sub_functions/G01_F01_SF01.md` as the canonical template. Required sections in order:

```
frontmatter (id, name, group, feature, mvp_scope)
## 📝 Change History
# Title: ID: Name
status block (MVP scope, Function, Status, Priority, Difficulty)
## 📋 Description
## 🎯 Detailed Requirements  (Input Parameters + Validation Rules + Output Schemas)
## 🗏️ Business Logic (N Steps)
## 🔄 Flow Diagram  (Mermaid flowchart)
## 💻 Backend Implementation  (Status + Location + Tests + Architecture table + Implementation Highlights + Future Enhancements)
## 📊 Security Considerations
## ✅ Test Coverage
## 🚀 API Endpoint
## 📋 Implementation Checklist
## 🔗 Related Documentation
Last Updated / Implementation Status / Test Status footer
```

### Language

All documentation must be written in **English**. Variable names, code snippets, error codes, and API field names use English. Inline Vietnamese comments are not allowed in doc files.

### Change History

Every file must have a Change History table as the **first section after frontmatter**, before any heading. Format:

```markdown
## 📝 Change History
| Date | Version | Changes | Status |
|------|---------|---------|--------|
| YYYY-MM-DD | X.Y.Z | What changed and why (specific, not vague) | ✅ Complete / 📝 Draft / 🔄 In Progress |
```

Rules:
- **Date**: `YYYY-MM-DD` format only
- **Version**: Semantic versioning — `1.0.0` for initial, `1.1.0` for minor update, `2.0.0` for major redesign
- **Changes**: Describe what changed, not just "updated" — e.g., `"Added timeout handling flow"`, `"Changed score formula to include streak bonus"`
- **Status**: Use `✅ Complete`, `📝 Draft`, `🔄 In Progress`, or `❌ Deprecated`
- Add a new row for every meaningful change; never overwrite history

### Implementation Highlights

In the `## 💻 Backend Implementation` section, list implementation points using status icons:

```markdown
✅ **Feature name**: description  ← already implemented
⬜ **Feature name**: description  ← planned, not yet done
```

### Related Documentation

The last named section must be `## 🔗 Related Documentation`. It should point to **actual or planned code file paths**, not just spec IDs:

```markdown
## 🔗 Related Documentation
- **Database Models**: `app/models/game.py`
- **Test Suite**: `tests/test_quick_calculate.py`
- **API Router**: `app/api/v1/game.py`
- **Service Logic**: `app/services/quick_calculate_service.py`
- **Related Specs**: G02_F04_SF02, G02_F04_SF07
```

---

## Code Standards (enforced)

### Mandatory rules

- **Type hints on every function parameter and return value** — no exceptions
- **`async def` for all route handlers and DB operations** — never block the event loop
- **No relative imports** — always use absolute: `from app.models import User`
- **No wildcard imports** (`from x import *`)
- **No `print()`** — use `logging.getLogger(__name__)`
- **No hardcoded secrets** — all config via `app/config.py` → `.env`
- **Line length ≤ 100 characters** (Black formatter)
- **Google-style docstrings** on all public functions, classes, and modules

### Import order (isort)
```python
# 1. Standard library
# 2. Third-party (fastapi, sqlalchemy, pydantic...)
# 3. Local (app.*)
```

### Naming conventions
- `snake_case` — functions, variables, module names
- `PascalCase` — classes
- `UPPER_SNAKE_CASE` — constants
- `_leading_underscore` — private/internal helpers

### HTTP status codes
| Action | Code |
|--------|------|
| GET (found) / POST action success | 200 |
| POST (created resource) | 201 |
| Bad input / validation fail | 400 |
| Unauthenticated | 401 |
| Forbidden (authenticated but not allowed) | 403 |
| Not found | 404 |
| Conflict (duplicate resource) | 409 |
| Unprocessable Entity (Pydantic error) | 422 |
| Account locked | 423 |
| Rate limited | 429 |
| Server error | 500 |

### Standardized response format
```python
{
  "success": True,
  "data": {...},
  "error": None
}
# or on error:
{
  "success": False,
  "data": None,
  "error": {"code": "ERROR_CODE", "message": "Human-readable message"}
}
```

### Error handling
```python
# Always raise HTTPException, never bare Exception
raise HTTPException(
    status_code=status.HTTP_404_NOT_FOUND,
    detail={"code": "USER_NOT_FOUND", "message": "User not found"},
)
```

---

## Database Models

All models inherit from `BaseModel` in `app/models/base.py`, which provides `id`, `created_at`, `updated_at`.

Current tables:
- `users` — email, password_hash, is_verified, is_active, account_locked_until
- `user_profiles` — username, current_level, total_points (1:1 with users)
- `user_settings` — theme, language, notifications (1:1 with users)
- `tokens` — refresh tokens with revocation support
- `login_sessions` — audit trail (IP address, user agent)

**Important:** User email is stored lowercase. Always normalize email to lowercase before DB operations.

---

## Authentication

**Strategy:** Stateless JWT (HS256)

- **Access token**: 7 days, carries `user_id` + `email` + `type`
- **Refresh token**: 7 days, stored in `tokens` table when `remember_me=True`
- **Email verification token**: 24 hours, stateless (not stored in DB)
- **Current user dependency**: `app/api/deps.py` → `get_current_user_id()`

**Note:** Email verification is currently disabled in the login flow (marked `TEMP` in `app/api/v1/auth.py`). Do not remove the check, just keep it disabled until the email feature is implemented.

---

## Testing

- **Test DB**: In-memory SQLite (`sqlite+aiosqlite:///:memory:`) — auto-created per session
- **Never mock the database** — tests use a real (in-memory) DB
- **Async mode**: `pytest.ini` sets `asyncio_mode = auto` — no `@pytest.mark.asyncio` needed
- **Fixtures** (from `tests/conftest.py`): `async_client`, `test_db`, `verified_user`, `unverified_user`, `inactive_user`, `locked_user`, `expired_locked_user`

```python
# Pattern for all tests
async def test_something(async_client, verified_user):
    response = await async_client.post("/api/v1/auth/login", json={...})
    assert response.status_code == 200
    assert response.json()["success"] is True
```

---

## Common Commands

```bash
# Dev server (reload on change)
uvicorn app.main:app --reload

# Run tests
pytest -v
pytest --cov=app --cov-report=term-missing

# Format and lint
black app/ tests/
isort app/ tests/
flake8 app/ tests/

# Alembic migrations
alembic revision --autogenerate -m "description"
alembic upgrade head
```

---

## Environment Variables

Copy `.env.example` to `.env`. Required variables:

| Variable | Description |
|----------|-------------|
| `DATABASE_URL` | `postgresql+asyncpg://user:pass@host/db` |
| `SECRET_KEY` | JWT signing secret (keep secure) |
| `SENDGRID_API_KEY` | SendGrid for verification emails |
| `ENVIRONMENT` | `development` / `production` |
| `DEBUG` | `True` / `False` |

---

## Pre-commit Checklist

- [ ] Type hints on all functions
- [ ] `async def` for all handlers and DB calls
- [ ] HTTPException (not bare Exception) for all errors
- [ ] Google-style docstrings on public functions
- [ ] No `print()` — use logger
- [ ] Tests written and passing (`pytest -v`)
- [ ] No hardcoded secrets
- [ ] Lines ≤ 100 chars
