"""Business logic for Quick Calculate game (G02_F04, SF01–SF07)."""

import uuid
import logging
from datetime import datetime, timedelta
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.game_session import GameMode, GameSession
from app.models.question import Question
from app.models.session_operation import SessionOperation
from app.models.user import UserProfile
from app.utils.difficulty_ramp import get_difficulty_params_for_count

logger = logging.getLogger(__name__)

_ANSWER_TOLERANCE_SECONDS: float = 2.0
_MAX_ERRORS_ALLOWED: int = 1  # Quick Calculate: end on first wrong answer or timeout


# ── SF01 ─────────────────────────────────────────────────────────────────────

async def start_session(user_id: int, db: AsyncSession) -> dict:
    """
    SF01: Initialize a Quick Calculate game session.

    Precondition: user_id is authenticated (provided by FastAPI dependency).

    Args:
        user_id: Authenticated user's ID.
        db: Async database session.

    Returns:
        Dict with session_id, initial_ramp_config, started_at.

    Raises:
        HTTPException 409: If the user already has an active session.
    """
    existing = await db.execute(
        select(GameSession).where(
            GameSession.user_id == user_id,
            GameSession.status == "active",
        )
    ) # Check for existing active session
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "SESSION_ALREADY_ACTIVE", "message": "You already have an active session"},
        ) # Prevent multiple concurrent sessions

    profile_result = await db.execute(
        select(UserProfile).where(UserProfile.user_id == user_id)
    )
    profile = profile_result.scalar_one_or_none()
    level_at_start = profile.current_level if profile else 1

    session = GameSession(
        user_id=user_id,
        game_mode=GameMode.QUICK_CALCULATE,
        level_player_at_start=level_at_start,
        status="active",
    )
    db.add(session)
    await db.commit()
    await db.refresh(session)

    logger.info("Session %s started for user %d", session.id, user_id)

    initial_params = get_difficulty_params_for_count(0, level_at_start)
    return {
        "session_id": str(session.id),
        "initial_ramp_config": {
            "ramp_level": initial_params["level"],
            "time_limit_per_question": initial_params["time_limit"],
            "max_questions": None,
            "max_errors_allowed": _MAX_ERRORS_ALLOWED,
        },
        "started_at": session.created_at.isoformat() + "Z",
    }


# ── SF02 ─────────────────────────────────────────────────────────────────────

async def generate_next_operation(session_id: str, user_id: int, db: AsyncSession) -> dict:
    """
    SF02: Generate the next math operation for the session.

    Creates a Question record then a SessionOperation linking it to the session.
    Difficulty is derived from the session's current correct answer count (SF06 ramp).

    Args:
        session_id: UUID string of the session.
        user_id: Authenticated user's ID.
        db: Async database session.

    Returns:
        Dict with operation_id, question_id, question_index, content, time_limit, generated_at.
        The correct_answer is stored in the questions table only — never sent to the client.
    """
    session = await _get_active_session(session_id, user_id, db)

    correct_count = await _get_correct_count(session.id, db)
    total_count = await _get_total_count(session.id, db)
    ramp = get_difficulty_params_for_count(correct_count, session.level_player_at_start)

    last_question_id = await _get_last_question_id(session.id, db)
    question = await _fetch_question_for_level(ramp["level"], last_question_id, db)

    operation = SessionOperation(
        session_id=session.id,
        user_id=user_id,
        question_id=question.id,
        question_index=total_count,
        time_limit=ramp["time_limit"],
    )
    db.add(operation)
    await db.commit()
    await db.refresh(operation)

    return {
        "operation_id": str(operation.id),
        "question_id": str(question.id),
        "question_index": total_count,
        "content": question.content,
        "time_limit": operation.time_limit,
        "generated_at": operation.created_at.isoformat() + "Z",
    }


# ── SF03 ─────────────────────────────────────────────────────────────────────

async def record_timeout(
    session_id: str, operation_id: str, user_id: int, db: AsyncSession
) -> dict:
    """
    SF03: Record a timeout for the current operation.

    Marks the operation as timed_out and auto-ends the session (max_errors_allowed=1).

    Args:
        session_id: UUID string of the session.
        operation_id: UUID string of the operation.
        user_id: Authenticated user's ID.
        db: Async database session.

    Returns:
        Dict with operation_id, timed_out, correct_answer, session_stats, session_ended.

    Raises:
        HTTPException 400: If the operation was already answered or timed out.
    """
    session = await _get_active_session(session_id, user_id, db)
    operation = await _get_operation(operation_id, session.id, db)

    if operation.timed_out or operation.user_answer is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "OPERATION_ALREADY_ANSWERED", "message": "Operation already answered or timed out"},
        )

    now = datetime.utcnow()
    operation.timed_out = True
    operation.is_correct = False
    operation.evaluated_at = now

    await db.commit()

    question = await _get_question(operation.question_id, db)
    wrong_count = await _get_wrong_count(session.id, db)
    correct_count = await _get_correct_count(session.id, db)
    current_streak = await _get_current_streak(session.id, db)

    end_reason = _check_end_conditions(wrong_count)
    if end_reason:
        await _finalize_session(session, end_reason, db)

    return {
        "operation_id": str(operation.id),
        "timed_out": True,
        "correct_answer": question.correct_answer,
        "session_stats": {
            "correct_count": correct_count,
            "wrong_count": wrong_count,
            "questions_answered": correct_count + wrong_count,
            "current_streak": current_streak,
        },
        "session_ended": end_reason is not None,
        "end_reason": end_reason,
    }


# ── SF04 + SF05 ───────────────────────────────────────────────────────────────

async def submit_answer(
    session_id: str,
    operation_id: str,
    answer: str,
    user_id: int,
    client_submitted_at: Optional[datetime],
    db: AsyncSession,
) -> dict:
    """
    SF04 + SF05: Submit an answer and evaluate its correctness in one request.

    SF04: validates format, checks time window, records user_answer.
    SF05: compares against correct_answer from the questions table, updates stats.
    SF06: ramp level is derived from the session's correct_count.

    Args:
        session_id: UUID string of the session.
        operation_id: UUID string of the operation.
        answer: Player's answer as a string (must parse to integer).
        user_id: Authenticated user's ID.
        client_submitted_at: Client-reported timestamp stored for analytics (optional).
        db: Async database session.

    Returns:
        Dict with evaluation result, updated session stats, and optional session_ended flag.

    Raises:
        HTTPException 400: Invalid format, already answered, or answer too late.
    """
    try:
        answer_int = int(answer.strip())
    except (ValueError, AttributeError):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "INVALID_ANSWER_FORMAT", "message": "Answer must be a valid integer"},
        )

    session = await _get_active_session(session_id, user_id, db)
    operation = await _get_operation(operation_id, session.id, db)

    if operation.user_answer is not None or operation.timed_out:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "OPERATION_ALREADY_ANSWERED", "message": "Operation already answered"},
        )

    now = datetime.utcnow()
    deadline = operation.created_at + timedelta(
        seconds=operation.time_limit + _ANSWER_TOLERANCE_SECONDS
    )
    if now > deadline:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "ANSWER_TOO_LATE", "message": "Answer submitted after the allowed time window"},
        )

    question = await _get_question(operation.question_id, db)

    # SF04: record submission
    operation.user_answer = answer_int
    operation.submitted_at = now
    if client_submitted_at:
        operation.client_submitted_at = client_submitted_at

    # SF05: evaluate correctness
    is_correct = (answer_int == question.correct_answer)
    operation.is_correct = is_correct
    operation.evaluated_at = now

    await db.commit()

    correct_count = await _get_correct_count(session.id, db)
    wrong_count = await _get_wrong_count(session.id, db)
    current_streak = await _get_current_streak(session.id, db)

    if is_correct:
        level = get_difficulty_params_for_count(correct_count, session.level_player_at_start)["level"]
        logger.info(
            "Session %s: correct answer — correct_count=%d level=%d",
            session.id, correct_count, level,
        )

    end_reason = _check_end_conditions(wrong_count)
    if end_reason:
        await _finalize_session(session, end_reason, db)

    return {
        "operation_id": str(operation.id),
        "received": True,
        "server_received_at": now.isoformat() + "Z",
        "is_correct": is_correct,
        "correct_answer": question.correct_answer,
        "user_answer": answer_int,
        "consecutive_correct": current_streak,
        "session_stats": {
            "correct_count": correct_count,
            "wrong_count": wrong_count,
            "questions_answered": correct_count + wrong_count,
            "current_streak": current_streak,
        },
        "session_ended": end_reason is not None,
        "end_reason": end_reason,
    }


# ── SF07 ─────────────────────────────────────────────────────────────────────

async def end_session(session_id: str, user_id: int, end_reason: str, db: AsyncSession) -> dict:
    """
    SF07: End the game session and compute the final score.

    Idempotency: already-completed sessions return HTTP 400.

    Args:
        session_id: UUID string of the session.
        user_id: Authenticated user's ID.
        end_reason: One of 'max_errors', 'manual'.
        db: Async database session.

    Returns:
        Dict with session_id, end_reason, final_score, stats, ended_at.

    Raises:
        HTTPException 404: Session not found.
        HTTPException 400: Session already completed.
    """
    try:
        sid = uuid.UUID(session_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "SESSION_NOT_FOUND", "message": "Session not found"},
        )

    result = await db.execute(
        select(GameSession).where(
            GameSession.id == sid,
            GameSession.user_id == user_id,
        )
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "SESSION_NOT_FOUND", "message": "Session not found"},
        )

    if session.status == "completed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "SESSION_ALREADY_ENDED", "message": "Session already completed"},
        )

    return await _finalize_session(session, end_reason, db)


# ── Private helpers ───────────────────────────────────────────────────────────

def _check_end_conditions(wrong_count: int) -> Optional[str]:
    """Return end_reason if the session should auto-terminate, else None."""
    if wrong_count >= _MAX_ERRORS_ALLOWED:
        return "max_errors"
    return None


async def _finalize_session(session: GameSession, end_reason: str, db: AsyncSession) -> dict:
    """Mark session as completed, compute final score and stats from session_operations."""
    now = datetime.utcnow()

    correct_count = await _get_correct_count(session.id, db)
    wrong_count = await _get_wrong_count(session.id, db)
    max_streak = await _get_max_streak(session.id, db)
    total = correct_count + wrong_count
    accuracy = round(correct_count / total * 100, 1) if total > 0 else 0.0
    duration = round((now - session.created_at).total_seconds(), 1)
    max_ramp_level = get_difficulty_params_for_count(correct_count, session.level_player_at_start)["level"]

    session.status = "completed"
    session.score = correct_count
    session.ended_at = now

    await db.commit()
    await db.refresh(session)

    logger.info("Session %s ended — reason=%s score=%d", session.id, end_reason, session.score)

    return {
        "session_id": str(session.id),
        "end_reason": end_reason,
        "final_score": session.score,
        "stats": {
            "correct_count": correct_count,
            "wrong_count": wrong_count,
            "questions_answered": total,
            "accuracy_percent": accuracy,
            "max_streak": max_streak,
            "max_ramp_level": max_ramp_level,
            "duration_seconds": duration,
        },
        "ended_at": now.isoformat() + "Z",
    }


async def _get_active_session(session_id: str, user_id: int, db: AsyncSession) -> GameSession:
    """Load and validate a session: must exist, belong to user, and be active."""
    try:
        sid = uuid.UUID(session_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "SESSION_NOT_FOUND", "message": "Session not found"},
        )

    result = await db.execute(
        select(GameSession).where(
            GameSession.id == sid,
            GameSession.user_id == user_id,
        )
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "SESSION_NOT_FOUND", "message": "Session not found"},
        )

    if session.status != "active":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "SESSION_NOT_ACTIVE", "message": "Session is not active"},
        )

    return session


async def _get_operation(
    operation_id: str, session_id: uuid.UUID, db: AsyncSession
) -> SessionOperation:
    """Load an operation and verify it belongs to the given session."""
    try:
        oid = uuid.UUID(operation_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "OPERATION_NOT_FOUND", "message": "Operation not found"},
        )

    result = await db.execute(
        select(SessionOperation).where(
            SessionOperation.id == oid,
            SessionOperation.session_id == session_id,
        )
    )
    operation = result.scalar_one_or_none()
    if not operation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "OPERATION_NOT_FOUND", "message": "Operation not found"},
        )

    return operation


async def _get_question(question_id: uuid.UUID, db: AsyncSession) -> Question:
    """Load a question by ID."""
    result = await db.execute(select(Question).where(Question.id == question_id))
    question = result.scalar_one_or_none()
    if not question:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"code": "QUESTION_NOT_FOUND", "message": "Question record missing"},
        )
    return question


async def _get_correct_count(session_id: uuid.UUID, db: AsyncSession) -> int:
    """Count correct answers in the session."""
    result = await db.execute(
        select(func.count()).where(
            SessionOperation.session_id == session_id,
            SessionOperation.is_correct == True,  # noqa: E712
        )
    )
    return result.scalar_one()


async def _get_wrong_count(session_id: uuid.UUID, db: AsyncSession) -> int:
    """Count wrong/timed-out answers in the session."""
    result = await db.execute(
        select(func.count()).where(
            SessionOperation.session_id == session_id,
            SessionOperation.is_correct == False,  # noqa: E712
        )
    )
    return result.scalar_one()


async def _get_total_count(session_id: uuid.UUID, db: AsyncSession) -> int:
    """Count all operations (answered or not) in the session."""
    result = await db.execute(
        select(func.count()).where(SessionOperation.session_id == session_id)
    )
    return result.scalar_one()


async def _get_current_streak(session_id: uuid.UUID, db: AsyncSession) -> int:
    """Count consecutive correct answers from the most recent evaluated operation."""
    result = await db.execute(
        select(SessionOperation)
        .where(
            SessionOperation.session_id == session_id,
            SessionOperation.is_correct.isnot(None),
        )
        .order_by(SessionOperation.question_index.desc())
    )
    ops = result.scalars().all()
    streak = 0
    for op in ops:
        if op.is_correct is True:
            streak += 1
        else:
            break
    return streak


async def _get_max_streak(session_id: uuid.UUID, db: AsyncSession) -> int:
    """Find the longest consecutive correct answer run in the session."""
    result = await db.execute(
        select(SessionOperation)
        .where(
            SessionOperation.session_id == session_id,
            SessionOperation.is_correct.isnot(None),
        )
        .order_by(SessionOperation.question_index.asc())
    )
    ops = result.scalars().all()
    max_s, current = 0, 0
    for op in ops:
        if op.is_correct is True:
            current += 1
            max_s = max(max_s, current)
        else:
            current = 0
    return max_s


async def _get_last_question_id(
    session_id: uuid.UUID, db: AsyncSession
) -> Optional[uuid.UUID]:
    """Return the question_id of the most recent operation (anti-repeat guard)."""
    result = await db.execute(
        select(SessionOperation.question_id)
        .where(SessionOperation.session_id == session_id)
        .order_by(SessionOperation.question_index.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


async def _fetch_question_for_level(
    level: int,
    exclude_id: Optional[uuid.UUID],
    db: AsyncSession,
) -> Question:
    """Fetch a random question at the given difficulty level, excluding the last seen."""
    stmt = select(Question).where(
        Question.type == "math",
        Question.difficulty_level == level,
    )
    if exclude_id is not None:
        stmt = stmt.where(Question.id != exclude_id)
    stmt = stmt.order_by(func.random()).limit(1)
    result = await db.execute(stmt)
    question = result.scalar_one_or_none()
    if not question:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"code": "NO_QUESTION_AVAILABLE", "message": "No question available for this difficulty level"},
        )
    return question
