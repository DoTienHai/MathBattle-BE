"""Question model — defines the structure for quiz questions (G02_F01)."""

import uuid
from datetime import datetime

from app.models.base import Base
from sqlalchemy import Column, DateTime, Integer, String, JSON
from sqlalchemy import Uuid

class Question(Base):
    __tablename__ = "questions"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    type = Column(String(20), nullable=False)  # math | sequence | mcq | ...

    content = Column(JSON, nullable=False)  
    correct_answer = Column(JSON, nullable=False)

    hint = Column(String(255), nullable=True)
    explanation = Column(String(255), nullable=True)
    
    difficulty_level = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    