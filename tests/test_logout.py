"""
Tests for logout (G01_F01_SF07) endpoint.

Endpoint: POST /api/v1/auth/logout
Requires: Authorization: Bearer <access_token>
Optional body: { "refresh_token": "..." }
"""

import pytest
import pytest_asyncio
from datetime import datetime, timedelta
from sqlalchemy import select
from httpx import AsyncClient

from app.models.user import Token, LoginSession
from app.utils.security import TokenGenerator


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture
async def auth_headers(async_client: AsyncClient, verified_user):
    """
    Fixture: Log in with verified_user and return Authorization headers.

    Returns:
        dict with Authorization header using access token
    """
    response = await async_client.post(
        "/api/v1/auth/login",
        json={
            "email": verified_user.email,
            "password": verified_user.plain_password,
            "remember_me": False,
        },
    )
    assert response.status_code == 200, f"Login failed: {response.json()}"
    access_token = response.json()["data"]["access_token"]
    return {"Authorization": f"Bearer {access_token}"}


@pytest_asyncio.fixture
async def auth_headers_with_refresh(async_client: AsyncClient, verified_user):
    """
    Fixture: Log in with remember_me=True, return headers + refresh_token.

    Returns:
        tuple of (headers dict, refresh_token string)
    """
    response = await async_client.post(
        "/api/v1/auth/login",
        json={
            "email": verified_user.email,
            "password": verified_user.plain_password,
            "remember_me": True,
        },
    )
    assert response.status_code == 200, f"Login failed: {response.json()}"
    data = response.json()["data"]
    access_token = data["access_token"]
    refresh_token = data["refresh_token"]
    headers = {"Authorization": f"Bearer {access_token}"}
    return headers, refresh_token


# ---------------------------------------------------------------------------
# 1. Success Scenarios
# ---------------------------------------------------------------------------

class TestLogoutSuccess:
    """Happy-path logout scenarios."""

    @pytest.mark.asyncio
    async def test_logout_without_refresh_token(
        self, async_client: AsyncClient, auth_headers: dict
    ):
        """Logout without providing refresh_token → 200 OK."""
        response = await async_client.post(
            "/api/v1/auth/logout",
            json={},
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["message"] == "Logged out successfully"
        assert data["error"] is None

    @pytest.mark.asyncio
    async def test_logout_with_valid_refresh_token(
        self, async_client: AsyncClient, auth_headers_with_refresh
    ):
        """Logout with valid refresh_token → 200 OK."""
        headers, refresh_token = auth_headers_with_refresh

        response = await async_client.post(
            "/api/v1/auth/logout",
            json={"refresh_token": refresh_token},
            headers=headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["message"] == "Logged out successfully"

    @pytest.mark.asyncio
    async def test_logout_with_invalid_refresh_token_still_succeeds(
        self, async_client: AsyncClient, auth_headers: dict
    ):
        """Logout with garbage refresh_token → 200 (silently ignored)."""
        response = await async_client.post(
            "/api/v1/auth/logout",
            json={"refresh_token": "not-a-real-token"},
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    @pytest.mark.asyncio
    async def test_logout_with_null_refresh_token(
        self, async_client: AsyncClient, auth_headers: dict
    ):
        """Logout with explicit null refresh_token → 200."""
        response = await async_client.post(
            "/api/v1/auth/logout",
            json={"refresh_token": None},
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True


# ---------------------------------------------------------------------------
# 2. Authentication Errors
# ---------------------------------------------------------------------------

class TestLogoutAuthentication:
    """Tests for missing / invalid access tokens."""

    @pytest.mark.asyncio
    async def test_logout_without_auth_header(self, async_client: AsyncClient):
        """No Authorization header → 401."""
        response = await async_client.post(
            "/api/v1/auth/logout",
            json={},
        )

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_logout_with_invalid_token(self, async_client: AsyncClient):
        """Garbage Bearer token → 401."""
        response = await async_client.post(
            "/api/v1/auth/logout",
            json={},
            headers={"Authorization": "Bearer this.is.garbage"},
        )

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_logout_with_expired_access_token(self, async_client: AsyncClient, verified_user):
        """Expired access token (TTL=-1s) → 401."""
        expired_token = TokenGenerator.create_access_token(
            user_id=verified_user.id,
            email=verified_user.email,
            expires_delta=timedelta(seconds=-1),
        )

        response = await async_client.post(
            "/api/v1/auth/logout",
            json={},
            headers={"Authorization": f"Bearer {expired_token}"},
        )

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_logout_using_refresh_token_as_bearer(
        self, async_client: AsyncClient, verified_user
    ):
        """Using a refresh-type token in Bearer header → 401 (wrong type)."""
        refresh_token = TokenGenerator.create_refresh_token(
            user_id=verified_user.id,
            email=verified_user.email,
        )

        response = await async_client.post(
            "/api/v1/auth/logout",
            json={},
            headers={"Authorization": f"Bearer {refresh_token}"},
        )

        assert response.status_code == 401


# ---------------------------------------------------------------------------
# 3. Database State Verification
# ---------------------------------------------------------------------------

class TestLogoutDatabaseState:
    """Verify that DB state changes correctly after logout."""

    @pytest.mark.asyncio
    async def test_refresh_token_revoked_in_db(
        self, async_client: AsyncClient, auth_headers_with_refresh, test_db
    ):
        """After logout, the refresh token record must have is_revoked=True."""
        headers, refresh_token = auth_headers_with_refresh

        response = await async_client.post(
            "/api/v1/auth/logout",
            json={"refresh_token": refresh_token},
            headers=headers,
        )
        assert response.status_code == 200

        async with test_db() as session:
            result = await session.execute(
                select(Token).where(Token.refresh_token == refresh_token)
            )
            token_record = result.scalars().first()

        assert token_record is not None, "Token record should still exist in DB"
        assert token_record.is_revoked is True, "Token should be revoked"

    @pytest.mark.asyncio
    async def test_login_session_deleted_after_logout(
        self, async_client: AsyncClient, auth_headers, verified_user, test_db
    ):
        """After logout, the login session for this user should be deleted."""
        response = await async_client.post(
            "/api/v1/auth/logout",
            json={},
            headers=auth_headers,
        )
        assert response.status_code == 200

        async with test_db() as session:
            result = await session.execute(
                select(LoginSession).where(LoginSession.user_id == verified_user.id)
            )
            sessions = result.scalars().all()

        # Should have 0 sessions after logout (1 was created on login, 1 deleted on logout)
        assert len(sessions) == 0, "Login session should be deleted after logout"

    @pytest.mark.asyncio
    async def test_already_revoked_refresh_token_still_returns_200(
        self, async_client: AsyncClient, auth_headers_with_refresh, test_db
    ):
        """Sending already-revoked refresh token → 200 (silent ignore)."""
        headers, refresh_token = auth_headers_with_refresh

        # First logout
        first = await async_client.post(
            "/api/v1/auth/logout",
            json={"refresh_token": refresh_token},
            headers=headers,
        )
        assert first.status_code == 200

        # Re-login to get fresh access token for second logout attempt
        from app.models.user import User
        async with test_db() as session:
            result = await session.execute(
                select(User).where(User.email == "verified@example.com")
            )
            user = result.scalars().first()
            fresh_access_token = TokenGenerator.create_access_token(
                user_id=user.id,
                email=user.email,
            )

        # Second logout with same (now revoked) refresh_token → still 200
        second = await async_client.post(
            "/api/v1/auth/logout",
            json={"refresh_token": refresh_token},
            headers={"Authorization": f"Bearer {fresh_access_token}"},
        )
        assert second.status_code == 200
        assert second.json()["success"] is True


# ---------------------------------------------------------------------------
# 4. Response Schema Validation
# ---------------------------------------------------------------------------

class TestLogoutResponseSchema:
    """Verify response JSON structure matches expected schema."""

    @pytest.mark.asyncio
    async def test_success_response_schema(
        self, async_client: AsyncClient, auth_headers: dict
    ):
        """Success response must have success, data, error fields."""
        response = await async_client.post(
            "/api/v1/auth/logout",
            json={},
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()

        assert "success" in data
        assert "data" in data
        assert "error" in data
        assert data["success"] is True
        assert isinstance(data["data"], dict)
        assert "message" in data["data"]
        assert data["error"] is None

    @pytest.mark.asyncio
    async def test_error_response_schema(self, async_client: AsyncClient):
        """401 error response must have proper error structure."""
        response = await async_client.post(
            "/api/v1/auth/logout",
            json={},
        )

        assert response.status_code == 401
