---
name: MathBattle-BE Coding Rules
description: "Code standards, style guide, and implementation patterns for FastAPI development"
---

# 📝 copilot-instructions.md: Coding Rules

Câu hỏi: **"Viết code như thế nào cho đúng?"** ← File này trả lời.

---

## 1. Type Hints (MANDATORY)

**Rule**: Every function, parameter, and return must have type hints.

```python
# ❌ WRONG
def get_user(user_id):
    return user

# ✅ CORRECT
async def get_user(user_id: int) -> User:
    return await db.get_user(user_id)
```

**When to use types from `typing`:**
```python
from typing import List, Dict, Optional, Union, Callable

def process_games(game_ids: List[int]) -> Dict[int, Game]:
    ...

async def find_user(email: Optional[str] = None) -> Union[User, None]:
    ...
```

---

## 2. Code Style (PEP 8)

### Line Length
- **Maximum**: 100 characters (including comments)
- **Formatter**: Black (use when integrated)

```python
# ❌ WRONG (too long)
result = service.complex_function_name(param1, param2, param3, param4, param5, param6)

# ✅ CORRECT
result = service.complex_function_name(
    param1, param2, param3, param4, param5, param6
)
```

### Naming Conventions
```python
# Constants
MAX_GAME_SCORE = 1000
DIFFICULTY_LEVELS = ["easy", "medium", "hard"]

# Functions/Variables (snake_case)
def calculate_player_score(player_id: int) -> int:
    ...

# Classes (PascalCase)
class GameService:
    ...

# Private (leading underscore)
def _internal_helper() -> None:
    ...
```

### Import Organization
```python
# ① Standard library
from typing import List, Optional
from dataclasses import dataclass
import json

# ② Third-party
from fastapi import APIRouter, HTTPException
from sqlalchemy import Column, Integer, String
import pydantic

# ③ Local imports
from app.models import User, Game
from app.schemas import UserCreate
from app.services import GameService
```

**Rule**: No relative imports. No wildcard imports (`from module import *`).

```python
# ❌ WRONG
from ..models import *
from . import helpers

# ✅ CORRECT
from app.models import User, Game
from app.utils.helpers import calculate_score
```

---

## 3. Async/Await (FastAPI is Async-First)

**Rule**: Use `async def` for all handlers and database operations.

```python
# ❌ WRONG (blocking operation in async context)
@app.get("/games/{game_id}")
async def get_game(game_id: int):
    game = db.query(Game).filter(Game.id == game_id).first()  # Blocks!
    return game

# ✅ CORRECT
@app.get("/games/{game_id}")
async def get_game(game_id: int) -> Game:
    game = await db.get_game(game_id)  # Async query
    return game
```

**Never block with**:
- `time.sleep()` → use `await asyncio.sleep()`
- `requests` library → use `httpx` async
- Synchronous database calls → use async drivers (asyncpg)

---

## 4. API Endpoint Structure

### Router Organization
Place routers in `app/api/v1/` by feature:

```python
# app/api/v1/games.py
from fastapi import APIRouter
from app.schemas import GameCreate, GameResponse
from app.services import GameService

router = APIRouter(prefix="/games", tags=["games"])

@router.get("/{game_id}", response_model=GameResponse)
async def get_game(game_id: int) -> GameResponse:
    ...

@router.post("", response_model=GameResponse, status_code=201)
async def create_game(game_data: GameCreate) -> GameResponse:
    ...
```

### Endpoint Naming & Status Codes
```python
# List all
GET /api/v1/games          → 200 OK

# Get one
GET /api/v1/games/{id}     → 200 OK or 404 Not Found

# Create
POST /api/v1/games         → 201 Created

# Update
PUT /api/v1/games/{id}     → 200 OK or 404 Not Found

# Delete
DELETE /api/v1/games/{id}  → 204 No Content or 404 Not Found
```

---

## 5. Pydantic Schemas (Request/Response)

**Rule**: Define schemas in `app/schemas/` for validation and documentation.

```python
# app/schemas/games.py
from pydantic import BaseModel, Field
from typing import Optional

class GameCreate(BaseModel):
    """Schema for creating a game."""
    title: str = Field(..., min_length=1, max_length=100)
    difficulty: str = Field(..., regex="^(easy|medium|hard)$")
    max_players: Optional[int] = Field(default=4, ge=1, le=100)

    class Config:
        example = {
            "title": "Addition Challenge",
            "difficulty": "easy",
            "max_players": 4
        }

class GameResponse(GameCreate):
    """Schema for game responses."""
    id: int
    created_at: str
```

---

## 6. Database Models (SQLAlchemy)

**Rule**: Place models in `app/models/` with proper type hints.

```python
# app/models/game.py
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base

class Game(Base):
    __tablename__ = "games"

    id: int = Column(Integer, primary_key=True)
    title: str = Column(String(100), nullable=False, unique=True)
    difficulty: str = Column(String(20), nullable=False)
    max_players: int = Column(Integer, default=4)
    created_at: datetime = Column(DateTime, default=datetime.utcnow)
    created_by_id: int = Column(Integer, ForeignKey("users.id"))

    # Relationships
    created_by = relationship("User", back_populates="games_created")
```

---

## 7. Docstrings (Google Style)

**Rule**: All public functions, classes, and modules need docstrings.

```python
async def create_game(game_data: GameCreate) -> GameResponse:
    """
    Create a new math game.
    
    Args:
        game_data: Game creation payload with title, difficulty, and player count.
    
    Returns:
        Created Game object with assigned ID and timestamps.
    
    Raises:
        ValueError: If difficulty level is not in [easy, medium, hard].
        HTTPException: If user is not authenticated (status 401).
    """
    if game_data.difficulty not in ["easy", "medium", "hard"]:
        raise ValueError("Invalid difficulty")
    
    game = await GameService.create(game_data)
    return game
```

**Module docstring**:
```python
"""
Game management endpoints.

This module handles all game-related operations including:
- Creating new games
- Fetching game details
- Updating game settings
- Deleting games (soft delete)
"""
```

---

## 8. Error Handling

**Rule**: Use FastAPI HTTPException with proper status codes and error schemas.

```python
from fastapi import HTTPException, status

# ❌ WRONG
if not game:
    raise Exception("Game not found")

# ✅ CORRECT
if not game:
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Game not found",
    )

# With error code
raise HTTPException(
    status_code=status.HTTP_400_BAD_REQUEST,
    detail="Invalid difficulty level",
    headers={"error_code": "INVALID_DIFFICULTY"}
)
```

---

## 9. Logging

**Rule**: Use Python's `logging` module, no `print()` statements.

```python
import logging

logger = logging.getLogger(__name__)

async def create_game(game_data: GameCreate) -> GameResponse:
    logger.info(f"Creating game: {game_data.title}")
    
    try:
        game = await GameService.create(game_data)
        logger.info(f"Game created successfully: {game.id}")
        return game
    except Exception as e:
        logger.error(f"Failed to create game: {str(e)}", exc_info=True)
        raise
```

---

## 10. Testing

**Rule**: Tests in `tests/` mirror `app/` structure. Use pytest with async support.

```python
# tests/test_api/test_games.py
import pytest
from app.schemas import GameCreate

@pytest.mark.asyncio
async def test_create_game_success(async_client, db_session):
    """Test successful game creation."""
    game_data = GameCreate(title="Math Quiz", difficulty="easy")
    response = await async_client.post("/api/v1/games", json=game_data.dict())
    
    assert response.status_code == 201
    assert response.json()["title"] == "Math Quiz"

@pytest.mark.asyncio
async def test_create_game_invalid_difficulty(async_client):
    """Test game creation with invalid difficulty."""
    game_data = {"title": "Quiz", "difficulty": "impossible"}
    response = await async_client.post("/api/v1/games", json=game_data)
    
    assert response.status_code == 422  # Validation error
```

---

## 11. Configuration & Environment

**Rule**: Load settings via Pydantic Settings, never hardcode secrets.

```python
# app/config.py
from pydantic import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    DATABASE_URL: str
    DEBUG: bool = False
    API_V1_STR: str = "/api/v1"
    SECRET_KEY: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    MAX_GAME_PLAYERS: int = 10
    
    class Config:
        env_file = ".env"
        env_file_encoding = 'utf-8'

settings = Settings()
```

**.env file** (never commit):
```
DATABASE_URL=postgresql+asyncpg://user:pass@localhost/mathbattle
DEBUG=False
SECRET_KEY=your-secret-key-here
```

---

## 12. Common Patterns

### Service Layer (Business Logic)
```python
# app/services/game_service.py
class GameService:
    @staticmethod
    async def create(game_data: GameCreate) -> Game:
        """Create game and save to database."""
        game = Game(**game_data.dict())
        await db.add(game)
        await db.commit()
        return game
    
    @staticmethod
    async def get_by_id(game_id: int) -> Optional[Game]:
        return await db.get(Game, game_id)
```

### Dependency Injection
```python
from fastapi import Depends, HTTPException

async def get_current_user(token: str = Depends(oauth2_scheme)) -> User:
    """Dependency to verify user token."""
    user = await verify_token(token)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid token")
    return user

@app.get("/me")
async def get_profile(user: User = Depends(get_current_user)) -> UserResponse:
    return user
```

---

## Quick Checklist Before Committing

- [ ] Type hints on all functions
- [ ] No imports from `typing` after app imports
- [ ] All endpoints have proper status codes
- [ ] Error handling with HTTPException
- [ ] Docstrings on public functions
- [ ] No `print()` statements (use logging)
- [ ] Tests written and passing
- [ ] No hardcoded secrets
- [ ] < 100 characters per line
- [ ] PEP 8 compliant

---

**Last Updated**: May 2026  
**See also**: `AGENTS.md` for "WHAT the system does"

## Database & ORM

- **ORM**: SQLAlchemy (when applicable)
- **Migrations**: Alembic for schema management
- Models should be in `app/models/` with proper type hints
- Use async drivers (asyncpg for PostgreSQL)

## Dependency Management

- **Tool**: pip with requirements.txt or Poetry (preferred)
- **Virtual Environment**: Use Python venv or Poetry
- Core dependencies:
  - `fastapi`: Web framework
  - `uvicorn`: ASGI server
  - `pydantic`: Data validation
  - `sqlalchemy`: ORM (if needed)
  - `pytest`: Testing
  - `python-dotenv`: Environment variables

## Testing

### Structure
- Tests mirror source structure in `tests/` directory
- Use pytest for unit and integration tests
- Name test files as `test_*.py`

### Best Practices
- Each test function tests one behavior
- Use fixtures from `conftest.py` for common setup
- Mock external dependencies
- Aim for >80% code coverage

Example:
```python
@pytest.mark.asyncio
async def test_get_user_success(client, user_factory):
    user = user_factory()
    response = await client.get(f"/api/v1/users/{user.id}")
    assert response.status_code == 200
```

## Configuration & Environment

- Use `.env` file for environment-specific settings (never commit)
- Load via `python-dotenv` or Pydantic Settings
- Define all environment variables in `.env.example`

Example structure:
```python
# app/config.py
from pydantic import BaseSettings

class Settings(BaseSettings):
    DATABASE_URL: str
    DEBUG: bool = False
    API_V1_STR: str = "/api/v1"
    
    class Config:
        env_file = ".env"

settings = Settings()
```

## Async/Await

- FastAPI is async-first; use async functions by default
- Use `async def` for endpoint handlers and database operations
- Avoid blocking operations; use async libraries (httpx, asyncpg, etc.)

## Documentation

### Code Documentation
- Docstrings for all public functions, classes, and modules
- Use Google-style docstrings

Example:
```python
async def create_game(game_data: GameCreate) -> Game:
    """
    Create a new math game.
    
    Args:
        game_data: Game creation payload with difficulty and category.
    
    Returns:
        Created Game object with generated ID.
    
    Raises:
        ValueError: If difficulty level is invalid.
    """
```

### API Documentation
- FastAPI auto-generates OpenAPI docs at `/docs` (Swagger UI)
- Use endpoint descriptions and proper status code responses
- Document request/response examples in schemas

## Logging

- Use Python's built-in `logging` module
- Set up structured logging for production
- Log levels: DEBUG, INFO, WARNING, ERROR, CRITICAL

## Performance Considerations

- Use connection pooling for databases
- Cache frequently accessed data
- Implement pagination for list endpoints
- Use indexes on frequently queried database columns

## Git Workflow

- Use meaningful commit messages
- Keep commits atomic (one feature per commit)
- Branch naming: `feature/feature-name`, `bugfix/bug-name`, `docs/doc-name`
- Create pull requests for code review before merging to main

## Common Commands

```bash
# Setup
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Run development server
uvicorn app.main:app --reload

# Run tests
pytest -v
pytest --cov=app          # With coverage

# Format code
black app/ tests/

# Lint
flake8 app/ tests/
```

## Quick Tips for Copilot

When asking for help with MathBattle-BE:
- Mention the feature or endpoint you're working on
- Specify if it involves database operations, async logic, or API responses
- Reference the project structure when describing file locations
- Ask for type hints and docstring examples when generating new code
- Request test cases alongside implementation code

---

**Last Updated**: May 2026  
**Status**: Planning Phase
