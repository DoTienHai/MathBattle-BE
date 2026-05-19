# Sudoku Game Module Design
**Date:** 2026-05-20  
**Feature:** G02_F05 — Sudoku  
**Scope:** SF01–SF11 (excluding SF09 hint)

---

## Overview

Backend API for a Sudoku game mode within MathBattle-BE. Players start a session, receive a puzzle based on their level, fill in cells client-side, and submit for validation. Scoring is time- and error-based.

---

## Sub-functions In Scope

| SF | Name | Description |
|----|------|-------------|
| SF01 | Initialize Sudoku Session | Create GameSession + generate puzzle |
| SF02 | Resolve Sudoku Config From Player Level | Map player_level → board config |
| SF03 | Generate Full Sudoku Grid | Backtracking grid generation |
| SF04 | Generate Sudoku Puzzle By Level | Hide cells from full grid |
| SF05 | Validate Unique Solution | Backtracking solver to verify uniqueness |
| SF06 | Capture Single Number Input | Validate 1-digit input for a cell |
| SF07 | Replace Or Clear Cell Value | Overwrite or clear non-fixed cells |
| SF08 | Validate Player Move | Validate submitted grid, return violations |
| SF10 | Check Puzzle Completion | Check all cells filled and correct |
| SF11 | End Session & Compute Score | Compute score, close session |

**Excluded:** SF09 (Hint) — deferred to future milestone.

---

## API Design

### Endpoints

```
POST /api/v1/games/sudoku/start
POST /api/v1/games/sudoku/sessions/{session_id}/submit
```

### Start (SF01–SF05)

**Request:** `POST /api/v1/games/sudoku/start`  
Headers: `Authorization: Bearer <token>`

**Response (201):**
```json
{
  "success": true,
  "data": {
    "session_id": "uuid",
    "board_size": 9,
    "puzzle_grid": [[5,3,0,0,7,0,0,0,0], ...],
    "fixed_positions": [{"row": 0, "col": 0}, ...]
  },
  "error": null
}
```

### Submit (SF06–SF08, SF10–SF11)

**Request:** `POST /api/v1/games/sudoku/sessions/{session_id}/submit`

```json
{
  "current_grid": [[5,3,4,6,7,8,9,1,2], ...]
}
```

**Response — violations found (200):**
```json
{
  "success": true,
  "data": {
    "is_complete": false,
    "violated_cells": [{"row": 2, "col": 4}],
    "error_count": 1
  },
  "error": null
}
```

**Response — puzzle complete (200):**
```json
{
  "success": true,
  "data": {
    "is_complete": true,
    "violated_cells": [],
    "score": 571,
    "score_breakdown": {
      "base_score": 690,
      "time_penalty": 19,
      "error_penalty": 100,
      "final_score": 571
    },
    "duration_seconds": 384
  },
  "error": null
}
```

---

## Database Design

### Changes to existing tables

**`game_sessions`** — add enum value:
```python
class GameMode(str, Enum):
    QUICK_CALCULATE = "quick_calculate"
    SUDOKU = "sudoku"
```

**`session_operations`** — 3 changes:
```python
operation_type          = Column(String(50), nullable=True)   # NEW column
question_correct_answer = Column(JSON, nullable=True)         # BIGINT → JSON
user_answer             = Column(JSON, nullable=True)         # INT → JSON
```

### Operation type usage

| operation_type | question_content | is_correct |
|----------------|-----------------|-----------|
| `sudoku_start` | puzzle_grid, solution_grid, fixed_positions, board_size, hidden_count, score_multiplier, error_limit | null |
| `sudoku_submit` | current_grid, violated_cells | False if violations, True if valid |
| `sudoku_end` | duration_seconds, error_count, score_breakdown | True |

**Quick Calculate backward compatibility:** existing rows have `operation_type = NULL`. BIGINT/INT values auto-cast to JSON numbers via migration.

---

## Algorithm Design

### Grid Generation (SF03)

Backtracking with random number ordering:
1. For each cell in order, shuffle [1..N]
2. Try each number — check row/col/block validity
3. Place if valid, recurse; else backtrack

**Block shapes:**
| Board | Block |
|-------|-------|
| 4×4 | 2×2 |
| 6×6 | 2×3 |
| 9×9 | 3×3 |

### Puzzle Generation (SF04+SF05)

1. Shuffle all N² positions
2. For each position: remove cell, run solver
   - Solutions == 1 → keep removed
   - Solutions != 1 → restore, skip
3. Stop at hidden_count

Solver counts up to 2 solutions (early exit) for performance.

### Validation (SF08)

For each filled cell in submitted grid:
1. Check row uniqueness
2. Check column uniqueness
3. Check block uniqueness
4. Compare with solution_grid[row][col]

Any failure → append `{row, col}` to violated_cells.

Also validates:
- Fixed cells not modified
- Each value is 0–N (0 = empty)

### Score Formula (SF11)

```python
POINTS_PER_HIDDEN_CELL = 10
TIME_PENALTY_RATE      = 0.05   # points per second
ERROR_PENALTY_POINTS   = 50     # points per wrong submission

base_score    = hidden_count * POINTS_PER_HIDDEN_CELL * score_multiplier
time_penalty  = duration_seconds * TIME_PENALTY_RATE
error_penalty = error_count * ERROR_PENALTY_POINTS
final_score   = max(0, int(base_score - time_penalty - error_penalty))
```

Error count = number of submit calls where violated_cells is non-empty.

---

## File Structure

```
app/
├── models/
│   ├── game_session.py          (add SUDOKU to GameMode)
│   └── session_operation.py     (add operation_type, change column types)
├── schemas/
│   └── sudoku.py                (NEW)
├── services/
│   └── sudoku_service.py        (NEW)
├── utils/
│   └── sudoku_generator.py      (NEW)
└── api/v1/games/
    └── sudoku.py                (NEW)

tests/
└── test_sudoku.py               (NEW)

alembic/versions/
└── xxxx_sudoku_session_ops.py   (NEW)
```

---

## Security Considerations

| Risk | Mitigation |
|------|-----------|
| Client tampers fixed cells | Server validates fixed_positions on every submit |
| Client sends invalid values | Server validates all values are 0–N |
| Client sends wrong grid size | Server validates dimensions match board_size |
| Replay submit after completion | Server checks session status = active before processing |
