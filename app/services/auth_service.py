"""
Authentication service - business logic for user registration and login.
"""

import logging
from typing import Optional, Tuple
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.models.user import User, UserProfile, UserSettings, Token, LoginSession
from app.utils.security import PasswordHasher, PasswordValidator, EmailValidator, TokenGenerator

logger = logging.getLogger(__name__)


class AuthService:
    """Service for authentication operations."""

    @staticmethod
    async def register_user(
        session: AsyncSession,
        email: str,
        password: str,
        full_name: Optional[str] = None,
    ) -> Tuple[bool, dict]:
        """
        Register a new user with email and password.

        Args:
            session: Database session
            email: User email
            password: User password
            full_name: User full name (optional)

        Returns:
            Tuple of (success: bool, response: dict)
                If success: response contains user_id, email, full_name, message
                If error: response contains code, message, status_code
        """
        try:
            # Step 1: Validate email format
            is_valid, error_msg = EmailValidator.validate(email)
            if not is_valid:
                logger.warning(f"Invalid email format: {email}")
                return (
                    False,
                    {
                        "code": "INVALID_EMAIL_FORMAT",
                        "message": error_msg,
                        "status_code": 400,
                    },
                )

            # Step 2: Check email uniqueness (case-insensitive)
            query = select(User).where(
                User.email.ilike(email)  # Case-insensitive comparison
            )
            result = await session.execute(query)
            existing_user = result.scalars().first()

            if existing_user:
                logger.warning(f"Email already exists: {email}")
                return (
                    False,
                    {
                        "code": "EMAIL_ALREADY_EXISTS",
                        "message": "This email is already registered",
                        "status_code": 409,
                    },
                )

            # Step 3: Validate password strength
            is_valid, error_msg = PasswordValidator.validate(password)
            if not is_valid:
                logger.warning(f"Weak password for email: {email}")
                return (
                    False,
                    {
                        "code": "WEAK_PASSWORD",
                        "message": error_msg,
                        "status_code": 400,
                    },
                )

            # Step 4: Hash password using bcrypt
            try:
                password_hash = PasswordHasher.hash_password(password)
            except ValueError as e:
                logger.error(f"Password hashing failed: {str(e)}")
                return (
                    False,
                    {
                        "code": "INTERNAL_SERVER_ERROR",
                        "message": "Failed to process password",
                        "status_code": 500,
                    },
                )

            # Step 5: Create user + profile + settings atomically
            new_user = User(
                email=email.lower(),
                password_hash=password_hash,
                full_name=full_name if full_name else None,
                is_verified=False,
                is_active=True,
            )
            session.add(new_user)
            await session.flush()  # get new_user.id before creating child records

            name_part = full_name.lower().replace(" ", "_")[:20] if full_name else "user"
            
            username = f"{name_part}_{new_user.id}"
            session.add(UserProfile(user_id=new_user.id, username=username))
            session.add(UserSettings(user_id=new_user.id))

            await session.commit()

            logger.info(f"User registered successfully: {email} (ID: {new_user.id})")

            # Step 6: Generate email verification token
            try:
                token = TokenGenerator.create_email_verification_token(
                    user_id=new_user.id, email=new_user.email
                )
                logger.info(f"Email verification token generated for user: {new_user.id}")
            except ValueError as e:
                logger.error(f"Token generation failed: {str(e)}")
                return (
                    False,
                    {
                        "code": "INTERNAL_SERVER_ERROR",
                        "message": "Failed to generate verification token",
                        "status_code": 500,
                    },
                )

            # Step 7: Queue email task (for now, just log it)
            # TODO: Integrate with SendGrid async email queue
            logger.info(
                f"Email verification task queued for user: {new_user.id} (Token: {token[:20]}...)"
            )

            return (
                True,
                {
                    "user_id": new_user.id,
                    "email": new_user.email,
                    "full_name": new_user.full_name,
                    "message": "Account created successfully. Confirmation email sent.",
                    "verification_token": token,  # For testing purposes
                },
            )

        except Exception as e:
            logger.error(f"Registration error: {str(e)}", exc_info=True)
            return (
                False,
                {
                    "code": "INTERNAL_SERVER_ERROR",
                    "message": "An error occurred during registration",
                    "status_code": 500,
                },
            )

    @staticmethod
    async def login_user(
        session: AsyncSession,
        email: str,
        password: str,
        remember_me: bool = False,
        client_ip: str = "unknown",
        user_agent: str = "",
    ) -> Tuple[bool, dict]:
        """
        Authenticate user with email and password.

        Args:
            session: Database session
            email: User email
            password: User password
            remember_me: Whether to create long-lived refresh token
            client_ip: Client IP address for audit trail
            user_agent: Client user agent for audit trail

        Returns:
            Tuple of (success: bool, response: dict)
                If success: response contains access_token, refresh_token, user info
                If error: response contains code, message, status_code
        """
        try:
            # Step 1: Validate input parameters
            if email is None or password is None:
                logger.warning("Login attempt with missing credentials")
                return (
                    False,
                    {
                        "code": "MISSING_CREDENTIALS",
                        "message": "Email and password are required",
                        "status_code": 400,
                    },
                )

            # Step 2: Find user by email (case-insensitive)
            query = select(User).where(
                func.lower(User.email) == func.lower(email)
            )
            result = await session.execute(query)
            user = result.scalars().first()

            if not user:
                logger.warning(f"Login attempt with non-existent email: {email}")
                return (
                    False,
                    {
                        "code": "INVALID_CREDENTIALS",
                        "message": "Email or password is incorrect",
                        "status_code": 401,
                    },
                )

            # Step 3: Verify password hash
            if not PasswordHasher.verify_password(password, user.password_hash):
                logger.warning(f"Failed login attempt for user: {user.id}")
                return (
                    False,
                    {
                        "code": "INVALID_CREDENTIALS",
                        "message": "Email or password is incorrect",
                        "status_code": 401,
                    },
                )

            # Step 4: Check email verification status
            # TEMP: Disabled while activation/verification flow is under development.
            # if not user.is_verified:
            #     logger.info(f"Login attempt with unverified email: {user.id}")
            #     return (
            #         False,
            #         {
            #             "code": "EMAIL_NOT_VERIFIED",
            #             "message": "Please verify your email before logging in",
            #             "status_code": 403,
            #         },
            #     )

            # Step 5: Check account status
            if not user.is_active:
                logger.warning(f"Login attempt on inactive account: {user.id}")
                return (
                    False,
                    {
                        "code": "ACCOUNT_INACTIVE",
                        "message": "Your account has been deactivated",
                        
                        "status_code": 403,
                    },
                )

            # Step 6: Check if account is locked
            if (
                user.account_locked_until
                and user.account_locked_until > datetime.utcnow()
            ):
                unlock_time = user.account_locked_until.strftime("%Y-%m-%d %H:%M:%S")
                logger.warning(f"Login attempt on locked account: {user.id}")
                return (
                    False,
                    {
                        "code": "ACCOUNT_LOCKED",
                        "message": f"Account locked until {unlock_time}",
                        "status_code": 423,
                    },
                )

            # Step 7: Generate tokens
            try:
                access_token = TokenGenerator.create_access_token(
                    user_id=user.id, email=user.email
                )
                refresh_token = TokenGenerator.create_refresh_token(
                    user_id=user.id, email=user.email
                )
            except ValueError as e:
                logger.error(f"Token generation failed: {str(e)}")
                return (
                    False,
                    {
                        "code": "INTERNAL_SERVER_ERROR",
                        "message": "Failed to generate authentication tokens",
                        "status_code": 500,
                    },
                )

            # Step 8: Store refresh token if remember_me
            if remember_me:
                try:
                    token_record = Token(
                        user_id=user.id,
                        refresh_token=refresh_token,
                        token_type="refresh",
                        expires_at=datetime.utcnow() + timedelta(days=7),
                    )
                    session.add(token_record)
                except Exception as e:
                    logger.error(f"Failed to store refresh token: {str(e)}")

            # Step 9: Create login session for audit trail
            try:
                login_session = LoginSession(
                    user_id=user.id,
                    ip_address=client_ip,
                    user_agent=user_agent,
                )
                session.add(login_session)
            except Exception as e:
                logger.error(f"Failed to create login session: {str(e)}")

            # Commit changes
            try:
                await session.commit()
            except Exception as e:
                logger.error(f"Database commit failed: {str(e)}")
                await session.rollback()
                return (
                    False,
                    {
                        "code": "INTERNAL_SERVER_ERROR",
                        "message": "Login failed due to database error",
                        "status_code": 500,
                    },
                )

            logger.info(f"Successful login for user: {user.id}")

            # Step 10: Prepare response
            return (
                True,
                {
                    "access_token": access_token,
                    "refresh_token": refresh_token,
                    "token_type": "Bearer",
                    "expires_in": 86400 * 7,  # 7 days in seconds
                    "user": {
                        "user_id": user.id,
                        "email": user.email,
                        "full_name": user.full_name,
                        "level": 1,  # Default level for now
                        "role": "Free",
                    },
                },
            )

        except Exception as e:
            logger.error(f"Login error: {str(e)}", exc_info=True)
            return (
                False,
                {
                    "code": "INTERNAL_SERVER_ERROR",
                    "message": "An error occurred during login",
                    "status_code": 500,
                },
            )

    @staticmethod
    async def logout_user(
        session: AsyncSession,
        user_id: int,
        refresh_token: Optional[str] = None,
    ) -> Tuple[bool, dict]:
        """
        Log out user by revoking refresh token and deleting login session.

        Args:
            session: Database session
            user_id: Authenticated user's ID from JWT
            refresh_token: Optional refresh token to revoke

        Returns:
            Tuple of (success: bool, response: dict)
        """
        try:
            # Step 1: Revoke refresh token if provided
            if refresh_token:
                query = select(Token).where(
                    Token.user_id == user_id,
                    Token.refresh_token == refresh_token,
                    Token.is_revoked == False,
                )
                result = await session.execute(query)
                token_record = result.scalars().first()

                if token_record:
                    token_record.is_revoked = True
                    logger.info(f"Refresh token revoked for user: {user_id}")
                else:
                    logger.info(f"Refresh token not found or already revoked for user: {user_id}")

            # Step 2: Delete most recent login session
            session_query = (
                select(LoginSession)
                .where(LoginSession.user_id == user_id)
                .order_by(LoginSession.created_at.desc())
                .limit(1)
            )
            session_result = await session.execute(session_query)
            login_session = session_result.scalars().first()

            if login_session:
                await session.delete(login_session)
                logger.info(f"Login session deleted for user: {user_id}")

            await session.commit()
            logger.info(f"User logged out successfully: {user_id}")

            return (True, {"message": "Logged out successfully"})

        except Exception as e:
            logger.error(f"Logout error: {str(e)}", exc_info=True)
            await session.rollback()
            return (
                False,
                {
                    "code": "INTERNAL_SERVER_ERROR",
                    "message": "An error occurred during logout",
                    "status_code": 500,
                },
            )
