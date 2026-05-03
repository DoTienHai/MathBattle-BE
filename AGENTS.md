---
name: MathBattle-BE Project Architecture
description: "System design, architecture, and project workflow documentation"
---

# 🧠 AGENTS.md: Project Brain

Câu hỏi: **"Hệ thống này hoạt động như thế nào?"** ← File này trả lời.

---

## System Architecture

### Overview
**MathBattle-BE** là một FastAPI backend cho nền tảng học toán. Hệ thống được thiết kế:
- **Async-first** (FastAPI + asyncio)
- **Modular** (feature-based organization)
- **Type-safe** (Python type hints everywhere)
- **Testable** (pytest + fixtures)

### Technology Stack
```
┌─────────────────────────────┐
│   FastAPI (Web Framework)   │
├─────────────────────────────┤
│   Pydantic (Validation)     │
├─────────────────────────────┤
│   SQLAlchemy + Alembic      │
│   (Database + Migrations)   │
├─────────────────────────────┤
│   PostgreSQL (async driver) │
├─────────────────────────────┤
│   pytest + asyncio          │
│   (Testing)                 │
└─────────────────────────────┘
```

---

## Project Structure & Why

```
MathBattle-BE/
│
├── app/                    ← Application logic
│   ├── api/v1/            ← Endpoints by feature
│   │   ├── games.py       (game management)
│   │   ├── users.py       (user management)
│   │   └── scores.py      (scoring system)
│   │
│   ├── models/            ← Database models (SQLAlchemy)
│   ├── schemas/           ← Request/Response schemas (Pydantic)
│   ├── services/          ← Business logic layer
│   ├── database/          ← DB connection + config
│   └── utils/             ← Helper functions
│
├── tests/                 ← Test suite (mirrors app/)
│   ├── test_api/
│   ├── test_services/
│   └── conftest.py
│
├── migrations/            ← Alembic database migrations
├── docs/                  ← Documentation
│   ├── 00_Research/       (background research)
│   ├── 01_Design/         (feature specs)
│   └── 98_Tools/          (utilities)
│
└── copilot-instructions.md ← "Coding rules" (HOW file)
```

**Tại sao cấu trúc này?**
- `api/v1/` → Dễ maintain khi có v2, v3 sau
- `services/` → Tách business logic khỏi endpoint
- `models/` + `schemas/` → Tách database và API
- Mirrors in tests/ → Dễ tìm test file tương ứng

---

## Data Flow

```
User Request
    ↓
├─→ FastAPI Router (/api/v1/games)
    ├─→ Pydantic Schema Validation
    ├─→ Service Layer (business logic)
    ├─→ SQLAlchemy Query
    ├─→ Database (PostgreSQL)
    └─→ Response → Pydantic Model
    ↓
Return JSON
```

---

## Development Workflow (Feature-based)

```
1. Design Phase (docs/01_Design/)
   ↓
2. Create Database Schema
   └─→ New SQLAlchemy model in app/models/
   └─→ Create Alembic migration
   ↓
3. Build API Endpoint
   └─→ Create router in app/api/v1/
   └─→ Create Pydantic schemas
   ↓
4. Write Business Logic
   └─→ Create service in app/services/
   ↓
5. Test Coverage
   └─→ Add tests in tests/
   ↓
6. Deploy / Merge
```

---

## Key Design Decisions

| Decision | Why | Trade-off |
|----------|-----|-----------|
| **Async-first** | Better performance, real-time support | More complex code |
| **Type hints mandatory** | IDE support, early error detection | Verbose code |
| **Feature-based routing** | Easy to understand + scale | More files to manage |
| **Service layer** | Separate business logic from API | Extra indirection |
| **Pydantic schemas** | Validation + documentation | Duplicate definitions |

---

## Deployment Considerations

- **Environment variables** via `.env` file
- **Async driver** (asyncpg) for database
- **Connection pooling** configured
- **CORS** enabled for frontend integration
- **Logging** structured for production

---

## When to Use Each Tool/Agent

| Task | Use | Because |
|------|-----|---------|
| Create endpoint | `/API Development` | Needs type hints + proper status codes |
| Design database | `/Database Design` | Needs schema + migrations |
| Write tests | `/Testing` | Needs fixtures + async support |
| Add docstrings | `/Documentation` | Needs OpenAPI compatibility |
| Fix slow query | `/Debugging` | Needs profiling + optimization |

---

**Last Updated**: May 2026  
**Status**: Planning Phase → Development Ready  
**See also**: `copilot-instructions.md` for "HOW to code"

