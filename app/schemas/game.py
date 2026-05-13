"""Pydantic schemas for Quick Calculate game endpoints (G02_F04)."""

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel


class EndReason(str, Enum):
    """Valid reasons to end a game session."""

    MAX_ERRORS = "max_errors"
    MANUAL = "manual"


# ── SF03: Timeout Signal ─────────────────────────────────────────────────────

class TimeoutRequest(BaseModel):
    """Request body for POST /games/quick-calculate/sessions/{id}/timeout."""

    operation_id: str


# ── SF04 + SF05: Submit Answer & Evaluate ────────────────────────────────────

class SubmitAnswerRequest(BaseModel):
    """Request body for POST /games/quick-calculate/sessions/{id}/answer."""

    operation_id: str
    answer: str
    submitted_at: Optional[datetime] = None  # Client-reported timestamp (analytics only)


# ── SF07: End Session ─────────────────────────────────────────────────────────

class EndSessionRequest(BaseModel):
    """Request body for POST /games/quick-calculate/sessions/{id}/end."""

    end_reason: EndReason
