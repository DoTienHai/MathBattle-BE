"""SessionOperation model — one math question within a game session (G02_F04)."""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Index, Integer, String
from sqlalchemy import Uuid
from sqlalchemy.orm import relationship

from app.models.base import Base


class SessionOperation(Base):
    """A single math operation generated for a player during a game session."""

    __tablename__ = "session_operations"
    __allow_unmapped__ = True

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    session_id = Column(
        Uuid(as_uuid=True),
        ForeignKey("game_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    question_id = Column(
        Uuid(as_uuid=True),
        ForeignKey("questions.id"),
        nullable=False,
        index=True,
    )
    question_index = Column(Integer, nullable=False)  # The index of this question within the session (0-based)

    # Timing
    time_limit = Column(Float, nullable=False)

    # Player's answer (SF04)
    user_answer = Column(Integer, nullable=True)
    submitted_at = Column(DateTime, nullable=True)
    client_submitted_at = Column(DateTime, nullable=True)

    # Evaluation result (SF05)
    is_correct = Column(Boolean, nullable=True)
    timed_out = Column(Boolean, nullable=False, default=False)
    evaluated_at = Column(DateTime, nullable=True)

    # Relationships
    session = relationship("GameSession", back_populates="operations")
    question = relationship("Question")

    
    __table_args__ = (
        Index("idx_session_operations_session_idx", "session_id", "question_index"),
    )
