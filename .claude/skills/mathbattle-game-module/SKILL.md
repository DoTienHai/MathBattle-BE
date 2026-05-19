---
name: mathbattle-game-module
description: Use when implementing a new game mode or extending game functionality in MathBattle-BE
---

# MathBattle Game Module Patterns

## Overview

Patterns for adding game modes. Reference existing Quick Calculate implementation before creating anything new.

## Architecture

```
Request
  → app/api/v1/games/{game}.py        (thin router)
  → app/services/{game}_service.py    (all business logic)
  → app/models/game_session.py        (session state)
  → app/models/session_operation.py   (per-operation records)
  → app/utils/question_generator.py   (question creation)
  → app/utils/difficulty_ramp.py      (difficulty progression)
```

## Session Lifecycle

```
start_session() → [submit_answer() × N] → end_session()
```

Each operation creates a `SessionOperation` record. Final score computed on `end_session`.

## Service Layer Pattern

```python
# app/services/{game}_service.py
class MyGameService:
    async def start_session(
        self, db: AsyncSession, user_id: int
    ) -> GameSession:
        """Create and return a new active game session."""
        ...

    async def submit_answer(
        self, db: AsyncSession, session_id: int, user_id: int, answer: int
    ) -> AnswerResult:
        """Validate answer, update score, return correct answer + feedback."""
        ...

    async def end_session(
        self, db: AsyncSession, session_id: int, user_id: int
    ) -> GameResult:
        """Finalize session, compute final score, mark completed."""
        ...
```

## Question Generator

Before writing a new generator, check `app/utils/question_generator.py` — extend it rather than duplicating.

```python
from app.models.question import Question

def generate_question(difficulty: int, operation: str) -> Question:
    """Generate a question for the given difficulty and operation type."""
    ...
```

## Difficulty Ramp

Use `app/utils/difficulty_ramp.py` for progressive difficulty. Do not hardcode difficulty logic in services.

## New Game Mode Checklist

- [ ] Read spec in `docs/01_Design/BE/sub_functions/`
- [ ] Check if existing models cover needs (extend before creating new)
- [ ] Migration + validation (use `mathbattle-db-migration` skill)
- [ ] Schemas in `app/schemas/game.py` or a new `app/schemas/{game}.py`
- [ ] Service in `app/services/{game}_service.py`
- [ ] Router in `app/api/v1/games/{game}.py`
- [ ] Register router in `app/main.py`
- [ ] Tests in `tests/test_{game}.py` (start, submit, end, edge cases)

## Common Mistakes

- Putting score logic in the router → belongs in service
- Hardcoding operation types → use enums or constants
- Not recording `SessionOperation` rows → breaks per-question analytics
- New question generator instead of extending existing one → check first

## Commit and Push

After all tests pass:

```bash
git add app/ tests/ alembic/versions/
git commit -m "feat(game): implement <game mode name>"
git push origin main
```

Commit message examples:
- `feat(game): implement speed_drill game mode`
- `feat(game): add time_attack session management`
