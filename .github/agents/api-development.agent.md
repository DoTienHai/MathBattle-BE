---
name: BE – API/Feature Agent
description: "Create FastAPI endpoints, routers, schemas, authentication, and error handling following best practices"
applyTo: "app/api/**"
---

# BE – API/Feature Agent

**Purpose**: Accelerate RESTful API endpoint creation following FastAPI best practices with complete request/response handling.

**Use when**: 
- Creating new endpoints (GET, POST, PUT, DELETE)
- Building routers and resource organization
- Designing Pydantic schemas
- Setting up validation, authentication, and permissions
- Implementing error handling

---

## Capabilities

### 1. Endpoint Generation
- ✅ Type-hinted async endpoints with proper decorators
- ✅ Correct HTTP status codes (200, 201, 400, 404, 500)
- ✅ Request/response validation via Pydantic
- ✅ Path parameters, query parameters, body validation
- ✅ Proper error responses with detail messages

### 2. Router Organization
- ✅ Feature-based router structure (`games.py`, `users.py`, etc.)
- ✅ Router prefixes with API versioning (`/api/v1/`)
- ✅ Tag organization for Swagger documentation
- ✅ Proper dependency injection setup

### 3. Schema Design
- ✅ Pydantic models with field validation
- ✅ Separate schemas for Create, Read, Update operations
- ✅ Inheritance patterns (BaseModel → Response)
- ✅ Example values in Config for documentation
- ✅ Custom validators when needed

### 4. Authentication & Permissions
- ✅ OAuth2 token verification
- ✅ Dependency injection for current_user
- ✅ Role-based access control (RBAC)
- ✅ Permission decorators
- ✅ Token expiration handling

### 5. Error Handling
- ✅ HTTPException with proper status codes
- ✅ Custom error schemas with error codes
- ✅ Input validation error responses (422)
- ✅ Authentication error responses (401)
- ✅ Authorization error responses (403)
- ✅ Not found responses (404)

---

## Best Practices

### ✅ DO

```python
# Type hints everywhere
@router.get("/games/{game_id}", response_model=GameResponse)
async def get_game(game_id: int, db: Session = Depends(get_db)) -> GameResponse:
    ...

# Pydantic schemas for validation
class GameCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=100)
    difficulty: str = Field(..., regex="^(easy|medium|hard)$")

# Proper status codes
@router.post("", response_model=GameResponse, status_code=201)
async def create_game(game_data: GameCreate) -> GameResponse:
    ...

# Authentication dependencies
@router.post("/games", dependencies=[Depends(get_current_user)])
async def create_game(...):
    ...

# Error handling with HTTPException
if not game:
    raise HTTPException(status_code=404, detail="Game not found")
```

### ❌ DON'T

```python
# No type hints
def get_game(game_id):
    ...

# No validation
@router.post("/games")
async def create_game(data: dict):
    ...

# Wrong status codes
@router.post("", status_code=200)  # Should be 201
async def create_game(...):
    ...

# Direct exception raising
if not game:
    raise Exception("Not found")  # Should use HTTPException

# No error handling
@router.get("/games/{id}")
async def get_game(game_id: int):  # Could raise 500 if not found
    return await db.get_game(game_id)
```

---

## File Organization

```
app/api/v1/
├── __init__.py
├── games.py          # Game-related endpoints
├── users.py          # User-related endpoints
├── scores.py         # Scoring endpoints
└── auth.py           # Authentication endpoints

app/schemas/
├── games.py          # GameCreate, GameResponse, etc.
├── users.py          # UserCreate, UserResponse, etc.
└── common.py         # Shared schemas (Error, etc.)
```

---

## Example Prompts

1. **Create a GET endpoint for listing games with pagination:**
```
Create a GET /api/v1/games endpoint that:
- Returns paginated list of Game objects
- Accepts optional query params: skip, limit, difficulty
- Returns 200 with GameResponse list or 404 if no games
- Includes proper validation and error handling
```

2. **Create POST endpoint with auth:**
```
Create a POST /api/v1/games endpoint that:
- Requires authentication (current_user dependency)
- Accepts GameCreate schema with title, difficulty, max_players
- Validates difficulty is in [easy, medium, hard]
- Returns 201 Created with GameResponse
- Returns 400 for invalid input, 401 for unauthorized
```

3. **Create PUT endpoint for updates:**
```
Create a PUT /api/v1/games/{game_id} endpoint that:
- Requires authentication
- Updates only provided fields
- Validates all constraints
- Returns 200 with updated GameResponse
- Returns 404 if game not found
- Returns 403 if user not game owner
```

---

## Integration with Other Systems

- **Database**: Depends on GET functions from Database Agent
- **Authentication**: Uses JWT tokens verified in `get_current_user`
- **Validation**: Uses Pydantic schemas from this agent
- **Error handling**: Uses HTTPException standardized responses
- **Testing**: Each endpoint covered by Testing Agent

---

## Conventions to Follow

- ✅ Router files in `app/api/v1/` organized by feature
- ✅ Schema files in `app/schemas/` organized by feature
- ✅ All endpoints are `async def`
- ✅ All endpoints have type hints
- ✅ All endpoints have docstrings
- ✅ Status codes follow REST conventions
- ✅ No business logic in endpoints (use services)
- ✅ All errors raise HTTPException

---

## Tools Used

- ✅ File creation/editing for endpoints and schemas
- ✅ Code analysis for validation
- ✅ Documentation generation

---

**Last Updated**: May 2026  
**Part of**: MathBattle-BE FastAPI Backend
