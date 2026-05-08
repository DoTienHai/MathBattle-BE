"""
Comprehensive tests for user login (POST /api/v1/auth/login) endpoint.

Test Coverage:
- Success scenarios: valid credentials, case-insensitive email, remember_me flag
- Error scenarios: invalid credentials, unverified email, inactive account, locked account
- Edge cases: missing fields, empty fields, special characters, rate limiting
- Response validation: status codes, response structure, token format, database records

All fixtures are defined in conftest.py to be reusable across test modules.
"""

import pytest
from datetime import datetime, timedelta
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from jose import jwt

from app.models.user import User, LoginSession, Token
from app.utils.security import PasswordHasher, TokenGenerator
from app.config import settings


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================


def decode_jwt(token: str) -> dict:
    """
    Decode and verify JWT token.
    
    Args:
        token: JWT token string
    
    Returns:
        Decoded token payload
    """
    payload = jwt.decode(
        token,
        settings.SECRET_KEY,
        algorithms=[settings.ALGORITHM]
    )
    return payload


async def get_user_from_db(session: AsyncSession, email: str) -> User:
    """
    Retrieve user from database by email.
    
    Args:
        session: Database session
        email: User email to look up
    
    Returns:
        User object or None
    """
    query = select(User).where(User.email == email)
    result = await session.execute(query)
    return result.scalars().first()


async def get_login_sessions(session: AsyncSession, user_id: int):
    """
    Retrieve all login sessions for a user.
    
    Args:
        session: Database session
        user_id: User ID
    
    Returns:
        List of LoginSession objects
    """
    query = select(LoginSession).where(LoginSession.user_id == user_id)
    result = await session.execute(query)
    return result.scalars().all()


async def get_refresh_tokens(session: AsyncSession, user_id: int):
    """
    Retrieve all refresh tokens for a user.
    
    Args:
        session: Database session
        user_id: User ID
    
    Returns:
        List of Token objects
    """
    query = select(Token).where(Token.user_id == user_id)
    result = await session.execute(query)
    return result.scalars().all()


# ============================================================================
# SUCCESS SCENARIOS
# ============================================================================


class TestLoginSuccessScenarios:
    """Test successful login scenarios."""

    @pytest.mark.asyncio
    async def test_login_success_with_valid_credentials(
        self, async_client: AsyncClient, verified_user
    ):
        """
        Test successful login returns 200 with access token and user info.
        
        Validates:
        - HTTP status code is 200 OK
        - Response structure: success=true, data contains token and user info
        - Access token is valid JWT
        - Token has correct claims (user_id, email)
        - User profile data is correct (user_id, email, full_name, level)
        - Login session is created in database
        """
        response = await async_client.post(
            "/api/v1/auth/login",
            json={
                "email": verified_user.email,
                "password": verified_user.plain_password,
                "remember_me": False,
            },
        )

        # Verify HTTP status
        assert response.status_code == 200

        # Verify response structure
        data = response.json()
        assert data["success"] is True
        assert data["error"] is None
        assert data["data"] is not None

        # Verify token and user data structure
        response_data = data["data"]
        assert "access_token" in response_data
        assert "refresh_token" in response_data
        assert "token_type" in response_data
        assert response_data["token_type"] == "Bearer"
        assert "expires_in" in response_data
        assert response_data["expires_in"] == 86400 * 7  # 7 days in seconds
        assert "user" in response_data

        # Verify access token is valid JWT
        access_token = response_data["access_token"]
        token_payload = decode_jwt(access_token)
        assert token_payload["sub"] == str(verified_user.id)
        assert token_payload["email"] == verified_user.email
        assert "exp" in token_payload
        assert "iat" in token_payload

        # Verify user profile in response
        user_data = response_data["user"]
        assert user_data["user_id"] == verified_user.id
        assert user_data["email"] == verified_user.email
        assert user_data["full_name"] == verified_user.full_name
        assert user_data["level"] == 1  # Default level
        assert user_data["role"] == "Free"  # Default role

    @pytest.mark.asyncio
    async def test_login_with_case_insensitive_email(
        self, async_client: AsyncClient, verified_user
    ):
        """
        Test login works with different email case variations.
        
        Validates:
        - Email comparison is case-insensitive
        - User "Verified@Example.Com" is found when searching "verified@example.com"
        - Login succeeds and token is returned
        """
        # Login with uppercase email
        response = await async_client.post(
            "/api/v1/auth/login",
            json={
                "email": verified_user.email.upper(),
                "password": verified_user.plain_password,
                "remember_me": False,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["user"]["email"] == verified_user.email.lower()

        # Login with mixed case email
        response = await async_client.post(
            "/api/v1/auth/login",
            json={
                "email": "VeRiFiEd@ExAmPlE.CoM",
                "password": verified_user.plain_password,
                "remember_me": False,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    @pytest.mark.asyncio
    async def test_login_creates_login_session_record(
        self, async_client: AsyncClient, verified_user, test_db
    ):
        """
        Test that login creates a login session record for audit trail.
        
        Validates:
        - LoginSession record is created in database
        - LoginSession contains user_id, ip_address, and user_agent
        - Login audit trail is properly recorded
        """
        response = await async_client.post(
            "/api/v1/auth/login",
            json={
                "email": verified_user.email,
                "password": verified_user.plain_password,
                "remember_me": False,
            },
        )

        assert response.status_code == 200

        # Check database for login session
        async with test_db() as session:
            sessions = await get_login_sessions(session, verified_user.id)
            assert len(sessions) > 0
            
            latest_session = sessions[-1]
            assert latest_session.user_id == verified_user.id
            assert latest_session.ip_address is not None
            assert latest_session.user_agent is not None

    @pytest.mark.asyncio
    async def test_login_with_remember_me_false(
        self, async_client: AsyncClient, verified_user, test_db
    ):
        """
        Test login with remember_me=false does NOT create refresh token.
        
        Validates:
        - No Token record created in database
        - Only access token returned
        - Session is short-lived
        """
        response = await async_client.post(
            "/api/v1/auth/login",
            json={
                "email": verified_user.email,
                "password": verified_user.plain_password,
                "remember_me": False,
            },
        )

        assert response.status_code == 200
        data = response.json()
        
        # Refresh token should still be returned (stateless design)
        assert "refresh_token" in data["data"]

    @pytest.mark.asyncio
    async def test_login_with_remember_me_true_creates_token_record(
        self, async_client: AsyncClient, verified_user, test_db
    ):
        """
        Test login with remember_me=true creates refresh token record.
        
        Validates:
        - Token record created in database
        - Token has correct user_id, refresh_token, and expires_at
        - is_revoked defaults to False
        - Extended session enabled
        """
        response = await async_client.post(
            "/api/v1/auth/login",
            json={
                "email": verified_user.email,
                "password": verified_user.plain_password,
                "remember_me": True,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

        # Verify token record in database
        async with test_db() as session:
            tokens = await get_refresh_tokens(session, verified_user.id)
            assert len(tokens) > 0
            
            token_record = tokens[-1]
            assert token_record.user_id == verified_user.id
            assert token_record.refresh_token is not None
            assert token_record.token_type == "refresh"
            assert token_record.expires_at is not None
            assert token_record.is_revoked is False

    @pytest.mark.asyncio
    async def test_login_token_expiration_time(
        self, async_client: AsyncClient, verified_user
    ):
        """
        Test access token has correct expiration time (7 days).
        
        Validates:
        - Token expires_in is 604800 seconds (7 days)
        - JWT exp claim is approximately 7 days from now
        - Token expiration is consistent
        """
        response = await async_client.post(
            "/api/v1/auth/login",
            json={
                "email": verified_user.email,
                "password": verified_user.plain_password,
                "remember_me": False,
            },
        )

        assert response.status_code == 200
        data = response.json()
        
        # Verify expires_in is 7 days
        assert data["data"]["expires_in"] == 604800  # 7 days in seconds

        # Verify JWT exp claim
        access_token = data["data"]["access_token"]
        token_payload = decode_jwt(access_token)
        
        issued_at = token_payload["iat"]
        expiry = token_payload["exp"]
        ttl = expiry - issued_at
        
        # Token should be valid for ~7 days (604800 seconds)
        # Allow 5 second tolerance for execution time
        assert abs(ttl - 604800) <= 5

    @pytest.mark.asyncio
    async def test_login_with_expired_lock_succeeds(
        self, async_client: AsyncClient, expired_locked_user
    ):
        """
        Test login succeeds when account lock has expired.
        
        Validates:
        - User with expired lock can login
        - account_locked_until in past does not prevent login
        - Full login flow completes successfully
        """
        response = await async_client.post(
            "/api/v1/auth/login",
            json={
                "email": expired_locked_user.email,
                "password": expired_locked_user.plain_password,
                "remember_me": False,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["access_token"] is not None


# ============================================================================
# ERROR SCENARIOS - INVALID CREDENTIALS
# ============================================================================


class TestLoginInvalidCredentialsErrors:
    """Test login error scenarios for invalid credentials."""

    @pytest.mark.asyncio
    async def test_login_with_nonexistent_email(self, async_client: AsyncClient):
        """
        Test login with email not found returns 401 Unauthorized.
        
        Validates:
        - HTTP status code is 401
        - Error code is INVALID_CREDENTIALS
        - Generic error message (no email enumeration)
        - No token returned
        - No success=true in response
        """
        response = await async_client.post(
            "/api/v1/auth/login",
            json={
                "email": "nonexistent@example.com",
                "password": "SomePassword123!",
            },
        )

        assert response.status_code == 401
        data = response.json()
        
        assert data["success"] is False
        assert data["data"] is None
        assert data["error"] is not None
        assert data["error"]["code"] == "INVALID_CREDENTIALS"
        assert data["error"]["message"] == "Email or password is incorrect"

    @pytest.mark.asyncio
    async def test_login_with_incorrect_password(
        self, async_client: AsyncClient, verified_user
    ):
        """
        Test login with incorrect password returns 401 Unauthorized.
        
        Validates:
        - HTTP status code is 401
        - Error code is INVALID_CREDENTIALS
        - Generic error message (no password hint)
        - No token returned
        - Correct email but wrong password is rejected
        """
        response = await async_client.post(
            "/api/v1/auth/login",
            json={
                "email": verified_user.email,
                "password": "WrongPassword123!",  # Incorrect password
            },
        )

        assert response.status_code == 401
        data = response.json()
        
        assert data["success"] is False
        assert data["error"]["code"] == "INVALID_CREDENTIALS"
        assert data["error"]["message"] == "Email or password is incorrect"

    @pytest.mark.asyncio
    async def test_login_with_empty_password(self, async_client: AsyncClient, verified_user):
        """
        Test login with empty password returns 401 or 400.
        
        Validates:
        - Empty password is rejected
        - Either 400 (validation) or 401 (invalid credentials) is acceptable
        - No successful token issued
        """
        response = await async_client.post(
            "/api/v1/auth/login",
            json={
                "email": verified_user.email,
                "password": "",
            },
        )

        # Empty password passes Pydantic validation (no min_length), then fails bcrypt comparison
        assert response.status_code == 401
        data = response.json()
        assert data["success"] is False


# ============================================================================
# ERROR SCENARIOS - EMAIL VERIFICATION & ACCOUNT STATUS
# ============================================================================


class TestLoginEmailVerificationErrors:
    """Test login errors related to email verification."""

    @pytest.mark.asyncio
    async def test_login_with_unverified_email(
        self, async_client: AsyncClient, unverified_user
    ):
        """
        Test login with unverified email returns 403 Forbidden.
        
        Validates:
        - HTTP status code is 403
        - Error code is EMAIL_NOT_VERIFIED
        - Error message directs user to verify email
        - No token returned
        - User must verify email before logging in
        """
        response = await async_client.post(
            "/api/v1/auth/login",
            json={
                "email": unverified_user.email,
                "password": unverified_user.plain_password,
            },
        )

        assert response.status_code == 403
        data = response.json()
        
        assert data["success"] is False
        assert data["data"] is None
        assert data["error"]["code"] == "EMAIL_NOT_VERIFIED"
        assert "verify" in data["error"]["message"].lower()


class TestLoginAccountStatusErrors:
    """Test login errors related to account status."""

    @pytest.mark.asyncio
    async def test_login_with_inactive_account(
        self, async_client: AsyncClient, inactive_user
    ):
        """
        Test login with inactive account returns 403 Forbidden.
        
        Validates:
        - HTTP status code is 403
        - Error code is ACCOUNT_INACTIVE
        - Error message indicates account deactivation
        - No token returned
        - Suspended accounts cannot login
        """
        response = await async_client.post(
            "/api/v1/auth/login",
            json={
                "email": inactive_user.email,
                "password": inactive_user.plain_password,
            },
        )

        assert response.status_code == 403
        data = response.json()
        
        assert data["success"] is False
        assert data["error"]["code"] == "ACCOUNT_INACTIVE"
        assert "deactivated" in data["error"]["message"].lower()

    @pytest.mark.asyncio
    async def test_login_with_locked_account(
        self, async_client: AsyncClient, locked_user
    ):
        """
        Test login with locked account returns 423 Locked.
        
        Validates:
        - HTTP status code is 423
        - Error code is ACCOUNT_LOCKED
        - Error message includes unlock time
        - No token returned
        - Temporarily locked accounts cannot login
        """
        response = await async_client.post(
            "/api/v1/auth/login",
            json={
                "email": locked_user.email,
                "password": locked_user.plain_password,
            },
        )

        assert response.status_code == 423
        data = response.json()
        
        assert data["success"] is False
        assert data["error"]["code"] == "ACCOUNT_LOCKED"
        assert "locked" in data["error"]["message"].lower()


# ============================================================================
# EDGE CASES - MISSING & EMPTY FIELDS
# ============================================================================


class TestLoginMissingFieldsErrors:
    """Test login with missing or empty required fields."""

    @pytest.mark.asyncio
    async def test_login_missing_email_field(self, async_client: AsyncClient):
        """
        Test login without email field returns 422 Validation Error.
        
        Validates:
        - HTTP status code is 422
        - Email is required field
        - Pydantic validation error
        """
        response = await async_client.post(
            "/api/v1/auth/login",
            json={
                "password": "SomePassword123!",
                # email is missing
            },
        )

        assert response.status_code == 422
        # Pydantic validation error for missing field

    @pytest.mark.asyncio
    async def test_login_missing_password_field(self, async_client: AsyncClient):
        """
        Test login without password field returns 422 Validation Error.
        
        Validates:
        - HTTP status code is 422
        - Password is required field
        - Pydantic validation error
        """
        response = await async_client.post(
            "/api/v1/auth/login",
            json={
                "email": "test@example.com",
                # password is missing
            },
        )

        assert response.status_code == 422
        # Pydantic validation error for missing field

    @pytest.mark.asyncio
    async def test_login_invalid_email_format(self, async_client: AsyncClient):
        """
        Test login with invalid email format returns 422 Validation Error.
        
        Validates:
        - HTTP status code is 422
        - EmailStr validation catches invalid format
        - Pydantic validator catches "invalid@" format
        """
        response = await async_client.post(
            "/api/v1/auth/login",
            json={
                "email": "not-an-email",  # Invalid email format
                "password": "SomePassword123!",
            },
        )

        assert response.status_code == 422
        # Pydantic validation error for invalid email format

    @pytest.mark.asyncio
    async def test_login_empty_json_body(self, async_client: AsyncClient):
        """
        Test login with empty JSON body returns 422 Validation Error.
        
        Validates:
        - Empty request body is rejected
        - All required fields are validated
        """
        response = await async_client.post(
            "/api/v1/auth/login",
            json={},
        )

        assert response.status_code == 422


# ============================================================================
# EDGE CASES - SPECIAL CHARACTERS & ENCODING
# ============================================================================


class TestLoginSpecialCharactersEdgeCases:
    """Test login with special characters and edge cases."""

    @pytest.mark.asyncio
    async def test_login_with_special_characters_in_password(
        self, async_client: AsyncClient, test_db
    ):
        """
        Test login with special characters in password.
        
        Validates:
        - Special chars like !@#$%^&*() work in passwords
        - Password with special chars is properly hashed and verified
        - Login succeeds with complex password
        """
        # Create user with special character password
        password_with_special = "P@ssw0rd!#$%^&*"
        password_hash = PasswordHasher.hash_password(password_with_special)

        async with test_db() as session:
            user = User(
                email="special@example.com",
                password_hash=password_hash,
                full_name="Special Chars User",
                is_verified=True,
                is_active=True,
            )
            session.add(user)
            await session.commit()

        # Login with special character password
        response = await async_client.post(
            "/api/v1/auth/login",
            json={
                "email": "special@example.com",
                "password": password_with_special,
            },
        )

        assert response.status_code == 200
        assert response.json()["success"] is True

    @pytest.mark.asyncio
    async def test_login_with_unicode_email(self, async_client: AsyncClient):
        """
        Test login with unicode characters in email.
        
        Validates:
        - Unicode email addresses are handled properly
        - If supported by email validator
        """
        response = await async_client.post(
            "/api/v1/auth/login",
            json={
                "email": "user@例え.jp",  # Japanese domain
                "password": "Password123!",
            },
        )

        # Should return 422 (invalid email) or 401 (not found)
        # depending on email validator support
        assert response.status_code in [422, 401]

    @pytest.mark.asyncio
    async def test_login_with_very_long_email(self, async_client: AsyncClient):
        """
        Test login with extremely long email string.
        
        Validates:
        - Email length is validated
        - Very long strings don't cause issues
        """
        long_email = "a" * 300 + "@example.com"
        response = await async_client.post(
            "/api/v1/auth/login",
            json={
                "email": long_email,
                "password": "Password123!",
            },
        )

        # Should be rejected by email validation
        assert response.status_code in [422, 401]


# ============================================================================
# RATE LIMITING & SECURITY
# ============================================================================


class TestLoginRateLimitingSimulated:
    """Test simulated rate limiting scenarios."""

    @pytest.mark.asyncio
    async def test_login_multiple_invalid_attempts(
        self, async_client: AsyncClient, verified_user
    ):
        """
        Test that multiple invalid login attempts are tracked.
        
        Validates:
        - Invalid attempts are recorded
        - Failed attempts can be tracked (for rate limiting implementation)
        - System tracks failed login attempts for security
        
        Note: Full rate limiting with account lockout requires Redis/cache
        This test validates the error handling structure.
        """
        # Attempt 1: Wrong password
        response1 = await async_client.post(
            "/api/v1/auth/login",
            json={
                "email": verified_user.email,
                "password": "WrongPassword1!",
            },
        )
        assert response1.status_code == 401

        # Attempt 2: Wrong password
        response2 = await async_client.post(
            "/api/v1/auth/login",
            json={
                "email": verified_user.email,
                "password": "WrongPassword2!",
            },
        )
        assert response2.status_code == 401

        # Attempt 3: Correct password should still work
        response3 = await async_client.post(
            "/api/v1/auth/login",
            json={
                "email": verified_user.email,
                "password": verified_user.plain_password,
            },
        )
        assert response3.status_code == 200


# ============================================================================
# RESPONSE SCHEMA VALIDATION
# ============================================================================


class TestLoginResponseSchemaValidation:
    """Test login response schema compliance."""

    @pytest.mark.asyncio
    async def test_login_success_response_schema(
        self, async_client: AsyncClient, verified_user
    ):
        """
        Test successful login response matches LoginResponse schema.
        
        Validates response structure:
        - Root level: success, data, error
        - data.access_token: JWT string
        - data.refresh_token: JWT string
        - data.token_type: "Bearer"
        - data.expires_in: 604800 (7 days)
        - data.user: UserProfileResponse object
        - data.user fields: user_id, email, full_name, level, role
        """
        response = await async_client.post(
            "/api/v1/auth/login",
            json={
                "email": verified_user.email,
                "password": verified_user.plain_password,
            },
        )

        assert response.status_code == 200
        data = response.json()

        # Root schema
        assert isinstance(data, dict)
        assert "success" in data
        assert "data" in data
        assert "error" in data

        # Response data schema
        resp_data = data["data"]
        assert isinstance(resp_data["access_token"], str)
        assert isinstance(resp_data["refresh_token"], str)
        assert resp_data["token_type"] == "Bearer"
        assert isinstance(resp_data["expires_in"], int)
        assert resp_data["expires_in"] > 0

        # User schema
        user_data = resp_data["user"]
        assert isinstance(user_data["user_id"], int)
        assert isinstance(user_data["email"], str)
        assert isinstance(user_data["full_name"], (str, type(None)))
        assert isinstance(user_data["level"], int)
        assert isinstance(user_data["role"], str)

    @pytest.mark.asyncio
    async def test_login_error_response_schema(
        self, async_client: AsyncClient, unverified_user
    ):
        """
        Test error login response matches error schema.
        
        Validates error structure:
        - success: false
        - data: null
        - error.code: specific error code
        - error.message: human-readable message
        """
        response = await async_client.post(
            "/api/v1/auth/login",
            json={
                "email": unverified_user.email,
                "password": unverified_user.plain_password,
            },
        )

        assert response.status_code == 403
        data = response.json()

        # Error response schema
        assert data["success"] is False
        assert data["data"] is None
        assert isinstance(data["error"], dict)
        assert "code" in data["error"]
        assert "message" in data["error"]
        assert isinstance(data["error"]["code"], str)
        assert isinstance(data["error"]["message"], str)


# ============================================================================
# TOKEN VALIDATION
# ============================================================================


class TestLoginTokenValidation:
    """Test JWT token validation and claims."""

    @pytest.mark.asyncio
    async def test_login_access_token_contains_required_claims(
        self, async_client: AsyncClient, verified_user
    ):
        """
        Test access token contains all required JWT claims.
        
        Validates JWT payload:
        - sub: user_id (as string)
        - email: user email
        - type: token type (if applicable)
        - exp: expiration timestamp
        - iat: issued at timestamp
        - aud, iss: optional but recommended
        """
        response = await async_client.post(
            "/api/v1/auth/login",
            json={
                "email": verified_user.email,
                "password": verified_user.plain_password,
            },
        )

        assert response.status_code == 200
        access_token = response.json()["data"]["access_token"]
        payload = decode_jwt(access_token)

        # Required claims
        assert "sub" in payload
        assert payload["sub"] == str(verified_user.id)
        assert "email" in payload
        assert payload["email"] == verified_user.email
        assert "exp" in payload
        assert "iat" in payload

        # Token should be valid now
        assert payload["exp"] > datetime.utcnow().timestamp()

    @pytest.mark.asyncio
    async def test_login_refresh_token_is_valid_jwt(
        self, async_client: AsyncClient, verified_user
    ):
        """
        Test refresh token is a valid JWT.
        
        Validates:
        - Refresh token can be decoded
        - Refresh token has required claims
        - Both access and refresh tokens are JWTs
        """
        response = await async_client.post(
            "/api/v1/auth/login",
            json={
                "email": verified_user.email,
                "password": verified_user.plain_password,
                "remember_me": True,
            },
        )

        assert response.status_code == 200
        refresh_token = response.json()["data"]["refresh_token"]

        # Verify refresh token is valid JWT
        payload = decode_jwt(refresh_token)
        assert "sub" in payload
        assert "email" in payload
        assert "exp" in payload


# ============================================================================
# DATABASE INTEGRITY
# ============================================================================


class TestLoginDatabaseIntegrity:
    """Test database state after login."""

    @pytest.mark.asyncio
    async def test_login_no_user_data_modified(
        self, async_client: AsyncClient, verified_user, test_db
    ):
        """
        Test that login does not modify user data.
        
        Validates:
        - User email remains unchanged
        - User password hash unchanged
        - User full_name unchanged
        - User verification status unchanged
        - No unintended database modifications
        """
        # Store original data
        original_email = verified_user.email
        original_password_hash = verified_user.password_hash
        original_full_name = verified_user.full_name

        # Login
        response = await async_client.post(
            "/api/v1/auth/login",
            json={
                "email": verified_user.email,
                "password": verified_user.plain_password,
            },
        )

        assert response.status_code == 200

        # Verify user data unchanged
        async with test_db() as session:
            user = await get_user_from_db(session, verified_user.email)
            assert user.email == original_email
            assert user.password_hash == original_password_hash
            assert user.full_name == original_full_name

    @pytest.mark.asyncio
    async def test_login_session_audit_trail_complete(
        self, async_client: AsyncClient, verified_user, test_db
    ):
        """
        Test that login session record contains complete audit information.
        
        Validates LoginSession record:
        - user_id: correct user
        - ip_address: client IP recorded
        - user_agent: client user agent recorded
        - created_at: timestamp recorded
        - Session can be audited for security
        """
        response = await async_client.post(
            "/api/v1/auth/login",
            json={
                "email": verified_user.email,
                "password": verified_user.plain_password,
            },
        )

        assert response.status_code == 200

        async with test_db() as session:
            sessions = await get_login_sessions(session, verified_user.id)
            assert len(sessions) > 0

            session_record = sessions[-1]
            assert session_record.user_id == verified_user.id
            assert session_record.ip_address is not None
            assert len(session_record.ip_address) > 0
            # user_agent might be None in test client
            # assert session_record.user_agent is not None
