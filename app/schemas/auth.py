"""
Pydantic schemas for authentication.
"""

from pydantic import BaseModel, Field, ConfigDict, EmailStr
from typing import Optional


class UserRegisterRequest(BaseModel):
    """User registration request schema."""
    
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "email": "user@example.com",
            "password": "Secure123!",
            "confirm_password": "Secure123!",
            "full_name": "John Doe",
        }
    })

    email: str = Field(..., min_length=1, max_length=255, example="user@example.com")
    password: str = Field(..., min_length=8, example="Secure123!")
    confirm_password: str = Field(..., min_length=8, example="Secure123!")
    full_name: Optional[str] = Field(None, max_length=100, example="John Doe")


class UserRegisterResponse(BaseModel):
    """User registration response schema."""
    
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "success": True,
            "data": {
                "user_id": 1,
                "email": "user@example.com",
                "full_name": "John Doe",
                "message": "Account created successfully. Confirmation email sent.",
            },
        }
    })

    success: bool
    data: Optional[dict] = None
    error: Optional[dict] = None


class ErrorResponse(BaseModel):
    """Error response schema."""
    
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "success": False,
            "error": {
                "code": "INVALID_EMAIL_FORMAT",
                "message": "Email must be valid format",
            },
        }
    })

    success: bool = False
    error: dict = Field(..., example={"code": "ERROR_CODE", "message": "Error message"})


# ============================================================================
# Login Schemas
# ============================================================================

class LoginRequest(BaseModel):
    """User login request schema."""
    
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "email": "user@example.com",
            "password": "Secure123!",
            "remember_me": False,
        }
    })

    email: EmailStr = Field(..., description="Email address")
    password: str = Field(..., description="User password")
    remember_me: Optional[bool] = Field(False, description="Extended session if true")


class UserProfileResponse(BaseModel):
    """User profile info in login response."""
    
    user_id: int
    email: str
    full_name: Optional[str]
    level: int
    role: str = "Free"

    model_config = ConfigDict(from_attributes=True)


class LoginResponse(BaseModel):
    """User login response schema."""
    
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "success": True,
            "data": {
                "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "token_type": "Bearer",
                "expires_in": 604800,
                "user": {
                    "user_id": 1,
                    "email": "user@example.com",
                    "full_name": "John Doe",
                    "level": 1,
                    "role": "Free",
                }
            }
        }
    })

    success: bool
    data: Optional[dict] = None
    error: Optional[dict] = None


# ============================================================================
# Logout Schemas
# ============================================================================

class LogoutRequest(BaseModel):
    """Logout request schema."""

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
        }
    })

    refresh_token: Optional[str] = Field(
        None, description="Refresh token to revoke (only if remember_me was used)"
    )


class LogoutResponse(BaseModel):
    """Logout response schema."""

    success: bool
    data: Optional[dict] = None
    error: Optional[dict] = None
