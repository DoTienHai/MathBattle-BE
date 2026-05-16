"""Pydantic schemas for User Profile endpoints (G01_F02)."""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator


class BasicProfileResponse(BaseModel):
    """Response schema for GET /profile (SF01)."""

    user_id: int
    username: str
    full_name: Optional[str]
    current_level: int
    join_date: datetime


class PersonalStatsResponse(BaseModel):
    """Response schema for GET /profile/stats (SF02)."""

    elo: int
    current_streak: int
    longest_streak: int
    win_rate: float
    global_rank: int
    levels_completed: int


class BadgeItem(BaseModel):
    """Single badge entry in the badges list."""

    badge_id: int
    name: str
    description: str
    icon_url: str
    category: str
    earned_at: datetime


class BadgesResponse(BaseModel):
    """Response schema for GET /profile/badges (SF03)."""

    total: int
    badges: List[BadgeItem]


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
