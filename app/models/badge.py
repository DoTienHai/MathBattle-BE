"""Badge and UserBadge models (G01_F02_SF03)."""

from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Index, Integer, String, UniqueConstraint
from sqlalchemy.orm import relationship

from app.models.base import BaseModel


class Badge(BaseModel):
    """Badge definition — seeded at deployment, not user-specific."""

    __tablename__ = "badges"
    __allow_unmapped__ = True

    name = Column(String(100), nullable=False, unique=True)
    description = Column(String(500), nullable=False)
    icon_url = Column(String(500), nullable=False)
    category = Column(String(50), nullable=False, default="general")

    user_badges = relationship("UserBadge", back_populates="badge", cascade="all, delete-orphan")


class UserBadge(BaseModel):
    """Junction table: which badges a user has earned."""

    __tablename__ = "user_badges"
    __allow_unmapped__ = True

    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    badge_id = Column(Integer, ForeignKey("badges.id", ondelete="CASCADE"), nullable=False, index=True)
    earned_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    user = relationship("User", back_populates="badges")
    badge = relationship("Badge", back_populates="user_badges")

    __table_args__ = (
        UniqueConstraint("user_id", "badge_id", name="uq_user_badge"),
        Index("idx_user_badges_user_id", "user_id"),
    )
