"""GameSession model — tracks a single game session (G02_F04)."""

import uuid
from enum import Enum
from datetime import datetime

from sqlalchemy import Column, DateTime, Enum as SAEnum, ForeignKey, Index, Integer, String
from sqlalchemy import Uuid
from sqlalchemy.orm import relationship

from app.models.base import Base


class GameMode(str, Enum):
    DAILY_CHALLENGE = "daily_challenge"
    LEVEL_UP = "level_up"
    MINI_GAME = "mini_game"
    QUICK_CALCULATE = "quick_calculate"


class GameSession(Base):
    """One game session owned by a user."""

    __tablename__ = "game_sessions"
    __allow_unmapped__ = True

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    ended_at = Column(DateTime, nullable=True)

    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    game_mode = Column(SAEnum(GameMode, name="game_mode", native_enum=False), nullable=False)
    level_player_at_start = Column(Integer, nullable=False, default=1)
    status = Column(String(20), nullable=False, default="active")  # active, completed, timed_out
    score = Column(Integer, nullable=True)

    # Relationships
    user = relationship("User", back_populates="game_sessions")
    operations = relationship(
        "SessionOperation",
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="SessionOperation.question_index",
    )

    __table_args__ = (
        Index("idx_game_sessions_user_status", "user_id", "status"),
    )
