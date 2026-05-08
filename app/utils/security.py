"""
Security utilities for authentication.
"""

import re
from datetime import datetime, timedelta
from typing import Optional
import bcrypt
from jose import JWTError, jwt
from app.config import settings


class PasswordHasher:
    """Handle password hashing and verification."""

    @staticmethod
    def hash_password(password: str) -> str:
        """
        Hash password using bcrypt.

        Args:
            password: Plain text password

        Returns:
            Hashed password

        Raises:
            ValueError: If password hashing fails
        """
        try:
            salt = bcrypt.gensalt(rounds=settings.BCRYPT_ROUNDS)
            return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")
        except Exception as e:
            raise ValueError(f"Password hashing failed: {str(e)}")

    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """
        Verify plain password against hashed password.

        Args:
            plain_password: Plain text password to verify
            hashed_password: Hashed password from database

        Returns:
            True if password matches, False otherwise
        """
        try:
            return bcrypt.checkpw(
                plain_password.encode("utf-8"), hashed_password.encode("utf-8")
            )
        except Exception:
            return False


class PasswordValidator:
    """Validate password strength."""

    REQUIRED_LENGTH = 8
    UPPERCASE_REGEX = r"[A-Z]"
    LOWERCASE_REGEX = r"[a-z]"
    DIGIT_REGEX = r"[0-9]"
    SPECIAL_CHAR_REGEX = r"[!@#$%^&*]"

    @classmethod
    def validate(cls, password: str) -> tuple[bool, Optional[str]]:
        """
        Validate password strength.

        Args:
            password: Password to validate

        Returns:
            Tuple of (is_valid, error_message)
        """
        if len(password) < cls.REQUIRED_LENGTH:
            return (False, f"Password must be at least {cls.REQUIRED_LENGTH} characters long")

        if not re.search(cls.UPPERCASE_REGEX, password):
            return (False, "Password must contain at least one uppercase letter (A-Z)")

        if not re.search(cls.LOWERCASE_REGEX, password):
            return (False, "Password must contain at least one lowercase letter (a-z)")

        if not re.search(cls.DIGIT_REGEX, password):
            return (False, "Password must contain at least one digit (0-9)")

        if not re.search(cls.SPECIAL_CHAR_REGEX, password):
            return (False, "Password must contain at least one special character (!@#$%^&*)")

        return (True, None)


class TokenGenerator:
    """Generate and verify JWT tokens."""

    @staticmethod
    def create_email_verification_token(
        user_id: int, email: str, expires_delta: Optional[timedelta] = None
    ) -> str:
        """
        Create JWT token for email verification.

        Args:
            user_id: User ID
            email: User email
            expires_delta: Token expiration time delta

        Returns:
            JWT token string

        Raises:
            ValueError: If token creation fails
        """
        if expires_delta is None:
            expires_delta = timedelta(hours=24)

        expire = datetime.utcnow() + expires_delta
        payload = {
            "sub": str(user_id),
            "email": email,
            "type": "email_verification",
            "exp": expire,
        }

        try:
            token = jwt.encode(
                payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM
            )
            return token
        except Exception as e:
            raise ValueError(f"Token creation failed: {str(e)}")

    @staticmethod
    def verify_token(token: str) -> Optional[dict]:
        """
        Verify and decode JWT token.

        Args:
            token: JWT token to verify

        Returns:
            Token payload if valid, None if invalid or expired
        """
        try:
            payload = jwt.decode(
                token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
            )
            return payload
        except JWTError:
            return None

    @staticmethod
    def create_access_token(
        user_id: int, email: str, expires_delta: Optional[timedelta] = None
    ) -> str:
        """
        Create JWT access token for login.

        Args:
            user_id: User ID
            email: User email
            expires_delta: Token expiration time delta

        Returns:
            JWT token string
        """
        if expires_delta is None:
            expires_delta = timedelta(days=settings.ACCESS_TOKEN_EXPIRE_DAYS)

        now = datetime.utcnow()
        expire = now + expires_delta
        payload = {
            "sub": str(user_id),
            "email": email,
            "type": "access",
            "iat": now,
            "exp": expire,
        }

        token = jwt.encode(
            payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM
        )
        return token

    @staticmethod
    def create_refresh_token(
        user_id: int, email: str, expires_delta: Optional[timedelta] = None
    ) -> str:
        """
        Create JWT refresh token for session extension.

        Args:
            user_id: User ID
            email: User email
            expires_delta: Token expiration time delta

        Returns:
            JWT token string
        """
        if expires_delta is None:
            expires_delta = timedelta(days=7)

        now = datetime.utcnow()
        expire = now + expires_delta
        payload = {
            "sub": str(user_id),
            "email": email,
            "type": "refresh",
            "iat": now,
            "exp": expire,
        }

        token = jwt.encode(
            payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM
        )
        return token


class EmailValidator:
    """Validate email addresses."""

    # RFC 5322 simplified regex
    EMAIL_REGEX = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    MAX_EMAIL_LENGTH = 255

    @classmethod
    def validate(cls, email: str) -> tuple[bool, Optional[str]]:
        """
        Validate email format.

        Args:
            email: Email address to validate

        Returns:
            Tuple of (is_valid, error_message)
        """
        if not email:
            return (False, "Email is required")

        if len(email) > cls.MAX_EMAIL_LENGTH:
            return (False, f"Email must not exceed {cls.MAX_EMAIL_LENGTH} characters")

        if not re.match(cls.EMAIL_REGEX, email):
            return (False, "Email must be valid format (e.g., user@example.com)")

        return (True, None)
