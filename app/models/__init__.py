"""
Database models for MathBattle-BE.

Database Schema (per USER_AUTH_DESIGN.md):
1. users - User accounts
2. user_profiles - User profile info
3. user_settings - User preferences

Token Strategy: Stateless JWT (no token storage in database)
"""

from app.models.base import Base, BaseModel
from app.models.user import User, UserProfile, UserSettings

__all__ = [
    "Base",
    "BaseModel",
    "User",
    "UserProfile",
    "UserSettings",
]
