"""SessionOperation model — one math question within a game session (G02_F04)."""

import uuid
from datetime import datetime

from sqlalchemy import BigInteger, Boolean, Column, DateTime, Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy import Uuid
from sqlalchemy.orm import relationship

from app.models.base import Base


class SessionOperation(Base):
    """A single math operation generated for a player during a game session.

    Supports two question sources:
    - "bank": question fetched from the questions table (question_id is set)
    - "generated": question created by algorithm at runtime (question_content +
      question_correct_answer stored inline; question_id is None)
    """

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

    question_index = Column(Integer, nullable=False)  # 0-based position in session
    time_limit = Column(Float, nullable=False)

    # Question source — "bank" | "generated"
    question_source = Column(String(50), nullable=False, default="bank")

    # bank source: FK to questions table (null when source="generated")
    question_id = Column(
        Uuid(as_uuid=True),
        ForeignKey("questions.id"),
        nullable=True,
        index=True,
    )

    # generated source: inline content + answer (null when source="bank")
    # TEXT: unlimited length to support multi-operation expressions with large numbers
    # BIGINT: handles answers from chained multiplications of large operands
    question_content = Column(Text, nullable=True)
    question_correct_answer = Column(BigInteger, nullable=True)

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
