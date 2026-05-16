# G01_F02_SF04 — Update Profile Info Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add `PATCH /api/v1/profile` so authenticated users can update their `username` and/or `full_name`.

**Architecture:** `UpdateProfileRequest` Pydantic schema validates the request body (both fields optional, whitespace rules); `ProfileService.update_profile()` handles uniqueness check and writes to two tables (`user_profiles` and `users`) in one transaction; the PATCH route unpacks the service result and raises `HTTPException` on failure.

**Tech Stack:** FastAPI, SQLAlchemy 2.0 async, Pydantic v2, pytest + httpx (in-memory SQLite test DB)

**Spec:** `docs/01_Design/BE/sub_functions/G01_F02_SF04.md`

---

## File Map

| Action | File | What changes |
|--------|------|-------------|
| Modify | `app/schemas/profile.py` | Add `UpdateProfileRequest` |
| Modify | `app/services/profile_service.py` | Add `update_profile()` static method |
| Modify | `app/api/v1/profile.py` | Add `PATCH ""` route, import `UpdateProfileRequest` |
| Modify | `tests/test_profile.py` | Add `TestUpdateProfile` class (10 tests) |

No migration needed — `username` and `full_name` columns already exist.

---

## Task 1: Add `UpdateProfileRequest` Pydantic Schema

**Files:**
- Modify: `app/schemas/profile.py`

- [ ] **Step 1.1: Add the schema to `app/schemas/profile.py`**

Add these imports and class at the end of the file:

```python
# top of file — extend existing imports
from pydantic import BaseModel, Field, field_validator
```

```python
class UpdateProfileRequest(BaseModel):
    """Request body for PATCH /profile (SF04)."""

    username: Optional[str] = Field(default=None, min_length=3, max_length=30)
    full_name: Optional[str] = Field(default=None, min_length=1, max_length=100)

    @field_validator("username")
    @classmethod
    def username_no_whitespace(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and any(c.isspace() for c in v):
            raise ValueError("Username must not contain whitespace characters")
        return v

    @field_validator("full_name", mode="before")
    @classmethod
    def full_name_strip(cls, v: Optional[str]) -> Optional[str]:
        if isinstance(v, str):
            return v.strip()
        return v
```

> `mode="before"` on `full_name` ensures stripping happens before the `min_length=1` constraint is evaluated, so `"   "` (all spaces) correctly fails with 422.

- [ ] **Step 1.2: Verify the app still imports cleanly**

```bash
cd d:\01_CODING\MathBattle\MathBattle-BE
.\venv\Scripts\python.exe -c "from app.schemas.profile import UpdateProfileRequest; print('OK')"
```

Expected output: `OK`

- [ ] **Step 1.3: Commit**

```bash
git add app/schemas/profile.py
git commit -m "feat(profile): add UpdateProfileRequest schema for SF04"
```

---

## Task 2: Write Failing Tests

**Files:**
- Modify: `tests/test_profile.py`

- [ ] **Step 2.1: Append `TestUpdateProfile` class to `tests/test_profile.py`**

```python
# ---------------------------------------------------------------------------
# SF04 — Update Profile
# ---------------------------------------------------------------------------

UPDATE_URL = "/api/v1/profile"


class TestUpdateProfile:

    async def test_update_username_success(self, async_client: AsyncClient):
        token = await register_and_login(
            async_client,
            {
                "email": "upd_username@example.com",
                "password": "SecurePass123!",
                "confirm_password": "SecurePass123!",
            },
        )
        resp = await async_client.patch(
            UPDATE_URL,
            json={"username": "brand_new_name"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert data["data"]["username"] == "brand_new_name"

    async def test_update_full_name_success(self, async_client: AsyncClient):
        token = await register_and_login(
            async_client,
            {
                "email": "upd_fname@example.com",
                "password": "SecurePass123!",
                "confirm_password": "SecurePass123!",
                "full_name": "Old Name",
            },
        )
        resp = await async_client.patch(
            UPDATE_URL,
            json={"full_name": "New Name"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        assert resp.json()["data"]["full_name"] == "New Name"

    async def test_update_both_fields_success(self, async_client: AsyncClient):
        token = await register_and_login(
            async_client,
            {
                "email": "upd_both@example.com",
                "password": "SecurePass123!",
                "confirm_password": "SecurePass123!",
                "full_name": "Original",
            },
        )
        resp = await async_client.patch(
            UPDATE_URL,
            json={"username": "both_updated", "full_name": "Updated Name"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["username"] == "both_updated"
        assert data["full_name"] == "Updated Name"

    async def test_update_no_fields(self, async_client: AsyncClient):
        token = await register_and_login(
            async_client,
            {
                "email": "upd_nofields@example.com",
                "password": "SecurePass123!",
                "confirm_password": "SecurePass123!",
            },
        )
        resp = await async_client.patch(
            UPDATE_URL,
            json={},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 400
        assert resp.json()["detail"]["code"] == "NO_FIELDS_TO_UPDATE"

    async def test_update_username_taken(self, async_client: AsyncClient):
        # User A claims a unique username
        token_a = await register_and_login(
            async_client,
            {
                "email": "taken_a@example.com",
                "password": "SecurePass123!",
                "confirm_password": "SecurePass123!",
            },
        )
        await async_client.patch(
            UPDATE_URL,
            json={"username": "claimed_username"},
            headers={"Authorization": f"Bearer {token_a}"},
        )
        # User B tries to claim the same username
        token_b = await register_and_login(
            async_client,
            {
                "email": "taken_b@example.com",
                "password": "SecurePass123!",
                "confirm_password": "SecurePass123!",
            },
        )
        resp = await async_client.patch(
            UPDATE_URL,
            json={"username": "claimed_username"},
            headers={"Authorization": f"Bearer {token_b}"},
        )
        assert resp.status_code == 409
        assert resp.json()["detail"]["code"] == "USERNAME_TAKEN"

    async def test_update_username_same_as_self(self, async_client: AsyncClient):
        token = await register_and_login(
            async_client,
            {
                "email": "same_self@example.com",
                "password": "SecurePass123!",
                "confirm_password": "SecurePass123!",
            },
        )
        current = (
            await async_client.get(
                PROFILE_URL,
                headers={"Authorization": f"Bearer {token}"},
            )
        ).json()["data"]["username"]
        resp = await async_client.patch(
            UPDATE_URL,
            json={"username": current},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200

    async def test_update_username_too_short(self, async_client: AsyncClient):
        token = await register_and_login(
            async_client,
            {
                "email": "short_u@example.com",
                "password": "SecurePass123!",
                "confirm_password": "SecurePass123!",
            },
        )
        resp = await async_client.patch(
            UPDATE_URL,
            json={"username": "ab"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 422

    async def test_update_username_too_long(self, async_client: AsyncClient):
        token = await register_and_login(
            async_client,
            {
                "email": "long_u@example.com",
                "password": "SecurePass123!",
                "confirm_password": "SecurePass123!",
            },
        )
        resp = await async_client.patch(
            UPDATE_URL,
            json={"username": "a" * 31},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 422

    async def test_update_username_with_space(self, async_client: AsyncClient):
        token = await register_and_login(
            async_client,
            {
                "email": "space_u@example.com",
                "password": "SecurePass123!",
                "confirm_password": "SecurePass123!",
            },
        )
        resp = await async_client.patch(
            UPDATE_URL,
            json={"username": "has space"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 422

    async def test_update_unauthenticated(self, async_client: AsyncClient):
        resp = await async_client.patch(UPDATE_URL, json={"username": "test_user"})
        assert resp.status_code == 401
```

- [ ] **Step 2.2: Run the new tests — verify they FAIL (PATCH route doesn't exist yet)**

```bash
.\venv\Scripts\pytest.exe tests/test_profile.py::TestUpdateProfile -v
```

Expected: All 10 tests fail with `405 Method Not Allowed` or `404 Not Found`.

---

## Task 3: Implement `update_profile()` Service Method

**Files:**
- Modify: `app/services/profile_service.py`

- [ ] **Step 3.1: Add `Tuple` to the typing import at the top of `profile_service.py`**

Change:
```python
from typing import Optional
```
To:
```python
from typing import Optional, Tuple
```

- [ ] **Step 3.2: Add the `update_profile` static method to `ProfileService`**

Append inside the `ProfileService` class (after `get_user_badges`):

```python
    @staticmethod
    async def update_profile(
        session: AsyncSession,
        user_id: int,
        username: Optional[str],
        full_name: Optional[str],
    ) -> Tuple[bool, dict]:
        """
        Update editable profile fields for the given user.

        Returns:
            (True, data_dict) on success.
            (False, error_dict) with code/message/status_code on failure.
        """
        if username is None and full_name is None:
            return (
                False,
                {
                    "code": "NO_FIELDS_TO_UPDATE",
                    "message": "At least one of username or full_name must be provided",
                    "status_code": 400,
                },
            )

        # Username uniqueness check (case-insensitive, exclude self)
        if username is not None:
            conflict_result = await session.execute(
                select(UserProfile).where(
                    func.lower(UserProfile.username) == func.lower(username),
                    UserProfile.user_id != user_id,
                )
            )
            if conflict_result.scalars().first():
                return (
                    False,
                    {
                        "code": "USERNAME_TAKEN",
                        "message": "This username is already taken",
                        "status_code": 409,
                    },
                )

        # Fetch records
        profile_result = await session.execute(
            select(UserProfile).where(UserProfile.user_id == user_id)
        )
        profile = profile_result.scalars().first()

        user_result = await session.execute(
            select(User).where(User.id == user_id)
        )
        user = user_result.scalars().first()

        # Apply updates
        if username is not None and profile:
            profile.username = username
        if full_name is not None and user:
            user.full_name = full_name

        await session.commit()

        logger.info(f"update_profile: user {user_id} updated fields username={username!r} full_name={full_name!r}")

        return (
            True,
            {
                "user_id": user_id,
                "username": profile.username if profile else None,
                "full_name": user.full_name if user else None,
            },
        )
```

- [ ] **Step 3.3: Verify the module imports cleanly**

```bash
.\venv\Scripts\python.exe -c "from app.services.profile_service import ProfileService; print('OK')"
```

Expected: `OK`

---

## Task 4: Add the PATCH Route

**Files:**
- Modify: `app/api/v1/profile.py`

- [ ] **Step 4.1: Add `UpdateProfileRequest` to the import in `profile.py`**

Change:
```python
from app.services.profile_service import ProfileService
```
Add (also extend the schemas import at the top):
```python
from app.schemas.profile import UpdateProfileRequest
```

- [ ] **Step 4.2: Add the PATCH route handler in `app/api/v1/profile.py`**

Append after the existing `get_badges` route:

```python
@router.patch("")
async def update_profile(
    body: UpdateProfileRequest,
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    """Update username and/or full_name for the authenticated user (SF04)."""
    success, result = await ProfileService.update_profile(
        db, user_id, body.username, body.full_name
    )
    if not success:
        raise HTTPException(
            status_code=result["status_code"],
            detail={"code": result["code"], "message": result["message"]},
        )
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"success": True, "data": result, "error": None},
    )
```

- [ ] **Step 4.3: Verify the app starts without errors**

```bash
.\venv\Scripts\python.exe -c "from app.main import app; print('OK')"
```

Expected: `OK`

---

## Task 5: Run Tests and Verify

- [ ] **Step 5.1: Run only the SF04 tests**

```bash
.\venv\Scripts\pytest.exe tests/test_profile.py::TestUpdateProfile -v
```

Expected: All 10 tests pass.

- [ ] **Step 5.2: Run the full test suite to check for regressions**

```bash
.\venv\Scripts\pytest.exe -v
```

Expected: All tests pass (including existing SF01, SF02, SF03 tests).

- [ ] **Step 5.3: Commit everything**

```bash
git add app/schemas/profile.py app/services/profile_service.py app/api/v1/profile.py tests/test_profile.py
git commit -m "feat(profile): implement G01_F02_SF04 PATCH /profile for username and full_name update"
```

---

## Self-Review Checklist

- **Spec coverage:**
  - ✅ PATCH /api/v1/profile endpoint — Task 4
  - ✅ username validation (3–30, no whitespace, Unicode) — Task 1 Pydantic schema
  - ✅ full_name validation (1–100, trim) — Task 1 Pydantic schema
  - ✅ At least one field check → 400 NO_FIELDS_TO_UPDATE — Task 3 service
  - ✅ Username uniqueness (case-insensitive, exclude self) → 409 USERNAME_TAKEN — Task 3 service
  - ✅ 401 unauthenticated — covered by existing `get_current_user_id` dep, tested in Task 2
  - ✅ 422 for Pydantic violations (too short, too long, whitespace) — Task 2 tests verify
  - ✅ All 10 planned test cases from spec — Task 2
- **No placeholders:** All steps contain real code.
- **Type consistency:** `update_profile(session, user_id, username, full_name)` signature matches across Task 3 (definition) and Task 4 (call site).
