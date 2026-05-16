"""
Database models for MathBattle-BE.

Database Schema:
1. users              - User accounts
2. user_profiles      - User profile info (elo, streak, win_rate)
3. user_settings      - User preferences
4. badges             - Badge definitions (seeded)
5. user_badges        - Badges earned by users
6. questions          - Question bank (math, sequence, mcq, ...)
7. game_sessions      - Game sessions (G02_F04)
8. session_operations - Player actions within a session (G02_F04)
"""

from app.models.base import Base, BaseModel
from app.models.user import User, UserProfile, UserSettings
from app.models.badge import Badge, UserBadge
from app.models.question import Question
from app.models.game_session import GameSession, GameMode
from app.models.session_operation import SessionOperation

__all__ = [
    "Base",
    "BaseModel",
    "User",
    "UserProfile",
    "UserSettings",
    "Badge",
    "UserBadge",
    "Question",
    "GameSession",
    "GameMode",
    "SessionOperation",
]
