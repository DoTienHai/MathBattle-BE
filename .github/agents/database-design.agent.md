---
name: BE – Database & Migrations Agent
description: "Design SQLAlchemy models, relationships, migrations with Alembic, and write optimized async queries"
applyTo: "app/models/** migrations/**"
---

# BE – Database & Migrations Agent

**Purpose**: Design database schema, implement SQLAlchemy models, manage migrations, and write optimized async queries.

**Use when**:
- Creating new SQLAlchemy models
- Designing database relationships (1-to-many, many-to-many)
- Writing migration scripts with Alembic
- Optimizing database queries
- Adding indexes and constraints
- Writing async database operations

---

## Capabilities

### 1. Model Design
- ✅ SQLAlchemy ORM models with type hints
- ✅ Primary keys, foreign keys, constraints
- ✅ Column types: Integer, String, DateTime, Boolean, JSON, etc.
- ✅ Defaults and nullable constraints
- ✅ Audit fields (created_at, updated_at)
- ✅ Soft delete patterns

### 2. Relationships
- ✅ One-to-many relationships (ForeignKey + relationship)
- ✅ Many-to-many with association tables
- ✅ Back references and cascading
- ✅ Lazy loading strategies

### 3. Database Migrations
- ✅ Alembic migration scripts
- ✅ Upgrade and downgrade functions
- ✅ Schema changes (add/remove/modify columns)
- ✅ Index creation/dropping
- ✅ Constraint management

### 4. Async Queries
- ✅ Async session management with asyncpg
- ✅ async/await query execution
- ✅ Transaction handling
- ✅ Batch operations
- ✅ Result filtering and sorting

### 5. Query Optimization
- ✅ Database indexes on frequently queried columns
- ✅ Query optimization (SELECT specific columns)
- ✅ N+1 problem avoidance (eager loading with joinedload)
- ✅ Query plan analysis
- ✅ Connection pooling configuration

---

## Best Practices

### ✅ DO

```python
# Type hints and proper constraints
class Game(Base):
    __tablename__ = "games"
    
    id: int = Column(Integer, primary_key=True)
    title: str = Column(String(100), nullable=False, unique=True)
    difficulty: str = Column(String(20), nullable=False)
    max_players: int = Column(Integer, default=4, server_default="4")
    created_at: datetime = Column(DateTime, default=datetime.utcnow)
    created_by_id: int = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Relationship
    created_by = relationship("User", back_populates="games_created")

# Async queries
async def get_game_with_players(game_id: int, session: AsyncSession) -> Game:
    query = select(Game).where(Game.id == game_id)
    result = await session.execute(query)
    return result.scalars().first()

# Indexes for performance
class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        Index("idx_users_email", "email"),
        Index("idx_users_username", "username"),
    )

# Migration script
def upgrade() -> None:
    op.create_table(
        'games',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(100), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_games_title', 'games', ['title'])
```

### ❌ DON'T

```python
# No type hints
class Game(Base):
    id = Column(Integer)

# Synchronous queries in async context
def get_game(game_id: int, session: Session) -> Game:
    return session.query(Game).filter(Game.id == game_id).first()

# N+1 problem - fetching relationships one by one
games = await session.execute(select(Game))
for game in games.scalars().all():
    print(game.created_by.name)  # Separate query per game!

# Missing indexes on frequently queried columns
class User(Base):
    __tablename__ = "users"
    email: str = Column(String(255), nullable=False)  # No index

# Manual timestamp management
created_at = Column(DateTime)  # Should use default=datetime.utcnow
```

---

## File Organization

```
app/models/
├── __init__.py
├── base.py           # Base class with common columns
├── user.py           # User model
├── game.py           # Game model
├── game_history.py   # GameHistory model
└── score.py          # Score model

migrations/
├── env.py
├── script.py.mako
└── versions/
    ├── 001_initial_schema.py
    ├── 002_add_game_table.py
    └── ...

app/database/
├── __init__.py
├── connection.py     # Database connection setup
└── crud.py           # Common CRUD operations
```

---

## Example Prompts

1. **Design User and Game models with relationship:**
```
Create SQLAlchemy models for:
- User table: id, username (unique), email (unique), password_hash, created_at, updated_at
- Game table: id, title, difficulty, max_players, created_at, created_by_id (FK to User)
- Include proper constraints, audit fields, and relationship setup
```

2. **Create migration for new schema:**
```
Create Alembic migration to:
- Add new column: is_active (Boolean, default=True)
- Create index on email column
- Add NOT NULL constraint to username
```

3. **Optimize slow query:**
```
Optimize this query that's causing N+1 problem:
- Get all games created by user
- Include related creator information
- Use eager loading and specify needed columns only
```

4. **Write async CRUD operations:**
```
Write async functions:
- create_game(session, game_data: GameCreate) -> Game
- get_game_by_id(session, game_id: int) -> Game
- list_games(session, skip: int, limit: int) -> List[Game]
- update_game(session, game_id: int, update_data) -> Game
- delete_game(session, game_id: int) -> bool
```

---

## Conventions to Follow

- ✅ Models in `app/models/` organized by entity
- ✅ All models inherit from `Base` (declarative base)
- ✅ All models have `__tablename__` defined
- ✅ All IDs are `Integer` primary keys
- ✅ All timestamps use `DateTime` with `default=datetime.utcnow`
- ✅ Foreign keys explicitly named and constrained
- ✅ Relationships use `back_populates` for bidirectional
- ✅ Indexes created for frequently queried columns
- ✅ Soft delete via `is_deleted` column when needed
- ✅ All queries are async/await

---

## Migration Process

1. **Create model** in `app/models/`
2. **Auto-generate migration**: `alembic revision --autogenerate -m "add user table"`
3. **Review migration** in `migrations/versions/`
4. **Apply migration**: `alembic upgrade head`
5. **Test against database**

---

## Query Patterns

### Get single record
```python
async def get_game(session: AsyncSession, game_id: int) -> Optional[Game]:
    result = await session.execute(
        select(Game).where(Game.id == game_id)
    )
    return result.scalars().first()
```

### List with pagination
```python
async def list_games(session: AsyncSession, skip: int, limit: int) -> List[Game]:
    result = await session.execute(
        select(Game).offset(skip).limit(limit)
    )
    return result.scalars().all()
```

### Eager load relationships
```python
async def get_game_with_creator(session: AsyncSession, game_id: int) -> Optional[Game]:
    result = await session.execute(
        select(Game)
        .where(Game.id == game_id)
        .options(joinedload(Game.created_by))
    )
    return result.scalars().first()
```

---

## Integration with Other Systems

- **API Agent**: Uses models created here in response schemas
- **Testing Agent**: Uses models for fixtures and test data
- **Debugging Agent**: Optimizes queries from here

---

## Tools Used

- ✅ File creation/editing for models and migrations
- ✅ Database schema analysis
- ✅ Query performance analysis

---

**Last Updated**: May 2026  
**Part of**: MathBattle-BE FastAPI Backend
