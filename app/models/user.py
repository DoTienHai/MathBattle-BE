"""
User-related database models.

Tables (per USER_AUTH_DESIGN.md):
1. users - User accounts (authentication)
2. user_profiles - User profile info (username, level, points)
3. user_settings - User preferences (theme, language, notifications)

Token Strategy: Stateless JWT (no database storage)
"""

from datetime import datetime
from typing import Optional
from sqlalchemy import Column, Integer, Float, String, Boolean, DateTime, ForeignKey, Index, CheckConstraint
from sqlalchemy.orm import relationship
from app.models.base import BaseModel


class User(BaseModel):
    """Main user account model."""

    __tablename__ = "users"
    __allow_unmapped__ = True

    # Authentication
    email = Column(String(255), nullable=False, unique=True, index=True)
    password_hash = Column(String(255), nullable=False)

    # Profile
    full_name = Column(String(100), nullable=True)

    # Verification
    is_verified = Column(Boolean, default=False, index=True)
    verified_at = Column(DateTime, nullable=True)

    # Status
    is_active = Column(Boolean, default=True, index=True)

    # Account Security (for rate limiting/lockout)
    account_locked_until = Column(DateTime, nullable=True)

    # Relationships
    user_profile = relationship(
        "UserProfile",
        uselist=False,
        back_populates="user",
        cascade="all, delete-orphan"
    )
    user_settings = relationship(
        "UserSettings",
        uselist=False,
        back_populates="user",
        cascade="all, delete-orphan"
    )
    tokens = relationship(
        "Token",
        back_populates="user",
        cascade="all, delete-orphan"
    )
    login_sessions = relationship(
        "LoginSession",
        back_populates="user",
        cascade="all, delete-orphan"
    )
    game_sessions = relationship(
        "GameSession",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    badges = relationship(
        "UserBadge",
        back_populates="user",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index("idx_email_lower", "email"),
        Index("idx_is_verified_active", "is_verified", "is_active"),
    )


class UserProfile(BaseModel):
    """Extended user profile information."""

    __tablename__ = "user_profiles"
    __allow_unmapped__ = True

    # Foreign key
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, unique=True, index=True)

    # Profile data
    username = Column(String(30), nullable=False, unique=True, index=True)
    current_level = Column(Integer, default=1, nullable=False)
    elo = Column(Integer, default=1000, nullable=False)
    current_streak = Column(Integer, default=0, nullable=False)
    longest_streak = Column(Integer, default=0, nullable=False)
    win_rate = Column(Float, default=0.0, nullable=False)
    profile_completed = Column(Boolean, default=False, nullable=False)

    # Relationships
    user = relationship("User", back_populates="user_profile")

    __table_args__ = (
        CheckConstraint("current_level >= 1 AND current_level <= 100", name="check_level_range"),
        CheckConstraint("elo >= 0", name="check_elo_non_negative"),
        CheckConstraint("win_rate >= 0.0 AND win_rate <= 1.0", name="check_win_rate_range"),
        Index("idx_username_lower", "username"),
        Index("idx_user_profiles_elo", "elo"),
    )


class UserSettings(BaseModel):
    """User preferences and settings."""

    __tablename__ = "user_settings"
    __allow_unmapped__ = True

    # Foreign key
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, unique=True, index=True)

    # UI Preferences
    theme = Column(String(20), default="auto", nullable=False)
    language = Column(String(10), default="en", nullable=False)

    # Notification Settings
    notifications_enabled = Column(Boolean, default=True, nullable=False)

    # Relationships
    user = relationship("User", back_populates="user_settings")

    __table_args__ = (
        CheckConstraint("theme IN ('light', 'dark', 'auto')", name="check_theme_value"),
        Index("idx_user_settings_user_id", "user_id"),
    )


class Token(BaseModel):
    """Refresh tokens for extended sessions."""

    __tablename__ = "tokens"
    __allow_unmapped__ = True

    # Foreign key
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    # Token data
    refresh_token = Column(String(500), nullable=False, unique=True, index=True)
    token_type = Column(String(20), default="refresh", nullable=False)

    # Expiry
    expires_at = Column(DateTime, nullable=False, index=True)

    # Status
    is_revoked = Column(Boolean, default=False, nullable=False)

    # Relationships
    user = relationship("User", back_populates="tokens")

    __table_args__ = (
        Index("idx_user_token_active", "user_id", "is_revoked"),
    )


class LoginSession(BaseModel):
    """Login session audit trail for security."""

    __tablename__ = "login_sessions"
    __allow_unmapped__ = True

    # Foreign key
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    # Session info
    ip_address = Column(String(45), nullable=False)  # IPv4 (15) or IPv6 (39) chars
    user_agent = Column(String(500), nullable=True)

    # Relationships
    user = relationship("User", back_populates="login_sessions")

    __table_args__ = (
        Index("idx_login_session_user_time", "user_id", "created_at"),
    )
