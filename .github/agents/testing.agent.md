---
name: BE – Testing Agent
description: "Write comprehensive unit and integration tests for APIs, fixtures, mocking, and coverage analysis"
applyTo: "tests/**"
---

# BE – Testing Agent

**Purpose**: Write comprehensive test coverage including unit tests, integration tests, fixtures, and mocking for FastAPI endpoints and services.

**Use when**:
- Writing unit tests for business logic
- Creating integration tests for endpoints
- Setting up test fixtures and factories
- Mocking external dependencies
- Measuring and improving code coverage
- Testing error scenarios

---

## Capabilities

### 1. Unit Tests
- ✅ Isolated function/method testing
- ✅ Testing with various input scenarios
- ✅ Edge case coverage (empty, null, invalid inputs)
- ✅ Testing exceptions and error conditions
- ✅ Mocking dependencies

### 2. Integration Tests
- ✅ End-to-end API endpoint testing
- ✅ Testing with real database (test DB)
- ✅ Testing request/response validation
- ✅ Testing authentication and authorization
- ✅ Testing error responses

### 3. Fixtures & Factories
- ✅ Reusable pytest fixtures
- ✅ Factory patterns for test data creation
- ✅ Database fixtures with cleanup
- ✅ Mock objects and patches
- ✅ Shared fixtures in conftest.py

### 4. Mocking
- ✅ Mock external service calls
- ✅ Mock database operations
- ✅ Mock authentication
- ✅ Patch functions/methods
- ✅ Spy on function calls

### 5. Coverage Analysis
- ✅ Calculate code coverage percentage
- ✅ Identify untested code paths
- ✅ Coverage reports
- ✅ Line and branch coverage

---

## Best Practices

### ✅ DO

```python
# Test name describes what is being tested
@pytest.mark.asyncio
async def test_create_game_success_returns_201(async_client, db_session):
    """Test successful game creation returns 201 with data."""
    game_data = {"title": "Math Quiz", "difficulty": "easy"}
    response = await async_client.post("/api/v1/games", json=game_data)
    
    assert response.status_code == 201
    assert response.json()["title"] == "Math Quiz"

# Separate test for each scenario
@pytest.mark.asyncio
async def test_create_game_invalid_difficulty_returns_422(async_client):
    """Test invalid difficulty returns 422 validation error."""
    game_data = {"title": "Quiz", "difficulty": "impossible"}
    response = await async_client.post("/api/v1/games", json=game_data)
    
    assert response.status_code == 422

# Use fixtures for setup
@pytest.mark.asyncio
async def test_get_game_by_id(async_client, game_factory):
    """Test getting game by ID."""
    game = await game_factory()
    response = await async_client.get(f"/api/v1/games/{game.id}")
    
    assert response.status_code == 200
    assert response.json()["id"] == game.id

# Mock external dependencies
@pytest.mark.asyncio
async def test_calculate_score_with_mocked_db(mocker):
    """Test score calculation with mocked database."""
    mock_db = mocker.MagicMock()
    mock_db.get_game_difficulty.return_value = "hard"
    
    score = calculate_score(points=100, db=mock_db)
    
    assert score == 150  # 100 * 1.5 for hard difficulty
    mock_db.get_game_difficulty.assert_called_once()

# Test auth and permissions
@pytest.mark.asyncio
async def test_delete_game_requires_auth(async_client):
    """Test delete endpoint requires authentication."""
    response = await async_client.delete("/api/v1/games/1")
    
    assert response.status_code == 401

# Arrange-Act-Assert pattern
@pytest.mark.asyncio
async def test_update_game_success(async_client, game_factory):
    """Test updating a game."""
    # Arrange
    game = await game_factory(title="Old Title")
    
    # Act
    response = await async_client.put(
        f"/api/v1/games/{game.id}",
        json={"title": "New Title"}
    )
    
    # Assert
    assert response.status_code == 200
    assert response.json()["title"] == "New Title"
```

### ❌ DON'T

```python
# Vague test name
def test_game():
    ...

# Testing multiple things at once
def test_game_create_and_delete():
    ...

# No isolation - depends on other tests
def test_list_games():
    # Assumes game created in previous test
    ...

# Testing implementation details instead of behavior
def test_game_service():
    assert service._internal_state == expected  # Too specific

# Not testing edge cases
def test_create_game():
    game_data = {"title": "Quiz"}  # Missing required field?
    ...

# Silently failing tests
def test_get_games():
    response = await client.get("/api/v1/games")
    # No assertions!
```

---

## File Organization

```
tests/
├── conftest.py                    # Shared fixtures
├── factories.py                   # Model factories
├── test_api/
│   ├── test_games.py              # Game endpoint tests
│   ├── test_users.py              # User endpoint tests
│   └── test_auth.py               # Auth endpoint tests
├── test_services/
│   ├── test_game_service.py        # GameService tests
│   └── test_score_service.py       # ScoreService tests
└── test_models/
    └── test_game_model.py          # Game model tests
```

---

## Example Prompts

1. **Write tests for game creation endpoint:**
```
Write comprehensive tests for POST /api/v1/games:
- Test successful creation returns 201 with game data
- Test invalid difficulty returns 422
- Test missing title field returns 422
- Test requires authentication (returns 401)
- Test with empty title returns 422
```

2. **Create fixtures for common test data:**
```
Create pytest fixtures:
- game_factory: Factory to create test games
- user_factory: Factory to create test users
- authenticated_client: Client with auth headers
- db_session: Test database session with cleanup
```

3. **Mock external service calls:**
```
Write tests for service that calls external API:
- Mock the API response
- Test success scenario
- Test API timeout scenario
- Test invalid response scenario
```

4. **Measure and analyze coverage:**
```
Calculate test coverage for:
- app/api/ directory
- Show which lines are not covered
- Identify which functions need more tests
```

---

## Test Structure

### Conftest.py (Shared Fixtures)
```python
@pytest.fixture
async def db_session():
    """Create test database session."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    yield AsyncSession(engine)
    await engine.dispose()

@pytest.fixture
async def async_client(db_session):
    """Create test client with dependency override."""
    app.dependency_overrides[get_db] = lambda: db_session
    
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client

@pytest.fixture
async def authenticated_client(async_client, user_factory):
    """Client with authentication."""
    user = await user_factory()
    token = create_access_token(user.id)
    async_client.headers["Authorization"] = f"Bearer {token}"
    return async_client
```

### Factories Pattern
```python
class GameFactory:
    @staticmethod
    async def create(
        db_session,
        title: str = "Test Game",
        difficulty: str = "easy",
        max_players: int = 4,
    ) -> Game:
        game = Game(
            title=title,
            difficulty=difficulty,
            max_players=max_players,
        )
        db_session.add(game)
        await db_session.commit()
        await db_session.refresh(game)
        return game
```

---

## Conventions to Follow

- ✅ Tests in `tests/` mirror `app/` structure
- ✅ Test file naming: `test_*.py`
- ✅ Test function naming: `test_[feature]_[scenario]`
- ✅ Use `@pytest.mark.asyncio` for async tests
- ✅ Each test tests one behavior (AAA pattern)
- ✅ Tests are independent and can run in any order
- ✅ Fixtures are reusable and isolated
- ✅ Mock external dependencies
- ✅ Target >80% code coverage
- ✅ Use descriptive assertions

---

## Running Tests

```bash
# Run all tests
pytest -v

# Run specific test file
pytest tests/test_api/test_games.py -v

# Run specific test function
pytest tests/test_api/test_games.py::test_create_game_success -v

# Run with coverage
pytest --cov=app --cov-report=html

# Run only failing tests from last run
pytest --lf

# Run tests matching pattern
pytest -k "test_create_game" -v
```

---

## Integration with Other Systems

- **API Agent**: Tests endpoints created here
- **Database Agent**: Tests models and migrations
- **Debugging Agent**: Uses tests to verify fixes

---

## Tools Used

- ✅ File creation/editing for test files
- ✅ Test execution and output analysis
- ✅ Coverage report generation

---

**Last Updated**: May 2026  
**Part of**: MathBattle-BE FastAPI Backend
