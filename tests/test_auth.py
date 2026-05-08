"""
Tests for user registration (SF01) endpoint.
"""

import pytest
from httpx import AsyncClient
from app.main import app


class TestUserRegistration:
    """Test suite for user registration endpoint."""

    @pytest.mark.asyncio
    async def test_register_success(self, async_client: AsyncClient):
        """Test successful user registration."""
        response = await async_client.post(
            "/api/v1/auth/register",
            json={
                "email": "test@example.com",
                "password": "SecurePass123!",
                "confirm_password": "SecurePass123!",
                "full_name": "Test User",
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["success"] is True
        assert data["data"]["user_id"] is not None
        assert data["data"]["email"] == "test@example.com"
        assert data["data"]["full_name"] == "Test User"
        assert data["data"]["message"] == "Account created successfully. Confirmation email sent."

    @pytest.mark.asyncio
    async def test_register_without_full_name(self, async_client: AsyncClient):
        """Test registration without optional full_name."""
        response = await async_client.post(
            "/api/v1/auth/register",
            json={
                "email": "user2@example.com",
                "password": "SecurePass123!",
                "confirm_password": "SecurePass123!",
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["success"] is True
        assert data["data"]["full_name"] is None

    @pytest.mark.asyncio
    async def test_register_invalid_email_format(self, async_client: AsyncClient):
        """Test registration with invalid email format."""
        response = await async_client.post(
            "/api/v1/auth/register",
            json={
                "email": "invalid-email",
                "password": "SecurePass123!",
                "confirm_password": "SecurePass123!",
            },
        )

        assert response.status_code == 400
        data = response.json()
        assert data["success"] is False
        assert data["error"]["code"] == "INVALID_EMAIL_FORMAT"

    @pytest.mark.asyncio
    async def test_register_duplicate_email(self, async_client: AsyncClient):
        """Test registration with duplicate email."""
        # First registration
        await async_client.post(
            "/api/v1/auth/register",
            json={
                "email": "duplicate@example.com",
                "password": "SecurePass123!",
                "confirm_password": "SecurePass123!",
            },
        )

        # Second registration with same email
        response = await async_client.post(
            "/api/v1/auth/register",
            json={
                "email": "duplicate@example.com",
                "password": "SecurePass123!",
                "confirm_password": "SecurePass123!",
            },
        )

        assert response.status_code == 409
        data = response.json()
        assert data["success"] is False
        assert data["error"]["code"] == "EMAIL_ALREADY_EXISTS"

    @pytest.mark.asyncio
    async def test_register_case_insensitive_email_duplicate(
        self, async_client: AsyncClient
    ):
        """Test that email duplicate check is case-insensitive."""
        # First registration
        await async_client.post(
            "/api/v1/auth/register",
            json={
                "email": "CaseSensitive@example.com",
                "password": "SecurePass123!",
                "confirm_password": "SecurePass123!",
            },
        )

        # Second registration with different case
        response = await async_client.post(
            "/api/v1/auth/register",
            json={
                "email": "casesensitive@example.com",
                "password": "SecurePass123!",
                "confirm_password": "SecurePass123!",
            },
        )

        assert response.status_code == 409
        assert response.json()["error"]["code"] == "EMAIL_ALREADY_EXISTS"

    @pytest.mark.asyncio
    async def test_register_weak_password_too_short(
        self, async_client: AsyncClient
    ):
        """Test registration with password too short."""
        response = await async_client.post(
            "/api/v1/auth/register",
            json={
                "email": "user@example.com",
                "password": "Pass1!",  # Only 6 chars
                "confirm_password": "Pass1!",
            },
        )

        assert response.status_code == 422  # Pydantic validation error

    @pytest.mark.asyncio
    async def test_register_weak_password_no_uppercase(
        self, async_client: AsyncClient
    ):
        """Test registration with password missing uppercase."""
        response = await async_client.post(
            "/api/v1/auth/register",
            json={
                "email": "user@example.com",
                "password": "securepass123!",  # No uppercase
                "confirm_password": "securepass123!",
            },
        )

        assert response.status_code == 400
        data = response.json()
        assert data["success"] is False
        assert "uppercase" in data["error"]["message"].lower()

    @pytest.mark.asyncio
    async def test_register_weak_password_no_lowercase(
        self, async_client: AsyncClient
    ):
        """Test registration with password missing lowercase."""
        response = await async_client.post(
            "/api/v1/auth/register",
            json={
                "email": "user@example.com",
                "password": "SECUREPASS123!",  # No lowercase
                "confirm_password": "SECUREPASS123!",
            },
        )

        assert response.status_code == 400
        assert "lowercase" in response.json()["error"]["message"].lower()

    @pytest.mark.asyncio
    async def test_register_weak_password_no_digit(self, async_client: AsyncClient):
        """Test registration with password missing digit."""
        response = await async_client.post(
            "/api/v1/auth/register",
            json={
                "email": "user@example.com",
                "password": "SecurePass!",  # No digit
                "confirm_password": "SecurePass!",
            },
        )

        assert response.status_code == 400
        assert "digit" in response.json()["error"]["message"].lower()

    @pytest.mark.asyncio
    async def test_register_weak_password_no_special_char(
        self, async_client: AsyncClient
    ):
        """Test registration with password missing special character."""
        response = await async_client.post(
            "/api/v1/auth/register",
            json={
                "email": "user@example.com",
                "password": "SecurePass123",  # No special char
                "confirm_password": "SecurePass123",
            },
        )

        assert response.status_code == 400
        assert "special" in response.json()["error"]["message"].lower()

    @pytest.mark.asyncio
    async def test_register_password_mismatch(self, async_client: AsyncClient):
        """Test registration with non-matching passwords."""
        response = await async_client.post(
            "/api/v1/auth/register",
            json={
                "email": "user@example.com",
                "password": "SecurePass123!",
                "confirm_password": "DifferentPass123!",
            },
        )

        assert response.status_code == 400
        data = response.json()
        assert data["success"] is False
        assert "do not match" in data["error"]["message"].lower()

    @pytest.mark.asyncio
    async def test_register_email_max_length(self, async_client: AsyncClient):
        """Test registration with very long email (edge case)."""
        long_email = "a" * 250 + "@example.com"  # > 255 chars
        response = await async_client.post(
            "/api/v1/auth/register",
            json={
                "email": long_email,
                "password": "SecurePass123!",
                "confirm_password": "SecurePass123!",
            },
        )

        assert response.status_code == 422  # Pydantic validation error

    @pytest.mark.asyncio
    async def test_register_full_name_max_length(self, async_client: AsyncClient):
        """Test registration with very long full name."""
        long_name = "a" * 150  # > 100 chars
        response = await async_client.post(
            "/api/v1/auth/register",
            json={
                "email": "user@example.com",
                "password": "SecurePass123!",
                "confirm_password": "SecurePass123!",
                "full_name": long_name,
            },
        )

        # Pydantic should validate max_length
        assert response.status_code == 422  # Validation error

    @pytest.mark.asyncio
    async def test_register_missing_email(self, async_client: AsyncClient):
        """Test registration with missing email."""
        response = await async_client.post(
            "/api/v1/auth/register",
            json={
                "password": "SecurePass123!",
                "confirm_password": "SecurePass123!",
            },
        )

        assert response.status_code == 422  # Validation error

    @pytest.mark.asyncio
    async def test_register_missing_password(self, async_client: AsyncClient):
        """Test registration with missing password."""
        response = await async_client.post(
            "/api/v1/auth/register",
            json={
                "email": "user@example.com",
                "confirm_password": "SecurePass123!",
            },
        )

        assert response.status_code == 422  # Validation error

    @pytest.mark.asyncio
    async def test_register_missing_confirm_password(
        self, async_client: AsyncClient
    ):
        """Test registration with missing confirm_password."""
        response = await async_client.post(
            "/api/v1/auth/register",
            json={
                "email": "user@example.com",
                "password": "SecurePass123!",
            },
        )

        assert response.status_code == 422  # Validation error

    @pytest.mark.asyncio
    async def test_register_response_no_password_in_response(
        self, async_client: AsyncClient
    ):
        """Verify password/password_hash never returned in response."""
        response = await async_client.post(
            "/api/v1/auth/register",
            json={
                "email": "test@example.com",
                "password": "SecurePass123!",
                "confirm_password": "SecurePass123!",
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert "password" not in data["data"]
        assert "password_hash" not in data["data"]
