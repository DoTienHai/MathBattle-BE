"""
Authentication API endpoints.
"""

import logging
from fastapi import APIRouter, Depends, status, Request
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.connection import get_db
from app.schemas.auth import (
    UserRegisterRequest,
    UserRegisterResponse,
    ErrorResponse,
    LoginRequest,
    LoginResponse,
    LogoutRequest,
    LogoutResponse,
)
from app.services.auth_service import AuthService
from app.api.deps import get_current_user_id

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["authentication"])


@router.post(
    "/register",
    status_code=status.HTTP_201_CREATED,
)
async def register(
    request: UserRegisterRequest,
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    """
    Register a new user with email and password.

    ### Request Body
    - **email**: Valid email address (RFC 5322 format)
    - **password**: Strong password (min 8 chars, uppercase, lowercase, digit, special char)
    - **confirm_password**: Must match password
    - **full_name**: Optional user name

    ### Response (201 Created)
    - **success**: Registration status
    - **data**: User info and confirmation message
    - **error**: None if successful

    ### Errors
    - **400**: Invalid email or weak password
    - **409**: Email already registered
    - **500**: Server error
    """
    try:
        # Validate password confirmation
        if request.password != request.confirm_password:
            logger.warning(f"Password mismatch for email: {request.email}")
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={
                    "success": False,
                    "data": None,
                    "error": {
                        "code": "PASSWORD_MISMATCH",
                        "message": "Passwords do not match",
                    },
                },
            )

        # Call service to register user
        success, response_data = await AuthService.register_user(
            session=db,
            email=request.email,
            password=request.password,
            full_name=request.full_name,
        )

        if success:
            # Build success response
            user_data = {
                "user_id": response_data["user_id"],
                "email": response_data["email"],
                "full_name": response_data["full_name"],
                "message": response_data["message"],
            }
            return JSONResponse(
                status_code=status.HTTP_201_CREATED,
                content={
                    "success": True,
                    "data": user_data,
                    "error": None,
                },
            )
        else:
            # Extract error info
            status_code = response_data.get("status_code", 500)
            error_code = response_data.get("code", "INTERNAL_SERVER_ERROR")
            error_message = response_data.get("message", "An error occurred")

            # Map status codes
            http_status = {
                400: status.HTTP_400_BAD_REQUEST,
                409: status.HTTP_409_CONFLICT,
                500: status.HTTP_500_INTERNAL_SERVER_ERROR,
            }.get(status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)

            return JSONResponse(
                status_code=http_status,
                content={
                    "success": False,
                    "data": None,
                    "error": {
                        "code": error_code,
                        "message": error_message,
                    },
                },
            )

    except Exception as e:
        logger.error(f"Registration endpoint error: {str(e)}", exc_info=True)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "success": False,
                "data": None,
                "error": {
                    "code": "INTERNAL_SERVER_ERROR",
                    "message": "An unexpected error occurred",
                },
            },
        )


@router.post(
    "/login",
    status_code=status.HTTP_200_OK,
)
async def login(
    request: LoginRequest,
    http_request: Request,
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    """
    Authenticate user with email and password.

    ### Request Body
    - **email**: User email address
    - **password**: User password
    - **remember_me**: Optional boolean to create long-lived refresh token

    ### Response (200 OK)
    - **success**: Login status
    - **data**: Access token, refresh token, and user info
    - **error**: None if successful

    ### Errors
    - **400**: Missing or invalid input
    - **401**: Invalid email or password
    - **403**: Email not verified or account inactive
    - **423**: Account is locked
    - **429**: Too many failed login attempts (rate limited)
    - **500**: Server error
    """
    try:
        # Get client IP and user agent for audit trail
        client_ip = http_request.client.host or "unknown"
        user_agent = http_request.headers.get("user-agent", "")

        logger.info(f"Login attempt: email={request.email}, IP={client_ip}")

        # Call service to authenticate user
        success, response_data = await AuthService.login_user(
            session=db,
            email=request.email,
            password=request.password,
            remember_me=request.remember_me or False,
            client_ip=client_ip,
            user_agent=user_agent,
        )

        if success:
            # Build success response
            return JSONResponse(
                status_code=status.HTTP_200_OK,
                content={
                    "success": True,
                    "data": response_data,
                    "error": None,
                },
            )
        else:
            # Extract error info
            http_status_code = response_data.get("status_code", 500)
            error_code = response_data.get("code", "INTERNAL_SERVER_ERROR")
            error_message = response_data.get("message", "An error occurred")

            # Map status codes
            http_status = {
                400: status.HTTP_400_BAD_REQUEST,
                401: status.HTTP_401_UNAUTHORIZED,
                403: status.HTTP_403_FORBIDDEN,
                423: status.HTTP_423_LOCKED,
                429: status.HTTP_429_TOO_MANY_REQUESTS,
                500: status.HTTP_500_INTERNAL_SERVER_ERROR,
            }.get(http_status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)

            return JSONResponse(
                status_code=http_status,
                content={
                    "success": False,
                    "data": None,
                    "error": {
                        "code": error_code,
                        "message": error_message,
                    },
                },
            )

    except Exception as e:
        logger.error(f"Login endpoint error: {str(e)}", exc_info=True)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "success": False,
                "data": None,
                "error": {
                    "code": "INTERNAL_SERVER_ERROR",
                    "message": "An unexpected error occurred",
                },
            },
        )


@router.post(
    "/logout",
    status_code=status.HTTP_200_OK,
)
async def logout(
    request: LogoutRequest,
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    """
    Log out the current user.

    ### Headers
    - **Authorization**: Bearer <access_token> (required)

    ### Request Body
    - **refresh_token**: Optional — revoke stored refresh token if provided

    ### Response (200 OK)
    - Refresh token revoked (if provided)
    - Login session deleted from audit trail

    ### Errors
    - **401**: Invalid or expired access token
    - **500**: Server error
    """
    try:
        logger.info(f"Logout attempt for user: {user_id}")

        success, response_data = await AuthService.logout_user(
            session=db,
            user_id=user_id,
            refresh_token=request.refresh_token,
        )

        if success:
            return JSONResponse(
                status_code=status.HTTP_200_OK,
                content={
                    "success": True,
                    "data": response_data,
                    "error": None,
                },
            )

        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "success": False,
                "data": None,
                "error": {
                    "code": response_data.get("code", "INTERNAL_SERVER_ERROR"),
                    "message": response_data.get("message", "Logout failed"),
                },
            },
        )

    except Exception as e:
        logger.error(f"Logout endpoint error: {str(e)}", exc_info=True)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "success": False,
                "data": None,
                "error": {
                    "code": "INTERNAL_SERVER_ERROR",
                    "message": "An unexpected error occurred",
                },
            },
        )
