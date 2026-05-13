"""Quick Calculate game API endpoints (G02_F04, SF01–SF07)."""

import logging

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user_id
from app.database.connection import get_db
from app.schemas.game import (
    EndSessionRequest,
    SubmitAnswerRequest,
    TimeoutRequest,
)
from app.services.quick_calculate_service import (
    end_session,
    generate_next_operation,
    record_timeout,
    start_session,
    submit_answer,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/games/quick-calculate", tags=["quick-calculate"])


@router.post("/sessions", status_code=status.HTTP_201_CREATED)
async def start_game_session(
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """SF01: Start a new Quick Calculate session."""
    data = await start_session(user_id=user_id, db=db)
    return {"success": True, "data": data, "error": None}


@router.post("/sessions/{session_id}/next")
async def next_operation(
    session_id: str,
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """SF02: Generate the next operation for the session."""
    data = await generate_next_operation(session_id=session_id, user_id=user_id, db=db)
    return {"success": True, "data": data, "error": None}


@router.post("/sessions/{session_id}/timeout")
async def timeout_operation(
    session_id: str,
    body: TimeoutRequest,
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """SF03: Record a timeout for the current operation."""
    data = await record_timeout(
        session_id=session_id,
        operation_id=body.operation_id,
        user_id=user_id,
        db=db,
    )
    return {"success": True, "data": data, "error": None}


@router.post("/sessions/{session_id}/answer")
async def submit_answer_endpoint(
    session_id: str,
    body: SubmitAnswerRequest,
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """SF04 + SF05: Submit an answer and evaluate its correctness."""
    data = await submit_answer(
        session_id=session_id,
        operation_id=body.operation_id,
        answer=body.answer,
        user_id=user_id,
        client_submitted_at=body.submitted_at,
        db=db,
    )
    return {"success": True, "data": data, "error": None}


@router.post("/sessions/{session_id}/end")
async def end_game_session(
    session_id: str,
    body: EndSessionRequest,
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """SF07: End the session and compute the final score."""
    data = await end_session(
        session_id=session_id,
        user_id=user_id,
        end_reason=body.end_reason.value,
        db=db,
    )
    return {"success": True, "data": data, "error": None}
