---
name: mathbattle-db-migration
description: Use when adding new tables, columns, or modifying database schema in MathBattle-BE
---

# MathBattle Database Migration Workflow

## Overview

Steps 3–5 of the feature dev workflow. Complete ALL steps before writing schemas or services.

## Step 1: Create/Update SQLAlchemy Model

File: `app/models/`

```python
from app.models.base import BaseModel  # provides id, created_at, updated_at
from sqlalchemy import Column, Integer, String, ForeignKey, Boolean
from sqlalchemy.orm import relationship

class MyModel(BaseModel):
    __tablename__ = "my_table"

    user_id: int = Column(Integer, ForeignKey("users.id"), nullable=False)
    name: str = Column(String(100), nullable=False)
    is_active: bool = Column(Boolean, default=True)

    user = relationship("User", back_populates="my_models")
```

Always inherit from `BaseModel` — gives `id`, `created_at`, `updated_at` for free.

## Step 2: Generate and Apply Migration

```bash
alembic revision --autogenerate -m "add my_table"
```

**Before running `upgrade head`, review the generated file for:**
- Missing `nullable` constraints
- Missing indexes on FK columns
- Unintended column drops (Alembic sometimes misdetects renames as drop+add)

```bash
alembic upgrade head
```

## Step 3: Validate Schema (MANDATORY)

Insert sample data and query it back manually before writing any application code.

```bash
# psql or any DB client
psql $DATABASE_URL

INSERT INTO my_table (user_id, name) VALUES (1, 'test');
SELECT * FROM my_table WHERE user_id = 1;

-- Test FK constraint (should fail)
INSERT INTO my_table (user_id, name) VALUES (99999, 'bad');

-- Check timestamps auto-set
SELECT id, created_at, updated_at FROM my_table;
```

✅ Only proceed to Pydantic schemas after validation passes.

## Rollback

```bash
alembic downgrade -1   # undo last migration
```

## Common Mistakes

| Mistake | Fix |
|---------|-----|
| Not inheriting `BaseModel` | Loses `id`, `created_at`, `updated_at` |
| Skipping step 3 | Schema bugs surface much later, harder to debug |
| No index on FK columns | Slow queries at scale — add `index=True` to FK Column |
| Trusting autogenerate blindly | Always review migration file before `upgrade head` |

## Commit and Push

After schema is validated (step 3 passes):

```bash
git add app/models/<model>.py alembic/versions/<migration>.py
git commit -m "feat(models): add <table/column description>"
git push origin main
```

Commit message examples:
- `feat(models): add game_sessions table`
- `feat(models): add streak_count column to user_profiles`
